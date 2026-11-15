"""
Module: KiemThuToanDien.py (truoc day la test_robustness_battery.py)
Chuc nang: Bo kiem thu tu dong kiem tra do on dinh va toan ven cua Spec2RTL & Prompt2Silicon.
Kiem tra 20 thiet ke phan cung khac nhau ve:
  - Nhan dien day du cac cong, khong thua thieu cong.
  - Cu phap Verilog chuan xac, khong chua ky tu loi.
  - Tao file so do khoi BDF va bieu tuong BSF Quartus hop le.
"""

import os
import sys
import tempfile
import shutil

# Dam bao thu muc agent nam trong he thong sys.path
ThuMucAgent = os.path.dirname(os.path.abspath(__file__))
if ThuMucAgent not in sys.path:
    sys.path.insert(0, ThuMucAgent)

from PhanTichSpec import SpecAnalyzer
from TaoRtl import RTLGenerator
from TaoBdf import BDFGenerator
from KiemToanCong import PortAuditor
from DonDepVerilog import VerilogLinter

DANH_SACH_SPEC_THU_NGHIEM = [
    # 1. Dong ho bam gio 0-9 kem LED 7 doan
    {
        "id": "TC01_Stopwatch_7Seg",
        "spec": """# Đồng Hồ Bấm Giờ 0-9 Giây Kèm Giải Mã LED 7 Đoạn (Stopwatch)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp đếm 1Hz (1 giây 1 xung)
- rst: Xung reset về 0 (active-high)
- start_stop: Nút bấm chạy/tạm dừng (1: Cho phép đếm, 0: Tạm dừng giữ nguyên số)
## 2. Đầu ra (Outputs):
- [3:0] count: Giá trị số đếm nhị phân (0 đến 9)
- [6:0] seg: Mã hiển thị LED 7 đoạn Anode chung (active-low: a, b, c, d, e, f, g)
## 3. Hoạt động:
- Đếm từ 0 đến 9 khi start_stop = 1."""
    },

    # 2. Khoa ma so dien tu (Dang chu in dam)
    {
        "id": "TC02_Digital_Lock_Bold",
        "spec": """# Khóa Mã Số Điện Tử Bảo Mật (Digital Safe Lock)
## 1. Đầu vào (Inputs):
- **clk**: Xung nhịp hệ thống
- **rst**: Reset tích cực mức cao
- **[3:0] key_in**: Chữ số người dùng nhập vào (0-9)
- **enter**: Xung kích xác nhận nhập một số
## 2. Đầu ra (Outputs):
- **unlock**: Mở khóa thành công (1: Mở khóa, 0: Khóa)
- **alarm**: Còi báo động (1: Báo động khi nhập sai quá 3 lần)
- **[1:0] err_count**: Số lần đã nhập sai
## 3. Hoạt động:
- Mật khẩu 4 số: 4 -> 2 -> 7 -> 9."""
    },

    # 3. Dieu khien dong co buoc (Dang bang Markdown)
    {
        "id": "TC03_Stepper_Motor_Table",
        "spec": """# Điều Khiển Động Cơ Bước 4 Pha (Stepper Motor)
| Port | Direction | Width | Description |
| `clk` | Input | 1 bit | Xung nhịp điều khiển tốc độ bước |
| `rst` | Input | 1 bit | Reset về trạng thái ban đầu |
| `direction` | Input | 1 bit | Hướng quay (1: Quay thuận CW, 0: Quay ngược CCW) |
| `enable` | Input | 1 bit | Cho phép động cơ hoạt động |
| `phase_out` | Output | 4 bit | Tín hiệu kích hoạt 4 cuộn dây pha (A, B, C, D) |
## Hoạt động:
- Kích cuộn dây lần lượt theo chuỗi."""
    },

    # 4. Truyen du lieu noi tiep UART TX (Dang danh sach danh so)
    {
        "id": "TC04_UART_TX_Numbered",
        "spec": """# Truyền Dữ Liệu Nối Tiếp (UART TX)
## 1. Đầu vào (Inputs):
1. clk: Xung nhịp baudrate
2. rst: Reset hệ thống
3. tx_start: Xung kích bắt đầu truyền 1 byte
4. [7:0] tx_data: Byte dữ liệu cần truyền đi
## 2. Đầu ra (Outputs):
1. tx_serial: Đường truyền nối tiếp UART (Mặc định ở mức 1 khi rảnh)
2. tx_busy: Báo bận (1: Đang truyền khung dữ liệu, 0: Rảnh)
## 3. Hoạt động:
- Khung truyền: 1 start bit, 8 data bit, 1 stop bit."""
    },

    # 5. Dieu khien may giat tu dong (Dang do rong trong dau ngoac)
    {
        "id": "TC05_Washing_Machine_Parens",
        "spec": """# Điều Khiển Máy Giặt Tự Động (Washing Machine)
## 1. Đầu vào:
- clk (1 bit): Xung nhịp hệ thống
- rst (1 bit): Reset về trạng thái chờ
- start_btn (1 bit): Nút bấm bắt đầu chu trình giặt
- lid_closed (1 bit): Cảm biến đóng nắp an toàn
## 2. Đầu ra:
- water_valve (1 bit): Van cấp nước
- motor_wash (1 bit): Động cơ quay đảo chiều
- motor_spin (1 bit): Động cơ vắt tốc độ cao
- drain_pump (1 bit): Bơm xả nước thải
- [1:0] state_led (2 bit): LED báo giai đoạn giặt"""
    },

    # 6. He thong bao dong nha thong minh
    {
        "id": "TC06_Smart_Home_Alarm",
        "spec": """# Cảnh Báo Nhà Thông Minh (Smart Home Alarm)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống báo động
- smoke_sensor: Cảm biến phát hiện khói/khí gas cháy
- motion_pir: Cảm biến chuyển động hồng ngoại PIR
- arm_mode: Chế độ kích hoạt báo trộm
## 2. Đầu ra (Outputs):
- fire_alarm: Còi hú báo cháy ưu tiên cao
- burglar_alarm: Còi báo trộm đột nhập
- [1:0] status_code: Mã trạng thái an ninh"""
    },

    # 7. Bo tao xung dieu che do rong PWM 8-bit
    {
        "id": "TC07_PWM_Generator",
        "spec": """# Bộ Tạo Xung Điều Chế PWM 8-bit (PWM Generator)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset bộ đếm xung
- [7:0] duty: Giá trị điều chỉnh độ rộng xung (0-255)
## 2. Đầu ra (Outputs):
- pwm_out: Tín hiệu xung ngõ ra điều khiển công suất
- [7:0] counter_val: Giá trị đếm nhị phân nội tại"""
    },

    # 8. Mach do chuoi bit 1011
    {
        "id": "TC08_Sequence_Detector",
        "spec": """# Mạch Dò Chuỗi Bit 1011 (Sequence Detector)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng bộ
- rst: Reset tích cực mức cao
- din: Chuỗi bit nối tiếp đi vào mạch
## 2. Đầu ra (Outputs):
- detected: Bật lên mức 1 trong 1 chu kỳ khi nhận đủ mẫu 1011
- [2:0] state_out: Trạng thái hiện tại của máy FSM"""
    },

    # 9. Bo dem hang doi FIFO dong bo
    {
        "id": "TC09_FIFO_Buffer",
        "spec": """# Bộ Đệm Hàng Đợi FIFO Đồng Bộ (FIFO Buffer)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng bộ đọc/ghi
- rst: Reset con trỏ hàng đợi
- wr_en: Tín hiệu cho phép ghi dữ liệu
- rd_en: Tín hiệu cho phép đọc dữ liệu
- [7:0] data_in: Dữ liệu nạp vào FIFO
## 2. Đầu ra (Outputs):
- [7:0] data_out: Dữ liệu lấy ra từ FIFO
- full: Cờ báo đầy bộ đệm (không thể ghi thêm)
- empty: Cờ báo rỗng bộ đệm (không có dữ liệu đọc)"""
    },

    # 10. Khoi so hoc va logic ALU 4-bit
    {
        "id": "TC10_ALU_4bit",
        "spec": """# Đơn Vị Số Học Và Logic 4-Bit (ALU)
## 1. Đầu vào (Inputs):
- [3:0] a: Toán hạng A (4-bit)
- [3:0] b: Toán hạng B (4-bit)
- [2:0] opcode: Mã phép toán cần thực hiện
## 2. Đầu ra (Outputs):
- [3:0] alu_out: Kết quả phép toán
- zero: Cờ báo kết quả bằng 0"""
    },

    # 11. Mach nhan nhi phan 8-bit
    {
        "id": "TC11_Multiplier_8bit",
        "spec": """# Mạch Nhân Nhị Phân 8-bit (Multiplier)
## 1. Đầu vào (Inputs):
- [7:0] a: Thừa số thứ nhất
- [7:0] b: Thừa số thứ hai
- clk: Xung nhịp đồng bộ
- rst: Xung xóa dữ liệu
## 2. Đầu ra (Outputs):
- [15:0] product: Tích số 16-bit"""
    },

    # 12. Bo dem len xuong 16-bit voi ten cong tuy bien
    {
        "id": "TC12_Counter_16bit_Custom_Pins",
        "spec": """# Bộ Đếm Nhị Phân 16-Bit (Counter 16bit)
## 1. Đầu vào (Inputs):
- clock: Tín hiệu xung nhịp
- reset_n: Reset tích cực mức thấp
- count_enable: Cho phép đếm
- dir_up: Chọn hướng đếm (1: Lên, 0: Xuống)
## 2. Đầu ra (Outputs):
- [15:0] q_count: Giá trị đếm nhị phân 16 bit
- roll_over: Xung tràn khi đạt cực trị"""
    },

    # 13. Bo ma hoa uu tien 8 sang 3
    {
        "id": "TC13_Priority_Encoder_8to3",
        "spec": """# Bộ Mã Hóa Ưu Tiên 8 Sang 3 (Priority Encoder)
## 1. Đầu vào (Inputs):
- [7:0] req_in: 8 đường yêu cầu ngắt vào (bit 7 ưu tiên cao nhất)
- enable: Cho phép bộ mã hóa
## 2. Đầu ra (Outputs):
- [2:0] code_out: Mã nhị phân tương ứng với ngõ vào ưu tiên
- valid: Tín hiệu xác nhận có ít nhất 1 ngõ vào tích cực"""
    },

    # 14. Bo dich xoay Barrel Shifter 4-bit
    {
        "id": "TC14_Barrel_Shifter_4bit",
        "spec": """# Bộ Dịch Xoay Barrel Shifter 4-bit (Barrel Shifter)
## 1. Đầu vào (Inputs):
- [3:0] data_in: Dữ liệu 4-bit cần dịch
- [1:0] shift_amt: Số vị trí dịch (0, 1, 2, 3)
- dir_right: Hướng dịch (1: Dịch phải, 0: Dịch trái)
## 2. Đầu ra (Outputs):
- [3:0] data_out: Dữ liệu sau khi dịch xoay"""
    },

    # 15. Dieu khien den giao thong nga tu
    {
        "id": "TC15_Traffic_Light",
        "spec": """# Điều Khiển Đèn Giao Thông Ngã Tư (Traffic Light)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp định thời 1Hz
- rst: Reset hệ thống
- sensor_rush: Cảm biến phát hiện giờ cao điểm
## 2. Đầu ra (Outputs):
- [2:0] light_main: Đèn tuyến chính (Đỏ, Vàng, Xanh)
- [2:0] light_side: Đèn tuyến phụ (Đỏ, Vàng, Xanh)"""
    },

    # 16. Chuyen doi ma BCD sang ma Du 3
    {
        "id": "TC16_BCD_to_Excess3_Custom",
        "spec": """# Bộ Chuyển Đổi Mã BCD Sang Mã Dư 3 (BCD to Excess-3)
## 1. Đầu vào (Inputs):
- [3:0] bcd_in: Mã BCD ngõ vào (từ 0 đến 9)
- valid_in: Tín hiệu cho phép chuyển đổi
## 2. Đầu ra (Outputs):
- [3:0] excess3_out: Mã Excess-3 (BCD + 3)
- error_code: Cờ báo lỗi nếu bcd_in vượt quá 9"""
    },

    # 17. Bo dem ma Gray 4-bit
    {
        "id": "TC17_Gray_Counter_4bit",
        "spec": """# Bộ Đếm Mã Gray 4-Bit (Gray Counter)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp đếm
- rst: Reset bộ đếm
- enable: Cho phép đếm
## 2. Đầu ra (Outputs):
- [3:0] gray_out: Mã Gray 4-bit chỉ đổi 1 bit mỗi chu kỳ
- [3:0] bin_cnt: Giá trị đếm nhị phân tương ứng"""
    },

    # 18. Mach phat hien canh xung
    {
        "id": "TC18_Edge_Detector",
        "spec": """# Mạch Phát Hiện Cạnh Xung Nhịp (Edge Detector)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp lấy mẫu tốc độ cao
- rst: Reset hệ thống
- sig_in: Tín hiệu đầu vào không đồng bộ
## 2. Đầu ra (Outputs):
- rising_edge: Xung 1 chu kỳ khi có cạnh lên
- falling_edge: Xung 1 chu kỳ khi có cạnh xuống"""
    },

    # 19. Giao tiep SPI Slave
    {
        "id": "TC19_SPI_Slave_Interface",
        "spec": """# Giao Tiếp Ngoại Vi Nối Tiếp SPI Phụ (SPI Slave)
## 1. Đầu vào (Inputs):
- sclk: Xung nhịp bus SPI từ Master
- cs_n: Tín hiệu chọn chip tích cực mức thấp
- mosi: Dữ liệu Master Out Slave In
- [7:0] tx_byte: Dữ liệu nội bộ chuẩn bị gửi lên Master
## 2. Đầu ra (Outputs):
- miso: Dữ liệu Master In Slave Out
- [7:0] rx_byte: Dữ liệu nhận được từ Master
- rx_ready: Cờ báo đã nhận xong 1 byte"""
    },

    # 20. Bo tao ma CRC 8-bit
    {
        "id": "TC20_CRC8_Generator",
        "spec": """# Bộ Tạo Mã Kiểm Tra Dư Thừa CRC 8-Bit (CRC Generator)
## 1. Đầu vào (Inputs):
- clk: Xung nhịp tính toán
- rst: Reset thanh ghi CRC
- data_valid: Cho phép tính toán byte dữ liệu
- [7:0] data_byte: Byte dữ liệu cần tính CRC
## 2. Đầu ra (Outputs):
- [7:0] crc_out: Mã CRC-8 tích lũy
- crc_valid: Báo mã CRC đã sẵn sàng"""
    }
]

