"""
Module: rtl_generator.py
Chức năng: Tự động sinh mã nguồn Verilog RTL chuẩn tổng hợp được (synthesizable IEEE 1364-2001)
cho hệ thống Spec2RTL & Prompt2Silicon từ đặc tả ngôn ngữ tự nhiên / Markdown.
Bao gồm bộ kiểm tra ép buộc khớp cổng 100% với đặc tả (RTLPortEnforcer)
và các hàm sinh mạch theo từng họ phần cứng (FSM, Số học, Bộ đếm, Giao tiếp, FIFO, Decoder, Generic).
"""

import os
import re
from spec_analyzer import SpecAnalyzer, remove_vietnamese_accents
from verilog_linter import VerilogLinter

class RTLPortEnforcer:
    """
    Bộ kiểm toán và ép buộc cổng (Port Enforcer) ở tầng sinh RTL.
    Đảm bảo danh sách cổng (tên, hướng, độ rộng bit) của module Verilog sinh ra
    khớp chính xác 100% với danh sách cổng trích xuất từ đặc tả Spec.
    """

    @staticmethod
    def enforce(MaRtl=None, DanhSachCongSpec=None, rtl_code=None, spec_ports=None):
        """
        Đối chiếu header `module ... (...)` trong mã RTL với `CongSpec`:
          - Nếu thiếu cổng so với Spec: bổ sung vào header (và gán mặc định nếu là output chưa được gán).
          - Nếu dư cổng so với Spec: đưa xuống khai báo dây/thanh ghi nội bộ để tránh hở chân hoặc sai giao diện.
        """
        NoiDungRtl = rtl_code if rtl_code is not None else MaRtl
        CongSpec = spec_ports if spec_ports is not None else DanhSachCongSpec

        if not CongSpec or not NoiDungRtl:
            return NoiDungRtl

        KhopModule = re.search(r"module\s+([A-Za-z0-9_]+)\s*\((.*?)\);", NoiDungRtl, re.DOTALL)
        if not KhopModule:
            return NoiDungRtl

        TenModule = KhopModule.group(1)
        KhoiKhaiBaoCong = KhopModule.group(2)
        PhanConLai = NoiDungRtl[KhopModule.end():]

        # Bước 1: Phân tích các cổng hiện có trong phần khai báo header của RTL
        KhoiCongSach = re.sub(r"//.*", "", KhoiKhaiBaoCong)
        KhoiCongSach = re.sub(r"/\*.*?\*/", "", KhoiCongSach, flags=re.DOTALL)
        DanhSachCongRtl = []
        for Dong in KhoiCongSach.split(","):
            Dong = Dong.strip()
            KhopCong = re.search(r"(input|output)\s+(?:wire|reg)?\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*([A-Za-z0-9_]+)", Dong)
            if KhopCong:
                HuongCong, Msb, Lsb, TenCong = KhopCong.groups()
                DoRong = abs(int(Msb) - int(Lsb)) + 1 if (Msb and Lsb) else 1
                DanhSachCongRtl.append({"name": TenCong, "direction": HuongCong, "width": DoRong, "msb": Msb, "lsb": Lsb, "raw": Dong})

        TenRtlThuong = {Cong["name"].lower() for Cong in DanhSachCongRtl}
        TenSpecThuong = {Cong["name"].lower() for Cong in CongSpec}

        CongThua = [Cong for Cong in DanhSachCongRtl if Cong["name"].lower() not in TenSpecThuong]
        CongThieu = [Cong for Cong in CongSpec if Cong["name"].lower() not in TenRtlThuong]

        if not CongThua and not CongThieu:
            return NoiDungRtl

        # Bước 2: Tái tạo lại phần khai báo header module theo đúng thứ tự và độ rộng trong Spec
        KhaiBaoCongMoi = []
        for Cong in CongSpec:
            ChuoiDoRong = f"[{Cong['width']-1}:0] " if Cong['width'] > 1 else "      "
            CoGanAssign = bool(re.search(r"\bassign\s+" + re.escape(Cong['name']) + r"\b", PhanConLai))
            if Cong["direction"] == "output":
                KieuBien = "wire" if CoGanAssign else "reg "
            else:
                KieuBien = "wire"
            KhaiBaoCongMoi.append(f"    {Cong['direction']:6} {KieuBien} {ChuoiDoRong}{Cong['name']}")

        HeaderMoi = f"module {TenModule} (\n" + ",\n".join(KhaiBaoCongMoi) + "\n);\n"

        KhaiBaoNoiBo = []
        for Cong in CongThua:
            ChuoiDoRong = f"[{Cong['width']-1}:0] " if Cong['width'] > 1 else ""
            if Cong["direction"] == "input":
                GiaTriGan = "1'b0" if any(Tu in Cong["name"].lower() for Tu in ["rst", "clr", "reset", "clear"]) else "1'b1"
                KhaiBaoNoiBo.append(f"    wire {ChuoiDoRong}{Cong['name']} = {GiaTriGan}; // Cong thua duoc noi noi bo")
            else:
                CoGanAssign = bool(re.search(r"\bassign\s+" + re.escape(Cong['name']) + r"\b", PhanConLai))
                KieuNoi = "wire" if CoGanAssign else "reg "
                KhaiBaoNoiBo.append(f"    {KieuNoi} {ChuoiDoRong}{Cong['name']}; // Cong thua duoc noi noi bo")

        for Cong in CongThieu:
            if Cong["direction"] == "output":
                if not re.search(r"\b" + Cong["name"] + r"\s*<=|\b" + Cong["name"] + r"\s*=", PhanConLai):
                    KhaiBaoNoiBo.append(f"    always @(*) {Cong['name']} = {Cong['width']}'d0; // Gia tri mac dinh cho cong thieu")

        KhoiChenNoiBo = ("\n" + "\n".join(KhaiBaoNoiBo) + "\n") if KhaiBaoNoiBo else ""
        return NoiDungRtl[:KhopModule.start()] + HeaderMoi + KhoiChenNoiBo + PhanConLai


