# -*- coding: utf-8 -*-
"""
Module: TaoHarness.py (truoc day la harness_generator.py)
Mô tả: Tự động sinh khung kiểm thử phần cứng Verilog Test Harness Wrapper (Option A).
Cấu trúc chuẩn:
  1. Bộ tạo xung nhịp đồng hồ và reset đồng bộ
  2. Watchdog Timer chống lặp vô tận / treo mô phỏng
  3. Tự động kiểm tra assertion và tính hợp lệ của tín hiệu
  4. Ghép nối DUT tự động
"""

import os
import re
import sys

# Đảm bảo console xuất tiếng Việt UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from DonDepVerilog import VerilogLinter

class HarnessGenerator:
    """Tự động sinh Test Harness Verilog chuẩn công nghiệp."""

    def __init__(self, ThuMucSim=None):
        ThuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sim_dir = ThuMucSim or os.path.join(ThuMucGoc, "sim")
        os.makedirs(self.sim_dir, exist_ok=True)

    def extract_ports(self, MaRtl):
        """Trích xuất danh sách cổng và thông số tín hiệu từ mã Verilog RTL."""
        MaSach = re.sub(r"//.*", "", MaRtl)
        MaSach = re.sub(r"/\*.*?\*/", "", MaSach, flags=re.DOTALL)

        KhopModule = re.search(r"module\s+([A-Za-z0-9_]+)\s*(?:#\s*\(.*?\)\s*)?\((.*?)\);", MaSach, re.DOTALL)
        if not KhopModule:
            return None, []

        TenModule = KhopModule.group(1)
        KhoiCong = KhopModule.group(2)

        TuKhoaVerilog = {
            "input", "output", "inout", "wire", "reg", "for", "while",
            "case", "default", "assign", "begin", "end", "integer", "genvar"
        }

        DanhSachCong = []
        for Dong in KhoiCong.split(","):
            Dong = Dong.strip()
            if not Dong:
                continue
            KhopCong = re.search(
                r"(input|output|inout)\s+(?:wire|reg)?\s*(?:signed\s*)?(?:\[\s*([^:]+)\s*:\s*([^\]]+)\s*\])?\s*([A-Za-z0-9_]+)",
                Dong
            )
            if KhopCong:
                Huong, ChuoiMsb, ChuoiLsb, TenCong = KhopCong.groups()
                if TenCong.lower() in TuKhoaVerilog:
                    continue

                DoRong = 1
                if ChuoiMsb is not None and ChuoiLsb is not None:
                    try:
                        DoRong = abs(int(ChuoiMsb.strip()) - int(ChuoiLsb.strip())) + 1
                    except ValueError:
                        DoRong = 8

                TenThuong = TenCong.lower()
                LaClk = any(TuKhoa in TenThuong for TuKhoa in ["clk", "clock"])
                LaRst = any(TuKhoa in TenThuong for TuKhoa in ["rst", "clr", "reset", "clear"])
                TichCucThap = TenThuong.endswith("_n") or TenThuong.startswith("rst_n") or TenThuong == "rst_n"

                DanhSachCong.append({
                    "name": TenCong,
                    "direction": Huong,
                    "width": DoRong,
                    "msb": ChuoiMsb,
                    "lsb": ChuoiLsb,
                    "is_clk": LaClk,
                    "is_rst": LaRst,
                    "is_active_low": TichCucThap
                })

        return TenModule, DanhSachCong

    def generate_harness(self, DuongDanRtl, ThuMucXuat=None):
        """Sinh mã Verilog Test Harness bao đóng module RTL."""
        if not os.path.exists(DuongDanRtl):
            raise FileNotFoundError(f"Không tìm thấy file RTL: {DuongDanRtl}")

        ThuMucDich = ThuMucXuat or self.sim_dir
        os.makedirs(ThuMucDich, exist_ok=True)

        with open(DuongDanRtl, "r", encoding="utf-8", errors="replace") as TepTin:
            MaRtl = TepTin.read()

        TenModule, DanhSachCong = self.extract_ports(MaRtl)
        if not TenModule:
            TenModule = os.path.splitext(os.path.basename(DuongDanRtl))[0]

        TenModuleHarness = f"harness_{TenModule}"

        # 1. Khai báo tín hiệu và ghép cổng DUT
        DanhSachKhaiBao = []
        KetNoiDut = []
        CoClk = False
        TenClk = "clk"
        CoRst = False
        TenRst = "rst_n"
        RstTichCucThap = True

        for Cong in DanhSachCong:
            Ten = Cong["name"]
            ChuoiRong = f"[{Cong['width']-1}:0] " if Cong["width"] > 1 else ""
            KetNoiDut.append(f"        .{Ten}({Ten})")

            if Cong["direction"] == "input":
                DanhSachKhaiBao.append(f"    reg  {ChuoiRong:<8} {Ten};")
                if Cong["is_clk"] and not CoClk:
                    CoClk = True
                    TenClk = Ten
                if Cong["is_rst"] and not CoRst:
                    CoRst = True
                    TenRst = Ten
                    RstTichCucThap = Cong["is_active_low"]
            else:
                DanhSachKhaiBao.append(f"    wire {ChuoiRong:<8} {Ten};")

        # Cung cấp clock mặc định nếu mạch không có sẵn
        if not CoClk:
            DanhSachKhaiBao.append("    reg           clk;")
            TenClk = "clk"

        KhoiKhaiBao = "\n".join(DanhSachKhaiBao)
        KhoiKetNoiDut = ",\n".join(KetNoiDut) if KetNoiDut else "        // Không có cổng ngoại vi"

        # 2. Sinh kích thích kiểm thử
        DanhSachKichThich = []
        CongVaoDuLieu = [p for p in DanhSachCong if p["direction"] == "input" and not p["is_clk"] and not p["is_rst"]]
        CongRaDuLieu = [p for p in DanhSachCong if p["direction"] == "output"]

        # Trạng thái ban đầu
        for Cong in DanhSachCong:
            if Cong["direction"] == "input":
                if Cong["is_rst"]:
                    GiaTri = "1'b0" if Cong["is_active_low"] else "1'b1"
                    DanhSachKichThich.append(f"        {Cong['name']} = {GiaTri}; // Kích hoạt reset ban đầu")
                elif not Cong["is_clk"]:
                    DanhSachKichThich.append(f"        {Cong['name']} = {Cong['width']}'d0;")

        # Nhả reset sau 25ns
        DanhSachKichThich.append("\n        #25;")
        for Cong in DanhSachCong:
            if Cong["direction"] == "input" and Cong["is_rst"]:
                GiaTri = "1'b1" if Cong["is_active_low"] else "1'b0"
                DanhSachKichThich.append(f"        {Cong['name']} = {GiaTri}; // Nhả reset để mạch hoạt động")

        # Thực thi 6 kịch bản kiểm tra
        DanhSachKichThich.append("\n        //====================================================================")
        DanhSachKichThich.append("        // KỊCH BẢN KIỂM TRA ĐẦU VÀO VÀ ĐỐI SOÁT ĐẦU RA")
        DanhSachKichThich.append("        //====================================================================")

        for Buoc in range(1, 7):
            DanhSachKichThich.append(f"\n        // --- Kịch bản kiểm thử {Buoc} ---")
            for ChiSo, CongVao in enumerate(CongVaoDuLieu):
                MatNa = (1 << min(CongVao["width"], 16)) - 1
                GiaTri = ((Buoc * 17) + (ChiSo * 23) + 7) & MatNa
                DanhSachKichThich.append(f"        {CongVao['name']} = {CongVao['width']}'d{GiaTri};")

            DanhSachKichThich.append("        #20;")

            for CongRa in CongRaDuLieu:
                ThongDiep = f"Kịch bản {Buoc} - Cổng {CongRa['name']}"
                DanhSachKichThich.append(f"        harness_assert_valid({CongRa['name']}, \"{ThongDiep}\");")

        DanhSachKichThich.append("\n        #40;")
        KhoiKichThich = "\n".join(DanhSachKichThich)

        # 3. Lắp ráp toàn bộ file Verilog Test Harness
        MaNguonHarness = f"""//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER
// Module: {TenModuleHarness}
// Mạch kiểm thử: {TenModule}
// Chuẩn: IEEE 1364-2001 Test Fixture
// Tính năng:
//   1. Hệ thống tạo xung nhịp 50 MHz & Reset đồng bộ
//   2. Watchdog an toàn: Tự ngắt sau 100,000 ps để tránh treo lặp vô tận
//   3. Bộ task tự động kiểm tra assertion hợp lệ
//   4. Ghép nối DUT socket tường minh
//==============================================================================
`timescale 1ns / 1ps

module {TenModuleHarness};

    // -------------------------------------------------------------------------
    // 1. KHAI BÁO TÍN HIỆU HARNESS
    // -------------------------------------------------------------------------
{KhoiKhaiBao}

    // Biến đếm thống kê kết quả
    integer total_tests  = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    // -------------------------------------------------------------------------
    // 2. BỘ PHÁT XUNG CLOCK (50 MHz, Chu kỳ = 20ns)
    // -------------------------------------------------------------------------
    always #10 {TenClk} = ~{TenClk};

    // -------------------------------------------------------------------------
    // 3. WATCHDOG TIMER AN TOÀN (Ngắt tự động nếu FSM bị treo)
    // -------------------------------------------------------------------------
    initial begin
        #100000;
        $display("\\n============================================================================");
        $display("   [HARNESS WATCHDOG TIMEOUT] Quá thời gian mô phỏng an toàn (100 us)!");
        $display("   Phát hiện nguy cơ lặp vô tận hoặc treo trạng thái trong mạch '{TenModule}'.");
        $display("   Thống kê tại thời điểm ngắt -> Tổng: %0d | Đạt: %0d | Lỗi: %0d",
                 total_tests, passed_tests, failed_tests);
        $display("============================================================================");
        $finish;
    end

    // -------------------------------------------------------------------------
    // 4. CÁC TASK KIỂM TRA ĐỐI SOÁT TÍN HIỆU
    // -------------------------------------------------------------------------
    task harness_assert_eq;
        input [31:0]  actual;
        input [31:0]  expected;
        input [255:0] test_name;
        begin
            total_tests = total_tests + 1;
            if (actual === expected) begin
                passed_tests = passed_tests + 1;
                $display("  [HARNESS PASS] %0s | Thực tế: %h == Kỳ vọng: %h", test_name, actual, expected);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [HARNESS FAIL] %0s | Thực tế: %h != Kỳ vọng: %h tại %0t ps",
                         test_name, actual, expected, $time);
            end
        end
    endtask

    task harness_assert_valid;
        input [31:0]  val;
        input [255:0] signal_name;
        begin
            total_tests = total_tests + 1;
            if (^val !== 1'bx && ^val !== 1'bz) begin
                passed_tests = passed_tests + 1;
                $display("  [HARNESS PASS] %0s hợp lệ (xác định): %h", signal_name, val);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [HARNESS FAIL] %0s chứa bit thả nổi X/Z: %h tại %0t ps",
                         signal_name, val, $time);
            end
        end
    endtask

    // -------------------------------------------------------------------------
    // 5. GHÉP NỐI LINH KIỆN MẠCH CẦN TEST (DUT)
    // -------------------------------------------------------------------------
    {TenModule} dut (
{KhoiKetNoiDut}
    );

    // -------------------------------------------------------------------------
    // 6. TRÌNH TỰ KÍCH THÍCH VÀ XUẤT DẠNG SÓNG
    // -------------------------------------------------------------------------
    initial begin
        $dumpfile("{TenModule}.vcd");
        $dumpvars(0, {TenModuleHarness});

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): {TenModuleHarness}");
        $display("   Linh kiện kiểm thử: {TenModule}");
        $display("============================================================================");

        // Khởi động
        {TenClk} = 0;
{KhoiKichThich}
        // Tổng kết
        $display("============================================================================");
        $display("       BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ HARNESS");
        $display("============================================================================");
        $display("  Mạch kiểm thử           : {TenModule}");
        $display("  Tổng số bài test đã chạy: %0d", total_tests);
        $display("  Số phép kiểm tra đạt    : %0d", passed_tests);
        $display("  Số phép kiểm tra lỗi    : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Độ chính xác chức năng  : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] KIỂM THỬ MẠCH '{TenModule}' ĐẠT 100 PERCENT!");
        end else begin
            $display("  [ERROR] KIỂM THỬ MẠCH '{TenModule}' PHÁT HIỆN %0d LỖI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        MaNguonHarness = VerilogLinter.sanitize_verilog_code(MaNguonHarness)
        FileDauRa = os.path.join(ThuMucDich, f"{TenModuleHarness}.v")
        with open(FileDauRa, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaNguonHarness)

        return TenModuleHarness, FileDauRa

if __name__ == "__main__":
    DuongDanRtl = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "src", "alu_4bit.v")
    BoSinh = HarnessGenerator()
    TenHarness, DuongDan = BoSinh.generate_harness(DuongDanRtl)
    print(f"[HarnessGenerator]: Đã sinh Test Harness '{TenHarness}': {DuongDan}")