TEST_SPECS = DANH_SACH_SPEC_THU_NGHIEM

def chay_kiem_thu_toan_dien():
    """Chay 20 ca kiem thu kiem tra toan bo quy trinh tu Spec den RTL va BDF."""
    print("=" * 80)
    print("   BO KIEM THU TU DONG HOAT DONG TOAN VEN SPEC2RTL (20/20 CA KIEM THU)")
    print("=" * 80)

    ThuMucTam = tempfile.mkdtemp(prefix="spec2rtl_test_")
    ThuMucSrc = os.path.join(ThuMucTam, "src")
    ThuMucQuartus = os.path.join(ThuMucTam, "quartus")
    os.makedirs(ThuMucSrc, exist_ok=True)
    os.makedirs(ThuMucQuartus, exist_ok=True)

    SoLuongDat = 0
    DanhSachLoi = []

    BoTaoRtl = RTLGenerator(ThuMucSrc)
    BoTaoBdf = BDFGenerator()

    for ChiMuc, CaKiemThu in enumerate(DANH_SACH_SPEC_THU_NGHIEM):
        MaKiemThu = CaKiemThu["id"]
        NoiDungSpec = CaKiemThu["spec"]

        print(f"\n[{ChiMuc + 1:02d}/20] Dang kiem tra: {MaKiemThu}...")

        try:
            # Buoc 1: Trich xuat dac ta cong
            BoPhanTich = SpecAnalyzer(NoiDungSpec)
            TenModule = BoPhanTich.extract_module_name()
            DanhSachCongSpec = BoPhanTich.extract_ports()
            PhanLoai = BoPhanTich.classify_system()

            if not DanhSachCongSpec:
                raise ValueError(f"Khong the trich xuat cong tu dac ta: {MaKiemThu}")

            # Buoc 2: Sinh ma nguon RTL
            _, TepVerilog = BoTaoRtl.generate_from_spec(NoiDungSpec)
            if not os.path.exists(TepVerilog):
                raise FileNotFoundError(f"Khong tim thay file RTL da tao: {TepVerilog}")

            # Buoc 3: Kiem tra va don dep cu phap Verilog
            VerilogLinter.sanitize_file(TepVerilog)

            # Buoc 4: Tao bieu tuong BSF va so do khoi BDF
            DuongDanBsf = os.path.join(ThuMucQuartus, f"{TenModule}.bsf")
            DuongDanBdf = os.path.join(ThuMucQuartus, f"sch_{TenModule}.bdf")
            BoTaoBdf.generate_bsf_from_rtl(TepVerilog, DuongDanBsf)
            BoTaoBdf.generate_bdf_from_bsf(DuongDanBsf, DuongDanBdf)

            # Buoc 5: Kiem toan toan ven cac cong
            KiemTraHopLe = PortAuditor.audit(DanhSachCongSpec, TepVerilog, DuongDanBsf, DuongDanBdf)
            if not KiemTraHopLe:
                raise AssertionError(f"Kiem toan cong that bai cho {MaKiemThu}")

            print(f"  -> [DAT]: {MaKiemThu} | Module: '{TenModule}' | Loai: '{PhanLoai}' | So cong: {len(DanhSachCongSpec)}")
            SoLuongDat += 1

        except Exception as Loi:
            print(f"  -> [LOI]: {MaKiemThu} Chi tiet: {str(Loi)}")
            DanhSachLoi.append((MaKiemThu, str(Loi)))

    # Xoa thu muc tam sau khi kiem thu
    shutil.rmtree(ThuMucTam, ignore_errors=True)

    print("\n" + "=" * 80)
    print("                    TONG KET KET QUA KIEM THU")
    print("=" * 80)
    print(f" Tong so ca kiem thu : {len(DANH_SACH_SPEC_THU_NGHIEM)}")
    print(f" So ca thanh cong    : {SoLuongDat} / {len(DANH_SACH_SPEC_THU_NGHIEM)} ({SoLuongDat / len(DANH_SACH_SPEC_THU_NGHIEM) * 100:.1f}%)")
    print(f" So ca that bai      : {len(DanhSachLoi)}")
    if DanhSachLoi:
        print("\n Chi tiet loi:")
        for MaLoi, NoiDungLoi in DanhSachLoi:
            print(f"  * {MaLoi}: {NoiDungLoi}")
        print("=" * 80)
        return False
    else:
        print("\n >>> [TAT CA 20 CA KIEM THU DEU DAT 100% VE TINH DUNG DONG VA CU PHAP] <<<")
        print("=" * 80)
        return True

run_battery = chay_kiem_thu_toan_dien

if __name__ == "__main__":
    KetQuaChay = chay_kiem_thu_toan_dien()
    sys.exit(0 if KetQuaChay else 1)