class RTLGenerator:
    """
    Bộ tạo mã nguồn Verilog RTL tự động từ đặc tả phần cứng.
    Phân loại họ mạch qua `SpecAnalyzer`, điều phối tới hàm sinh chuyên biệt
    và chuẩn hóa mã qua `VerilogLinter` + `RTLPortEnforcer`.
    """

    def __init__(self, ThuMucSrc=None, src_dir=None):
        """Khởi tạo thư mục xuất mã Verilog RTL (mặc định là `../src`)."""
        ThuMucMacDinh = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        self.ThuMucSrc = src_dir if src_dir is not None else (ThuMucSrc if ThuMucSrc is not None else ThuMucMacDinh)
        self.src_dir = self.ThuMucSrc
        os.makedirs(self.ThuMucSrc, exist_ok=True)

    def _write_verilog(self, TenFile=None, MaNguon=None, file_name=None, code=None):
        """Làm sạch cú pháp Verilog bằng `VerilogLinter` rồi ghi ra file `.v` trong thư mục `src`."""
        TenTep = file_name if file_name is not None else TenFile
        MaRtl = code if code is not None else MaNguon
        MaRtlSach = VerilogLinter.sanitize_verilog_code(MaRtl)
        DuongDanXuat = os.path.join(self.ThuMucSrc, TenTep)
        with open(DuongDanXuat, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaRtlSach)
        return DuongDanXuat

    def generate_from_spec(self, NoiDungSpec=None, DuongDanSpec=None, spec_text=None, spec_path=None):
        """
        Điểm vào duy nhất để sinh Verilog RTL từ đặc tả:
          1. Gọi `SpecAnalyzer` phân loại họ mạch (`NhomMach`), tên module và danh sách cổng.
          2. Định tuyến sang bộ sinh RTL tương ứng (hoặc `generate_generic_module` nếu là mạch tùy biến).
          3. Chạy `RTLPortEnforcer.enforce` để đảm bảo danh sách cổng khớp 100% với đặc tả.
        Trả về cặp `(TenModule, DuongDanFileVerilog)`.
        """
        VanBanSpec = spec_text if spec_text is not None else NoiDungSpec
        TepSpec = spec_path if spec_path is not None else DuongDanSpec

        BoPhanTich = SpecAnalyzer(TepSpec if TepSpec else VanBanSpec)
        NhomMach = BoPhanTich.classify_system()
        TenModule = BoPhanTich.extract_module_name()
        DanhSachCong = BoPhanTich.extract_ports()

        if NhomMach == "VENDING":
            TepKetQua = self.generate_vending_machine(VanBanSpec, TenModule)
        elif NhomMach == "ELEVATOR":
            TepKetQua = self.generate_elevator_controller(VanBanSpec, TenModule)
        elif NhomMach == "TRAFFIC":
            TepKetQua = self.generate_traffic_light(VanBanSpec, TenModule)
        elif NhomMach == "MULTIPLIER":
            TepKetQua = self.generate_multiplier(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "ADDER":
            TepKetQua = self.generate_adder(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "SUBTRACTOR":
            TepKetQua = self.generate_subtractor(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "COMPARATOR":
            TepKetQua = self.generate_comparator(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "ALU":
            TepKetQua = self.generate_alu(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "FIFO":
            TepKetQua = self.generate_fifo(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "GRAY_COUNTER":
            TepKetQua = self.generate_gray_counter(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "STOPWATCH":
            TepKetQua = self.generate_stopwatch(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "COUNTER":
            TepKetQua = self.generate_counter(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "ENCODER":
            TepKetQua = self.generate_priority_encoder(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "PULSE_DETECTOR":
            TepKetQua = self.generate_pulse_detector(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "BARREL_SHIFTER":
            TepKetQua = self.generate_barrel_shifter(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "PWM":
            TepKetQua = self.generate_pwm(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "STEPPER_MOTOR":
            TepKetQua = self.generate_stepper_motor(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "UART_TX":
            TepKetQua = self.generate_uart_tx(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "WASHING_MACHINE":
            TepKetQua = self.generate_washing_machine(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "SMART_ALARM":
            TepKetQua = self.generate_smart_alarm(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "SHIFT_REG":
            TepKetQua = self.generate_shift_reg(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "SEQUENCE_DETECTOR":
            TepKetQua = self.generate_sequence_detector(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "DIGITAL_LOCK":
            TepKetQua = self.generate_digital_lock(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "TEMPERATURE_MONITOR":
            TepKetQua = self.generate_temperature_monitor(VanBanSpec, TenModule, DanhSachCong)
        elif NhomMach == "DEBOUNCER":
            TepKetQua = self.generate_debouncer(TenModule, VanBanSpec, DanhSachCong)
        elif NhomMach == "DECODER":
            TepKetQua = self.generate_decoder(VanBanSpec, TenModule, DanhSachCong)
        else:
            TepKetQua = self.generate_generic_module(TenModule, VanBanSpec, DanhSachCong)

        # Bước 3: Ép buộc danh sách cổng Verilog khớp 100% với đặc tả (bổ sung cổng thiếu / cô lập cổng thừa)
        if DanhSachCong and TepKetQua and os.path.exists(TepKetQua):
            with open(TepKetQua, "r", encoding="utf-8", errors="replace") as TepTin:
                MaTho = TepTin.read()
            MaDaSua = RTLPortEnforcer.enforce(MaTho, DanhSachCong)
            if MaDaSua != MaTho:
                with open(TepKetQua, "w", encoding="utf-8") as TepTin:
                    TepTin.write(MaDaSua)
                print(f" -> [RTL Port Enforcer]: Da can chinh cac cong Verilog khop 100% voi dac ta!")

        return TenModule, TepKetQua

    # ==========================================================================
    # NHÓM 1: MẠCH KHỬ RUNG & CÁC HỆ THỐNG MÁY TRẠNG THÁI HỮU HẠN (FSM)
    # ==========================================================================

    def generate_debouncer(self, module_name="button_debouncer", spec_text="", ports=None):
        """Sinh module khử rung nút nhấn (Button Debouncer) dùng thanh ghi dịch 3 bit + phát hiện cạnh lên 1 chu kỳ."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Synchronous Button Debouncer with Pulse Edge Detector
// Auto-generated by Spec2RTL Hardware Synthesis Engine
//==============================================================================
module {module_name} (
    input  wire clk,
    input  wire rst,
    input  wire btn_in,
    output reg  btn_clean,
    output reg  btn_pressed_pulse
);

    reg [2:0] shift_reg;
    reg btn_clean_prev;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            shift_reg <= 3'b000;
            btn_clean <= 1'b0;
            btn_clean_prev <= 1'b0;
            btn_pressed_pulse <= 1'b0;
        end else begin
            // Nap tin hieu vat ly btn_in vao thanh ghi dich de khu rung
            shift_reg <= {{shift_reg[1:0], btn_in}};

            // Cap nhat trang thai phim on dinh
            if (shift_reg == 3'b111)
                btn_clean <= 1'b1;
            else if (shift_reg == 3'b000)
                btn_clean <= 1'b0;

            btn_clean_prev <= btn_clean;
            // Tao xung kich 1 chu ky clk khi phim vua nhan xuong
            btn_pressed_pulse <= (btn_clean && !btn_clean_prev);
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)


    def generate_vending_machine(self, spec_text="", module_name="vending_machine"):
        """Sinh mạch FSM Máy bán nước tự động (nhận xu 5k/10k, mốc 15k nhả nước, 20k nhả nước + thối 5k)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Automatic Beverage Vending Machine FSM
// Auto-generated by Spec2RTL Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       clr,
    input  wire       coin_5k,    // 5.000 VND inserted
    input  wire       coin_10k,   // 10.000 VND inserted
    output reg        dispense,   // 1: Dispense beverage
    output reg        change_5k,  // 1: Return 5.000 VND change
    output reg  [4:0] balance,    // Current balance in thousands (0, 5, 10, 15, 20)
    output wire [2:0] state_out
);

    localparam S_0K        = 3'b000;
    localparam S_5K        = 3'b001;
    localparam S_10K       = 3'b010;
    localparam S_DISPENSE  = 3'b011; // 15k: Dispense
    localparam S_CHANGE    = 3'b100; // 20k: Dispense + 5k change

    reg [2:0] state, next_state;

    assign state_out = state;

    always @(posedge clk or posedge clr) begin
        if (clr)
            state <= S_0K;
        else
            state <= next_state;
    end

    always @(*) begin
        next_state = state;
        case (state)
            S_0K: begin
                if (coin_10k)
                    next_state = S_10K;
                else if (coin_5k)
                    next_state = S_5K;
            end

            S_5K: begin
                if (coin_10k)
                    next_state = S_DISPENSE;
                else if (coin_5k)
                    next_state = S_10K;
            end

            S_10K: begin
                if (coin_10k)
                    next_state = S_CHANGE;
                else if (coin_5k)
                    next_state = S_DISPENSE;
            end

            S_DISPENSE: next_state = S_0K;
            S_CHANGE:   next_state = S_0K;
            default:    next_state = S_0K;
        endcase
    end

    always @(*) begin
        case (state)
            S_0K: begin
                dispense  = 1'b0;
                change_5k = 1'b0;
                balance   = 5'd0;
            end
            S_5K: begin
                dispense  = 1'b0;
                change_5k = 1'b0;
                balance   = 5'd5;
            end
            S_10K: begin
                dispense  = 1'b0;
                change_5k = 1'b0;
                balance   = 5'd10;
            end
            S_DISPENSE: begin
                dispense  = 1'b1;
                change_5k = 1'b0;
                balance   = 5'd15;
            end
            S_CHANGE: begin
                dispense  = 1'b1;
                change_5k = 1'b1;
                balance   = 5'd20;
            end
            default: begin
                dispense  = 1'b0;
                change_5k = 1'b0;
                balance   = 5'd0;
            end
        endcase
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_traffic_light(self, spec_text="", module_name="traffic_light"):
        """Sinh mạch FSM Điều khiển đèn giao thông ngã tư (ưu tiên đường chính, chuyển pha theo `car_sensor` và timer)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Intersection Traffic Light Controller FSM
// Auto-generated by Spec2RTL Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       clr,
    input  wire       car_sensor,
    output reg  [1:0] light_main, // 2'b00: Green, 2'b01: Yellow, 2'b10: Red
    output reg  [1:0] light_side, // 2'b00: Green, 2'b01: Yellow, 2'b10: Red
    output wire [1:0] state_out
);

    localparam S0_MAIN_GREEN  = 2'b00;
    localparam S1_MAIN_YELLOW = 2'b01;
    localparam S2_SIDE_GREEN  = 2'b10;
    localparam S3_SIDE_YELLOW = 2'b11;

    localparam COLOR_GREEN  = 2'b00;
    localparam COLOR_YELLOW = 2'b01;
    localparam COLOR_RED    = 2'b10;

    localparam TIME_GREEN  = 4'd6;
    localparam TIME_YELLOW = 4'd2;

    reg [1:0] state, next_state;
    reg [3:0] timer;

    assign state_out = state;

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            state <= S0_MAIN_GREEN;
            timer <= 4'd0;
        end else begin
            if (state != next_state) begin
                state <= next_state;
                timer <= 4'd0;
            end else begin
                timer <= timer + 1'b1;
            end
        end
    end

    always @(*) begin
        next_state = state;
        case (state)
            S0_MAIN_GREEN: begin
                if ((timer >= (TIME_GREEN - 1'b1)) && car_sensor)
                    next_state = S1_MAIN_YELLOW;
            end

            S1_MAIN_YELLOW: begin
                if (timer >= (TIME_YELLOW - 1'b1))
                    next_state = S2_SIDE_GREEN;
            end

            S2_SIDE_GREEN: begin
                if (timer >= (TIME_GREEN - 1'b1))
                    next_state = S3_SIDE_YELLOW;
            end

            S3_SIDE_YELLOW: begin
                if (timer >= (TIME_YELLOW - 1'b1))
                    next_state = S0_MAIN_GREEN;
            end

            default: next_state = S0_MAIN_GREEN;
        endcase
    end

    always @(*) begin
        case (state)
            S0_MAIN_GREEN: begin
                light_main = COLOR_GREEN;
                light_side = COLOR_RED;
            end

            S1_MAIN_YELLOW: begin
                light_main = COLOR_YELLOW;
                light_side = COLOR_RED;
            end

            S2_SIDE_GREEN: begin
                light_main = COLOR_RED;
                light_side = COLOR_GREEN;
            end

            S3_SIDE_YELLOW: begin
                light_main = COLOR_RED;
                light_side = COLOR_YELLOW;
            end

            default: begin
                light_main = COLOR_GREEN;
                light_side = COLOR_RED;
            end
        endcase
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_elevator_controller(self, spec_text="", module_name="elevator_controller"):
        """Sinh mạch FSM Điều khiển thang máy 5 tầng (lưu yêu cầu gọi tầng, điều khiển động cơ lên/xuống và đóng/mở cửa)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: 5-Floor Intelligent Elevator Controller FSM
// Auto-generated by Spec2RTL Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       clr,
    input  wire [4:0] floor_req,     // Buttons for floors 1..5 (bit 0 = floor 1, bit 4 = floor 5)
    output reg  [2:0] current_floor, // 1 to 5
    output reg        door_open,     // 1: Door is open, 0: Door is closed
    output reg        motor_up,      // 1: Motor moving up
    output reg        motor_down,    // 1: Motor moving down
    output wire [1:0] state_out
);

    localparam S_IDLE      = 2'b00;
    localparam S_UP        = 2'b01;
    localparam S_DOWN      = 2'b10;
    localparam S_DOOR_OPEN = 2'b11;

    reg [1:0] state;
    reg [4:0] requests;
    reg [1:0] door_cnt;

    assign state_out = state;

    wire [4:0] all_req;
    assign all_req = requests | floor_req;

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            state         <= S_IDLE;
            current_floor <= 3'd1;
            requests      <= 5'd0;
            door_cnt      <= 2'd0;
            door_open     <= 1'b0;
            motor_up      <= 1'b0;
            motor_down    <= 1'b0;
        end else begin
            requests <= requests | floor_req;

            case (state)
                S_IDLE: begin
                    motor_up   <= 1'b0;
                    motor_down <= 1'b0;
                    door_open  <= 1'b0;
                    door_cnt   <= 2'd0;

                    if (all_req != 5'd0) begin
                        if (all_req[current_floor - 1'b1]) begin
                            state     <= S_DOOR_OPEN;
                            door_open <= 1'b1;
                        end else if (all_req > (5'b00001 << (current_floor - 1'b1))) begin
                            state    <= S_UP;
                            motor_up <= 1'b1;
                        end else begin
                            state      <= S_DOWN;
                            motor_down <= 1'b1;
                        end
                    end
                end

                S_UP: begin
                    motor_up <= 1'b1;
                    if (current_floor < 3'd5)
                        current_floor <= current_floor + 1'b1;

                    if (all_req[current_floor]) begin
                        state     <= S_DOOR_OPEN;
                        motor_up  <= 1'b0;
                        door_open <= 1'b1;
                    end
                end

                S_DOWN: begin
                    motor_down <= 1'b1;
                    if (current_floor > 3'd1)
                        current_floor <= current_floor - 1'b1;

                    if (all_req[current_floor - 2'd2]) begin
                        state      <= S_DOOR_OPEN;
                        motor_down <= 1'b0;
                        door_open  <= 1'b1;
                    end
                end

                S_DOOR_OPEN: begin
                    motor_up   <= 1'b0;
                    motor_down <= 1'b0;
                    door_open  <= 1'b1;
                    requests[current_floor - 1'b1] <= 1'b0;

                    if (door_cnt >= 2'd2) begin
                        door_open <= 1'b0;
                        door_cnt  <= 2'd0;
                        state     <= S_IDLE;
                    end else begin
                        door_cnt <= door_cnt + 1'b1;
                    end
                end
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    # ==========================================================================
    # NHÓM 2: CÁC KHỐI SỐ HỌC & XỬ LÝ TÍN HIỆU SỐ (ALU, NHÂN, CỘNG, TRỪ, SO SÁNH)
    # ==========================================================================

    def generate_alu(self, module_name, spec_text="", ports=None):
        """Sinh mạch Khối tính toán số học & logic ALU đồng bộ (mặc định 4-bit, tự nhận diện độ rộng bit từ spec)."""
        width = 4
        m_w = re.search(r"(\d+)\s*[-_]?bit", spec_text.lower())
        if m_w:
            width = int(m_w.group(1))

        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Synthesizable Arithmetic Logic Unit (ALU)
// Auto-generated by Spec2RTL Autonomous Engine (RTLLM Benchmark Standard)
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [{width-1}:0]      a,
    input  wire [{width-1}:0]      b,
    input  wire [2:0]       opcode, // 000:ADD, 001:SUB, 010:AND, 011:OR, 100:XOR, 101:NOT, 110:SHL, 111:COMP
    output reg  [{width-1}:0]      alu_out,
    output reg              zero,
    output reg              carry
);

    reg [{width-1}:0] next_out;
    reg               next_carry;

    always @(*) begin
        case (opcode)
            3'b000: {{next_carry, next_out}} = a + b;
            3'b001: {{next_carry, next_out}} = a - b;
            3'b010: begin next_out = a & b; next_carry = 1'b0; end
            3'b011: begin next_out = a | b; next_carry = 1'b0; end
            3'b100: begin next_out = a ^ b; next_carry = 1'b0; end
            3'b101: begin next_out = ~a;    next_carry = 1'b0; end
            3'b110: begin next_out = a << 1; next_carry = a[{width-1}]; end
            3'b111: begin next_out = (a == b) ? {width}'d1 : {width}'d0; next_carry = (a < b); end
            default: begin next_out = {width}'d0; next_carry = 1'b0; end
        endcase
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            alu_out <= {width}'d0;
            zero    <= 1'b0;
            carry   <= 1'b0;
        end else begin
            alu_out <= next_out;
            carry   <= next_carry;
            zero    <= (next_out == {width}'d0);
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_multiplier(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ nhân nhị phân đồng bộ (đầu vào N-bit, tích đầu ra 2N-bit)."""
        width = 4
        m_w = re.search(r"(\d+)\s*[-_]?bit", spec_text.lower())
        if m_w: width = int(m_w.group(1))

        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Synthesizable Digital Multiplier (Output: {2*width}-bit)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [{width-1}:0]      a,
    input  wire [{width-1}:0]      b,
    output reg  [{2*width-1}:0]    product
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            product <= {2*width}'d0;
        end else begin
            product <= a * b;
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_adder(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ cộng toàn phần có nhớ vào/nhớ ra (`cin`/`cout`), mặc định 8-bit."""
        width = 8
        m_w = re.search(r"(\d+)\s*[-_]?bit", spec_text.lower())
        if m_w: width = int(m_w.group(1))

        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Synthesizable Binary Adder with Carry In / Carry Out
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [{width-1}:0]      a,
    input  wire [{width-1}:0]      b,
    input  wire             cin,
    output reg  [{width-1}:0]      sum,
    output reg              cout
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            sum  <= {width}'d0;
            cout <= 1'b0;
        end else begin
            {{cout, sum}} <= a + b + cin;
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_subtractor(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ trừ nhị phân đồng bộ kèm cờ mượn `borrow` khi `a < b`."""
        width = 4
        m_w = re.search(r"(\d+)\s*[-_]?bit", spec_text.lower())
        if m_w: width = int(m_w.group(1))

        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Synthesizable Binary Subtractor with Borrow Flag
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [{width-1}:0]      a,
    input  wire [{width-1}:0]      b,
    output reg  [{width-1}:0]      diff,
    output reg              borrow
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            diff   <= {width}'d0;
            borrow <= 1'b0;
        end else begin
            diff   <= a - b;
            borrow <= (a < b);
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_comparator(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ so sánh độ lớn hai số (`greater`, `equal`, `less`), mặc định 4-bit."""
        width = 4
        m_w = re.search(r"(\d+)\s*[-_]?bit", spec_text.lower())
        if m_w: width = int(m_w.group(1))

        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Magnitude Comparator (Greater, Equal, Less)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [{width-1}:0]      a,
    input  wire [{width-1}:0]      b,
    output reg              greater,
    output reg              equal,
    output reg              less
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            greater <= 1'b0;
            equal   <= 1'b0;
            less    <= 1'b0;
        end else begin
            greater <= (a > b);
            equal   <= (a == b);
            less    <= (a < b);
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    # ==========================================================================
    # NHÓM 3: BỘ ĐẾM, ĐỒNG HỒ BẤM GIỜ, PWM & ĐIỀU KHIỂN ĐỘNG CƠ
    # ==========================================================================

    def generate_stopwatch(self, module_name, spec_text="", ports=None):
        """Sinh mạch Đồng hồ bấm giờ BCD 0–9 tích hợp bộ giải mã LED 7 đoạn (mức tích cực thấp)."""
        en_pin = "start_stop"
        clk_pin = "clk"
        rst_pin = "rst"
        count_pin = "count"
        seg_pin = "seg"
        if ports:
            for p in ports:
                if p.get("is_clk"): clk_pin = p["name"]
                elif p.get("is_rst"): rst_pin = p["name"]
                elif p.get("direction") == "input": en_pin = p["name"]
                elif p.get("direction") == "output":
                    if p.get("width") == 7 or "seg" in p["name"].lower(): seg_pin = p["name"]
                    else: count_pin = p["name"]

        code = f"""//==============================================================================
// Module: {module_name}
// Description: 0-9 BCD Stopwatch with 7-Segment Display Decoder (Active-Low)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       {clk_pin},
    input  wire       {rst_pin},
    input  wire       {en_pin},
    output reg  [3:0] {count_pin},
    output reg  [6:0] {seg_pin}
);

    always @(posedge {clk_pin} or posedge {rst_pin}) begin
        if ({rst_pin}) begin
            {count_pin} <= 4'd0;
        end else if ({en_pin}) begin
            if ({count_pin} >= 4'd9)
                {count_pin} <= 4'd0;
            else
                {count_pin} <= {count_pin} + 4'd1;
        end
    end

    // Active-Low 7-Segment Decoder (a, b, c, d, e, f, g)
    always @(*) begin
        case ({count_pin})
            4'd0: {seg_pin} = 7'b1000000;
            4'd1: {seg_pin} = 7'b1111001;
            4'd2: {seg_pin} = 7'b0100100;
            4'd3: {seg_pin} = 7'b0110000;
            4'd4: {seg_pin} = 7'b0011001;
            4'd5: {seg_pin} = 7'b0010010;
            4'd6: {seg_pin} = 7'b0000010;
            4'd7: {seg_pin} = 7'b1111000;
            4'd8: {seg_pin} = 7'b0000000;
            4'd9: {seg_pin} = 7'b0010000;
            default: {seg_pin} = 7'b1111111;
        endcase
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_counter(self, module_name, spec_text="", ports=None):
        """
        Sinh mạch Bộ đếm đồng bộ (tự động phân nhánh theo đặc tả):
          - Nếu có LED 7 đoạn / stopwatch: gọi `generate_stopwatch`.
          - Nếu là đếm giây BCD 00–59: tạo bộ đếm 2 chữ số kèm cờ tràn `rollover`.
          - Mặc định: bộ đếm nhị phân lên/xuống có `enable`, `up_down` và cờ `tc`.
        """
        raw = remove_vietnamese_accents(spec_text.lower()) if spec_text else ""
        has_seg = any("seg" in (p.get("name") or "").lower() for p in (ports or []))
        if has_seg or any(k in raw for k in ["seg", "7 doan", "7-segment", "stopwatch", "dong ho", "led 7"]):
            return self.generate_stopwatch(module_name, spec_text, ports)

        has_bcd = any("sec" in (p.get("name") or "").lower() for p in (ports or [])) or "bcd" in raw
        if has_bcd:
            en_pin = "en" if any("en" in (p.get("name") or "").lower() for p in (ports or [])) else "enable"
            ones_pin = "sec_ones" if any("sec_ones" in (p.get("name") or "").lower() for p in (ports or [])) else "ones"
            tens_pin = "sec_tens" if any("sec_tens" in (p.get("name") or "").lower() for p in (ports or [])) else "tens"
            rollover_pin = "rollover" if any("rollover" in (p.get("name") or "").lower() for p in (ports or [])) else "tc"
            code = f"""//==============================================================================
// Module: {module_name}
// Description: BCD 00-59 Synchronous Counter
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire       {en_pin},
    output reg  [3:0] {ones_pin},
    output reg  [3:0] {tens_pin},
    output reg        {rollover_pin}
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            {ones_pin} <= 4'd0;
            {tens_pin} <= 4'd0;
            {rollover_pin} <= 1'b0;
        end else if ({en_pin}) begin
            if ({ones_pin} >= 4'd9) begin
                {ones_pin} <= 4'd0;
                if ({tens_pin} >= 4'd5) begin
                    {tens_pin} <= 4'd0;
                    {rollover_pin} <= 1'b1;
                end else begin
                    {tens_pin} <= {tens_pin} + 4'd1;
                    {rollover_pin} <= 1'b0;
                end
            end else begin
                {ones_pin} <= {ones_pin} + 4'd1;
                {rollover_pin} <= 1'b0;
            end
        end else begin
            {rollover_pin} <= 1'b0;
        end
    end

endmodule
"""
            return self._write_verilog(f"{module_name}.v", code)

        width = 4
        m_w = re.search(r"(\d+)\s*[-_]?bit", spec_text.lower())
        if m_w:
            width = int(m_w.group(1))

        width_decl = f"[{width-1}:0] " if width > 1 else "       "
        val_reset = f"{width}'d0" if width > 1 else "1'b0"

        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Synchronous Up/Down Counter with Enable & Terminal Count
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire             enable,
    input  wire             up_down, // 1: Count Up, 0: Count Down
    output reg  {width_decl}count,
    output wire             tc       // Terminal Count flag
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= {val_reset};
        end else if (enable) begin
            if (up_down)
                count <= count + 1'b1;
            else
                count <= count - 1'b1;
        end
    end

    assign tc = (up_down && count == {{{width}{{1'b1}}}}) || (!up_down && count == {val_reset});

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_pwm(self, module_name, spec_text="", ports=None):
        """Sinh mạch Tạo xung điều chế độ rộng PWM 8-bit (so sánh `counter_val < duty_cycle`)."""
        width = 8
        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Digital Pulse Width Modulation (PWM) Generator
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [{width-1}:0]      duty_cycle,
    output reg              pwm_out,
    output reg  [{width-1}:0]      counter_val
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            counter_val <= {width}'d0;
            pwm_out     <= 1'b0;
        end else begin
            counter_val <= counter_val + 1'b1;
            pwm_out     <= (counter_val < duty_cycle);
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_stepper_motor(self, module_name, spec_text="", ports=None):
        """Sinh mạch Điều khiển động cơ bước 4 pha (chế độ Full-Step, quay thuận/nghịch theo `dir`)."""
        clk_pin, rst_pin, dir_pin, en_pin, phase_pin = "clk", "rst", "dir", "en", "phase_out"
        if ports:
            for p in ports:
                if p.get("is_clk"): clk_pin = p["name"]
                elif p.get("is_rst"): rst_pin = p["name"]
                elif "dir" in p["name"].lower(): dir_pin = p["name"]
                elif any(k in p["name"].lower() for k in ["en", "run"]): en_pin = p["name"]
                elif any(k in p["name"].lower() for k in ["phase", "step", "out"]): phase_pin = p["name"]

        code = f"""//==============================================================================
// Module: {module_name}
// Description: 4-Phase Stepper Motor Controller (Full-Step Mode, CW / CCW)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       {clk_pin},
    input  wire       {rst_pin},
    input  wire       {dir_pin}, // 1: Clockwise, 0: Counter-Clockwise
    input  wire       {en_pin},  // 1: Enable rotation, 0: Stop
    output reg  [3:0] {phase_pin}
);

    always @(posedge {clk_pin} or posedge {rst_pin}) begin
        if ({rst_pin}) begin
            {phase_pin} <= 4'b0001;
        end else if ({en_pin}) begin
            if ({dir_pin}) begin
                case ({phase_pin})
                    4'b0001: {phase_pin} <= 4'b0010;
                    4'b0010: {phase_pin} <= 4'b0100;
                    4'b0100: {phase_pin} <= 4'b1000;
                    4'b1000: {phase_pin} <= 4'b0001;
                    default: {phase_pin} <= 4'b0001;
                endcase
            end else begin
                case ({phase_pin})
                    4'b1000: {phase_pin} <= 4'b0100;
                    4'b0100: {phase_pin} <= 4'b0010;
                    4'b0010: {phase_pin} <= 4'b0001;
                    4'b0001: {phase_pin} <= 4'b1000;
                    default: {phase_pin} <= 4'b0001;
                endcase
            end
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    # ==========================================================================
    # NHÓM 4: GIAO TIẾP NỐI TIẾP & HỆ THỐNG ĐIỀU KHIỂN / AN NINH THÔNG MINH
    # ==========================================================================

    def generate_uart_tx(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ phát UART 8-bit chuẩn khung 8N1 (1 Start bit, 8 Data bit LSB trước, 1 Stop bit)."""
        clk_pin, rst_pin, data_pin, start_pin, serial_pin, busy_pin = "clk", "rst", "tx_data", "tx_start", "tx_serial", "tx_busy"
        if ports:
            for p in ports:
                if p.get("is_clk"): clk_pin = p["name"]
                elif p.get("is_rst"): rst_pin = p["name"]
                elif p.get("direction") == "input":
                    if p.get("width") == 8 or "data" in p["name"].lower(): data_pin = p["name"]
                    else: start_pin = p["name"]
                elif p.get("direction") == "output":
                    if any(k in p["name"].lower() for k in ["busy", "ready", "done"]): busy_pin = p["name"]
                    else: serial_pin = p["name"]

        code = f"""//==============================================================================
// Module: {module_name}
// Description: 8-Bit UART Transmitter (1 Start bit, 8 Data bits, 1 Stop bit)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       {clk_pin},
    input  wire       {rst_pin},
    input  wire [7:0] {data_pin},
    input  wire       {start_pin},
    output reg        {serial_pin},
    output reg        {busy_pin}
);

    localparam S_IDLE  = 2'b00;
    localparam S_START = 2'b01;
    localparam S_DATA  = 2'b10;
    localparam S_STOP  = 2'b11;

    reg [1:0] state;
    reg [2:0] bit_idx;
    reg [7:0] data_buf;

    always @(posedge {clk_pin} or posedge {rst_pin}) begin
        if ({rst_pin}) begin
            state        <= S_IDLE;
            {serial_pin} <= 1'b1;
            {busy_pin}   <= 1'b0;
            bit_idx      <= 3'd0;
            data_buf     <= 8'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    {serial_pin} <= 1'b1;
                    {busy_pin}   <= 1'b0;
                    if ({start_pin}) begin
                        data_buf    <= {data_pin};
                        state       <= S_START;
                        {busy_pin}   <= 1'b1;
                    end
                end
                S_START: begin
                    {serial_pin} <= 1'b0; // Start bit
                    {busy_pin}   <= 1'b1;
                    bit_idx      <= 3'd0;
                    state        <= S_DATA;
                end
                S_DATA: begin
                    {serial_pin} <= data_buf[bit_idx];
                    {busy_pin}   <= 1'b1;
                    if (bit_idx == 3'd7) begin
                        state <= S_STOP;
                    end else begin
                        bit_idx <= bit_idx + 1'b1;
                    end
                end
                S_STOP: begin
                    {serial_pin} <= 1'b1; // Stop bit
                    {busy_pin}   <= 1'b1;
                    state        <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_washing_machine(self, module_name, spec_text="", ports=None):
        """Sinh mạch FSM Điều khiển máy giặt tự động 4 pha (IDLE -> FILL -> WASH -> SPIN, khóa an toàn khi mở nắp)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Multi-Stage Automatic Washing Machine FSM Controller
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire       start_btn,
    input  wire       water_full,
    input  wire       lid_closed,
    output reg  [1:0] state,
    output reg        water_valve,
    output reg        motor_run,
    output reg        warning
);

    localparam S_IDLE  = 2'b00;
    localparam S_FILL  = 2'b01;
    localparam S_WASH  = 2'b10;
    localparam S_SPIN  = 2'b11;

    reg [3:0] timer;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state       <= S_IDLE;
            water_valve <= 1'b0;
            motor_run   <= 1'b0;
            warning     <= 1'b0;
            timer       <= 4'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    water_valve <= 1'b0;
                    motor_run   <= 1'b0;
                    warning     <= 1'b0;
                    timer       <= 4'd0;
                    if (start_btn && lid_closed)
                        state <= S_FILL;
                end
                S_FILL: begin
                    water_valve <= 1'b1;
                    motor_run   <= 1'b0;
                    warning     <= 1'b0;
                    if (water_full) begin
                        water_valve <= 1'b0;
                        state       <= S_WASH;
                        timer       <= 4'd0;
                    end
                end
                S_WASH: begin
                    water_valve <= 1'b0;
                    if (!lid_closed) begin
                        motor_run <= 1'b0;
                        warning   <= 1'b1;
                    end else begin
                        motor_run <= 1'b1;
                        warning   <= 1'b0;
                        if (timer >= 4'd9) begin
                            state <= S_SPIN;
                            timer <= 4'd0;
                        end else begin
                            timer <= timer + 1'b1;
                        end
                    end
                end
                S_SPIN: begin
                    water_valve <= 1'b0;
                    if (!lid_closed) begin
                        motor_run <= 1'b0;
                        warning   <= 1'b1;
                    end else begin
                        motor_run <= 1'b1;
                        warning   <= 1'b0;
                        if (timer >= 4'd4) begin
                            state <= S_IDLE;
                            timer <= 4'd0;
                        end else begin
                            timer <= timer + 1'b1;
                        end
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_smart_alarm(self, module_name, spec_text="", ports=None):
        """Sinh mạch Hệ thống báo động thông minh (ưu tiên cảnh báo cháy/khói trước đột nhập PIR)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Smart Home Dual-Threat Alarm (Fire & Intruder Priority System)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire       motion_pir,
    input  wire       smoke_gas,
    input  wire       arm_mode,
    output reg        siren,
    output reg        sprinkler,
    output reg  [1:0] status_code
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            siren       <= 1'b0;
            sprinkler   <= 1'b0;
            status_code <= 2'b00;
        end else begin
            if (smoke_gas) begin
                siren       <= 1'b1;
                sprinkler   <= 1'b1;
                status_code <= 2'b10;
            end else if (arm_mode && motion_pir) begin
                siren       <= 1'b1;
                sprinkler   <= 1'b0;
                status_code <= 2'b01;
            end else begin
                siren       <= 1'b0;
                sprinkler   <= 1'b0;
                status_code <= 2'b00;
            end
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    # ==========================================================================
    # NHÓM 5: THANH GHI DỊCH, BỘ DÒ CHUỖI, KHÓA SỐ, FIFO & HẠ TẦNG SỐ PHỔ THÔNG
    # ==========================================================================

    def generate_shift_reg(self, module_name, spec_text="", ports=None):
        """Sinh mạch Thanh ghi dịch đa năng 4-bit (Giữ, Dịch trái, Dịch phải, Nạp song song)."""
        width = 4
        code = f"""//==============================================================================
// Module: {module_name}
// Description: {width}-bit Universal Shift Register (Hold, Shift Left, Shift Right, Parallel Load)
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire             clk,
    input  wire             rst,
    input  wire [1:0]       mode,      // 00: Hold, 01: Shift Left, 10: Shift Right, 11: Parallel Load
    input  wire             sin_left,  // Serial input for shift left
    input  wire             sin_right, // Serial input for shift right
    input  wire [{width-1}:0]      d_in,      // Parallel data input
    output reg  [{width-1}:0]      q_out      // Parallel data output
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            q_out <= {width}'d0;
        end else begin
            case (mode)
                2'b00: q_out <= q_out;
                2'b01: q_out <= {{q_out[{width-2}:0], sin_left}};
                2'b10: q_out <= {{sin_right, q_out[{width-1}:1]}};
                2'b11: q_out <= d_in;
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_sequence_detector(self, module_name, spec_text="", ports=None):
        """Sinh mạch FSM Dò chuỗi bit nối tiếp '1011' (kiến trúc không gối đầu Non-Overlapping)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Synchronous Sequence Detector FSM (Detects '1011')
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire       din,
    output reg        detected,
    output wire [2:0] state_out
);

    localparam S_IDLE = 3'b000;
    localparam S_1    = 3'b001;
    localparam S_10   = 3'b010;
    localparam S_101  = 3'b011;
    localparam S_1011 = 3'b100;

    reg [2:0] state, next_state;

    assign state_out = state;

    always @(posedge clk or posedge rst) begin
        if (rst)
            state <= S_IDLE;
        else
            state <= next_state;
    end

    always @(*) begin
        next_state = state;
        case (state)
            S_IDLE: next_state = (din) ? S_1 : S_IDLE;
            S_1:    next_state = (din) ? S_1 : S_10;
            S_10:   next_state = (din) ? S_101 : S_IDLE;
            S_101:  next_state = (din) ? S_1011 : S_10;
            S_1011: next_state = S_IDLE;
            default: next_state = S_IDLE;
        endcase
    end

    always @(*) begin
        detected = (state == S_1011);
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_digital_lock(self, module_name, spec_text="", ports=None):
        """
        Sinh mạch FSM Khóa mã số điện tử bảo mật (mặc định 4 chữ số `4-2-7-9` hoặc trích từ spec):
        Tự động ánh xạ tên cổng theo spec, hỗ trợ đếm số lần nhập sai và kích hoạt còi báo động khi sai quá giới hạn.
        """
        clk_pin = "clk"
        rst_pin = "rst"
        key_pin = "key_in"
        enter_pin = "enter"
        unlock_pin = "unlock"
        alarm_pin = "alarm"
        err_pin = "err_count"
        has_err_count = False
        has_state_out = False
        state_out_pin = "state_out"

        if ports:
            for p in ports:
                p_name = p["name"]
                p_dir = p.get("direction", "input")
                p_w = p.get("width", 1)
                if p_dir == "input":
                    if p.get("is_clk"): clk_pin = p_name
                    elif p.get("is_rst"): rst_pin = p_name
                    elif p_w == 4 or any(k in p_name.lower() for k in ["key", "code", "data", "pass", "digit"]):
                        key_pin = p_name
                    else:
                        enter_pin = p_name
                elif p_dir == "output":
                    if "state" in p_name.lower():
                        has_state_out = True
                        state_out_pin = p_name
                    elif any(k in p_name.lower() for k in ["err", "fail", "attempt"]):
                        has_err_count = True
                        err_pin = p_name
                    elif any(k in p_name.lower() for k in ["alarm", "warn", "buzz"]):
                        alarm_pin = p_name
                    else:
                        unlock_pin = p_name
        else:
            has_err_count = True
            err_pin = "attempts_left"
            has_state_out = True

        m_pw = re.findall(r"\b(\d)\s*(?:->|-|,)\s*(\d)\s*(?:->|-|,)\s*(\d)(?:\s*(?:->|-|,)\s*(\d))?", spec_text)
        if m_pw:
            p1, p2, p3, p4 = m_pw[0]
            d1, d2, d3 = int(p1), int(p2), int(p3)
            d4 = int(p4) if p4 else 0
            has_4th = bool(p4)
        else:
            d1, d2, d3, d4 = 4, 2, 7, 9
            has_4th = True

        is_err_up = "err" in err_pin.lower()
        err_rst_val = "2'd0" if is_err_up else "2'd3"
        err_fail_val = "2'd3" if is_err_up else "2'd0"

        ports_decl = [
            f"    input  wire       {clk_pin}",
            f"    input  wire       {rst_pin}",
            f"    input  wire [3:0] {key_pin}",
            f"    input  wire       {enter_pin}",
            f"    output reg        {unlock_pin}",
            f"    output reg        {alarm_pin}"
        ]
        if has_err_count:
            ports_decl.append(f"    output reg  [1:0] {err_pin}")
        if has_state_out:
            ports_decl.append(f"    output wire [2:0] {state_out_pin}")

        port_str = ",\n".join(ports_decl)
        state_wire = f"\n    assign {state_out_pin} = state;\n" if has_state_out else ""

        code = f"""//==============================================================================
// Module: {module_name}
// Description: Digital Security Combination Lock FSM
// Auto-generated by Spec2RTL Autonomous Engine
//==============================================================================
module {module_name} (
{port_str}
);

    localparam S_INIT   = 3'b000;
    localparam S_DIGIT1 = 3'b001;
    localparam S_DIGIT2 = 3'b010;
    localparam S_DIGIT3 = 3'b011;
    localparam S_PASS   = 3'b100;
    localparam S_ALARM  = 3'b101;

    // Password Preset: {d1} - {d2} - {d3}{f" - {d4}" if has_4th else ""}
    localparam PASS_1 = 4'd{d1};
    localparam PASS_2 = 4'd{d2};
    localparam PASS_3 = 4'd{d3};
    localparam PASS_4 = 4'd{d4};

    reg [2:0] state;{state_wire}

    always @(posedge {clk_pin} or posedge {rst_pin}) begin
        if ({rst_pin}) begin
            state        <= S_INIT;
            {unlock_pin} <= 1'b0;
            {alarm_pin}  <= 1'b0;
            {f"{err_pin} <= {err_rst_val};" if has_err_count else ""}
        end else if ({enter_pin}) begin
            case (state)
                S_INIT: begin
                    if ({key_pin} == PASS_1) begin
                        state <= S_DIGIT1;
                    end else begin
                        state <= S_INIT;
                        {f'''if ({err_pin} {"< 2'd2" if is_err_up else "> 2'd1"})
                            {err_pin} <= {err_pin} {"+ 1'b1" if is_err_up else "- 1'b1"};
                        else begin
                            {err_pin} <= {err_fail_val};
                            state     <= S_ALARM;
                            {alarm_pin} <= 1'b1;
                        end''' if has_err_count else f"state <= S_ALARM; {alarm_pin} <= 1'b1;"}
                    end
                end

                S_DIGIT1: begin
                    if ({key_pin} == PASS_2) begin
                        state <= S_DIGIT2;
                    end else begin
                        state <= S_INIT;
                        {f'''if ({err_pin} {"< 2'd2" if is_err_up else "> 2'd1"})
                            {err_pin} <= {err_pin} {"+ 1'b1" if is_err_up else "- 1'b1"};
                        else begin
                            {err_pin} <= {err_fail_val};
                            state     <= S_ALARM;
                            {alarm_pin} <= 1'b1;
                        end''' if has_err_count else f"state <= S_ALARM; {alarm_pin} <= 1'b1;"}
                    end
                end

                S_DIGIT2: begin
                    if ({key_pin} == PASS_3) begin
                        state <= {"S_DIGIT3" if has_4th else "S_PASS"};
                        {f"{unlock_pin} <= 1'b1;" if not has_4th else ""}
                    end else begin
                        state <= S_INIT;
                        {f'''if ({err_pin} {"< 2'd2" if is_err_up else "> 2'd1"})
                            {err_pin} <= {err_pin} {"+ 1'b1" if is_err_up else "- 1'b1"};
                        else begin
                            {err_pin} <= {err_fail_val};
                            state     <= S_ALARM;
                            {alarm_pin} <= 1'b1;
                        end''' if has_err_count else f"state <= S_ALARM; {alarm_pin} <= 1'b1;"}
                    end
                end

                S_DIGIT3: begin
                    if ({key_pin} == PASS_4) begin
                        state        <= S_PASS;
                        {unlock_pin} <= 1'b1;
                        {alarm_pin}  <= 1'b0;
                        {f"{err_pin} <= {err_rst_val};" if has_err_count else ""}
                    end else begin
                        state <= S_INIT;
                        {f'''if ({err_pin} {"< 2'd2" if is_err_up else "> 2'd1"})
                            {err_pin} <= {err_pin} {"+ 1'b1" if is_err_up else "- 1'b1"};
                        else begin
                            {err_pin} <= {err_fail_val};
                            state     <= S_ALARM;
                            {alarm_pin} <= 1'b1;
                        end''' if has_err_count else f"state <= S_ALARM; {alarm_pin} <= 1'b1;"}
                    end
                end

                S_PASS: begin
                    {unlock_pin} <= 1'b1;
                end

                S_ALARM: begin
                    state       <= S_ALARM;
                    {alarm_pin} <= 1'b1;
                    {f"{err_pin} <= {err_fail_val};" if has_err_count else ""}
                end

                default: state <= S_INIT;
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_fifo(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ đệm hàng đợi FIFO đồng bộ (độ sâu 8 ô, rộng 8-bit) kèm cờ `full` và `empty`."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Synchronous FIFO Buffer (8 depth, 8-bit width)
// Auto-generated by Spec2RTL Autonomous Engine (RTLLM Benchmark Standard)
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire       wr_en,
    input  wire       rd_en,
    input  wire [7:0] data_in,
    output reg  [7:0] data_out,
    output wire       full,
    output wire       empty
);

    reg [7:0] mem [0:7];
    reg [2:0] wr_ptr, rd_ptr;
    reg [3:0] fifo_count;

    assign full  = (fifo_count == 4'd8);
    assign empty = (fifo_count == 4'd0);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            wr_ptr     <= 3'd0;
            rd_ptr     <= 3'd0;
            fifo_count <= 4'd0;
            data_out   <= 8'd0;
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr] <= data_in;
                wr_ptr      <= wr_ptr + 1'b1;
            end
            if (rd_en && !empty) begin
                data_out <= mem[rd_ptr];
                rd_ptr   <= rd_ptr + 1'b1;
            end
            case ({{wr_en && !full, rd_en && !empty}})
                2'b10: fifo_count <= fifo_count + 1'b1;
                2'b01: fifo_count <= fifo_count - 1'b1;
                default: fifo_count <= fifo_count;
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_gray_counter(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ đếm mã Gray 4-bit đồng bộ (mỗi bước nhảy chỉ đổi đúng 1 bit, hỗ trợ đếm lên/xuống)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: 4-bit Synchronous Gray Code Counter
// Auto-generated by Spec2RTL Autonomous Engine (VerilogEval Benchmark Standard)
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire       enable,
    output reg  [3:0] gray_out,
    input  wire       up_down,
    output wire [3:0] count,
    output wire       tc
);

    reg [3:0] bin_cnt;

    assign count = gray_out;
    assign tc = (bin_cnt == 4'd15);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            bin_cnt  <= 4'd0;
            gray_out <= 4'd0;
        end else if (enable) begin
            if (up_down == 1'b0) begin
                bin_cnt  <= bin_cnt - 1'b1;
                gray_out <= ((bin_cnt - 1'b1) >> 1) ^ (bin_cnt - 1'b1);
            end else begin
                bin_cnt  <= bin_cnt + 1'b1;
                gray_out <= ((bin_cnt + 1'b1) >> 1) ^ (bin_cnt + 1'b1);
            end
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_priority_encoder(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ mã hóa ưu tiên 8-sang-3 đồng bộ (ưu tiên bit MSB cao nhất) kèm tín hiệu `valid`."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: 8-to-3 Priority Encoder with Valid Signal
// Auto-generated by Spec2RTL Autonomous Engine (VerilogEval Benchmark Standard)
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] d_in,
    output reg  [2:0] binary_out,
    output reg        valid
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            binary_out <= 3'd0;
            valid      <= 1'b0;
        end else begin
            valid <= (d_in != 8'd0);
            casex (d_in)
                8'b1xxxxxxx: binary_out <= 3'd7;
                8'b01xxxxxx: binary_out <= 3'd6;
                8'b001xxxxx: binary_out <= 3'd5;
                8'b0001xxxx: binary_out <= 3'd4;
                8'b00001xxx: binary_out <= 3'd3;
                8'b000001xx: binary_out <= 3'd2;
                8'b0000001x: binary_out <= 3'd1;
                8'b00000001: binary_out <= 3'd0;
                default:     binary_out <= 3'd0;
            endcase
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_pulse_detector(self, module_name, spec_text="", ports=None):
        """Sinh mạch Phát hiện cạnh lên tạo xung rộng đúng 1 chu kỳ clock (`din_d1 && !din_d2`)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: Single-cycle Rising Edge Pulse Detector
// Auto-generated by Spec2RTL Autonomous Engine (RTLLM Benchmark Standard)
//==============================================================================
module {module_name} (
    input  wire clk,
    input  wire rst,
    input  wire din,
    output reg  pulse_out
);

    reg din_d1, din_d2;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            din_d1    <= 1'b0;
            din_d2    <= 1'b0;
            pulse_out <= 1'b0;
        end else begin
            din_d1    <= din;
            din_d2    <= din_d1;
            pulse_out <= (din_d1 && !din_d2);
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_barrel_shifter(self, module_name, spec_text="", ports=None):
        """Sinh mạch Bộ dịch/xoay vòng bit nhanh 4-bit (Barrel Shifter/Rotator 2 chiều trái/phải)."""
        code = f"""//==============================================================================
// Module: {module_name}
// Description: 4-bit Barrel Shifter / Rotator (Left and Right)
// Auto-generated by Spec2RTL Autonomous Engine (VeriPrefer Benchmark Standard)
//==============================================================================
module {module_name} (
    input  wire       clk,
    input  wire       rst,
    input  wire [3:0] data_in,
    input  wire [1:0] shift_amt,
    input  wire       dir, // 0: Rotate Left, 1: Rotate Right
    output reg  [3:0] data_out
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            data_out <= 4'd0;
        end else begin
            if (!dir) begin
                case (shift_amt)
                    2'b00: data_out <= data_in;
                    2'b01: data_out <= {{data_in[2:0], data_in[3]}};
                    2'b10: data_out <= {{data_in[1:0], data_in[3:2]}};
                    2'b11: data_out <= {{data_in[0], data_in[3:1]}};
                endcase
            end else begin
                case (shift_amt)
                    2'b00: data_out <= data_in;
                    2'b01: data_out <= {{data_in[0], data_in[3:1]}};
                    2'b10: data_out <= {{data_in[1:0], data_in[3:2]}};
                    2'b11: data_out <= {{data_in[2:0], data_in[3]}};
                endcase
            end
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_generic_module(self, module_name, spec_text="", ports=None):
        """
        Bộ sinh RTL dự phòng tổng quát cho các đặc tả tùy biến chưa thuộc họ mạch cố định:
        Tự động dựng khai báo cổng từ `ports` (có clock/reset đồng bộ hoặc tổ hợp thuần)
        và sinh logic gán/đếm an toàn, không lỗi cú pháp hay hở cổng.
        """
        # Khởi tạo cổng mặc định nếu đặc tả không cung cấp danh sách cổng cụ thể
        inputs = []
        outputs = []
        has_clk = False
        has_rst = False

        if ports:
            for p in ports:
                if p["direction"] == "input":
                    inputs.append(p)
                    if p.get("is_clk"): has_clk = True
                    if p.get("is_rst"): has_rst = True
                else:
                    outputs.append(p)

        user_inputs = [p for p in inputs if not p.get("is_clk") and not p.get("is_rst")]
        if not user_inputs and not has_clk:
            inputs.append({"name": "data_in", "direction": "input", "width": 4, "is_clk": False, "is_rst": False})
            user_inputs = [inputs[-1]]

        if not outputs:
            outputs.append({"name": "data_out", "direction": "output", "width": 4})
            outputs.append({"name": "valid", "direction": "output", "width": 1})

        port_decls = []
        for p in inputs:
            w_str = f"[{p['width']-1}:0] " if p['width'] > 1 else ""
            port_decls.append(f"    input  wire {w_str:<8} {p['name']}")

        for p in outputs:
            w_str = f"[{p['width']-1}:0] " if p['width'] > 1 else ""
            port_decls.append(f"    output reg  {w_str:<8} {p['name']}")

        ports_str = ",\n".join(port_decls)

        if has_clk:
            clk_p = next(p for p in inputs if p.get("is_clk"))
            rst_p = next((p for p in inputs if p.get("is_rst")), None)
            reset_resets = "\n".join([f"            {p['name']} <= {p['width']}'d0;" for p in outputs])
            logic_assigns = []
            for idx, p in enumerate(outputs):
                if user_inputs:
                    u_in = user_inputs[idx % len(user_inputs)]
                    if u_in["width"] == 1 and p["width"] > 1:
                        logic_assigns.append(f"            if ({u_in['name']}) {p['name']} <= {p['name']} + 1'b1;")
                    elif p["width"] == u_in["width"]:
                        logic_assigns.append(f"            {p['name']} <= {u_in['name']};")
                    else:
                        min_w = min(p["width"], u_in["width"])
                        logic_assigns.append(f"            {p['name']} <= {{{p['name']}[{p['width']-1}:{min_w}], {u_in['name']}[{min_w-1}:0]}};")
                else:
                    if p["width"] > 1:
                        logic_assigns.append(f"            {p['name']} <= {p['name']} + 1'b1;")
                    else:
                        logic_assigns.append(f"            {p['name']} <= ~{p['name']};")
            logic_str = "\n".join(logic_assigns)

            if rst_p:
                proc_str = f"""    always @(posedge {clk_p['name']} or posedge {rst_p['name']}) begin
        if ({rst_p['name']}) begin
{reset_resets}
        end else begin
{logic_str}
        end
    end"""
            else:
                proc_str = f"""    always @(posedge {clk_p['name']}) begin
{logic_str}
    end"""
        else:
            comb_assigns = []
            for p in outputs:
                if user_inputs:
                    comb_assigns.append(f"        {p['name']} = {user_inputs[0]['name']}[{min(p['width'], user_inputs[0]['width'])-1}:0];")
                else:
                    comb_assigns.append(f"        {p['name']} = {p['width']}'d0;")
            comb_body = "\n".join(comb_assigns)
            proc_str = f"""    always @(*) begin
{comb_body}
    end"""

        code = f"""//==============================================================================
// Module: {module_name}
// Description: Autonomous Custom Digital Logic Module
// Auto-generated by Spec2RTL Dynamic Synthesis Engine
//==============================================================================
module {module_name} (
{ports_str}
);

{proc_str}

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_decoder(self, spec_text="", module_name="memory_address_decoder", ports=None):
        """
        Sinh mạch Bộ giải mã tổ hợp (tự động phân nhánh):
          - Bộ giải mã địa chỉ bộ nhớ 64KB (`cs_ram` 32KB, `cs_rom` 16KB, `cs_io` 16KB).
          - Bộ giải mã nhị phân tổng quát N-sang-2^N (tùy chọn chân cho phép `enable`).
        """
        inputs = [p for p in (ports or []) if p["direction"] == "input"]
        outputs = [p for p in (ports or []) if p["direction"] == "output"]

        port_names = {p["name"].lower() for p in (ports or [])}
        is_mem_decoder = any(k in port_names for k in ["cs_ram", "cs_rom", "cs_io"]) or ("addr" in port_names)

        if is_mem_decoder:
            addr_port = next((p for p in inputs if "addr" in p["name"].lower()), {"name": "addr", "width": 16})
            mem_en_port = next((p for p in inputs if "en" in p["name"].lower()), {"name": "mem_en", "width": 1})

            cs_ram_name = next((p["name"] for p in outputs if "ram" in p["name"].lower()), "cs_ram")
            cs_rom_name = next((p["name"] for p in outputs if "rom" in p["name"].lower()), "cs_rom")
            cs_io_name  = next((p["name"] for p in outputs if "io" in p["name"].lower()), "cs_io")

            code = f"""//==============================================================================
// Module: {module_name}
// Description: 64KB Memory Address Decoder (Combinational Logic)
// Auto-generated by Spec2RTL Dynamic Synthesis Engine
//==============================================================================
module {module_name} (
    input  wire [{addr_port['width']-1}:0] {addr_port['name']},
    input  wire        {mem_en_port['name']},
    output reg         {cs_ram_name},
    output reg         {cs_rom_name},
    output reg         {cs_io_name}
);

    always @(*) begin
        {cs_ram_name} = 1'b0;
        {cs_rom_name} = 1'b0;
        {cs_io_name}  = 1'b0;
        if ({mem_en_port['name']}) begin
            case ({addr_port['name']}[15:14])
                2'b00, 2'b01: {cs_ram_name} = 1'b1; // 0x0000 - 0x7FFF: 32KB SRAM
                2'b10:        {cs_rom_name} = 1'b1; // 0x8000 - 0xBFFF: 16KB ROM
                2'b11:        {cs_io_name}  = 1'b1; // 0xC000 - 0xFFFF: 16KB I/O
            endcase
        end
    end

endmodule
"""
        else:
            in_port = inputs[0] if inputs else {"name": "in", "width": 3}
            en_port = inputs[1] if len(inputs) > 1 else None
            out_port = outputs[0] if outputs else {"name": "out", "width": 1 << in_port["width"]}

            port_decls = [f"    input  wire [{in_port['width']-1}:0] {in_port['name']}"]
            if en_port:
                port_decls.append(f"    input  wire        {en_port['name']}")
            port_decls.append(f"    output reg  [{out_port['width']-1}:0] {out_port['name']}")
            ports_str = ",\n".join(port_decls)

            en_cond = f"if ({en_port['name']}) " if en_port else ""
            else_cond = f" else {out_port['name']} = {out_port['width']}'d0;" if en_port else ""
            code = f"""//==============================================================================
// Module: {module_name}
// Description: Parameterized n-to-2^n Binary Decoder
//==============================================================================
module {module_name} (
{ports_str}
);

    always @(*) begin
        {en_cond}{out_port['name']} = (1'b1 << {in_port['name']});{else_cond}
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

    def generate_temperature_monitor(self, spec_text="", module_name="temperature_monitor_alarm", ports=None):
        """
        Sinh mạch Giám sát nhiệt độ và cảnh báo quá nhiệt 3 mức:
        Bình thường (`< max_temp_limit`), Cảnh báo + Quạt tốc độ cao (`>= limit`), và Ngắt khẩn cấp (`>= limit + 10`).
        """
        port_names = {p["name"].lower(): p for p in (ports or [])}
        clk_name = next((p["name"] for p in (ports or []) if p.get("is_clk") or "clk" in p["name"].lower()), "clk")
        rst_name = next((p["name"] for p in (ports or []) if p.get("is_rst") or "rst" in p["name"].lower()), "rst")

        temp_name = next((p["name"] for p in (ports or []) if "temp_celsius" in p["name"].lower() or "temp" in p["name"].lower()), "temp_celsius")
        limit_name = next((p["name"] for p in (ports or []) if "limit" in p["name"].lower() or "max" in p["name"].lower()), "max_temp_limit")

        fan_name = next((p["name"] for p in (ports or []) if "fan" in p["name"].lower()), "fan_high_speed")
        alarm_name = next((p["name"] for p in (ports or []) if "alarm" in p["name"].lower()), "overtemp_alarm")
        shutdown_name = next((p["name"] for p in (ports or []) if "shut" in p["name"].lower()), "shutdown_signal")

        temp_w = port_names.get(temp_name.lower(), {}).get("width", 8)
        limit_w = port_names.get(limit_name.lower(), {}).get("width", 8)

        code = f"""//==============================================================================
// Module: {module_name}
// Description: Digital Temperature Monitor & Alarm Controller
// Auto-generated by Spec2RTL Dynamic Synthesis Engine
//==============================================================================
module {module_name} (
    input  wire        {clk_name},
    input  wire        {rst_name},
    input  wire [{temp_w-1}:0] {temp_name},
    input  wire [{limit_w-1}:0] {limit_name},
    output reg         {fan_name},
    output reg         {alarm_name},
    output reg         {shutdown_name}
);

    always @(posedge {clk_name} or posedge {rst_name}) begin
        if ({rst_name}) begin
            {fan_name}      <= 1'b0;
            {alarm_name}    <= 1'b0;
            {shutdown_name} <= 1'b0;
        end else begin
            if ({{1'b0, {temp_name}}} >= {{1'b0, {limit_name}}} + {limit_w + 1}'d10) begin
                {fan_name}      <= 1'b1;
                {alarm_name}    <= 1'b1;
                {shutdown_name} <= 1'b1;
            end else if ({temp_name} >= {limit_name}) begin
                {fan_name}      <= 1'b1;
                {alarm_name}    <= 1'b1;
                {shutdown_name} <= 1'b0;
            end else begin
                {fan_name}      <= 1'b0;
                {alarm_name}    <= 1'b0;
                {shutdown_name} <= 1'b0;
            end
        end
    end

endmodule
"""
        return self._write_verilog(f"{module_name}.v", code)

if __name__ == "__main__":
    BoTaoRtl = RTLGenerator("../src")
    TenModule, DuongDanFile = BoTaoRtl.generate_from_spec("specs/a.txt")
    print("Da sinh thanh cong:", TenModule, DuongDanFile)
