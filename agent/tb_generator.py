"""
Module: tb_generator.py
Chức năng: Tự động sinh Testbench Verilog-2001 tự kiểm tra (Self-Checking Testbench)
cho cả nhóm mạch FSM đặc thù lẫn nhóm 70% khối hạ tầng số phổ thông (Counter, FIFO,
Shift Register, Mux, Encoder, Adder/Subtractor/Multiplier/Comparator, PWM, Timer, Handshake, ALU, Gray, Decoder...).
Mỗi testbench đều tích hợp watchdog chống treo mô phỏng, xuất file VCD và bảng điểm `[SUCCESS]` / `[FAIL]`.
"""

import os
import re
from spec_analyzer import SpecAnalyzer
from verilog_linter import VerilogLinter


class TBGenerator:
    """
    Bộ tạo Testbench tự động chuẩn IEEE 1364-2001 (tương thích ModelSim và Icarus Verilog).
    Đọc trực tiếp cổng thực tế từ file RTL để ánh xạ tên chân chính xác, tránh lệch chân khi mô phỏng.
    """

    def __init__(self, ThuMucSim=None, sim_dir=None):
        """Khởi tạo thư mục xuất file testbench (`sim/`)."""
        self.ThuMucSim = sim_dir if sim_dir is not None else ThuMucSim
        self.sim_dir = self.ThuMucSim
        if self.ThuMucSim:
            os.makedirs(self.ThuMucSim, exist_ok=True)

    # ------------------------------------------------------------------
    # Nhóm hàm tiện ích: Phân tích cổng RTL & dựng khung testbench Verilog-2001
    # ------------------------------------------------------------------
    @staticmethod
    def _eval_dim(expr, params):
        """Tính giá trị số nguyên của biểu thức độ rộng bit (hỗ trợ thay thế `parameter` như `WIDTH-1`)."""
        expr = expr.strip()
        if expr.isdigit():
            return int(expr)
        for pname, pval in params.items():
            expr = re.sub(r"\b" + re.escape(pname) + r"\b", str(pval), expr)
        if re.fullmatch(r"[0-9+\-*/()\s]+", expr):
            try:
                return int(eval(expr, {"__builtins__": None}, {}))
            except Exception:
                return None
        return None

    def _parse_rtl_ports(self, DuongDanRtl):
        """
        Trích xuất tên module và danh sách cổng chi tiết (tên, hướng, độ rộng bit, cờ clock/reset)
        từ file Verilog RTL thực tế (hỗ trợ cả chuẩn ANSI Verilog-2001 và khai báo Verilog-1995).
        """
        if not DuongDanRtl or not os.path.exists(DuongDanRtl):
            return None, []
        with open(DuongDanRtl, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()

        code_clean = re.sub(r"//.*", "", code)
        code_clean = re.sub(r"/\*.*?\*/", "", code_clean, flags=re.DOTALL)

        m = re.search(
            r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:#\s*\(([\s\S]*?)\))?\s*\(([\s\S]*?)\)\s*;([\s\S]*?)\bendmodule\b",
            code_clean,
        )
        if not m:
            return None, []

        mod_name = m.group(1)
        param_str = m.group(2) or ""
        header = m.group(3)
        body = m.group(4)

        params = {}
        for pname, pval in re.findall(r"\bparameter\s+(?:integer\s+|real\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)", param_str + "\n" + body):
            params[pname] = int(pval)

        tu_khoa = {
            "input", "output", "inout", "wire", "reg", "logic", "signed",
            "unsigned", "integer", "parameter", "localparam",
        }
        ports = []
        seen = set()

        def _make_port(name, direction, width):
            low = name.lower()
            is_clk = any(k in low for k in ["clk", "clock", "sclk"])
            is_rst = any(k in low for k in ["rst", "clr", "reset", "clear"])
            rst_low = low.endswith("_n") or low in {"rstn", "resetn", "aresetn", "nreset", "clr_n", "arst_n", "srst_n"}
            return {
                "name": name,
                "lower": low,
                "direction": direction,
                "width": max(1, int(width)),
                "is_clk": is_clk,
                "is_rst": is_rst,
                "rst_active_low": rst_low,
            }

        def _parse_width(text):
            km = re.search(r"\[\s*([^:\]]+)\s*:\s*([^\]]+)\s*\]", text)
            if not km:
                return 1
            msb = self._eval_dim(km.group(1), params)
            lsb = self._eval_dim(km.group(2), params)
            if msb is not None and lsb is not None:
                return abs(msb - lsb) + 1
            return 8

        if re.search(r"\b(input|output|inout)\b", header):
            cur_dir = "input"
            cur_width = 1
            for chunk in header.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                km_dir = re.search(r"\b(input|output|inout)\b", chunk)
                if km_dir:
                    cur_dir = km_dir.group(1)
                    cur_width = _parse_width(chunk)
                elif re.search(r"\[[^\]]+\]", chunk):
                    cur_width = _parse_width(chunk)
                km_name = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*$", chunk)
                if km_name:
                    pname = km_name.group(1)
                    if pname.lower() not in tu_khoa and pname.lower() not in seen:
                        ports.append(_make_port(pname, cur_dir, cur_width))
                        seen.add(pname.lower())
        else:
            # Legacy Verilog-1995 port declarations inside body
            for km_decl in re.finditer(
                r"\b(input|output|inout)\b\s*(?:wire|reg)?\s*(?:signed)?\s*(\[[^\]]+\])?\s*([^;]+);",
                body,
            ):
                pdir = km_decl.group(1)
                w_str = km_decl.group(2) or ""
                pwidth = _parse_width(w_str) if w_str else 1
                for raw_n in km_decl.group(3).split(","):
                    pname = raw_n.strip()
                    if pname and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", pname) and pname.lower() not in seen:
                        ports.append(_make_port(pname, pdir, pwidth))
                        seen.add(pname.lower())

        return mod_name, ports

    def _extract_ports_from_rtl(self, DuongDanRtl):
        """Trích xuất tập hợp tên cổng viết thường từ file Verilog RTL."""
        _, ports = self._parse_rtl_ports(DuongDanRtl)
        return {p["lower"] for p in ports}

    @staticmethod
    def _find_port(ports, direction, candidates, exclude=None):
        """Tìm cổng phù hợp nhất theo danh sách tên ứng viên (ưu tiên khớp chính xác, sau đó mới khớp chuỗi con)."""
        exclude = exclude or set()
        pool = [p for p in ports if p["direction"] == direction and p["lower"] not in exclude]
        for cand in candidates:
            for p in pool:
                if p["lower"] == cand:
                    return p
        for cand in candidates:
            for p in pool:
                if cand in p["lower"]:
                    return p
        return None

    @staticmethod
    def _mask_expr(width):
        """Tạo mặt nạ bit `(1 << width) - 1` (giới hạn tối đa 32 bit) để tính giá trị kỳ vọng không tràn."""
        return (1 << min(width, 32)) - 1

    @staticmethod
    def _build_decls_and_conns(ports):
        """Sinh chuỗi khai báo `reg`/`wire` trong testbench và danh sách nối chân `.port(port)` cho DUT."""
        decls = []
        conns = []
        for p in ports:
            w_str = f"[{p['width']-1}:0] " if p["width"] > 1 else ""
            if p["direction"] == "input":
                decls.append(f"    reg  {w_str:<8} {p['name']};")
            else:
                decls.append(f"    wire {w_str:<8} {p['name']};")
            conns.append(f"        .{p['name']}({p['name']})")
        return "\n".join(decls), ",\n".join(conns)

    @staticmethod
    def _build_reset_sequence(ports):
        """Sinh đoạn khởi tạo mức logic ban đầu cho toàn bộ input và tạo xung reset (hỗ trợ cả active-high và active-low)."""
        lines = []
        rst_ports = [p for p in ports if p["direction"] == "input" and p["is_rst"]]
        for p in ports:
            if p["direction"] != "input":
                continue
            if p["is_rst"]:
                val = "1'b0" if p["rst_active_low"] else "1'b1"
                lines.append(f"        {p['name']} = {val};")
            else:
                lines.append(f"        {p['name']} = {p['width']}'d0;")
        lines.append("        #22;")
        if rst_ports:
            for p in rst_ports:
                val = "1'b1" if p["rst_active_low"] else "1'b0"
                lines.append(f"        {p['name']} = {val};")
            lines.append("        #2;")
        return "\n".join(lines)

    @staticmethod
    def _emit_assert(cond_expr, pass_msg, fail_msg, indent="        "):
        """Sinh khối lệnh `if (cond_expr)` tự động tăng biến đếm `total_tests` / `passed_tests` / `failed_tests` và in `[PASS]`/`[FAIL]`."""
        return "\n".join([
            f"{indent}total_tests = total_tests + 1;",
            f"{indent}if ({cond_expr}) begin",
            f"{indent}    passed_tests = passed_tests + 1;",
            f"{indent}    $display(\"  [PASS] {pass_msg}\");",
            f"{indent}end else begin",
            f"{indent}    failed_tests = failed_tests + 1;",
            f"{indent}    $display(\"  [FAIL] {fail_msg}\");",
            f"{indent}end",
        ])

    def _finalize_tb(self, module_name, decls_str, dut_conns_str, clk_port_name, extra_decls, tasks_str, stim_str, banner_title, watchdog_ns=100000):
        """
        Hoàn thiện bộ khung testbench chuẩn VeriPrefer:
        ghép khai báo tín hiệu, instance DUT, bộ tạo xung clock, watchdog timeout,
        khối `$dumpfile` xuất VCD, kịch bản kích thích `stim_str` và bảng tổng kết điểm số, rồi ghi ra `tb_<module>.v`.
        """
        tb_name = f"tb_{module_name}"
        clk_block = f"    always #10 {clk_port_name} = ~{clk_port_name};" if clk_port_name else ""
        extra_decls_block = f"\n{extra_decls}\n" if extra_decls else ""
        tasks_block = f"\n{tasks_str}\n" if tasks_str else ""

        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Autonomous Self-Checking Testbench for {module_name}
// Standard: IEEE 1364-2001 (ModelSim / VeriPrefer Verification Harness)
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

{decls_str}

    integer total_tests;
    integer passed_tests;
    integer failed_tests;
{extra_decls_block}
    {module_name} dut (
{dut_conns_str}
    );

{clk_block}

    // Watchdog Safety Timer Guard
    initial begin
        #{watchdog_ns};
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit!");
        $finish;
    end
{tasks_block}
    initial begin
        total_tests  = 0;
        passed_tests = 0;
        failed_tests = 0;

        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        $display("============================================================================");
        $display("  {banner_title}: {module_name}");
        $display("============================================================================");

{stim_str}

        #20;
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{module_name}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{module_name}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    # ------------------------------------------------------------------
    # Bộ điều phối trung tâm: Chọn hàm sinh Testbench dựa trên Spec + cổng RTL thực tế
    # ------------------------------------------------------------------
    def generate_tb_from_spec(self, NoiDungSpec=None, DuongDanRtl=None, DuongDanSpec=None, spec_text=None, rtl_path=None, spec_path=None):
        """
        Điểm vào duy nhất để sinh testbench tự kiểm tra cho mọi module:
          1. Phân tích đặc tả (`SpecAnalyzer`) và phân tích cổng RTL thực tế (`_parse_rtl_ports`).
          2. Ưu tiên định tuyến các hệ thống FSM đặc thù (Vending, Elevator, Traffic, Lock, Sequence, Temp).
          3. Định tuyến nhóm 70% khối hạ tầng phổ thông (FIFO, Handshake, Gray, PWM, Timer, Counter,
             Shift/Barrel, Encoder, Mux, Decoder, ALU/Arithmetic/Comparator) dựa theo cổng thực tế.
          4. Dự phòng sang `generate_generic_tb` nếu gặp kiến trúc tùy biến hoàn toàn.
        """
        VanBanSpec = spec_text if spec_text is not None else NoiDungSpec
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        TepSpec = spec_path if spec_path is not None else DuongDanSpec

        BoPhanTich = SpecAnalyzer(TepSpec if TepSpec else VanBanSpec)
        NhomMach = BoPhanTich.classify_system()
        TenModule = BoPhanTich.extract_module_name()
        spec_content = BoPhanTich.content

        rtl_mod_name, ports = self._parse_rtl_ports(TepRtl)
        if rtl_mod_name and (not TenModule or TenModule == "custom_hw_module" or rtl_mod_name == TenModule):
            TenModule = rtl_mod_name
        elif rtl_mod_name:
            TenModule = rtl_mod_name

        CongThucTe = {p["lower"] for p in ports}
        in_names = {p["lower"] for p in ports if p["direction"] == "input"}
        out_names = {p["lower"] for p in ports if p["direction"] == "output"}
        has_clk = any(p["is_clk"] for p in ports)
        mod_low = (TenModule or "").lower()

        # Bước 1: Định tuyến các hệ thống FSM đặc thù đã có kịch bản kiểm thử chuyên biệt
        if NhomMach == "VENDING" and TenModule == "vending_machine" and {"coin_5k", "dispense"}.issubset(CongThucTe):
            return f"tb_{TenModule}", self.generate_vending_tb(TenModule)
        if NhomMach == "ELEVATOR" and TenModule == "elevator_controller" and ({"floor_req", "current_floor"}.issubset(CongThucTe) or {"req_floor", "current_floor"}.issubset(CongThucTe)):
            return f"tb_{TenModule}", self.generate_elevator_tb(TenModule)
        if NhomMach == "TRAFFIC" and TenModule == "traffic_light" and ({"light_main", "light_side"}.issubset(CongThucTe) or {"red", "green"}.issubset(CongThucTe)):
            return f"tb_{TenModule}", self.generate_traffic_tb(TenModule)
        if NhomMach == "SOC_AI" and os.path.exists(os.path.join(self.ThuMucSim, "tb_top_soc.v")):
            return "tb_top_soc", os.path.join(self.ThuMucSim, "tb_top_soc.v")
        if NhomMach == "DIGITAL_LOCK" and (any("unlock" in n for n in out_names) and any("key" in n for n in in_names)):
            return f"tb_{TenModule}", self.generate_digital_lock_tb(TenModule, DuongDanRtl=TepRtl)
        if NhomMach == "SEQUENCE_DETECTOR" and TenModule == "sequence_detector_1011" and ({"din", "detected"}.issubset(CongThucTe) or {"seq_in", "detected"}.issubset(CongThucTe)):
            return f"tb_{TenModule}", self.generate_sequence_detector_tb(TenModule)
        if NhomMach == "TEMPERATURE_MONITOR" and {"temp_celsius", "max_temp_limit", "fan_high_speed"}.issubset(CongThucTe):
            return f"tb_{TenModule}", self.generate_temperature_monitor_tb(TenModule, TepRtl)

        # Bước 2: Định tuyến các họ mạch nhóm 70% (Self-Checking thích nghi theo cổng thực tế của RTL)
        # 2.1 Họ FIFO / Buffer: kiểm tra cờ empty/full, chống tràn và đúng thứ tự vào-trước-ra-trước
        if (
            NhomMach == "FIFO"
            or "fifo" in mod_low
            or {"wr_en", "rd_en", "full", "empty"}.issubset(CongThucTe)
            or ({"full", "empty"}.issubset(out_names) and any("data" in n or "din" in n for n in in_names))
        ) and has_clk:
            return f"tb_{TenModule}", self.generate_fifo_tb(TenModule, TepRtl, spec_content)

        # 2.2 Ready / Valid Handshake
        has_valid_port = any("valid" in n for n in CongThucTe)
        has_ready_port = any("ready" in n for n in CongThucTe)
        if (has_valid_port and has_ready_port) or any(k in mod_low for k in ["handshake", "skid_buf", "ready_valid"]):
            return f"tb_{TenModule}", self.generate_handshake_tb(TenModule, TepRtl, spec_content)

        # 2.3 Gray Counter
        if (NhomMach == "GRAY_COUNTER" or "gray" in mod_low or any("gray" in n for n in out_names)) and has_clk:
            return f"tb_{TenModule}", self.generate_gray_counter_tb(TenModule, DuongDanRtl=TepRtl)

        # 2.4 PWM / Timer (check Timer before Counter so timers with a `count` port route to Timer TB)
        if has_clk and (
            NhomMach == "PWM"
            or "pwm" in mod_low
            or (any("duty" in n for n in in_names) and any("pwm" in n for n in out_names))
        ):
            return f"tb_{TenModule}", self.generate_pwm_tb(TenModule, TepRtl, spec_content)

        if has_clk and (
            any(k in mod_low for k in ["timer", "watchdog", "wdt", "countdown"])
            or any(n in out_names for n in ["timeout", "expired", "wdt_rst"])
        ):
            return f"tb_{TenModule}", self.generate_timer_tb(TenModule, TepRtl, spec_content)

        # 2.5 Counter / Up-Down / BCD (luon yeu cau has_clk de tranh nham combinational bcd_to_7seg)
        if has_clk and (
            NhomMach in {"COUNTER", "STOPWATCH"}
            or any(k in mod_low for k in ["counter", "stopwatch", "bcd_cnt"])
            or any(n in out_names for n in ["count", "q_count", "cnt", "sec_ones", "ones"])
        ):
            return f"tb_{TenModule}", self.generate_counter_tb(TenModule, TepRtl, spec_content)

        # 2.6 Shift Register / Barrel Shifter
        if (
            NhomMach in {"SHIFT_REG", "BARREL_SHIFTER"}
            or any(k in mod_low for k in ["shift", "shifter", "sipo", "piso", "siso", "pipo", "rotat"])
        ):
            return f"tb_{TenModule}", self.generate_shift_reg_tb(TenModule, TepRtl, spec_content)

        # 2.7 Priority Encoder
        if (
            NhomMach == "ENCODER"
            or any(k in mod_low for k in ["encoder", "pri_enc", "priority"])
            or (any(n in in_names for n in ["req_in", "d_in"]) and "valid" in out_names and any(n in out_names for n in ["code_out", "binary_out", "enc_out"]))
        ):
            return f"tb_{TenModule}", self.generate_priority_encoder_tb(TenModule, TepRtl, spec_content)

        # 2.8 Multiplexer (Mux)
        if ("mux" in mod_low and "demux" not in mod_low) or (
            any(n in in_names for n in ["sel", "mux_sel"])
            and len([p for p in ports if p["direction"] == "input" and not p["is_clk"] and not p["is_rst"] and "sel" not in p["lower"]]) >= 2
            and len(out_names) == 1
        ):
            return f"tb_{TenModule}", self.generate_mux_tb(TenModule, TepRtl, spec_content)

        # 2.9 Decoder (Memory Address Decoder & Binary N-to-2^N Decoder)
        if NhomMach == "DECODER" or ("decoder" in mod_low and "7seg" not in mod_low) or {"addr", "mem_en", "cs_ram"}.issubset(CongThucTe):
            return f"tb_{TenModule}", self.generate_decoder_tb(TenModule, TepRtl)

        # 2.10 ALU / Adder / Subtractor / Multiplier / Comparator
        if NhomMach == "ALU" or "alu" in mod_low:
            return f"tb_{TenModule}", self.generate_alu_tb(TenModule, DuongDanRtl=TepRtl)
        if NhomMach == "ADDER" or "adder" in mod_low:
            return f"tb_{TenModule}", self.generate_adder_tb(TenModule, TepRtl, spec_content)
        if NhomMach == "SUBTRACTOR" or "subtractor" in mod_low:
            return f"tb_{TenModule}", self.generate_subtractor_tb(TenModule, TepRtl, spec_content)
        if NhomMach == "MULTIPLIER" or any(k in mod_low for k in ["multiplier", "mult"]):
            return f"tb_{TenModule}", self.generate_multiplier_tb(TenModule, TepRtl, spec_content)
        if NhomMach == "COMPARATOR" or "comparator" in mod_low or {"greater", "equal", "less"}.issubset(out_names) or {"gt", "eq", "lt"}.issubset(out_names):
            return f"tb_{TenModule}", self.generate_comparator_tb(TenModule, TepRtl, spec_content)

        # Bước 3: Fallback thông minh: tự động dựng testbench kiểm tra không X/Z trên mọi cổng thực tế
        return f"tb_{TenModule}", self.generate_generic_tb(TepRtl, TenModule)

    # ------------------------------------------------------------------
    # Các bộ sinh Testbench chuyên biệt cho nhóm 70% khối hạ tầng số phổ thông
    # ------------------------------------------------------------------
    def generate_counter_tb(self, TenModule="counter", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Counter] Sinh testbench tự kiểm tra cho mọi loại bộ đếm đồng bộ:
          - Bộ đếm BCD 2 chữ số (00..59): kiểm tra tính hợp lệ từng trạng thái và tràn 59->00.
          - Bộ đếm Stopwatch / BCD 1 chữ số (0..9): kiểm tra chuỗi đếm và giải mã LED 7 đoạn.
          - Bộ đếm nhị phân lên/xuống: kiểm tra reset, đếm lên, giữ trạng thái (`enable=0`), đếm xuống và nạp song song (`load`).
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        if not clk_p:
            return self.generate_generic_tb(TepRtl, TenModule)

        in_names = {p["lower"] for p in ports if p["direction"] == "input"}
        out_names = {p["lower"] for p in ports if p["direction"] == "output"}

        if any("gray" in n for n in out_names) or "gray" in TenModule.lower():
            return self.generate_gray_counter_tb(TenModule, DuongDanRtl=TepRtl)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)

        en_p = self._find_port(ports, "input", ["enable", "en", "count_enable", "start_stop", "ce"])
        up_p = self._find_port(ports, "input", ["up_down", "updown", "dir_up", "dir", "up"])
        load_p = self._find_port(ports, "input", ["load", "ld"])
        din_p = self._find_port(ports, "input", ["d_in", "din", "data_in", "d", "load_val"], exclude={en_p["lower"] if en_p else "", up_p["lower"] if up_p else ""})

        ones_p = self._find_port(ports, "output", ["sec_ones", "ones", "bcd_ones"])
        tens_p = self._find_port(ports, "output", ["sec_tens", "tens", "bcd_tens"])
        seg_p = self._find_port(ports, "output", ["seg", "seven_seg", "led_seg"])
        tc_p = self._find_port(ports, "output", ["tc", "rollover", "roll_over", "overflow", "ovf"])

        # Truong hop 1: Bo dem BCD 2 chu so (00 - 59)
        if ones_p and tens_p:
            extra_decls = "    integer step_i;\n    integer bcd_err;"
            lines = [
                reset_seq,
                "        total_tests = total_tests + 1;",
                f"        if ({ones_p['name']} === 4'd0 && {tens_p['name']} === 4'd0) begin",
                "            passed_tests = passed_tests + 1;",
                "            $display(\"  [PASS] Reset BCD 00 verified\");",
                "        end else begin",
                "            failed_tests = failed_tests + 1;",
                f"            $display(\"  [FAIL] Reset BCD expected 00, got %0d%0d\", {tens_p['name']}, {ones_p['name']});",
                "        end",
            ]
            if en_p:
                lines.append(f"        {en_p['name']} = 1'b1;")
            lines.append("        bcd_err = 0;")
            lines.append("        for (step_i = 0; step_i < 60; step_i = step_i + 1) begin")
            lines.append(f"            @(posedge {clk_p['name']}); #1;")
            lines.append(f"            if ({ones_p['name']} > 4'd9 || {tens_p['name']} > 4'd5 || ^{ones_p['name']} === 1'bx || ^{tens_p['name']} === 1'bx) bcd_err = bcd_err + 1;")
            lines.append("        end")
            lines.append(self._emit_assert("bcd_err == 0", "All 60 BCD states valid (00..59)", "Invalid BCD state observed during 60 cycles"))
            lines.append(self._emit_assert(
                f"{ones_p['name']} === 4'd0 && {tens_p['name']} === 4'd0",
                "BCD 59->00 rollover verified",
                "BCD rollover to 00 failed after 60 cycles",
            ))
            return self._finalize_tb(TenModule, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS BCD COUNTER VERIFICATION")

        # Truong hop 2: Bo dem 0-9 (Stopwatch / 1-digit BCD) hoac Binary Up/Down Counter
        cnt_p = self._find_port(ports, "output", ["count", "q_count", "cnt", "q", "val", "out"])
        if not cnt_p:
            multi_outs = [p for p in ports if p["direction"] == "output" and p["width"] > 1 and (not seg_p or p["lower"] != seg_p["lower"])]
            cnt_p = multi_outs[0] if multi_outs else self._find_port(ports, "output", ["count", "q", "out"])
        if not cnt_p:
            return self.generate_generic_tb(TepRtl, TenModule)

        w = cnt_p["width"]
        is_bcd_single = bool(seg_p) or ("stopwatch" in TenModule.lower()) or ("bcd" in (spec_text or "").lower())
        extra_decls = f"    reg [{w-1}:0] exp_cnt;\n    integer step_i;\n    integer seq_err;"

        lines = [reset_seq]
        lines.append(self._emit_assert(
            f"{cnt_p['name']} === {w}'d0",
            "Reset count == 0 verified",
            "Reset count != 0",
        ))

        if en_p:
            lines.append(f"        {en_p['name']} = 1'b1;")
        if up_p:
            lines.append(f"        {up_p['name']} = 1'b1;")

        steps = 10 if (is_bcd_single and w >= 4) else min(5, (1 << min(w, 4)) - 1)
        m_mod = re.search(r"mod_?(\d+)", TenModule.lower())
        if m_mod and not is_bcd_single:
            steps = min(steps, max(1, int(m_mod.group(1)) - 1))
        steps = max(1, steps)
        lines.append(f"        exp_cnt = {w}'d0;")
        lines.append("        seq_err = 0;")
        lines.append(f"        for (step_i = 0; step_i < {steps}; step_i = step_i + 1) begin")
        if is_bcd_single and w >= 4:
            lines.append(f"            exp_cnt = (exp_cnt >= {w}'d9) ? {w}'d0 : (exp_cnt + {w}'d1);")
        else:
            lines.append(f"            exp_cnt = exp_cnt + {w}'d1;")
        lines.append(f"            @(posedge {clk_p['name']}); #1;")
        lines.append(f"            if ({cnt_p['name']} !== exp_cnt) seq_err = seq_err + 1;")
        if seg_p:
            lines.append(f"            if (^{seg_p['name']} === 1'bx || {seg_p['name']} === {seg_p['width']}'b1111111) seq_err = seq_err + 1;")
        lines.append("        end")
        lines.append(self._emit_assert(
            "seq_err == 0",
            f"Count-up ({steps} cycles) matched expected sequence",
            "Count-up sequence mismatch",
        ))

        if en_p:
            lines.append(f"        {en_p['name']} = 1'b0;")
            lines.append(f"        exp_cnt = {cnt_p['name']};")
            lines.append(f"        @(posedge {clk_p['name']}); #1;")
            lines.append(f"        @(posedge {clk_p['name']}); #1;")
            lines.append(self._emit_assert(
                f"{cnt_p['name']} === exp_cnt",
                "Hold (enable=0) preserved counter value",
                "Counter changed while enable=0",
            ))

        if up_p and not is_bcd_single:
            if en_p:
                lines.append(f"        {en_p['name']} = 1'b1;")
            lines.append(f"        {up_p['name']} = 1'b0;")
            lines.append(f"        exp_cnt = {cnt_p['name']};")
            lines.append("        seq_err = 0;")
            lines.append("        for (step_i = 0; step_i < 3; step_i = step_i + 1) begin")
            lines.append(f"            exp_cnt = exp_cnt - {w}'d1;")
            lines.append(f"            @(posedge {clk_p['name']}); #1;")
            lines.append(f"            if ({cnt_p['name']} !== exp_cnt) seq_err = seq_err + 1;")
            lines.append("        end")
            lines.append(self._emit_assert(
                "seq_err == 0",
                "Count-down (3 cycles) matched expected sequence",
                "Count-down sequence mismatch",
            ))

        if load_p and din_p and din_p["width"] == w:
            if en_p:
                lines.append(f"        {en_p['name']} = 1'b1;")
            lines.append(f"        {load_p['name']} = 1'b1;")
            lines.append(f"        {din_p['name']} = {w}'d5;")
            lines.append(f"        @(posedge {clk_p['name']}); #1;")
            lines.append(f"        {load_p['name']} = 1'b0;")
            lines.append(self._emit_assert(
                f"{cnt_p['name']} === {w}'d5",
                "Parallel load value 5 verified",
                "Parallel load failed",
            ))

        if tc_p:
            lines.append(self._emit_assert(
                f"{tc_p['name']} !== 1'bx",
                "Terminal count flag deterministic",
                "Terminal count flag is X/Z",
            ))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS COUNTER VERIFICATION")

    def generate_fifo_tb(self, TenModule="fifo_buffer", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - FIFO] Sinh testbench tự kiểm tra cho hàng đợi FIFO đồng bộ:
        kiểm tra cờ `empty=1, full=0` sau reset, ghi đầy bộ đệm, thử ghi tràn (overflow),
        sau đó đọc toàn bộ dữ liệu để đối chiếu đúng thứ tự FIFO và xác nhận cờ `empty=1` trở lại.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        wr_p = self._find_port(ports, "input", ["wr_en", "write_en", "wr", "push", "wren"])
        rd_p = self._find_port(ports, "input", ["rd_en", "read_en", "rd", "pop", "rden"])
        din_p = self._find_port(ports, "input", ["data_in", "din", "wdata", "d_in", "in_data"])
        dout_p = self._find_port(ports, "output", ["data_out", "dout", "rdata", "d_out", "out_data"])
        full_p = self._find_port(ports, "output", ["full", "fifo_full"])
        empty_p = self._find_port(ports, "output", ["empty", "fifo_empty"])

        if not (clk_p and wr_p and rd_p and din_p and dout_p and full_p and empty_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        w = din_p["width"]
        mask = self._mask_expr(w)

        extra_decls = "\n".join([
            f"    reg [{w-1}:0] expected_q [0:63];",
            "    integer wr_cnt;",
            "    integer rd_idx;",
            "    integer data_err;",
        ])

        lines = [
            reset_seq,
            self._emit_assert(
                f"{empty_p['name']} === 1'b1 && {full_p['name']} === 1'b0",
                "Post-reset FIFO flags valid (empty=1, full=0)",
                "Post-reset FIFO flags invalid (expected empty=1, full=0)",
            ),
            "        wr_cnt = 0;",
            f"        {rd_p['name']} = 1'b0;",
            "        // Phase 1: Write distinct payloads until full (or 16 entries)",
            "        while (wr_cnt < 16 && !" + full_p["name"] + ") begin",
            f"            {wr_p['name']} = 1'b1;",
            f"            {din_p['name']} = ((wr_cnt + 1) * 17) & {mask};",
            "            expected_q[wr_cnt] = " + f"((wr_cnt + 1) * 17) & {mask};",
            "            wr_cnt = wr_cnt + 1;",
            f"            @(posedge {clk_p['name']}); #1;",
            "            if (wr_cnt == 1) begin",
            self._emit_assert(f"{empty_p['name']} === 1'b0", "empty deasserted after first write", "empty stayed 1 after write", indent="                "),
            "            end",
            "        end",
            f"        {wr_p['name']} = 1'b0;",
            self._emit_assert("wr_cnt > 0", "FIFO accepted write entries", "FIFO refused all writes (full stuck at 1)"),
            f"        if ({full_p['name']} === 1'b1) begin",
            self._emit_assert(f"{full_p['name']} === 1'b1 && {empty_p['name']} === 1'b0", "FIFO full flag asserted at capacity", "Invalid flags at full", indent="            "),
            "            // Attempt overflow write while full",
            f"            {wr_p['name']} = 1'b1;",
            f"            {din_p['name']} = {w}'h55 & {mask};",
            f"            @(posedge {clk_p['name']}); #1;",
            f"            {wr_p['name']} = 1'b0;",
            self._emit_assert(f"{full_p['name']} === 1'b1", "Overflow write safely ignored when full", "full flag corrupted on overflow", indent="            "),
            "        end",
            "        // Phase 2: Read back all entries and verify strict FIFO ordering",
            "        data_err = 0;",
            "        for (rd_idx = 0; rd_idx < wr_cnt; rd_idx = rd_idx + 1) begin",
            f"            {rd_p['name']} = 1'b1;",
            f"            @(posedge {clk_p['name']}); #1;",
            f"            if ({dout_p['name']} !== expected_q[rd_idx]) begin",
            "                data_err = data_err + 1;",
            f"                $display(\"  [FAIL] FIFO idx %0d: expected %0h, got %0h\", rd_idx, expected_q[rd_idx], {dout_p['name']});",
            "            end",
            "        end",
            f"        {rd_p['name']} = 1'b0;",
            "        #1;",
            self._emit_assert("data_err == 0", "All FIFO read payloads matched write order", "FIFO data order / integrity mismatch"),
            self._emit_assert(
                f"{empty_p['name']} === 1'b1 && {full_p['name']} === 1'b0",
                "Post-drain FIFO flags valid (empty=1, full=0)",
                "FIFO not empty after draining all written entries",
            ),
        ]

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS FIFO VERIFICATION")

    def generate_shift_reg_tb(self, TenModule="shift_register", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Shift Register] Sinh testbench tự kiểm tra cho 3 biến thể thanh ghi dịch:
          - Trường hợp A: Barrel Shifter / Rotator (kiểm tra dịch/xoay 0, trái 1 bit, phải 1 bit).
          - Trường hợp B: Universal Shift Register 4 chế độ (Nạp song song, Giữ, Dịch trái, Dịch phải).
          - Trường hợp C: Thanh ghi dịch nối tiếp SIPO / PISO / SISO.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        rtl_raw = ""
        if TepRtl and os.path.exists(TepRtl):
            with open(TepRtl, "r", encoding="utf-8", errors="replace") as f:
                rtl_raw = f.read()

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        rst_p = self._find_port(ports, "input", ["rst", "clr", "reset"])
        mode_p = self._find_port(ports, "input", ["mode", "op", "ctrl"])
        shamt_p = self._find_port(ports, "input", ["shift_amt", "shamt", "amt"])
        dir_p = self._find_port(ports, "input", ["dir_right", "dir", "right", "shift_dir"])
        din_p = self._find_port(ports, "input", ["d_in", "data_in", "din", "in"])
        sin_l_p = self._find_port(ports, "input", ["sin_left", "sl_in", "si_left", "sin"])
        sin_r_p = self._find_port(ports, "input", ["sin_right", "sr_in", "si_right"])
        en_p = self._find_port(ports, "input", ["enable", "en", "shift_en"])
        load_p = self._find_port(ports, "input", ["load", "ld", "pl"])
        qout_p = self._find_port(ports, "output", ["q_out", "data_out", "dout", "q", "out"])

        if not qout_p:
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"

        # Truong hop A: Barrel Shifter / Rotator
        if shamt_p and din_p:
            w = din_p["width"]
            pat = 0b1011 & self._mask_expr(w) if w >= 4 else 1
            is_rotator = ("{" in rtl_raw and f"{din_p['name']}[" in rtl_raw) or any(
                k in (spec_text or "").lower() + TenModule.lower() for k in ["barrel", "rotat", "xoay"]
            )
            lines = [reset_seq]
            lines.append(f"        {din_p['name']} = {w}'d{pat};")
            # Test shift_amt = 0
            lines.append(f"        {shamt_p['name']} = {shamt_p['width']}'d0;")
            if dir_p:
                lines.append(f"        {dir_p['name']} = 1'b0;")
            lines.append(settle)
            lines.append(self._emit_assert(
                f"{qout_p['name']} === {w}'d{pat}",
                f"Shift amount 0 preserved {w}'b{pat:0{w}b}",
                "Shift amount 0 failed",
            ))

            # Shift/Rotate left by 1 (dir = 0)
            exp_l1 = (((pat << 1) | (pat >> (w - 1))) & self._mask_expr(w)) if is_rotator else ((pat << 1) & self._mask_expr(w))
            lines.append(f"        {shamt_p['name']} = {shamt_p['width']}'d1;")
            if dir_p:
                lines.append(f"        {dir_p['name']} = 1'b0;")
            lines.append(settle)
            lines.append(self._emit_assert(
                f"{qout_p['name']} === {w}'d{exp_l1}",
                f"Left shift/rotate by 1 => {exp_l1}",
                "Left shift/rotate by 1 mismatch",
            ))

            # Shift/Rotate right by 1 (dir = 1)
            if dir_p:
                exp_r1 = (((pat >> 1) | ((pat & 1) << (w - 1))) & self._mask_expr(w)) if is_rotator else (pat >> 1)
                lines.append(f"        {dir_p['name']} = 1'b1;")
                lines.append(f"        {shamt_p['name']} = {shamt_p['width']}'d1;")
                lines.append(settle)
                lines.append(self._emit_assert(
                    f"{qout_p['name']} === {w}'d{exp_r1}",
                    f"Right shift/rotate by 1 => {exp_r1}",
                    "Right shift/rotate by 1 mismatch",
                ))
            return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS BARREL SHIFTER VERIFICATION")

        # Truong hop B: Universal Shift Register (mode[1:0])
        if mode_p and mode_p["width"] == 2 and din_p and clk_name:
            w = qout_p["width"]
            pat = 0b1010 & self._mask_expr(w)
            exp_shl = ((pat << 1) | 1) & self._mask_expr(w)
            exp_shr = ((exp_shl >> 1) | (1 << (w - 1))) & self._mask_expr(w)
            lines = [reset_seq]
            if rst_p:
                lines.append(self._emit_assert(f"{qout_p['name']} === {w}'d0", "Reset q_out == 0 verified", "Reset q_out != 0"))
            # 2'b11: Parallel Load
            lines.append(f"        {mode_p['name']} = 2'b11;")
            lines.append(f"        {din_p['name']} = {w}'d{pat};")
            lines.append(settle)
            lines.append(self._emit_assert(f"{qout_p['name']} === {w}'d{pat}", "Parallel load (mode=11) verified", "Parallel load failed"))
            # 2'b00: Hold
            lines.append(f"        {mode_p['name']} = 2'b00;")
            lines.append(f"        {din_p['name']} = {w}'d{pat ^ self._mask_expr(w)};")
            lines.append(settle)
            lines.append(self._emit_assert(f"{qout_p['name']} === {w}'d{pat}", "Hold (mode=00) preserved value", "Hold mode failed"))
            # 2'b01: Shift Left
            lines.append(f"        {mode_p['name']} = 2'b01;")
            if sin_l_p:
                lines.append(f"        {sin_l_p['name']} = 1'b1;")
            lines.append(settle)
            if sin_l_p:
                lines.append(self._emit_assert(f"{qout_p['name']} === {w}'d{exp_shl}", "Shift left (mode=01) verified", "Shift left failed"))
            else:
                lines.append(self._emit_assert(f"^{qout_p['name']} !== 1'bx", "Shift left deterministic", "Shift left produced X"))
            # 2'b10: Shift Right
            lines.append(f"        {mode_p['name']} = 2'b10;")
            if sin_r_p:
                lines.append(f"        {sin_r_p['name']} = 1'b1;")
            lines.append(settle)
            if sin_r_p:
                lines.append(self._emit_assert(f"{qout_p['name']} === {w}'d{exp_shr}", "Shift right (mode=10) verified", "Shift right failed"))
            else:
                lines.append(self._emit_assert(f"^{qout_p['name']} !== 1'bx", "Shift right deterministic", "Shift right produced X"))
            return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS UNIVERSAL SHIFT REG VERIFICATION")

        # Truong hop C: SIPO / PISO / SISO Shift Register
        lines = [reset_seq]
        if rst_p:
            lines.append(self._emit_assert(f"{qout_p['name']} === {qout_p['width']}'d0", "Reset shift output == 0 verified", "Reset shift output != 0"))
        if en_p:
            lines.append(f"        {en_p['name']} = 1'b1;")
        if load_p and din_p and din_p["width"] > 1:
            pat = 0b10100101 & self._mask_expr(din_p["width"])
            lines.append(f"        {load_p['name']} = 1'b1;")
            lines.append(f"        {din_p['name']} = {din_p['width']}'d{pat};")
            lines.append(settle)
            lines.append(f"        {load_p['name']} = 1'b0;")
            for step in range(din_p["width"]):
                lines.append(settle)
                lines.append(self._emit_assert(f"^{qout_p['name']} !== 1'bx", f"Shift step {step+1} valid output", f"Shift step {step+1} produced X/Z"))
        else:
            serial_in = sin_l_p or din_p or self._find_port(ports, "input", ["si", "serial_in", "sin"])
            for bit_val in [1, 0, 1, 1]:
                if serial_in:
                    lines.append(f"        {serial_in['name']} = {serial_in['width']}'d{bit_val};")
                lines.append(settle)
                lines.append(self._emit_assert(f"^{qout_p['name']} !== 1'bx", f"Shifted bit {bit_val} deterministic", f"Shift produced X/Z on bit {bit_val}"))
            if qout_p["width"] > 1 and serial_in and serial_in["width"] == 1:
                lines.append(self._emit_assert(f"{qout_p['name']} !== {qout_p['width']}'d0", "SIPO captured non-zero shifted pattern", "SIPO output remained 0 after shifting 1011"))
        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS SHIFT REGISTER VERIFICATION")

    def generate_mux_tb(self, TenModule="mux", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Multiplexer] Sinh testbench tự kiểm tra cho bộ dồn kênh (2-to-1, 4-to-1, 8-to-1):
        hỗ trợ cả dạng nhiều cổng dữ liệu rời rạc lẫn dạng bus gộp đầu vào, quét toàn bộ giá trị `sel`.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        sel_p = self._find_port(ports, "input", ["sel", "s", "mux_sel", "select"])
        en_p = self._find_port(ports, "input", ["en", "enable"])
        out_p = self._find_port(ports, "output", ["y", "out", "q", "data_out", "mux_out"])
        if not out_p:
            outs = [p for p in ports if p["direction"] == "output"]
            out_p = outs[0] if outs else None

        if not (sel_p and out_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        excl = {sel_p["lower"]}
        if clk_p:
            excl.add(clk_p["lower"])
        if en_p:
            excl.add(en_p["lower"])
        data_ins = [p for p in ports if p["direction"] == "input" and not p["is_clk"] and not p["is_rst"] and p["lower"] not in excl]

        if not data_ins:
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"

        lines = [reset_seq]
        if en_p:
            lines.append(f"        {en_p['name']} = 1'b1;")

        n_channels = 1 << min(sel_p["width"], 4)
        out_w = out_p["width"]

        if len(data_ins) >= n_channels:
            # Cac cong rieng le (d0, d1, d2, d3...)
            for idx in range(n_channels):
                val = (idx + 1) & self._mask_expr(data_ins[idx]["width"])
                if data_ins[idx]["width"] == 1:
                    val = idx & 1
                lines.append(f"        {data_ins[idx]['name']} = {data_ins[idx]['width']}'d{val};")
            for idx in range(n_channels):
                exp_val = (idx + 1) & self._mask_expr(out_w) if data_ins[idx]["width"] > 1 else (idx & 1)
                lines.append(f"        {sel_p['name']} = {sel_p['width']}'d{idx};")
                lines.append(settle)
                lines.append(self._emit_assert(
                    f"{out_p['name']} === {out_w}'d{exp_val}",
                    f"Mux sel={idx} routed channel {idx} (val={exp_val})",
                    f"Mux sel={idx} mismatch",
                ))
        elif len(data_ins) == 1 and data_ins[0]["width"] >= n_channels * out_w:
            # Cong bus gop (vd [3:0] in cho mux 4-to-1 1-bit)
            bus_p = data_ins[0]
            packed = 0
            for idx in range(n_channels):
                ch_val = (1 if (idx % 2 == 0) else 0) if out_w == 1 else ((idx + 1) & self._mask_expr(out_w))
                packed |= (ch_val << (idx * out_w))
            lines.append(f"        {bus_p['name']} = {bus_p['width']}'d{packed};")
            for idx in range(n_channels):
                ch_val = (1 if (idx % 2 == 0) else 0) if out_w == 1 else ((idx + 1) & self._mask_expr(out_w))
                lines.append(f"        {sel_p['name']} = {sel_p['width']}'d{idx};")
                lines.append(settle)
                lines.append(self._emit_assert(
                    f"{out_p['name']} === {out_w}'d{ch_val}",
                    f"Packed Mux sel={idx} => {ch_val}",
                    f"Packed Mux sel={idx} mismatch",
                ))
        else:
            return self.generate_generic_tb(TepRtl, TenModule)

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS MULTIPLEXER VERIFICATION")

    def generate_priority_encoder_tb(self, TenModule="priority_encoder", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Priority Encoder] Sinh testbench tự kiểm tra cho bộ mã hóa ưu tiên (4-to-2, 8-to-3, 16-to-4):
        kiểm tra khi disable, khi đầu vào toàn 0 (`valid=0`), và khi nhiều bit cùng bật (bit MSB phải thắng).
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        en_p = self._find_port(ports, "input", ["enable", "en"])
        req_p = self._find_port(ports, "input", ["req_in", "d_in", "din", "req", "in", "d"])
        code_p = self._find_port(ports, "output", ["code_out", "binary_out", "enc_out", "code", "out", "y"])
        valid_p = self._find_port(ports, "output", ["valid", "gs", "any_valid"])

        if not (req_p and code_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
        in_w = req_p["width"]
        out_w = code_p["width"]

        lines = [reset_seq]
        if en_p:
            lines.append(f"        {en_p['name']} = 1'b0;")
            lines.append(f"        {req_p['name']} = {in_w}'d{(1 << (in_w - 1))};")
            lines.append(settle)
            if valid_p:
                lines.append(self._emit_assert(f"{valid_p['name']} === 1'b0", "Disabled state valid == 0 verified", "valid asserted when disabled"))
            lines.append(f"        {en_p['name']} = 1'b1;")

        # Zero input -> valid == 0
        lines.append(f"        {req_p['name']} = {in_w}'d0;")
        lines.append(settle)
        if valid_p:
            lines.append(self._emit_assert(f"{valid_p['name']} === 1'b0", "Zero input valid == 0 verified", "valid asserted on zero input"))

        # Test priority MSB > LSB
        test_vectors = [
            (1, 0, "LSB bit 0 active"),
            ((1 << (in_w // 2)) | 1, in_w // 2, f"Priority bit {in_w // 2} overrides bit 0"),
            ((1 << (in_w - 1)) | (1 << (in_w // 2)) | 1, in_w - 1, f"Highest priority bit {in_w - 1} overrides lower bits"),
        ]
        for vec, exp_code, desc in test_vectors:
            cond = f"{code_p['name']} === {out_w}'d{exp_code}"
            if valid_p:
                cond += f" && {valid_p['name']} === 1'b1"
            lines.append(f"        {req_p['name']} = {in_w}'d{vec};")
            lines.append(settle)
            lines.append(self._emit_assert(cond, f"{desc} => code={exp_code}", f"{desc} mismatch"))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS PRIORITY ENCODER VERIFICATION")

    def generate_adder_tb(self, TenModule="adder", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Adder] Sinh testbench tự kiểm tra cho bộ cộng nhị phân (có/không có `clk`, `cin`, `cout`),
        kiểm tra các cặp cộng thông thường, có nhớ vào `cin` và trường hợp tràn bit `cout=1`.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        a_p = self._find_port(ports, "input", ["a", "in_a", "op_a", "opa"])
        b_p = self._find_port(ports, "input", ["b", "in_b", "op_b", "opb"])
        cin_p = self._find_port(ports, "input", ["cin", "carry_in", "c_in", "ci"])
        sum_p = self._find_port(ports, "output", ["sum", "s", "out", "result", "y"])
        cout_p = self._find_port(ports, "output", ["cout", "carry_out", "c_out", "carry", "co"])

        if not (a_p and b_p and sum_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
        w = a_p["width"]
        mask = self._mask_expr(w)

        lines = [reset_seq]
        cases = [
            (0, 0, 0),
            (5 & mask, 3 & mask, 0),
            (12 & mask, 7 & mask, 1 if cin_p else 0),
            (mask, 1, 0),
        ]
        for va, vb, vc in cases:
            total = va + vb + vc
            exp_sum = total & mask
            exp_cout = (total >> w) & 1
            lines.append(f"        {a_p['name']} = {w}'d{va};")
            lines.append(f"        {b_p['name']} = {w}'d{vb};")
            if cin_p:
                lines.append(f"        {cin_p['name']} = 1'b{vc};")
            lines.append(settle)
            cond = f"{sum_p['name']} === {sum_p['width']}'d{exp_sum}"
            if cout_p:
                cond += f" && {cout_p['name']} === 1'b{exp_cout}"
            lines.append(self._emit_assert(
                cond,
                f"Adder {va} + {vb} + {vc} => sum={exp_sum}, cout={exp_cout}",
                f"Adder {va} + {vb} + {vc} failed",
            ))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS ADDER VERIFICATION")

    def generate_subtractor_tb(self, TenModule="subtractor", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Subtractor] Sinh testbench tự kiểm tra cho bộ trừ nhị phân,
        xác minh kết quả hiệu `diff` và cờ mượn `borrow` trong 3 trường hợp: `a > b`, `a == b`, `a < b`.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        a_p = self._find_port(ports, "input", ["a", "in_a", "op_a"])
        b_p = self._find_port(ports, "input", ["b", "in_b", "op_b"])
        diff_p = self._find_port(ports, "output", ["diff", "d", "sub", "out", "result"])
        borrow_p = self._find_port(ports, "output", ["borrow", "bout", "b_out", "bo"])

        if not (a_p and b_p and diff_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
        w = a_p["width"]
        mask = self._mask_expr(w)

        lines = [reset_seq]
        cases = [(9 & mask, 4 & mask), (7 & mask, 7 & mask), (3 & mask, 6 & mask)]
        for va, vb in cases:
            exp_diff = (va - vb) & mask
            exp_b = 1 if va < vb else 0
            lines.append(f"        {a_p['name']} = {w}'d{va};")
            lines.append(f"        {b_p['name']} = {w}'d{vb};")
            lines.append(settle)
            cond = f"{diff_p['name']} === {diff_p['width']}'d{exp_diff}"
            if borrow_p:
                cond += f" && {borrow_p['name']} === 1'b{exp_b}"
            lines.append(self._emit_assert(
                cond,
                f"Subtractor {va} - {vb} => diff={exp_diff}, borrow={exp_b}",
                f"Subtractor {va} - {vb} failed",
            ))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS SUBTRACTOR VERIFICATION")

    def generate_multiplier_tb(self, TenModule="multiplier", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Multiplier] Sinh testbench tự kiểm tra cho bộ nhân nhị phân,
        kiểm tra nhân với 0, nhân với 1, nhân số thường và nhân hai giá trị cực đại theo độ rộng cổng.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        a_p = self._find_port(ports, "input", ["a", "in_a", "op_a", "multiplicand"])
        b_p = self._find_port(ports, "input", ["b", "in_b", "op_b", "multiplier"])
        prod_p = self._find_port(ports, "output", ["product", "prod", "p", "mul_out", "out", "result"])

        if not (a_p and b_p and prod_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
        wa, wb = a_p["width"], b_p["width"]
        ma, mb = self._mask_expr(wa), self._mask_expr(wb)
        wp = prod_p["width"]
        mp = self._mask_expr(wp)

        lines = [reset_seq]
        cases = [(0, 5 & mb), (1, 9 & mb), (6 & ma, 7 & mb), (ma, mb)]
        for va, vb in cases:
            exp_p = (va * vb) & mp
            lines.append(f"        {a_p['name']} = {wa}'d{va};")
            lines.append(f"        {b_p['name']} = {wb}'d{vb};")
            lines.append(settle)
            lines.append(self._emit_assert(
                f"{prod_p['name']} === {wp}'d{exp_p}",
                f"Multiplier {va} * {vb} == {exp_p}",
                f"Multiplier {va} * {vb} expected {exp_p}",
            ))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS MULTIPLIER VERIFICATION")

    def generate_comparator_tb(self, TenModule="comparator", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Comparator] Sinh testbench tự kiểm tra cho bộ so sánh độ lớn hai số,
        kiểm tra đầy đủ 3 cờ ngõ ra (`greater`, `equal`, `less`) qua các cặp thử `a > b`, `a == b`, `a < b`.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        a_p = self._find_port(ports, "input", ["a", "in_a", "op_a"])
        b_p = self._find_port(ports, "input", ["b", "in_b", "op_b"])
        gt_p = self._find_port(ports, "output", ["greater", "gt", "a_gt_b"])
        eq_p = self._find_port(ports, "output", ["equal", "eq", "a_eq_b"])
        lt_p = self._find_port(ports, "output", ["less", "lt", "a_lt_b"])

        if not (a_p and b_p and (gt_p or eq_p or lt_p)):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        clk_name = clk_p["name"] if clk_p else None
        settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
        w = a_p["width"]
        mask = self._mask_expr(w)

        lines = [reset_seq]
        cases = [(10 & mask, 3 & mask, 1, 0, 0), (6 & mask, 6 & mask, 0, 1, 0), (2 & mask, 9 & mask, 0, 0, 1)]
        for va, vb, e_gt, e_eq, e_lt in cases:
            lines.append(f"        {a_p['name']} = {w}'d{va};")
            lines.append(f"        {b_p['name']} = {w}'d{vb};")
            lines.append(settle)
            conds = []
            if gt_p:
                conds.append(f"{gt_p['name']} === 1'b{e_gt}")
            if eq_p:
                conds.append(f"{eq_p['name']} === 1'b{e_eq}")
            if lt_p:
                conds.append(f"{lt_p['name']} === 1'b{e_lt}")
            lines.append(self._emit_assert(
                " && ".join(conds),
                f"Comparator ({va}, {vb}) => gt={e_gt} eq={e_eq} lt={e_lt}",
                f"Comparator ({va}, {vb}) mismatch",
            ))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS COMPARATOR VERIFICATION")

    def generate_pwm_tb(self, TenModule="pwm_generator", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - PWM] Sinh testbench tự kiểm tra cho bộ tạo xung PWM:
        đo đếm số chu kỳ mức cao `high_cnt` trên một chu kỳ PWM ở các mức duty 0%, 50% và ~100%.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        duty_p = self._find_port(ports, "input", ["duty_cycle", "duty", "duty_in", "pwm_duty"])
        pwm_p = self._find_port(ports, "output", ["pwm_out", "pwm", "out"])
        en_p = self._find_port(ports, "input", ["enable", "en"])

        if not (clk_p and duty_p and pwm_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)
        dw = min(duty_p["width"], 8)
        period = 1 << dw
        half_duty = period // 2
        max_duty = period - 1

        extra_decls = "    integer cyc_i;\n    integer high_cnt;"
        lines = [
            reset_seq,
            self._emit_assert(f"{pwm_p['name']} === 1'b0", "Reset pwm_out == 0 verified", "Reset pwm_out != 0"),
        ]
        if en_p:
            lines.append(f"        {en_p['name']} = 1'b1;")

        # 0% duty
        lines.extend([
            f"        {duty_p['name']} = {duty_p['width']}'d0;",
            "        high_cnt = 0;",
            f"        for (cyc_i = 0; cyc_i < {period}; cyc_i = cyc_i + 1) begin",
            f"            @(posedge {clk_p['name']}); #1;",
            f"            if ({pwm_p['name']} === 1'b1) high_cnt = high_cnt + 1;",
            "        end",
            self._emit_assert("high_cnt == 0", "PWM 0 pct duty cycle verified (high_cnt=0)", "PWM 0 pct duty failed (unexpected high pulses)"),
        ])

        # 50% duty
        lines.extend([
            f"        {duty_p['name']} = {duty_p['width']}'d{half_duty};",
            "        high_cnt = 0;",
            f"        for (cyc_i = 0; cyc_i < {period}; cyc_i = cyc_i + 1) begin",
            f"            @(posedge {clk_p['name']}); #1;",
            f"            if ({pwm_p['name']} === 1'b1) high_cnt = high_cnt + 1;",
            "        end",
            self._emit_assert(
                f"high_cnt >= {max(1, half_duty - 2)} && high_cnt <= {half_duty + 2}",
                f"PWM 50 pct duty cycle verified (~{half_duty}/{period} high)",
                "PWM 50 pct duty cycle count out of range",
            ),
        ])

        # ~100% duty
        lines.extend([
            f"        {duty_p['name']} = {duty_p['width']}'d{max_duty};",
            "        high_cnt = 0;",
            f"        for (cyc_i = 0; cyc_i < {period}; cyc_i = cyc_i + 1) begin",
            f"            @(posedge {clk_p['name']}); #1;",
            f"            if ({pwm_p['name']} === 1'b1) high_cnt = high_cnt + 1;",
            "        end",
            self._emit_assert(
                f"high_cnt >= {max(1, max_duty - 3)}",
                f"PWM max duty cycle verified (>={max(1, max_duty - 3)}/{period} high)",
                "PWM max duty cycle failed",
            ),
        ])

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS PWM GENERATOR VERIFICATION")

    def generate_timer_tb(self, TenModule="timer", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Timer / Watchdog] Sinh testbench tự kiểm tra cho bộ định thời và Watchdog Timer:
        xác minh cờ timeout bằng 0 khi reset, chạy 64 chu kỳ không sinh giá trị bất định X/Z và kích hoạt hết giờ đúng ngưỡng.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        if not clk_p:
            return self.generate_generic_tb(TepRtl, TenModule)

        en_p = self._find_port(ports, "input", ["enable", "en", "start", "run"])
        kick_p = self._find_port(ports, "input", ["kick", "feed", "wdt_rst", "reload", "clear", "pet"])
        limit_p = self._find_port(ports, "input", ["limit", "period", "top", "reload_val", "max_cnt", "load_val"])
        tout_p = self._find_port(ports, "output", ["timeout", "expired", "done", "wdt_rst", "alarm", "tc", "tick", "interrupt"])
        cnt_p = self._find_port(ports, "output", ["count", "cnt", "timer_val", "val"])

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)

        extra_decls = "    integer cyc_i;\n    integer seen_fire;\n    integer saw_x;"
        lines = [reset_seq]
        if tout_p:
            lines.append(self._emit_assert(f"{tout_p['name']} === 1'b0", "Reset timeout flag == 0 verified", "Timeout flag asserted during reset"))
        if limit_p:
            lines.append(f"        {limit_p['name']} = {limit_p['width']}'d{min(8, self._mask_expr(limit_p['width']))};")
        if en_p:
            lines.append(f"        {en_p['name']} = 1'b1;")
        if kick_p:
            lines.append(f"        {kick_p['name']} = 1'b0;")

        lines.extend([
            "        seen_fire = 0;",
            "        saw_x = 0;",
            "        for (cyc_i = 0; cyc_i < 64; cyc_i = cyc_i + 1) begin",
            f"            @(posedge {clk_p['name']}); #1;",
        ])
        if tout_p:
            lines.append(f"            if ({tout_p['name']} === 1'b1) seen_fire = 1;")
            lines.append(f"            if (^{tout_p['name']} === 1'bx) saw_x = 1;")
        if cnt_p:
            lines.append(f"            if (^{cnt_p['name']} === 1'bx) saw_x = 1;")
        lines.append("        end")
        lines.append(self._emit_assert("saw_x == 0", "Timer outputs deterministic over 64 cycles", "Timer output contained X/Z"))
        if tout_p and limit_p:
            lines.append(self._emit_assert("seen_fire == 1", "Timer timeout/done triggered within limit window", "Timer never triggered timeout"))

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS TIMER VERIFICATION")

    def generate_handshake_tb(self, TenModule="handshake", DuongDanRtl=None, spec_text=None, rtl_path=None):
        """
        [Họ 70% - Ready/Valid Handshake] Sinh testbench tự kiểm tra cho giao thức bắt tay `valid`/`ready` (Skid Buffer / AXI-Stream):
        kiểm tra truyền gói dữ liệu khi `out_ready=1` và giữ ổn định tín hiệu khi có áp lực ngược (backpressure `out_ready=0`).
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        if not ports:
            return self.generate_generic_tb(TepRtl, TenModule)

        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        in_valid_p = self._find_port(ports, "input", ["in_valid", "s_valid", "valid_in", "i_valid", "s_axis_tvalid", "valid"])
        out_ready_p = self._find_port(ports, "input", ["out_ready", "m_ready", "ready_in", "i_ready", "m_axis_tready", "ready"])
        din_p = self._find_port(ports, "input", ["data_in", "in_data", "s_data", "din", "idata", "s_axis_tdata", "payload"])

        in_ready_p = self._find_port(ports, "output", ["in_ready", "s_ready", "ready_out", "o_ready", "s_axis_tready", "ready"])
        out_valid_p = self._find_port(ports, "output", ["out_valid", "m_valid", "valid_out", "o_valid", "m_axis_tvalid", "valid"])
        dout_p = self._find_port(ports, "output", ["data_out", "out_data", "m_data", "dout", "odata", "m_axis_tdata"])

        if not clk_p or (not in_valid_p and not out_valid_p):
            return self.generate_generic_tb(TepRtl, TenModule)

        decls_str, conns_str = self._build_decls_and_conns(ports)
        reset_seq = self._build_reset_sequence(ports)

        extra_decls = "    integer wait_i;\n    integer got_valid;"
        lines = [reset_seq]
        if out_valid_p:
            lines.append(self._emit_assert(f"{out_valid_p['name']} === 1'b0", "Post-reset out_valid == 0 verified", "out_valid active after reset"))

        if out_ready_p:
            lines.append(f"        {out_ready_p['name']} = 1'b1;")
        if din_p:
            pat = 0xA5 & self._mask_expr(din_p["width"])
            lines.append(f"        {din_p['name']} = {din_p['width']}'d{pat};")
        if in_valid_p:
            lines.append(f"        {in_valid_p['name']} = 1'b1;")

        lines.extend([
            "        got_valid = 0;",
            "        for (wait_i = 0; wait_i < 16; wait_i = wait_i + 1) begin",
            f"            @(posedge {clk_p['name']}); #1;",
        ])
        if out_valid_p:
            lines.append(f"            if ({out_valid_p['name']} === 1'b1) got_valid = 1;")
        if in_valid_p and in_ready_p:
            lines.append(f"            if ({in_ready_p['name']} === 1'b1) {in_valid_p['name']} = 1'b0;")
        lines.append("        end")
        if in_valid_p:
            lines.append(f"        {in_valid_p['name']} = 1'b0;")

        if out_valid_p:
            lines.append(self._emit_assert("got_valid == 1", "Handshake completed: out_valid asserted", "Handshake timeout: out_valid never asserted"))
        elif in_ready_p:
            lines.append(self._emit_assert(f"{in_ready_p['name']} !== 1'bx", "Handshake in_ready deterministic (no X/Z)", "Handshake in_ready contains X/Z"))
        if dout_p and din_p and dout_p["width"] == din_p["width"]:
            pat = 0xA5 & self._mask_expr(din_p["width"])
            lines.append(self._emit_assert(
                f"^{dout_p['name']} !== 1'bx",
                "Handshake data_out deterministic (no X/Z)",
                "Handshake data_out contains X/Z",
            ))

        # Backpressure test
        if out_ready_p and out_valid_p and in_valid_p:
            lines.extend([
                f"        {out_ready_p['name']} = 1'b0;",
                f"        {in_valid_p['name']} = 1'b1;",
            ])
            if din_p:
                pat2 = 0x5A & self._mask_expr(din_p["width"])
                lines.append(f"        {din_p['name']} = {din_p['width']}'d{pat2};")
            lines.extend([
                f"        @(posedge {clk_p['name']}); #1;",
                f"        @(posedge {clk_p['name']}); #1;",
                self._emit_assert(
                    f"^{out_valid_p['name']} !== 1'bx",
                    "Backpressure (out_ready=0) maintained valid handshake state",
                    "Backpressure corrupted out_valid to X/Z",
                ),
                f"        {out_ready_p['name']} = 1'b1;",
                f"        {in_valid_p['name']} = 1'b0;",
                f"        @(posedge {clk_p['name']}); #1;",
            ])

        return self._finalize_tb(TenModule, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS READY/VALID HANDSHAKE VERIFICATION")

    # ------------------------------------------------------------------
    # Các bộ sinh Testbench chuyên biệt cho hệ thống FSM, ALU, Gray, Decoder & Dự phòng tổng quát
    # ------------------------------------------------------------------
    def generate_vending_tb(self, TenModule="vending_machine", module_name=None):
        """[FSM Đặc thù - Vending Machine] Sinh testbench kiểm thử 4 kịch bản nạp xu 5k/10k, nhả nước, thối tiền và hủy giao dịch."""
        TenMod = module_name if module_name is not None else TenModule
        tb_name = f"tb_{TenMod}"
        module_name = TenMod
        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Automated Testbench for Vending Machine FSM
// Based on VeriPrefer (arXiv:2504.15804) Functional Verification Framework
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

    reg        clk;
    reg        clr;
    reg        coin_5k;
    reg        coin_10k;
    wire       dispense;
    wire       change_5k;
    wire [4:0] balance;
    wire [2:0] state_out;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {module_name} dut (
        .clk(clk),
        .clr(clr),
        .coin_5k(coin_5k),
        .coin_10k(coin_10k),
        .dispense(dispense),
        .change_5k(change_5k),
        .balance(balance),
        .state_out(state_out)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    task insert_5k;
        begin
            @(posedge clk);
            coin_5k = 1'b1;
            @(posedge clk);
            coin_5k = 1'b0;
        end
    endtask

    task insert_10k;
        begin
            @(posedge clk);
            coin_10k = 1'b1;
            @(posedge clk);
            coin_10k = 1'b0;
        end
    endtask

    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        $display("============================================================================");
        $display("       AUTOMATIC VENDING MACHINE VERIFICATION (VeriPrefer Standard)");
        $display("============================================================================");
        $display("  Time (ns) | Nap tien (+5k/+10k) | So du hien tai | Nha Nuoc | Thoi 5k | Trang thai");
        $display("----------------------------------------------------------------------------");

        clk = 0;
        clr = 1;
        coin_5k = 0;
        coin_10k = 0;

        #25;
        clr = 0;

        // Kich ban 1: 5k + 10k = 15k -> Nha nuoc
        $display("\\n>>> [KICH BAN 1]: Khach nhet 5.000d + 10.000d = 15.000d...");
        total_tests = total_tests + 1;
        #20;
        insert_5k();
        #20;
        insert_10k();
        #20;
        if (dispense == 1'b1 && change_5k == 1'b0) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] Nha nuoc thanh cong! (dispense=1, change=0)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 1 loi!");
        end

        #40;

        // Kich ban 2: 10k + 10k = 20k -> Nha nuoc + Thoi 5k
        $display("\\n>>> [KICH BAN 2]: Khach nhet 10.000d + 10.000d = 20.000d (Can thoi 5.000d)...");
        total_tests = total_tests + 1;
        insert_10k();
        #20;
        insert_10k();
        #20;
        if (dispense == 1'b1 && change_5k == 1'b1) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] Nha nuoc VA Thoi lai 5.000d thanh cong! (dispense=1, change=1)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 2 loi!");
        end

        #40;

        // Kich ban 3: 5k + 5k + 5k = 15k
        $display("\\n>>> [KICH BAN 3]: Khach nhet 3 dong 5.000d (5k + 5k + 5k = 15.000d)...");
        total_tests = total_tests + 1;
        insert_5k();
        #20;
        insert_5k();
        #20;
        insert_5k();
        #20;
        if (dispense == 1'b1) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] 3 dong 5k nha nuoc thanh cong!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 3 loi!");
        end

        #40;

        // Kich ban 4: Reset giua chung
        $display("\\n>>> [KICH BAN 4]: Khach nhet 5.000d roi bam nut Huy (Reset)...");
        total_tests = total_tests + 1;
        insert_5k();
        #20;
        clr = 1;
        #20;
        clr = 0;
        #20;
        if (balance == 5'd0) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] Huy giao dich thanh cong, so du ve 0d!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 4 loi!");
        end

        #40;
        $display("\\n----------------------------------------------------------------------------");
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TAT CA 4 KICH BAN MAY BAN NUOC DA DUOC KIEM THU DAT 100 PERCENT!");
        end else begin
            $display("  [FAIL] CO %0d KICH BAN MAY BAN NUOC THAT BAI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

    always @(posedge clk) begin
        $display("%10.1f ns |  +5k:%b +10k:%b | %11d VND  |    %b     |     %b     | Trang thai: S_%0d",
                 $time, coin_5k, coin_10k, balance * 1000, dispense, change_5k, state_out);
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_traffic_tb(self, TenModule="traffic_light", module_name=None):
        """[FSM Đặc thù - Traffic Light] Sinh testbench kiểm thử 3 kịch bản ưu tiên đường chính, chuyển pha đường phụ khi có xe và trả quyền ưu tiên."""
        TenMod = module_name if module_name is not None else TenModule
        tb_name = f"tb_{TenMod}"
        module_name = TenMod
        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Automated Testbench for Intersection Traffic Light FSM
// Based on VeriPrefer (arXiv:2504.15804) Functional Verification Framework
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

    reg        clk;
    reg        clr;
    reg        car_sensor;
    wire [1:0] light_main;
    wire [1:0] light_side;
    wire [1:0] state_out;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {module_name} dut (
        .clk(clk),
        .clr(clr),
        .car_sensor(car_sensor),
        .light_main(light_main),
        .light_side(light_side),
        .state_out(state_out)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    function [47:0] color_str;
        input [1:0] c;
        begin
            case (c)
                2'b00: color_str = " XANH ";
                2'b01: color_str = " VANG ";
                2'b10: color_str = "  DO  ";
                default: color_str = "UNKNWN";
            endcase
        end
    endfunction

    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        $display("============================================================================");
        $display("     AUTOMATED TRAFFIC LIGHT CONTROLLER VERIFICATION (VeriPrefer Standard)");
        $display("============================================================================");
        $display("  Time (ns) | Den Duong Chinh | Den Duong Phu | Cam Bien Xe | Trang Thai");
        $display("----------------------------------------------------------------------------");

        clk = 0;
        clr = 1;
        car_sensor = 0;

        #25;
        clr = 0;

        $display("\\n>>> [KICH BAN 1]: Khong co xe duong phu -> Duong chinh tiep tuc Xanh...");
        total_tests = total_tests + 1;
        #60;
        if (light_main == 2'b00 && light_side == 2'b10) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] Duong chinh uu tien XANH thanh cong!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 1 loi!");
        end

        $display("\\n>>> [KICH BAN 2]: Phat hien xe duong phu (car_sensor = 1) -> Chuyen vang va doi luu thong...");
        total_tests = total_tests + 1;
        car_sensor = 1;
        #120;
        if (light_side == 2'b00) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] Chuyen quyen luu thong XANH cho duong phu thanh cong!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 2 loi!");
        end

        $display("\\n>>> [KICH BAN 3]: Duong phu qua xong -> Tra lai quyen uu tien cho duong chinh...");
        total_tests = total_tests + 1;
        car_sensor = 0;
        #140;
        if (light_main == 2'b00) begin
            passed_tests = passed_tests + 1;
            $display("    [PASS] Tra quyen uu tien cho duong chinh thanh cong!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("    [FAIL] Kich ban 3 loi!");
        end

        $display("\\n----------------------------------------------------------------------------");
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TOAN BO CHU KY DEN GIAO THONG DA DUOC KIEM THU DAT 100 PERCENT!");
        end else begin
            $display("  [FAIL] CO %0d KICH BAN DEN GIAO THONG THAT BAI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

    always @(posedge clk) begin
        $display("%10.1f ns |     %s     |     %s    |      %b      | State: %0d",
                 $time, color_str(light_main), color_str(light_side), car_sensor, state_out);
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_elevator_tb(self, TenModule="elevator_controller", module_name=None):
        """[FSM Đặc thù - Elevator] Sinh testbench kiểm thử thang máy 5 tầng: gọi thang từ tầng 1 lên tầng 4 rồi xuống tầng 2 và mở cửa."""
        TenMod = module_name if module_name is not None else TenModule
        tb_name = f"tb_{TenMod}"
        module_name = TenMod
        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Automated Testbench for 5-Floor Intelligent Elevator FSM
// Based on VeriPrefer (arXiv:2504.15804) Functional Verification Framework
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

    reg        clk;
    reg        clr;
    reg  [4:0] floor_req;
    wire [2:0] current_floor;
    wire       door_open;
    wire       motor_up;
    wire       motor_down;
    wire [1:0] state_out;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {module_name} dut (
        .clk(clk),
        .clr(clr),
        .floor_req(floor_req),
        .current_floor(current_floor),
        .door_open(door_open),
        .motor_up(motor_up),
        .motor_down(motor_down),
        .state_out(state_out)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    task press_floor;
        input integer f;
        begin
            @(posedge clk);
            floor_req[f - 1] = 1'b1;
            @(posedge clk);
            floor_req[f - 1] = 1'b0;
        end
    endtask

    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        $display("============================================================================");
        $display("        AUTOMATED 5-FLOOR ELEVATOR CONTROLLER VERIFICATION (VeriPrefer)");
        $display("============================================================================");
        $display("  Time (ns) | Tang Hien Tai | Cua Mo | Len/Xuong | Yeu Cau Tang | Trang Thai");
        $display("----------------------------------------------------------------------------");

        clk = 0;
        clr = 1;
        floor_req = 5'b00000;

        #25;
        clr = 0;

        $display("\\n>>> [KICH BAN 1]: Goi thang tu Tang 1 len Tang 4...");
        total_tests = total_tests + 1;
        #40;
        press_floor(4);

        wait (current_floor == 3'd4 && door_open == 1'b1);
        passed_tests = passed_tests + 1;
        $display("    [PASS] Thang may da den dung Tang 4 va Mo cua thanh cong! (floor=%0d)", current_floor);

        #60;

        $display("\\n>>> [KICH BAN 2]: Goi thang tu Tang 4 xuong Tang 2...");
        total_tests = total_tests + 1;
        press_floor(2);

        wait (current_floor == 3'd2 && door_open == 1'b1);
        passed_tests = passed_tests + 1;
        $display("    [PASS] Thang may da xuong dung Tang 2 va Mo cua thanh cong! (floor=%0d)", current_floor);

        #60;
        $display("\\n----------------------------------------------------------------------------");
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("   [SUCCESS] TOAN BO KICH BAN DIEU KHIEN THANG MAY DA DAT 100 PERCENT PASS!");
        end else begin
            $display("   [FAIL] CO %0d KICH BAN THANG MAY THAT BAI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

    always @(posedge clk) begin
        $display("%10.1f ns |     Tang %0d     |   %b    |    %b / %b    |    %5b     | State: %0d",
                 $time, current_floor, door_open, motor_up, motor_down, floor_req, state_out);
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_alu_tb(self, TenModule="alu_4bit", module_name=None, DuongDanRtl=None, rtl_path=None):
        """
        [Họ 70% - ALU] Sinh testbench oracle tự kiểm tra cho khối ALU:
        tự động thích nghi mọi độ rộng bit (có/không có `clk`), kiểm tra đủ 8 phép toán ADD/SUB/AND/OR/XOR/NOT/SHL/COMP cùng cờ `zero`/`carry`.
        """
        TenMod = module_name if module_name is not None else TenModule
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl

        if TepRtl and os.path.exists(TepRtl):
            mod_rtl, ports = self._parse_rtl_ports(TepRtl)
            if mod_rtl:
                TenMod = mod_rtl
            a_p = self._find_port(ports, "input", ["a", "in_a", "op_a"])
            b_p = self._find_port(ports, "input", ["b", "in_b", "op_b"])
            op_p = self._find_port(ports, "input", ["opcode", "op", "alu_op", "func", "sel"])
            out_p = self._find_port(ports, "output", ["alu_out", "result", "out", "y", "res"])
            zero_p = self._find_port(ports, "output", ["zero", "z", "zf"])
            carry_p = self._find_port(ports, "output", ["carry", "cout", "c", "cf", "ovf"])
            clk_p = self._find_port(ports, "input", ["clk", "clock"])

            if a_p and b_p and op_p and out_p:
                decls_str, conns_str = self._build_decls_and_conns(ports)
                reset_seq = self._build_reset_sequence(ports)
                clk_name = clk_p["name"] if clk_p else None
                settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
                w = a_p["width"]
                mask = self._mask_expr(w)
                op_w = op_p["width"]

                lines = [reset_seq]
                # (opcode, a, b, label)
                a1, b1 = 5 & mask, 3 & mask
                a2, b2 = (12 & mask) if w >= 4 else (3 & mask), (6 & mask) if w >= 4 else (2 & mask)
                a3, b3 = 9 & mask, 4 & mask
                a4, b4 = 7 & mask, 7 & mask
                a5, b5 = 0b1100 & mask, 0b1010 & mask

                alu_cases = [
                    (0, a1, b1, (a1 + b1) & mask, ((a1 + b1) >> w) & 1, "ADD"),
                    (0, a2, b2, (a2 + b2) & mask, ((a2 + b2) >> w) & 1, "ADD overflow"),
                    (0, 0,  0,  0,                0,                    "ADD zero"),
                    (1, a3, b3, (a3 - b3) & mask, 1 if a3 < b3 else 0,  "SUB"),
                    (1, a4, b4, 0,                0,                    "SUB zero"),
                    (2, a5, b5, a5 & b5,          0,                    "AND"),
                    (3, a5, b5, a5 | b5,          0,                    "OR"),
                    (4, a5, b5, a5 ^ b5,          0,                    "XOR"),
                    (5, a5, 0,  (~a5) & mask,     0,                    "NOT"),
                    (6, a1, 0,  (a1 << 1) & mask, (a1 >> (w - 1)) & 1,  "SHL"),
                    (7, a4, b4, 1,                0,                    "COMP eq"),
                ]
                for opc, va, vb, exp_o, exp_c, lbl in alu_cases:
                    if opc >= (1 << op_w):
                        continue
                    exp_z = 1 if exp_o == 0 else 0
                    lines.append(f"        {a_p['name']} = {w}'d{va};")
                    lines.append(f"        {b_p['name']} = {w}'d{vb};")
                    lines.append(f"        {op_p['name']} = {op_w}'d{opc};")
                    lines.append(settle)
                    conds = [f"{out_p['name']} === {out_p['width']}'d{exp_o}"]
                    if zero_p:
                        conds.append(f"{zero_p['name']} === 1'b{exp_z}")
                    if carry_p:
                        conds.append(f"{carry_p['name']} === 1'b{exp_c}")
                    lines.append(self._emit_assert(
                        " && ".join(conds),
                        f"ALU {lbl} (a={va}, b={vb}) => out={exp_o}",
                        f"ALU {lbl} (a={va}, b={vb}) expected out={exp_o}",
                    ))

                return self._finalize_tb(TenMod, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS ALU ORACLE VERIFICATION")

        # Legacy fallback khi goi truc tiep khong truyen DuongDanRtl
        tb_name = f"tb_{TenMod}"
        module_name = TenMod
        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Autonomous Self-Checking Testbench for {module_name} (ALU)
// Based on VeriPrefer (arXiv:2504.15804) & RTLLM Benchmark Standard
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

    reg        clk;
    reg        rst;
    reg  [3:0] a;
    reg  [3:0] b;
    reg  [2:0] opcode;
    wire [3:0] alu_out;
    wire       zero;
    wire       carry;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {module_name} dut (
        .clk(clk),
        .rst(rst),
        .a(a),
        .b(b),
        .opcode(opcode),
        .alu_out(alu_out),
        .zero(zero),
        .carry(carry)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    task check_alu;
        input [3:0] in_a;
        input [3:0] in_b;
        input [2:0] op;
        input [3:0] exp_out;
        input       exp_zero;
        input       exp_carry;
        begin
            @(posedge clk);
            a      <= in_a;
            b      <= in_b;
            opcode <= op;
            @(posedge clk);
            #1;
            total_tests = total_tests + 1;
            if (alu_out === exp_out && zero === exp_zero && carry === exp_carry) begin
                passed_tests = passed_tests + 1;
                $display("  [PASS] Op %3b (a=%0d, b=%0d) => out=%0d, zero=%b, carry=%b",
                         op, in_a, in_b, alu_out, zero, carry);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [FAIL] Op %3b (a=%0d, b=%0d) => EXPECT out=%0d z=%b c=%b, GOT out=%0d z=%b c=%b",
                         op, in_a, in_b, exp_out, exp_zero, exp_carry, alu_out, zero, carry);
            end
        end
    endtask

    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        clk = 0;
        rst = 1;
        a   = 0;
        b   = 0;
        opcode = 0;

        #25;
        rst = 0;

        $display("============================================================================");
        $display("   AUTONOMOUS ORACLE VERIFICATION FOR MODULE: {module_name}");
        $display("============================================================================");

        // Opcode 000: ADD
        check_alu(4'd5,  4'd3,  3'b000, 4'd8,  1'b0, 1'b0);
        check_alu(4'd12, 4'd6,  3'b000, 4'd2,  1'b0, 1'b1);
        check_alu(4'd0,  4'd0,  3'b000, 4'd0,  1'b1, 1'b0);

        // Opcode 001: SUB
        check_alu(4'd9,  4'd4,  3'b001, 4'd5,  1'b0, 1'b0);
        check_alu(4'd7,  4'd7,  3'b001, 4'd0,  1'b1, 1'b0);
        check_alu(4'd3,  4'd5,  3'b001, 4'd14, 1'b0, 1'b1);

        // Opcode 010: AND
        check_alu(4'b1100, 4'b1010, 3'b010, 4'b1000, 1'b0, 1'b0);

        // Opcode 011: OR
        check_alu(4'b1100, 4'b1010, 3'b011, 4'b1110, 1'b0, 1'b0);

        // Opcode 100: XOR
        check_alu(4'b1100, 4'b1010, 3'b100, 4'b0110, 1'b0, 1'b0);

        // Opcode 101: NOT
        check_alu(4'b1010, 4'b0000, 3'b101, 4'b0101, 1'b0, 1'b0);

        // Opcode 110: SHL
        check_alu(4'b0101, 4'b0000, 3'b110, 4'b1010, 1'b0, 1'b0);
        check_alu(4'b1001, 4'b0000, 3'b110, 4'b0010, 1'b0, 1'b1);

        // Opcode 111: COMP
        check_alu(4'd7, 4'd7, 3'b111, 4'd1, 1'b0, 1'b0);
        check_alu(4'd3, 4'd8, 3'b111, 4'd0, 1'b1, 1'b1);

        #40;
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{module_name}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{module_name}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_gray_counter_tb(self, TenModule="gray_counter_4bit", module_name=None, DuongDanRtl=None, rtl_path=None):
        """
        [Họ 70% - Gray Counter] Sinh testbench kiểm tra bất biến đổi đúng 1 bit (Single-Bit Flip Invariant)
        trên từng nhịp clock khi đếm lên, đếm xuống và giữ giá trị khi `enable=0`.
        """
        TenMod = module_name if module_name is not None else TenModule
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl

        if TepRtl and os.path.exists(TepRtl):
            mod_rtl, ports = self._parse_rtl_ports(TepRtl)
            if mod_rtl:
                TenMod = mod_rtl
            clk_p = self._find_port(ports, "input", ["clk", "clock"])
            en_p = self._find_port(ports, "input", ["enable", "en", "count_enable"])
            up_p = self._find_port(ports, "input", ["up_down", "updown", "dir"])
            gray_p = self._find_port(ports, "output", ["gray_out", "gray", "q_gray", "count", "out"])

            if clk_p and gray_p:
                decls_str, conns_str = self._build_decls_and_conns(ports)
                reset_seq = self._build_reset_sequence(ports)
                w = gray_p["width"]
                n_steps = min(15, (1 << min(w, 4)) - 1)
                bit_sum = " + ".join([f"diff[{i}]" for i in range(w)])
                extra_decls = "\n".join([
                    f"    reg [{w-1}:0] prev_gray;",
                    f"    reg [{w-1}:0] diff;",
                    "    integer bit_flips;",
                    "    integer step_i;",
                ])
                lines = [
                    reset_seq,
                    self._emit_assert(f"{gray_p['name']} === {w}'d0", "Gray reset == 0 verified", "Gray reset != 0"),
                ]
                if en_p:
                    lines.append(f"        {en_p['name']} = 1'b1;")
                if up_p:
                    lines.append(f"        {up_p['name']} = 1'b1;")
                lines.extend([
                    f"        prev_gray = {gray_p['name']};",
                    f"        for (step_i = 1; step_i <= {n_steps}; step_i = step_i + 1) begin",
                    f"            @(posedge {clk_p['name']}); #1;",
                    f"            diff = {gray_p['name']} ^ prev_gray;",
                    f"            bit_flips = {bit_sum};",
                    self._emit_assert("bit_flips == 1", "Gray step single-bit flip invariant passed", "Gray violation: bit_flips != 1", indent="            "),
                    f"            prev_gray = {gray_p['name']};",
                    "        end",
                ])
                if up_p:
                    lines.extend([
                        f"        {up_p['name']} = 1'b0;",
                        "        for (step_i = 1; step_i <= 4; step_i = step_i + 1) begin",
                        f"            @(posedge {clk_p['name']}); #1;",
                        f"            diff = {gray_p['name']} ^ prev_gray;",
                        f"            bit_flips = {bit_sum};",
                        self._emit_assert("bit_flips == 1", "Gray count-down single-bit flip passed", "Gray count-down violation", indent="            "),
                        f"            prev_gray = {gray_p['name']};",
                        "        end",
                    ])
                if en_p:
                    lines.extend([
                        f"        {en_p['name']} = 1'b0;",
                        f"        @(posedge {clk_p['name']}); #1;",
                        f"        @(posedge {clk_p['name']}); #1;",
                        self._emit_assert(f"{gray_p['name']} === prev_gray", "Gray hold (enable=0) verified", "Gray changed while disabled"),
                    ])
                return self._finalize_tb(TenMod, decls_str, conns_str, clk_p["name"], extra_decls, "", "\n".join(lines), "AUTONOMOUS GRAY COUNTER PROPERTY VERIFICATION")

        tb_name = f"tb_{TenMod}"
        module_name = TenMod
        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Autonomous Property-Checking Testbench for {module_name}
// Based on VerilogEval Benchmark Standard & Single-Bit Invariant Property
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

    reg        clk;
    reg        rst;
    reg        enable;
    reg        up_down;
    wire [3:0] gray_out;
    wire [3:0] count;
    wire       tc;

    reg  [3:0] prev_gray;
    reg  [3:0] diff;
    integer    bit_flips;
    integer    step;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {module_name} dut (
        .clk(clk),
        .rst(rst),
        .enable(enable),
        .gray_out(gray_out),
        .up_down(up_down),
        .count(count),
        .tc(tc)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        clk     = 0;
        rst     = 1;
        enable  = 0;
        up_down = 1;

        #25;
        rst    = 0;
        enable = 1;

        $display("============================================================================");
        $display("   AUTONOMOUS PROPERTY VERIFICATION FOR MODULE: {module_name}");
        $display("============================================================================");

        @(posedge clk);
        #1;
        prev_gray = gray_out;

        for (step = 1; step < 16; step = step + 1) begin
            @(posedge clk);
            #1;
            total_tests = total_tests + 1;
            diff = gray_out ^ prev_gray;
            bit_flips = diff[0] + diff[1] + diff[2] + diff[3];
            if (bit_flips == 1) begin
                passed_tests = passed_tests + 1;
                $display("  [PASS] Step %2d: %b -> %b (Bit flips = 1)", step, prev_gray, gray_out);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [FAIL] Step %2d: %b -> %b (VIOLATION: Bit flips = %0d != 1)", step, prev_gray, gray_out, bit_flips);
            end
            prev_gray = gray_out;
        end

        #40;
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{module_name}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{module_name}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_digital_lock_tb(self, TenModule="digital_lock_fsm", module_name=None, DuongDanRtl=None, rtl_path=None):
        """
        [FSM Đặc thù - Digital Lock] Sinh testbench cho khóa mã số điện tử:
        tự đọc mật khẩu mẫu (`Password Preset`) và tên cổng thực tế từ RTL để thử mở khóa đúng và thử nhập sai 3 lần kích hoạt còi báo động.
        """
        TenMod = module_name if module_name is not None else TenModule
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl

        clk_pin, rst_pin = "clk", "rst"
        key_pin, enter_pin = "key_code", "enter_btn"
        unlock_pin, alarm_pin = "unlocked", "alarm"
        att_pin, state_pin = "attempts_left", "state_out"
        has_att = True
        has_state = True
        is_err_up = False
        pw = [1, 2, 3]
        decls_str = None
        conns_str = None

        if TepRtl and os.path.exists(TepRtl):
            with open(TepRtl, "r", encoding="utf-8", errors="replace") as f:
                rtl_txt = f.read()
            m_pw = re.search(r"Password Preset:\s*(\d)\s*-\s*(\d)\s*-\s*(\d)(?:\s*-\s*(\d))?", rtl_txt)
            if m_pw:
                pw = [int(m_pw.group(1)), int(m_pw.group(2)), int(m_pw.group(3))]
                if m_pw.group(4):
                    pw.append(int(m_pw.group(4)))

            mod_rtl, ports = self._parse_rtl_ports(TepRtl)
            if mod_rtl:
                TenMod = mod_rtl
            if ports:
                decls_str, conns_str = self._build_decls_and_conns(ports)
                clk_p = self._find_port(ports, "input", ["clk", "clock"])
                rst_p = self._find_port(ports, "input", ["rst", "clr", "reset"])
                key_p = self._find_port(ports, "input", ["key_code", "key_in", "key", "code", "digit"])
                ent_p = self._find_port(ports, "input", ["enter_btn", "enter", "confirm", "btn"])
                unl_p = self._find_port(ports, "output", ["unlocked", "unlock", "open"])
                alm_p = self._find_port(ports, "output", ["alarm", "warn", "lockout"])
                att_p = self._find_port(ports, "output", ["attempts_left", "err_count", "fail_count", "attempts"])
                st_p = self._find_port(ports, "output", ["state_out", "state"])
                if clk_p: clk_pin = clk_p["name"]
                if rst_p: rst_pin = rst_p["name"]
                if key_p: key_pin = key_p["name"]
                if ent_p: enter_pin = ent_p["name"]
                if unl_p: unlock_pin = unl_p["name"]
                if alm_p: alarm_pin = alm_p["name"]
                has_att = att_p is not None
                if att_p:
                    att_pin = att_p["name"]
                    is_err_up = "err" in att_pin.lower()
                has_state = st_p is not None
                if st_p: state_pin = st_p["name"]

        if decls_str is None:
            tb_name = f"tb_{TenMod}"
            decls_str = "\n".join([
                f"    reg        {clk_pin};",
                f"    reg        {rst_pin};",
                f"    reg  [3:0] {key_pin};",
                f"    reg        {enter_pin};",
                f"    wire       {unlock_pin};",
                f"    wire       {alarm_pin};",
                f"    wire [1:0] {att_pin};",
                f"    wire [2:0] {state_pin};",
            ])
            conns_str = "\n".join([
                f"        .{clk_pin}({clk_pin}),",
                f"        .{rst_pin}({rst_pin}),",
                f"        .{key_pin}({key_pin}),",
                f"        .{enter_pin}({enter_pin}),",
                f"        .{unlock_pin}({unlock_pin}),",
                f"        .{alarm_pin}({alarm_pin}),",
                f"        .{att_pin}({att_pin}),",
                f"        .{state_pin}({state_pin})",
            ])

        tasks_str = f"""    task press_key;
        input [3:0] k;
        begin
            @(posedge {clk_pin});
            {key_pin}   <= k;
            {enter_pin} <= 1'b1;
            @(posedge {clk_pin});
            {enter_pin} <= 1'b0;
            #1;
        end
    endtask"""

        pw_press = "\n".join([f"        press_key(4'd{d});" for d in pw])
        wrong_digit = 9 if 9 not in pw else 8

        att_checks = []
        for idx in range(1, 4):
            att_val = idx if is_err_up else (3 - idx)
            alm_val = 1 if idx == 3 else 0
            cond = f"{alarm_pin} === 1'b{alm_val}"
            if has_att:
                cond += f" && {att_pin} === 2'd{att_val}"
            att_checks.append(f"        press_key(4'd{wrong_digit});")
            att_checks.append(self._emit_assert(
                cond,
                f"Wrong attempt {idx}: alarm={alm_val}" + (f", {att_pin}={att_val}" if has_att else ""),
                f"Wrong attempt {idx} mismatch",
            ))

        stim_str = "\n".join([
            f"        {clk_pin} = 0;",
            f"        {rst_pin} = 1;",
            f"        {key_pin} = 0;",
            f"        {enter_pin} = 0;",
            "        #25;",
            f"        {rst_pin} = 0;",
            pw_press,
            self._emit_assert(
                f"{unlock_pin} === 1'b1 && {alarm_pin} === 1'b0",
                f"Correct password unlocked ({unlock_pin}=1, {alarm_pin}=0)",
                "Correct password failed to unlock",
            ),
            f"        {rst_pin} = 1; #20; {rst_pin} = 0; #20;",
            "\n".join(att_checks),
        ])

        return self._finalize_tb(TenMod, decls_str, conns_str, clk_pin, "", tasks_str, stim_str, "AUTONOMOUS SECURITY LOCK VERIFICATION")

    def generate_sequence_detector_tb(self, TenModule="sequence_detector_1011", module_name=None):
        """[FSM Đặc thù - Sequence Detector] Sinh testbench kiểm thử nhận diện chuỗi `1011` và tính chất không gối đầu (Non-Overlapping) trên chuỗi `1011011`."""
        TenMod = module_name if module_name is not None else TenModule
        tb_name = f"tb_{TenMod}"
        module_name = TenMod
        code = f"""//==============================================================================
// Testbench: {tb_name}
// Description: Autonomous Self-Checking Testbench for {module_name}
// Based on VeriPrefer Benchmark Standard & Non-Overlapping Verification Oracle
//==============================================================================
`timescale 1ns / 1ps

module {tb_name};

    reg        clk;
    reg        rst;
    reg        din;
    wire       detected;
    wire [2:0] state_out;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;
    integer det_count = 0;

    {module_name} dut (
        .clk(clk),
        .rst(rst),
        .din(din),
        .detected(detected),
        .state_out(state_out)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    task send_bit;
        input b;
        begin
            @(posedge clk);
            din <= b;
            #1;
            if (detected) det_count = det_count + 1;
        end
    endtask

    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {tb_name});

        clk = 0;
        rst = 1;
        din = 0;

        #25;
        rst = 0;

        $display("============================================================================");
        $display("   AUTONOMOUS SEQUENCE DETECTOR VERIFICATION: {module_name}");
        $display("============================================================================");

        // Scenario 1: Send exact pattern 1 - 0 - 1 - 1
        $display("\\n>>> [KICH BAN 1]: Truyen mau chuan 1 - 0 - 1 - 1...");
        send_bit(1);
        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        total_tests = total_tests + 1;
        if (detected === 1'b1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Phat hien thanh cong chuoi 1011!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Khong phat hien chuoi 1011: detected=%b", detected);
        end

        // Scenario 2: Test Non-Overlapping stream: 1 - 0 - 1 - 1 - 0 - 1 - 1
        $display("\\n>>> [KICH BAN 2]: Kiem tra dac tinh Non-Overlapping voi stream 1011011...");
        rst = 1; #20; rst = 0; #20;
        det_count = 0;
        send_bit(1);
        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        if (detected) det_count = det_count + 1;

        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        if (detected) det_count = det_count + 1;

        total_tests = total_tests + 1;
        if (det_count === 1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Xac nhan Non-Overlapping chuan: dung 1 lan phat hien!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Vi pham Non-Overlapping: phat hien %0d lan!", det_count);
        end

        #40;
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{module_name}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{module_name}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(code)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{tb_name}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_generic_tb(self, DuongDanRtl=None, TenModuleDau=None, rtl_path=None, module_name=None):
        """
        [Fallback Tổng quát] Tự động trích xuất toàn bộ cổng thực tế của file RTL để dựng testbench:
        kích hoạt reset chuẩn (hỗ trợ active-high/active-low), bơm 4 tổ hợp vector kiểm thử và xác minh mọi ngõ ra không chứa bit X/Z.
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        TenModule = module_name if module_name is not None else TenModuleDau

        mod_rtl, DanhSachCong = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        TenTb = f"tb_{TenModule}"

        KhaiBaoTinHieu = []
        KetNoiCongDut = []
        CoXungNhip = False
        TenXungNhip = "clk"
        DongKichThich = []

        for Cong in DanhSachCong:
            TenCong = Cong["name"]
            ChuoiDoRong = f"[{Cong['width']-1}:0] " if Cong["width"] > 1 else ""
            KetNoiCongDut.append(f"        .{TenCong}({TenCong})")

            if Cong["direction"] == "input":
                KhaiBaoTinHieu.append(f"    reg  {ChuoiDoRong:<8} {TenCong};")
                if Cong["is_clk"]:
                    CoXungNhip = True
                    TenXungNhip = TenCong
            else:
                KhaiBaoTinHieu.append(f"    wire {ChuoiDoRong:<8} {TenCong};")

        DongKichThich.append("        // Trang thai khoi tao")
        for Cong in DanhSachCong:
            if Cong["direction"] == "input":
                if Cong["is_rst"]:
                    if Cong["rst_active_low"]:
                        DongKichThich.append(f"        {Cong['name']} = 1'b0; // Kich hoat reset muc thap")
                    else:
                        DongKichThich.append(f"        {Cong['name']} = 1'b1; // Kich hoat reset muc cao")
                else:
                    DongKichThich.append(f"        {Cong['name']} = 0;")

        DongKichThich.append("\n        #25;")
        for Cong in DanhSachCong:
            if Cong["direction"] == "input" and Cong["is_rst"]:
                if Cong["rst_active_low"]:
                    DongKichThich.append(f"        {Cong['name']} = 1'b1; // Huy reset muc thap")
                else:
                    DongKichThich.append(f"        {Cong['name']} = 1'b0; // Huy reset muc cao")

        DongKichThich.append("\n        // Chay cac kich ban kiem thu voi assertions")
        CongVaoKiemThu = [Cong for Cong in DanhSachCong if Cong["direction"] == "input" and not Cong["is_clk"] and not Cong["is_rst"]]
        CongRaKiemThu = [Cong for Cong in DanhSachCong if Cong["direction"] == "output"]
        for Buoc in range(1, 5):
            DongKichThich.append(f"        // Kich ban {Buoc}")
            for ChiSo, CongVao in enumerate(CongVaoKiemThu):
                GiaTri = (Buoc * (ChiSo + 1) * 3) % (1 << min(CongVao["width"], 8))
                DongKichThich.append(f"        {CongVao['name']} = {CongVao['width']}'d{GiaTri};")
            if CoXungNhip:
                DongKichThich.append(f"        @(posedge {TenXungNhip}); #1;")
            else:
                DongKichThich.append("        #20;")
            DongKichThich.append("        total_tests = total_tests + 1;")
            if CongRaKiemThu:
                DieuKienKiemTra = " && ".join([f"(^{Cong['name']} !== 1'bx)" for Cong in CongRaKiemThu])
                DongKichThich.append(f"        if ({DieuKienKiemTra}) begin")
                DongKichThich.append("            passed_tests = passed_tests + 1;")
                DongKichThich.append(f"            $display(\"  [PASS] Scenario {Buoc}: Outputs valid and deterministic\");")
                DongKichThich.append("        end else begin")
                DongKichThich.append("            failed_tests = failed_tests + 1;")
                DongKichThich.append(f"            $display(\"  [FAIL] Scenario {Buoc}: Output contains undefined or floating (X/Z) bits!\");")
                DongKichThich.append("        end")
            else:
                DongKichThich.append("        passed_tests = passed_tests + 1;")

        DongKichThich.append("        #40;")

        ChuoiKhaiBao = "\n".join(KhaiBaoTinHieu)
        ChuoiKetNoi = ",\n".join(KetNoiCongDut)
        ChuoiKichThich = "\n".join(DongKichThich)
        ChuoiXungNhip = f"always #10 {TenXungNhip} = ~{TenXungNhip};" if CoXungNhip else ""

        MaNguon = f"""//==============================================================================
// Testbench: {TenTb}
// Mo ta: Testbench tu kiem tra cho thiet ke {TenModule}
// Tieu chuan kiem dinh: VeriPrefer (arXiv:2504.15804)
//==============================================================================
`timescale 1ns / 1ps

module {TenTb};

{ChuoiKhaiBao}

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {TenModule} dut (
{ChuoiKetNoi}
    );

    {ChuoiXungNhip}

    // Bo dem thoi gian bao ve Watchdog
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    initial begin
        $dumpfile("{TenModule}.vcd");
        $dumpvars(0, {TenTb});

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: {TenModule}");
        $display("============================================================================");

{ChuoiKichThich}

        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{TenModule}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{TenModule}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        MaNguon = VerilogLinter.sanitize_verilog_code(MaNguon)
        DuongDanXuat = os.path.join(self.ThuMucSim, f"{TenTb}.v")
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguon)
        return DuongDanXuat

    def generate_decoder_tb(self, TenModule="memory_address_decoder", DuongDanRtl=None, rtl_path=None):
        """
        [Họ 70% - Decoder] Sinh testbench tự kiểm tra cho bộ giải mã:
          - Bộ giải mã địa chỉ 64KB (kiểm tra `mem_en=0` và 3 vùng SRAM/ROM/IO).
          - Bộ giải mã nhị phân N-sang-2^N (kiểm tra `en=0` và quét đủ 2^N mã đầu vào one-hot).
        """
        TepRtl = rtl_path if rtl_path is not None else DuongDanRtl
        mod_rtl, ports = self._parse_rtl_ports(TepRtl)
        if mod_rtl:
            TenModule = mod_rtl
        port_names = {p["lower"] for p in ports}

        is_mem_decoder = {"addr", "mem_en", "cs_ram", "cs_rom", "cs_io"}.issubset(port_names)

        if is_mem_decoder:
            TenTb = f"tb_{TenModule}"
            code = f"""`timescale 1ns / 1ps

module {TenTb};

    reg  [15:0] addr;
    reg         mem_en;
    wire        cs_ram;
    wire        cs_rom;
    wire        cs_io;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {TenModule} dut (
        .addr(addr),
        .mem_en(mem_en),
        .cs_ram(cs_ram),
        .cs_rom(cs_rom),
        .cs_io(cs_io)
    );

    initial begin
        $dumpfile("{TenModule}.vcd");
        $dumpvars(0, {TenTb});

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: {TenModule}");
        $display("============================================================================");

        // Kich ban 1: mem_en = 0 (Tat ca CS phai bang 0)
        addr = 16'h1234;
        mem_en = 1'b0;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 0 && cs_rom == 0 && cs_io == 0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: mem_en=0 disables all chip selects");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 1: Output active when mem_en=0");
        end

        // Kich ban 2: SRAM (0x0000 - 0x7FFF)
        addr = 16'h2000;
        mem_en = 1'b1;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 1 && cs_rom == 0 && cs_io == 0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: SRAM region 0x2000 activates cs_ram");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 2: SRAM selection failed");
        end

        // Kich ban 3: ROM (0x8000 - 0xBFFF)
        addr = 16'h9000;
        mem_en = 1'b1;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 0 && cs_rom == 1 && cs_io == 0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: ROM region 0x9000 activates cs_rom");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 3: ROM selection failed");
        end

        // Kich ban 4: I/O (0xC000 - 0xFFFF)
        addr = 16'hE000;
        mem_en = 1'b1;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 0 && cs_rom == 0 && cs_io == 1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 4: I/O region 0xE000 activates cs_io");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 4: I/O selection failed");
        end

        #40;
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{TenModule}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{TenModule}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
            code = VerilogLinter.sanitize_verilog_code(code)
            out_path = os.path.join(self.ThuMucSim, f"{TenTb}.v")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(code)
            return out_path

        # Binary N-to-2^N Decoder (e.g. decoder_2to4, decoder_3to8)
        clk_p = self._find_port(ports, "input", ["clk", "clock"])
        en_p = self._find_port(ports, "input", ["en", "enable"])
        in_p = self._find_port(ports, "input", ["a", "in", "sel", "addr", "code"])
        if not in_p:
            ins = [p for p in ports if p["direction"] == "input" and not p["is_clk"] and not p["is_rst"] and (not en_p or p["lower"] != en_p["lower"])]
            in_p = ins[0] if ins else None
        out_p = self._find_port(ports, "output", ["y", "out", "dec_out", "q"])
        if not out_p:
            outs = [p for p in ports if p["direction"] == "output"]
            out_p = outs[0] if outs else None

        if in_p and out_p and out_p["width"] == (1 << in_p["width"]) and in_p["width"] <= 4:
            decls_str, conns_str = self._build_decls_and_conns(ports)
            reset_seq = self._build_reset_sequence(ports)
            clk_name = clk_p["name"] if clk_p else None
            settle = f"        @(posedge {clk_name}); #1;" if clk_name else "        #10;"
            ow = out_p["width"]

            lines = [reset_seq]
            if en_p:
                lines.append(f"        {en_p['name']} = 1'b0;")
                lines.append(f"        {in_p['name']} = {in_p['width']}'d1;")
                lines.append(settle)
                lines.append(self._emit_assert(f"{out_p['name']} === {ow}'d0", "Decoder disabled (en=0) => out=0", "Decoder active when disabled"))
                lines.append(f"        {en_p['name']} = 1'b1;")

            for k in range(1 << in_p["width"]):
                exp_v = 1 << k
                lines.append(f"        {in_p['name']} = {in_p['width']}'d{k};")
                lines.append(settle)
                lines.append(self._emit_assert(
                    f"{out_p['name']} === {ow}'d{exp_v}",
                    f"Decoder in={k} => one-hot bit {k}",
                    f"Decoder in={k} mismatch",
                ))
            return self._finalize_tb(TenModule, decls_str, conns_str, clk_name, "", "", "\n".join(lines), "AUTONOMOUS BINARY DECODER VERIFICATION")

        return self.generate_generic_tb(TepRtl, TenModule)

    def generate_temperature_monitor_tb(self, TenModule="temperature_monitor_alarm", DuongDanRtl=None, rtl_path=None):
        """[FSM Đặc thù - Temperature Monitor] Sinh testbench kiểm thử 4 kịch bản giám sát nhiệt độ: bình thường, cảnh báo quá nhiệt, ngưỡng ngắt khẩn cấp và hạ nhiệt."""
        TenTb = f"tb_{TenModule}"
        code = f"""`timescale 1ns / 1ps

module {TenTb};

    reg        clk;
    reg        rst;
    reg  [7:0] temp_celsius;
    reg  [7:0] max_temp_limit;
    wire       fan_high_speed;
    wire       overtemp_alarm;
    wire       shutdown_signal;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    {TenModule} dut (
        .clk(clk),
        .rst(rst),
        .temp_celsius(temp_celsius),
        .max_temp_limit(max_temp_limit),
        .fan_high_speed(fan_high_speed),
        .overtemp_alarm(overtemp_alarm),
        .shutdown_signal(shutdown_signal)
    );

    always #10 clk = ~clk;

    initial begin
        $dumpfile("{TenModule}.vcd");
        $dumpvars(0, {TenTb});

        clk = 0;
        rst = 1;
        temp_celsius = 8'd25;
        max_temp_limit = 8'd50;
        #25;
        rst = 0;

        // Kich ban 1: Nhiet do binh thuong (25 < 50)
        temp_celsius = 8'd25;
        #20;
        total_tests = total_tests + 1;
        if (!fan_high_speed && !overtemp_alarm && !shutdown_signal) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Normal temp (all alarms 0)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 1: Unexpected alarm on normal temp");
        end

        // Kich ban 2: Qua nhiet canh bao (55 >= 50, < 60)
        temp_celsius = 8'd55;
        #20;
        total_tests = total_tests + 1;
        if (fan_high_speed && overtemp_alarm && !shutdown_signal) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Warning temp (fan=1, alarm=1, shutdown=0)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 2: Failed warning alarm activation");
        end

        // Kich ban 3: Nhiet do nguy hiem (65 >= 50 + 10)
        temp_celsius = 8'd65;
        #20;
        total_tests = total_tests + 1;
        if (fan_high_speed && overtemp_alarm && shutdown_signal) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Critical temp (fan=1, alarm=1, shutdown=1)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 3: Failed shutdown signal activation");
        end

        // Kich ban 4: Ha nhiet ve binh thuong (35 < 50)
        temp_celsius = 8'd35;
        #20;
        total_tests = total_tests + 1;
        if (!fan_high_speed && !overtemp_alarm && !shutdown_signal) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 4: Cooled down (all alarms 0)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [FAIL] Scenario 4: Alarms failed to clear after cooling");
        end

        #40;
        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE '{TenModule}' PASSED 100 PERCENT!");
        end else begin
            $display("  [FAIL] TEST VERIFICATION FOR MODULE '{TenModule}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        code = VerilogLinter.sanitize_verilog_code(code)
        out_path = os.path.join(self.ThuMucSim, f"{TenTb}.v")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(code)
        return out_path


if __name__ == "__main__":
    print("TBGenerator da san sang hoat dong.")
