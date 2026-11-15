"""
Module: build_100_prompts_pdf.py
Chuc nang: Tao file PDF chuyen nghiep chua 100 de bai dac ta thiet ke vi mach so
bang tieng Viet, duoc dinh dang duoi dang danh sach liet ke de sao chep truc tiep.
Dich den: docs/100_Prompt_Thiet_Ke_Mach.pdf
"""

import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 1. Dang ky phong chu Unicode TrueType tieng Viet
PHONG_CHU_THUONG = "Arial"
PHONG_CHU_DAM = "Arial-Bold"
PHONG_CHU_NGHIENG = "Arial-Italic"

FONT_REGULAR = PHONG_CHU_THUONG
FONT_BOLD = PHONG_CHU_DAM
FONT_ITALIC = PHONG_CHU_NGHIENG

ThuMucFont = "C:/Windows/Fonts"
if os.path.exists(os.path.join(ThuMucFont, "arial.ttf")):
    pdfmetrics.registerFont(TTFont("Arial", os.path.join(ThuMucFont, "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", os.path.join(ThuMucFont, "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Italic", os.path.join(ThuMucFont, "ariali.ttf")))
else:
    print("[CANH BAO] Khong tim thay phong Arial trong C:/Windows/Fonts, dung phong mac dinh.")
    PHONG_CHU_THUONG = "Helvetica"
    PHONG_CHU_DAM = "Helvetica-Bold"
    PHONG_CHU_NGHIENG = "Helvetica-Oblique"
    FONT_REGULAR = PHONG_CHU_THUONG
    FONT_BOLD = PHONG_CHU_DAM
    FONT_ITALIC = PHONG_CHU_NGHIENG

# 2. Canvas danh so trang hai luot (Two-pass Numbered Canvas)
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._trang_thai_trang = []

    def showPage(self):
        self._trang_thai_trang.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        TongSoTrang = len(self._trang_thai_trang)
        for TrangThai in self._trang_thai_trang:
            self.__dict__.update(TrangThai)
            self.draw_page_decorations(TongSoTrang)
            super().showPage()
        super().save()

    def draw_page_decorations(self, TongSoTrang):
        if self._pageNumber == 1:
            return  # Bo qua trang bia
        self.saveState()
        self.setFont(PHONG_CHU_THUONG, 8)
        self.setFillColor(colors.HexColor("#555555"))

        # Header dau trang
        self.drawString(42, 810, "SPEC2RTL & PROMPT2SILICON: 100 ĐỀ BÀI ĐẶC TẢ THIẾT KẾ VI MẠCH SỐ")
        self.setStrokeColor(colors.HexColor("#D0D5DD"))
        self.setLineWidth(0.5)
        self.line(42, 804, 553, 804)

        # Footer cuoi trang
        self.line(42, 45, 553, 45)
        self.drawString(42, 32, "Khoa Điện - Điện Tử | Đồ Án 3: Thiết Kế & Kiểm Thử Vi Mạch Tự Động")
        ChuoiTrang = f"Trang {self._pageNumber} / {TongSoTrang}"
        self.drawRightString(553, 32, ChuoiTrang)
        self.restoreState()


def get_all_100_prompts():
    """Returns the full list of 100 clean, verified hardware prompts across 10 groups."""
    prompts = [
        # =========================================================================
        # NHÓM 1: MẠCH ĐẾM & ĐỊNH THỜI (COUNTERS & TIMERS) [01 - 10]
        # =========================================================================
        {
            "id": 1,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm Nhị Phân 4-bit Đếm Lên / Xuống (binary_counter_4bit)",
            "module": "binary_counter_4bit",
            "spec_text": """# Bộ Đếm Nhị Phân 4-bit Đếm Lên / Xuống (binary_counter_4bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset đồng bộ tích cực cao
- up_down: Hướng đếm (1: Đếm lên 0->15, 0: Đếm xuống 15->0)
- enable: Tín hiệu cho phép đếm (1: Đếm, 0: Tạm dừng)

## 2. Đầu ra (Outputs):
- [3:0] count: Giá trị số đếm nhị phân 4-bit
- tc: Cờ báo chạm đỉnh Terminal Count (1 khi đạt 15 lúc đếm lên hoặc 0 lúc đếm xuống)

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: count = 4'b0000, tc = 0.
- Khi enable = 1: Tại mỗi sườn dương clk, nếu up_down = 1 thì count tăng 1; nếu up_down = 0 thì count giảm 1.
- tc = 1 khi (up_down == 1 và count == 15) hoặc (up_down == 0 và count == 0), ngược lại tc = 0."""
        },
        {
            "id": 2,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Đồng Hồ Bấm Giờ 0-9 Giây Kèm Giải Mã LED 7 Đoạn (stopwatch_7seg)",
            "module": "stopwatch_7seg",
            "spec_text": """# Đồng Hồ Bấm Giờ 0-9 Giây Kèm LED 7 Đoạn (stopwatch_7seg)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đếm 1Hz (1 giây 1 xung)
- rst: Reset về 0 tích cực cao
- start_stop: Nút điều khiển chạy/dừng (1: Đếm, 0: Giữ nguyên số)

## 2. Đầu ra (Outputs):
- [3:0] count: Giá trị đếm nhị phân 0-9
- [6:0] seg: Mã hiển thị LED 7 đoạn Anode chung (active-low: a, b, c, d, e, f, g)

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: count = 0, seg hiển thị số 0 (7'b1000000).
- Khi start_stop = 1: Mỗi xung clk count tăng 1 đơn vị từ 0 lên 9; khi đạt 9 chu kỳ sau quay về 0.
- seg giải mã trực tiếp từ count (0: 7'b1000000, 1: 7'b1111001, ..., 9: 7'b0010000)."""
        },
        {
            "id": 3,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm BCD 00 Đến 59 Đếm Giây / Phút (bcd_counter_59)",
            "module": "bcd_counter_59",
            "spec_text": """# Bộ Đếm BCD 00 Đến 59 (bcd_counter_59)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp 1Hz
- rst: Reset đồng bộ tích cực cao
- en: Cho phép đếm

## 2. Đầu ra (Outputs):
- [3:0] sec_ones: Hàng đơn vị BCD (0 đến 9)
- [3:0] sec_tens: Hàng chục BCD (0 đến 5)
- rollover: Xung tràn 1 chu kỳ khi đạt 59 quay về 00

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: sec_ones = 0, sec_tens = 0, rollover = 0.
- Khi en = 1: sec_ones tăng từ 0->9; khi đạt 9 thì quay về 0 và tăng sec_tens thêm 1.
- Khi đạt 59, chu kỳ kế tiếp quay về 00 và phát xung rollover = 1 trong 1 chu kỳ clk."""
        },
        {
            "id": 4,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm Mã Gray 4-bit Không Nhiễu Trạng Thái (gray_counter_4bit)",
            "module": "gray_counter_4bit",
            "spec_text": """# Bộ Đếm Mã Gray 4-bit (gray_counter_4bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset bất đồng bộ tích cực cao
- enable: Cho phép đếm

## 2. Đầu ra (Outputs):
- [3:0] gray_out: Mã Gray 4-bit đầu ra
- [3:0] bin_cnt: Giá trị đếm nhị phân nội bộ

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: bin_cnt = 4'b0000, gray_out = 4'b0000.
- Khi enable = 1: bin_cnt tăng 1 đơn vị tại mỗi sườn dương clk.
- gray_out chuyển đổi theo công thức không trễ: gray_out = bin_cnt ^ (bin_cnt >> 1)."""
        },
        {
            "id": 5,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm Vòng 8-bit LED Sáng Đuổi (ring_counter_8bit)",
            "module": "ring_counter_8bit",
            "spec_text": """# Bộ Đếm Vòng 8-bit LED Sáng Đuổi (ring_counter_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng hồ
- rst: Reset tích cực cao
- dir: Hướng dịch vòng (1: Dịch trái, 0: Dịch phải)

## 2. Đầu ra (Outputs):
- [7:0] q: Trạng thái 8 đèn LED (chỉ có duy nhất 1 bit bật sáng tại một thời điểm)

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: q = 8'b00000001 (khởi tạo bit 1 tại vị trí LSB).
- Mỗi xung clk: nếu dir = 1 thì q dịch trái xoay vòng {q[6:0], q[7]}; nếu dir = 0 thì q dịch phải xoay vòng {q[0], q[7:1]}."""
        },
        {
            "id": 6,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm Johnson 4-bit (johnson_counter_4bit)",
            "module": "johnson_counter_4bit",
            "spec_text": """# Bộ Đếm Johnson 4-bit (johnson_counter_4bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset đồng bộ tích cực cao
- enable: Cho phép đếm

## 2. Đầu ra (Outputs):
- [3:0] q: Trạng thái 4-bit của bộ đếm Johnson (chu kỳ 8 trạng thái)

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: q = 4'b0000.
- Khi enable = 1: Tại mỗi sườn dương clk, thanh ghi dịch theo quy luật: q <= {q[2:0], ~q[3]}."""
        },
        {
            "id": 7,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm Modulo 12 Hiển Thị Giờ (mod12_counter)",
            "module": "mod12_counter",
            "spec_text": """# Bộ Đếm Modulo 12 (mod12_counter)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- en: Cho phép đếm

## 2. Đầu ra (Outputs):
- [3:0] hour: Giá trị giờ từ 1 đến 12
- rollover: Xung tràn tích cực mức cao khi đạt 12 chuẩn bị quay về 1

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: hour = 4'd1, rollover = 0.
- Khi en = 1: hour tăng từ 1 lên 12; khi đạt 12 thì chu kỳ kế tiếp quay về 1 và phát xung rollover = 1."""
        },
        {
            "id": 8,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Định Thời Đếm Lùi 99 Giây (countdown_timer_99s)",
            "module": "countdown_timer_99s",
            "spec_text": """# Bộ Định Thời Đếm Lùi 99 Giây (countdown_timer_99s)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp 1Hz
- rst: Reset hệ thống
- load: Nạp giá trị ban đầu
- [7:0] init_val: Giá trị nạp vào ban đầu (0 đến 99)
- start: Kích hoạt đếm lùi

## 2. Đầu ra (Outputs):
- [7:0] current_val: Giá trị thời gian đếm lùi hiện tại
- done: Cờ báo hết giờ (1 khi giá trị đếm giảm về đúng 0)

## 3. Hoạt động / Logic mong muốn:
- Khi load = 1: current_val = init_val, done = 0.
- Khi start = 1 và current_val > 0: Mỗi xung clk current_val giảm đi 1.
- Khi current_val chạm 0: done = 1 và giữ nguyên giá trị."""
        },
        {
            "id": 9,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Chia Tần Số Xung Nhịp 50MHz Xuống 1Hz (freq_divider_1hz)",
            "module": "freq_divider_1hz",
            "spec_text": """# Bộ Chia Tần Số 50MHz Xuống 1Hz (freq_divider_1hz)

## 1. Đầu vào (Inputs):
- clk_50m: Xung nhịp đầu vào 50MHz
- rst: Reset tích cực cao

## 2. Đầu ra (Outputs):
- clk_1hz: Xung vuông đầu ra tần số 1Hz với chu kỳ nhiệm vụ 50%

## 3. Hoạt động / Logic mong muốn:
- Bộ đếm nhị phân đếm từ 0 đến 24.999.999 (nửa chu kỳ).
- Khi chạm ngưỡng 24.999.999: clk_1hz đảo trạng thái (0 -> 1 hoặc 1 -> 0) và bộ đếm tự động reset về 0."""
        },
        {
            "id": 10,
            "group": "Nhóm 1: Mạch Đếm & Định Thời",
            "name": "Bộ Đếm Chu Kỳ Xung Xung Nhịp (clock_pulse_counter)",
            "module": "clock_pulse_counter",
            "spec_text": """# Bộ Đếm Chu Kỳ Xung Nhịp (clock_pulse_counter)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp lấy mẫu
- rst: Reset tích cực cao
- pulse_in: Xung tín hiệu cần đếm
- clear: Xóa số đếm về 0

## 2. Đầu ra (Outputs):
- [15:0] pulse_count: Số lượng xung tín hiệu đã phát hiện được

## 3. Hoạt động / Logic mong muốn:
- Mạch phát hiện cạnh lên của pulse_in.
- Mỗi khi xuất hiện sườn dương pulse_in, pulse_count tăng 1 đơn vị.
- Khi clear = 1 hoặc rst = 1: pulse_count = 0."""
        },

        # =========================================================================
        # NHÓM 2: MẠCH SỐ HỌC & ALU (ARITHMETIC & ALU) [11 - 20]
        # =========================================================================
        {
            "id": 11,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ Cộng Nhị Phân 8-bit Có Cờ Nhớ (adder_8bit)",
            "module": "adder_8bit",
            "spec_text": """# Bộ Cộng Nhị Phân 8-bit (adder_8bit)

## 1. Đầu vào (Inputs):
- [7:0] a: Toán hạng thứ nhất
- [7:0] b: Toán hạng thứ hai
- cin: Bit nhớ ngõ vào

## 2. Đầu ra (Outputs):
- [7:0] sum: Kết quả phép cộng 8-bit
- cout: Bit nhớ ngõ ra (Carry Out)

## 3. Hoạt động / Logic mong muốn:
- Thực hiện phép cộng không dấu: {cout, sum} = a + b + cin."""
        },
        {
            "id": 12,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ Trừ Nhị Phân 8-bit Có Cờ Mượn (subtractor_8bit)",
            "module": "subtractor_8bit",
            "spec_text": """# Bộ Trừ Nhị Phân 8-bit (subtractor_8bit)

## 1. Đầu vào (Inputs):
- [7:0] a: Số bị trừ
- [7:0] b: Số trừ
- bin: Bit mượn ngõ vào

## 2. Đầu ra (Outputs):
- [7:0] diff: Hiệu số 8-bit
- bout: Bit mượn ngõ ra (Borrow Out)

## 3. Hoạt động / Logic mong muốn:
- Thực hiện phép tính: {bout, diff} = a - b - bin."""
        },
        {
            "id": 13,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ Nhân Nhị Phân 4-bit (multiplier_4bit)",
            "module": "multiplier_4bit",
            "spec_text": """# Bộ Nhân Nhị Phân 4-bit (multiplier_4bit)

## 1. Đầu vào (Inputs):
- [3:0] a: Thừa số thứ nhất (4-bit không dấu)
- [3:0] b: Thừa số thứ hai (4-bit không dấu)

## 2. Đầu ra (Outputs):
- [7:0] product: Tích số 8-bit

## 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp thực hiện phép nhân nhị phân không dấu: product = a * b."""
        },
        {
            "id": 14,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ Nhân Nhị Phân 8-bit (multiplier_8bit)",
            "module": "multiplier_8bit",
            "spec_text": """# Bộ Nhân Nhị Phân 8-bit (multiplier_8bit)

## 1. Đầu vào (Inputs):
- [7:0] a: Thừa số thứ nhất 8-bit
- [7:0] b: Thừa số thứ hai 8-bit

## 2. Đầu ra (Outputs):
- [15:0] product: Tích số 16-bit

## 3. Hoạt động / Logic mong muốn:
- Thực hiện phép nhân số học không dấu: product = a * b."""
        },
        {
            "id": 15,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ So Sánh Số Học 4-bit (comparator_4bit)",
            "module": "comparator_4bit",
            "spec_text": """# Bộ So Sánh Số Học 4-bit (comparator_4bit)

## 1. Đầu vào (Inputs):
- [3:0] a: Số nhị phân thứ nhất 4-bit
- [3:0] b: Số nhị phân thứ hai 4-bit

## 2. Đầu ra (Outputs):
- a_gt_b: Bằng 1 khi a > b
- a_eq_b: Bằng 1 khi a == b
- a_lt_b: Bằng 1 khi a < b

## 3. Hoạt động / Logic mong muốn:
- So sánh giá trị hai số nhị phân không dấu 4-bit và kích hoạt chính xác một trong ba cờ ngõ ra."""
        },
        {
            "id": 16,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ ALU 4-bit Đa Năng 8 Phép Toán (alu_4bit)",
            "module": "alu_4bit",
            "spec_text": """# Bộ ALU 4-bit Đa Năng (alu_4bit)

## 1. Đầu vào (Inputs):
- [3:0] a: Toán hạng A
- [3:0] b: Toán hạng B
- [2:0] opcode: Mã thao tác (000: Cộng, 001: Trừ, 010: AND, 011: OR, 100: XOR, 101: NOT A, 110: Shift Left, 111: Shift Right)

## 2. Đầu ra (Outputs):
- [3:0] alu_out: Kết quả phép tính 4-bit
- zero: Cờ báo kết quả bằng 0 (1 khi alu_out == 4'b0000)

## 3. Hoạt động / Logic mong muốn:
- Thực thi đúng phép toán được chỉ định bởi opcode.
- zero = 1 khi alu_out = 0, ngược lại zero = 0."""
        },
        {
            "id": 17,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Bộ ALU 8-bit Có Cờ Tràn Overflow (alu_8bit)",
            "module": "alu_8bit",
            "spec_text": """# Bộ ALU 8-bit Có Cờ Tràn (alu_8bit)

## 1. Đầu vào (Inputs):
- [7:0] a: Toán hạng A
- [7:0] b: Toán hạng B
- [2:0] opcode: Mã lệnh (0: Add, 1: Sub, 2: AND, 3: OR, 4: XOR, 5: SLA, 6: SRA, 7: Compare)

## 2. Đầu ra (Outputs):
- [7:0] result: Kết quả 8-bit
- carry: Cờ nhớ bit cao
- zero: Cờ báo kết quả bằng 0

## 3. Hoạt động / Logic mong muốn:
- Thực hiện phép toán tương ứng với opcode.
- Cập nhật đầy đủ các cờ trạng thái carry và zero."""
        },
        {
            "id": 18,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Mạch Cộng / Trừ Số Bù 2 8-bit (adder_subtractor_8bit)",
            "module": "adder_subtractor_8bit",
            "spec_text": """# Mạch Cộng / Trừ Số Bù 2 8-bit (adder_subtractor_8bit)

## 1. Đầu vào (Inputs):
- [7:0] a: Toán hạng A (số có dấu bù 2)
- [7:0] b: Toán hạng B (số có dấu bù 2)
- sub_mode: Chế độ phép tính (0: Cộng a + b, 1: Trừ a - b)

## 2. Đầu ra (Outputs):
- [7:0] result: Kết quả phép tính 8-bit
- overflow: Cờ báo tràn số có dấu

## 3. Hoạt động / Logic mong muốn:
- Khi sub_mode = 0: result = a + b.
- Khi sub_mode = 1: result = a - b.
- overflow = 1 khi phép tính gây tràn số học bù 2."""
        },
        {
            "id": 19,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Mạch Tính Giá Trị Tuyệt Đối 8-bit (abs_calculator_8bit)",
            "module": "abs_calculator_8bit",
            "spec_text": """# Mạch Tính Giá Trị Tuyệt Đối 8-bit (abs_calculator_8bit)

## 1. Đầu vào (Inputs):
- [7:0] data_in: Số nguyên có dấu bù 2 (từ -128 đến +127)

## 2. Đầu ra (Outputs):
- [7:0] abs_out: Giá trị tuyệt đối không dấu

## 3. Hoạt động / Logic mong muốn:
- Nếu bit dấu data_in[7] == 0: abs_out = data_in.
- Nếu bit dấu data_in[7] == 1: abs_out = -data_in (nghịch đảo bù 2: ~data_in + 1)."""
        },
        {
            "id": 20,
            "group": "Nhóm 2: Mạch Xử Lý Số Học & ALU",
            "name": "Mạch Nhân Dồn Tích Lũy MAC 8-bit (mac_accumulator_8bit)",
            "module": "mac_accumulator_8bit",
            "spec_text": """# Mạch Nhân Dồn Tích Lũy MAC (mac_accumulator_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset đồng bộ
- clr_acc: Xóa thanh ghi tích lũy về 0
- [3:0] a: Thừa số A (4-bit)
- [3:0] b: Thừa số B (4-bit)

## 2. Đầu ra (Outputs):
- [15:0] acc_out: Giá trị tích lũy dồn: acc_out <= acc_out + (a * b)

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1 hoặc clr_acc = 1: acc_out = 0.
- Tại mỗi sườn dương clk: acc_out cộng dồn tích số a * b."""
        },

        # =========================================================================
        # NHÓM 3: MẠCH THANH GHI & BỘ ĐỆM DỮ LIỆU [21 - 30]
        # =========================================================================
        {
            "id": 21,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Thanh Ghi Dịch Vạn Năng 4-bit (universal_shift_reg_4bit)",
            "module": "universal_shift_reg_4bit",
            "spec_text": """# Thanh Ghi Dịch Vạn Năng 4-bit (universal_shift_reg_4bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset đồng bộ tích cực cao
- [1:0] mode: Chế độ hoạt động (00: Giữ nguyên, 01: Dịch phải, 10: Dịch trái, 11: Nạp song song)
- s_in_left: Bit nối tiếp nạp vào khi dịch trái
- s_in_right: Bit nối tiếp nạp vào khi dịch phải
- [3:0] d_in: Dữ liệu nạp song song

## 2. Đầu ra (Outputs):
- [3:0] q: Trạng thái ngõ ra 4-bit

## 3. Hoạt động / Logic mong muốn:
- mode = 00: q giữ nguyên.
- mode = 01: q <= {s_in_right, q[3:1]}.
- mode = 10: q <= {q[2:0], s_in_left}.
- mode = 11: q <= d_in."""
        },
        {
            "id": 22,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Thanh Ghi Dịch Nối Tiếp Sang Song Song SIPO 8-bit (sipo_shift_reg_8bit)",
            "module": "sipo_shift_reg_8bit",
            "spec_text": """# Thanh Ghi SIPO 8-bit (sipo_shift_reg_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng hồ
- rst: Reset tích cực cao
- s_in: Dữ liệu nối tiếp 1-bit vào
- en: Cho phép dịch

## 2. Đầu ra (Outputs):
- [7:0] p_out: Dữ liệu song song 8-bit ra

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: p_out = 8'b0.
- Khi en = 1: Mỗi xung clk đẩy s_in vào LSB và dịch trái: p_out <= {p_out[6:0], s_in}."""
        },
        {
            "id": 23,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Thanh Ghi Dịch Song Song Sang Nối Tiếp PISO 8-bit (piso_shift_reg_8bit)",
            "module": "piso_shift_reg_8bit",
            "spec_text": """# Thanh Ghi PISO 8-bit (piso_shift_reg_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng hồ
- rst: Reset tích cực cao
- load: 1: Nạp song song dữ liệu, 0: Chế độ dịch nối tiếp
- [7:0] p_in: Dữ liệu song song 8-bit vào

## 2. Đầu ra (Outputs):
- s_out: Bit dữ liệu nối tiếp xuất ra ở MSB

## 3. Hoạt động / Logic mong muốn:
- Khi load = 1: nạp p_in vào thanh ghi nội bộ.
- Khi load = 0: mỗi xung clk dịch trái 1 bit và xuất bit MSB ra s_out."""
        },
        {
            "id": 24,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Thanh Ghi Dữ Liệu 8-bit Có Chân Cho Phép Nạp (register_8bit_load)",
            "module": "register_8bit_load",
            "spec_text": """# Thanh Ghi Dữ Liệu 8-bit (register_8bit_load)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset đồng bộ
- load: Cho phép nạp dữ liệu
- [7:0] d: Dữ liệu ngõ vào

## 2. Đầu ra (Outputs):
- [7:0] q: Dữ liệu ngõ ra lưu trữ

## 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: q = 0.
- Khi load = 1: q <= d.
- Khi load = 0: q giữ nguyên giá trị cũ."""
        },
        {
            "id": 25,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Hàng Đợi Đệm Đồng Bộ FIFO 8x8-bit (fifo_syn_8x8)",
            "module": "fifo_syn_8x8",
            "spec_text": """# Hàng Đợi Đồng Bộ FIFO 8x8 (fifo_syn_8x8)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng bộ
- rst: Reset hệ thống
- wr_en: Cho phép ghi dữ liệu
- rd_en: Cho phép đọc dữ liệu
- [7:0] din: Dữ liệu ghi vào FIFO

## 2. Đầu ra (Outputs):
- [7:0] dout: Dữ liệu đọc ra từ FIFO
- empty: Cờ báo rỗng (1: Hàng đợi rỗng)
- full: Cờ báo đầy (1: Hàng đợi đầy)

## 3. Hoạt động / Logic mong muốn:
- Hoạt động theo nguyên tắc vào trước ra trước (FIFO).
- Không cho phép ghi khi full = 1; không cho phép đọc khi empty = 1."""
        },
        {
            "id": 26,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Ngăn Xếp Đệm LIFO / Stack 8-bit (lifo_stack_8bit)",
            "module": "lifo_stack_8bit",
            "spec_text": """# Ngăn Xếp LIFO / Stack 8-bit (lifo_stack_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- push: Lệnh đẩy phần tử vào đỉnh Stack
- pop: Lệnh lấy phần tử ra khỏi đỉnh Stack
- [7:0] data_in: Dữ liệu đưa vào

## 2. Đầu ra (Outputs):
- [7:0] data_out: Dữ liệu lấy ra
- full: Báo đầy ngăn xếp
- empty: Báo rỗng ngăn xếp

## 3. Hoạt động / Logic mong muốn:
- Vào sau ra trước (Last-In, First-Out).
- Quản lý con trỏ đỉnh Stack SP (Stack Pointer)."""
        },
        {
            "id": 27,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Bộ Đệm Tròn Vòng 16 Byte (circular_buffer_16byte)",
            "module": "circular_buffer_16byte",
            "spec_text": """# Bộ Đệm Tròn Vòng 16 Byte (circular_buffer_16byte)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- write_en: Cho phép ghi byte mới
- [7:0] write_data: Dữ liệu byte ghi vào

## 2. Đầu ra (Outputs):
- [7:0] read_data: Dữ liệu byte tại vị trí con trỏ đọc
- [3:0] write_ptr: Địa chỉ con trỏ ghi hiện tại (0-15)

## 3. Hoạt động / Logic mong muốn:
- Ghi dữ liệu nối tiếp xoay vòng 16 ô nhớ; khi ghi đến ô 15 thì lần kế tiếp tự động quay về ô 0."""
        },
        {
            "id": 28,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Thanh Ghi Dịch Thùng Barrel Shifter 4-bit (barrel_shifter_4bit)",
            "module": "barrel_shifter_4bit",
            "spec_text": """# Thanh Ghi Barrel Shifter 4-bit (barrel_shifter_4bit)

## 1. Đầu vào (Inputs):
- [3:0] data_in: Dữ liệu 4-bit ngõ vào
- [1:0] shift_amt: Số vị trí dịch (0, 1, 2, hoặc 3 bit)
- rotate: 1: Xoay vòng (Rotate), 0: Dịch logic (Shift chèn 0)

## 2. Đầu ra (Outputs):
- [3:0] data_out: Kết quả sau khi dịch hoặc xoay

## 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp dịch chuyển tức thì theo số bit được chọn bởi shift_amt."""
        },
        {
            "id": 29,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Bộ Tạo Mã Ngẫu Nhiên Tuyến Tính LFSR 8-bit (lfsr_random_8bit)",
            "module": "lfsr_random_8bit",
            "spec_text": """# Bộ Tạo Mã Ngẫu Nhiên LFSR 8-bit (lfsr_random_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- en: Cho phép sinh mã

## 2. Đầu ra (Outputs):
- [7:0] rand_out: Chuỗi số ngẫu nhiên giả lập (PRNG) 8-bit

## 3. Hoạt động / Logic mong muốn:
- Sử dụng đa thức sinh x^8 + x^6 + x^5 + x^4 + 1.
- Khi rst = 1: nạp giá trị hạt giống seed (khác 0) ví dụ 8'hA5."""
        },
        {
            "id": 30,
            "group": "Nhóm 3: Mạch Thanh Ghi & Bộ Đệm",
            "name": "Bộ Đệm Dữ Liệu 3 Trạng Thái Tri-state 8-bit (tristate_buffer_8bit)",
            "module": "tristate_buffer_8bit",
            "spec_text": """# Bộ Đệm Tri-state Buffer 8-bit (tristate_buffer_8bit)

## 1. Đầu vào (Inputs):
- [7:0] in_data: Dữ liệu ngõ vào
- oe: Tín hiệu cho phép ngõ ra (Output Enable, active-high)

## 2. Đầu ra (Outputs):
- [7:0] out_data: Tuyến bus ngõ ra

## 3. Hoạt động / Logic mong muốn:
- Khi oe = 1: out_data = in_data.
- Khi oe = 0: out_data ở trạng thái trở kháng cao (High-Z: 8'bzzzzzzzz)."""
        },

        # =========================================================================
        # NHÓM 4: MUX, DEMUX, ENCODER & DECODER [31 - 40]
        # =========================================================================
        {
            "id": 31,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Ghép Kênh MUX 4 Sang 1 8-bit (mux_4to1_8bit)",
            "module": "mux_4to1_8bit",
            "spec_text": """# Bộ Ghép Kênh MUX 4 Sang 1 (mux_4to1_8bit)

## 1. Đầu vào (Inputs):
- [7:0] in0: Kênh dữ liệu 0
- [7:0] in1: Kênh dữ liệu 1
- [7:0] in2: Kênh dữ liệu 2
- [7:0] in3: Kênh dữ liệu 3
- [1:0] sel: Tín hiệu chọn kênh (00: in0, 01: in1, 10: in2, 11: in3)

## 2. Đầu ra (Outputs):
- [7:0] mux_out: Kênh dữ liệu được chọn

## 3. Hoạt động / Logic mong muốn:
- Chọn kênh ngõ vào xuất ra mux_out tương ứng với mã chọn sel."""
        },
        {
            "id": 32,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Ghép Kênh MUX 8 Sang 1 1-bit (mux_8to1_1bit)",
            "module": "mux_8to1_1bit",
            "spec_text": """# Bộ Ghép Kênh MUX 8 Sang 1 (mux_8to1_1bit)

## 1. Đầu vào (Inputs):
- [7:0] data_in: 8 kênh dữ liệu 1-bit
- [2:0] sel: Mã chọn kênh 3-bit

## 2. Đầu ra (Outputs):
- out_bit: Bit ngõ ra được chọn

## 3. Hoạt động / Logic mong muốn:
- out_bit = data_in[sel]."""
        },
        {
            "id": 33,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Phân Kênh DEMUX 1 Sang 4 8-bit (demux_1to4_8bit)",
            "module": "demux_1to4_8bit",
            "spec_text": """# Bộ Phân Kênh DEMUX 1 Sang 4 (demux_1to4_8bit)

## 1. Đầu vào (Inputs):
- [7:0] din: Dữ liệu ngõ vào
- [1:0] sel: Kênh đích muốn phân phối đến
- en: Cho phép phân kênh

## 2. Đầu ra (Outputs):
- [7:0] out0: Kênh ra 0
- [7:0] out1: Kênh ra 1
- [7:0] out2: Kênh ra 2
- [7:0] out3: Kênh ra 3

## 3. Hoạt động / Logic mong muốn:
- Khi en = 1: din được dẫn đến kênh được chỉ định bởi sel; các kênh còn lại bằng 0.
- Khi en = 0: tất cả các kênh bằng 0."""
        },
        {
            "id": 34,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Phân Kênh DEMUX 1 Sang 8 1-bit (demux_1to8_1bit)",
            "module": "demux_1to8_1bit",
            "spec_text": """# Bộ Phân Kênh DEMUX 1 Sang 8 (demux_1to8_1bit)

## 1. Đầu vào (Inputs):
- in_bit: Tín hiệu bit ngõ vào
- [2:0] sel: Địa chỉ chọn kênh đích 3-bit

## 2. Đầu ra (Outputs):
- [7:0] out_bus: Tuyến bus 8-bit ngõ ra

## 3. Hoạt động / Logic mong muốn:
- Đặt out_bus[sel] = in_bit; tất cả 7 bit còn lại gán bằng 0."""
        },
        {
            "id": 35,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Giải Mã Nhị Phân 2 Sang 4 (decoder_2to4)",
            "module": "decoder_2to4",
            "spec_text": """# Bộ Giải Mã 2 Sang 4 (decoder_2to4)

## 1. Đầu vào (Inputs):
- [1:0] in: Mã nhị phân ngõ vào 2-bit
- enable: Tín hiệu cho phép giải mã (active-high)

## 2. Đầu ra (Outputs):
- [3:0] out: Tín hiệu ngõ ra 4-bit (One-Hot)

## 3. Hoạt động / Logic mong muốn:
- Khi enable = 1: out[in] = 1, các bit khác = 0.
- Khi enable = 0: out = 4'b0000."""
        },
        {
            "id": 36,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Giải Mã Nhị Phân 3 Sang 8 (decoder_3to8)",
            "module": "decoder_3to8",
            "spec_text": """# Bộ Giải Mã 3 Sang 8 (decoder_3to8)

## 1. Đầu vào (Inputs):
- [2:0] a: Địa chỉ ngõ vào 3-bit
- en: Cho phép giải mã

## 2. Đầu ra (Outputs):
- [7:0] y: Tuyến ngõ ra 8-bit active-high

## 3. Hoạt động / Logic mong muốn:
- Khi en = 1: y = (1 << a).
- Khi en = 0: y = 8'b00000000."""
        },
        {
            "id": 37,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Mã Hóa Ưu Tiên 8 Sang 3 (priority_encoder_8to3)",
            "module": "priority_encoder_8to3",
            "spec_text": """# Bộ Mã Hóa Ưu Tiên 8 Sang 3 (priority_encoder_8to3)

## 1. Đầu vào (Inputs):
- [7:0] req: Tuyến yêu cầu ngõ vào 8-bit (bit 7 có độ ưu tiên cao nhất)

## 2. Đầu ra (Outputs):
- [2:0] code: Mã nhị phân của yêu cầu có độ ưu tiên cao nhất
- valid: Bằng 1 nếu có ít nhất 1 yêu cầu kích hoạt

## 3. Hoạt động / Logic mong muốn:
- Quét từ bit req[7] xuống req[0]; xuất chỉ số của bit 1 đầu tiên tìm thấy ra code.
- valid = 0 khi req == 8'b00000000."""
        },
        {
            "id": 38,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Giải Mã BCD Sang LED 7 Đoạn Anode Chung (bcd_to_7seg_anode)",
            "module": "bcd_to_7seg_anode",
            "spec_text": """# Bộ Giải Mã BCD Sang LED 7 Đoạn Anode (bcd_to_7seg_anode)

## 1. Đầu vào (Inputs):
- [3:0] bcd: Chữ số BCD ngõ vào (0 đến 9)

## 2. Đầu ra (Outputs):
- [6:0] seg: Mã điều khiển 7 đoạn {a,b,c,d,e,f,g} (Active-low: 0 là sáng, 1 là tắt)

## 3. Hoạt động / Logic mong muốn:
- Giải mã chuẩn Anode chung:
  0: 7'b1000000, 1: 7'b1111001, 2: 7'b0100100, 3: 7'b0110000,
  4: 7'b0011001, 5: 7'b0010010, 6: 7'b0000010, 7: 7'b1111000,
  8: 7'b0000000, 9: 7'b0010000. Nếu > 9: 7'b1111111 (tắt hết)."""
        },
        {
            "id": 39,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Giải Mã BCD Sang LED 7 Đoạn Cathode Chung (bcd_to_7seg_cathode)",
            "module": "bcd_to_7seg_cathode",
            "spec_text": """# Bộ Giải Mã BCD Sang LED 7 Đoạn Cathode (bcd_to_7seg_cathode)

## 1. Đầu vào (Inputs):
- [3:0] bcd: Số BCD ngõ vào (0 đến 9)

## 2. Đầu ra (Outputs):
- [6:0] seg: Mã điều khiển 7 đoạn {a,b,c,d,e,f,g} (Active-high: 1 là sáng, 0 là tắt)

## 3. Hoạt động / Logic mong muốn:
- Giải mã chuẩn Cathode chung:
  0: 7'b0111111, 1: 7'b0000110, 2: 7'b1011011, 3: 7'b1001111,
  4: 7'b1100110, 5: 7'b1101101, 6: 7'b1111101, 7: 7'b0000111,
  8: 7'b1111111, 9: 7'b1101111."""
        },
        {
            "id": 40,
            "group": "Nhóm 4: MUX, DEMUX, Mã Hóa & Giải Mã",
            "name": "Bộ Chuyển Đổi Nhị Phân Sang Mã Gray 4-bit (bin_to_gray_4bit)",
            "module": "bin_to_gray_4bit",
            "spec_text": """# Bộ Chuyển Đổi Nhị Phân Sang Mã Gray (bin_to_gray_4bit)

## 1. Đầu vào (Inputs):
- [3:0] bin_in: Số nhị phân 4-bit ngõ vào

## 2. Đầu ra (Outputs):
- [3:0] gray_out: Mã Gray 4-bit tương ứng

## 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp chuyển đổi theo công thức logic: gray_out = bin_in ^ (bin_in >> 1)."""
        },

        # =========================================================================
        # NHÓM 5: FSM & BỘ DÒ CHUỖI (FSM & DETECTORS) [41 - 50]
        # =========================================================================
        {
            "id": 41,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Bộ Phát Hiện Chuỗi Bit 1011 Kiểu Mealy (seq_detector_1011_mealy)",
            "module": "seq_detector_1011_mealy",
            "spec_text": """# Bộ Dò Chuỗi 1011 Kiểu Mealy (seq_detector_1011_mealy)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset đồng bộ tích cực cao
- bit_in: Chuỗi bit nối tiếp vào

## 2. Đầu ra (Outputs):
- detected: Bằng 1 trong chu kỳ xuất hiện bit cuối cùng khớp mẫu 1011

## 3. Hoạt động / Logic mong muốn:
- FSM kiểu Mealy phát hiện chuỗi 1011 (cho phép chuỗi gối đầu nhau - overlapping).
- detected bật lên 1 ngay khi bit thứ 4 đưa vào là 1 và 3 bit trước đó là 1, 0, 1."""
        },
        {
            "id": 42,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Bộ Phát Hiện Chuỗi Bit 1101 Kiểu Moore (seq_detector_1101_moore)",
            "module": "seq_detector_1101_moore",
            "spec_text": """# Bộ Dò Chuỗi 1101 Kiểu Moore (seq_detector_1101_moore)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- d_in: Dữ liệu bit nối tiếp

## 2. Đầu ra (Outputs):
- found: Bằng 1 khi phát hiện thành công chuỗi 1101

## 3. Hoạt động / Logic mong muốn:
- FSM kiểu Moore: ngõ ra found chỉ phụ thuộc vào trạng thái hiện tại (bật lên 1 ở trạng thái nhận đủ chuỗi)."""
        },
        {
            "id": 43,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Khóa Mã Số Điện Tử An Toàn 4 Chữ Số (digital_safe_lock)",
            "module": "digital_safe_lock",
            "spec_text": """# Khóa Mã Số Điện Tử An Toàn (digital_safe_lock)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- [3:0] key_in: Chữ số người dùng nhập vào (0-9)
- enter: Xung xác nhận sau mỗi lần bấm phím

## 2. Đầu ra (Outputs):
- unlock: Mở khóa thành công (1: Mở khóa, 0: Khóa)
- alarm: Còi báo động khi nhập sai quá 3 lần
- [1:0] err_count: Số lần nhập sai

## 3. Hoạt động / Logic mong muốn:
- Mật khẩu cố định: 4 -> 2 -> 7 -> 9.
- Nếu nhập đúng liên tiếp 4 số: unlock = 1 trong 5 chu kỳ clk và xóa err_count về 0.
- Nếu nhập sai bất kỳ số nào: err_count tăng 1 và quay về chờ nhập lại.
- Nếu err_count == 3: alarm = 1 và khóa cứng mạch cho tới khi có rst = 1."""
        },
        {
            "id": 44,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Bộ Phát Hiện Chuỗi 3 Số 1 Liên Tiếp (seq_detector_111)",
            "module": "seq_detector_111",
            "spec_text": """# Bộ Phát Hiện Chuỗi 3 Số 1 Liên Tiếp (seq_detector_111)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- din: Bit dữ liệu vào nối tiếp

## 2. Đầu ra (Outputs):
- match_111: Bằng 1 khi phát hiện 3 bit 1 liên tiếp

## 3. Hoạt động / Logic mong muốn:
- Đếm số lượng bit 1 liên tục.
- Khi nhận đủ 3 bit 1: match_111 = 1."""
        },
        {
            "id": 45,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Máy Trạng Thái Điều Khiển Cửa Cuốn Tự Động (automatic_rolling_door_fsm)",
            "module": "automatic_rolling_door_fsm",
            "spec_text": """# Cửa Cuốn Tự Động FSM (automatic_rolling_door_fsm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- btn_open: Nút bấm mở cửa
- btn_close: Nút bấm đóng cửa
- btn_stop: Nút bấm dừng khẩn cấp
- sensor_top: Công tắc hành trình chạm đỉnh trên
- sensor_bottom: Công tắc hành trình chạm đáy dưới

## 2. Đầu ra (Outputs):
- motor_up: Động cơ kéo cửa cuốn lên
- motor_down: Động cơ thả cửa cuốn xuống

## 3. Hoạt động / Logic mong muốn:
- Khi bấm btn_open: motor_up = 1 cho đến khi sensor_top = 1 hoặc bấm stop.
- Khi bấm btn_close: motor_down = 1 cho đến khi sensor_bottom = 1 hoặc bấm stop.
- Đảm bảo an toàn: Tuyệt đối không bật đồng thời motor_up và motor_down."""
        },
        {
            "id": 46,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Máy Trạng Thái Rào Chắn Barrier Bãi Đỗ Xe (parking_barrier_fsm)",
            "module": "parking_barrier_fsm",
            "spec_text": """# Rào Chắn Barrier Bãi Xe FSM (parking_barrier_fsm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- car_detected: Cảm biến quang phát hiện xe đến trước rào chắn
- card_valid: Tín hiệu quẹt thẻ xe hợp lệ
- car_passed: Cảm biến xe đã đi qua hoàn toàn

## 2. Đầu ra (Outputs):
- barrier_open: Nâng thanh chắn barrier lên
- red_light: Đèn đỏ dừng xe
- green_light: Đèn xanh cho xe đi qua

## 3. Hoạt động / Logic mong muốn:
- Trạng thái chờ: barrier_open = 0, red_light = 1, green_light = 0.
- Khi car_detected = 1 và card_valid = 1: barrier_open = 1, green_light = 1, red_light = 0.
- Khi car_passed = 1: đóng barrier, chuyển về đèn đỏ."""
        },
        {
            "id": 47,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Máy Bán Vé Xe Bus Tự Động (ticket_vending_fsm)",
            "module": "ticket_vending_fsm",
            "spec_text": """# Máy Bán Vé Xe Bus FSM (ticket_vending_fsm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- coin_5k: Nhét vào đồng xu/tiền 5.000đ
- coin_10k: Nhét vào đồng xu/tiền 10.000đ
- cancel: Nút hủy giao dịch

## 2. Đầu ra (Outputs):
- dispense_ticket: Nhả vé xe (giá vé cố định 10.000đ)
- change_5k: Trả lại tiền thừa 5.000đ

## 3. Hoạt động / Logic mong muốn:
- Nhét đủ 10k: dispense_ticket = 1.
- Nhét 5k rồi nhét tiếp 10k (tổng 15k): dispense_ticket = 1 và change_5k = 1.
- Bấm cancel: trả lại số tiền đã nạp."""
        },
        {
            "id": 48,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Bộ Điều Khiển Đèn Pha Ô Tô Thông Minh (auto_headlight_fsm)",
            "module": "auto_headlight_fsm",
            "spec_text": """# Đèn Pha Ô Tô Thông Minh FSM (auto_headlight_fsm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- light_sensor_dark: Cảm biến trời tối
- oncoming_car: Cảm biến phát hiện xe đi ngược chiều
- engine_on: Động cơ ô tô đang nổ máy

## 2. Đầu ra (Outputs):
- low_beam: Đèn chiếu gần (đèn cos)
- high_beam: Đèn chiếu xa (đèn pha)

## 3. Hoạt động / Logic mong muốn:
- Khi engine_on = 0: tắt hết đèn.
- Khi engine_on = 1 và trời tối:
  + Nếu có xe ngược chiều: low_beam = 1, high_beam = 0 (tránh chói mắt).
  + Nếu không có xe ngược chiều: low_beam = 1, high_beam = 1."""
        },
        {
            "id": 49,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Mạch Giám Sát Watchdog Timer Cho Vi Xử Lý (watchdog_timer_fsm)",
            "module": "watchdog_timer_fsm",
            "spec_text": """# Mạch Giám Sát Watchdog Timer (watchdog_timer_fsm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset phần cứng
- kick_wdog: Tín hiệu xóa bộ đếm watchdog từ CPU (xung định kỳ)

## 2. Đầu ra (Outputs):
- system_reset: Xung reset toàn bộ hệ thống khi CPU bị treo

## 3. Hoạt động / Logic mong muốn:
- Bộ đếm thời gian tăng liên tục mỗi chu kỳ clk.
- Nếu kick_wdog = 1: bộ đếm xóa về 0.
- Nếu quá 1.000 chu kỳ mà không nhận được kick_wdog: phát xung system_reset = 1 trong 5 chu kỳ."""
        },
        {
            "id": 50,
            "group": "Nhóm 5: Máy Trạng Thái FSM & Bộ Dò Chuỗi",
            "name": "Bộ Giải Mã Bàn Phím Ma Trận 4x4 (keypad_matrix_fsm)",
            "module": "keypad_matrix_fsm",
            "spec_text": """# Giải Mã Bàn Phím Ma Trận 4x4 (keypad_matrix_fsm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp quét phím
- rst: Reset tích cực cao
- [3:0] row_in: Tín hiệu 4 hàng quét về từ bàn phím

## 2. Đầu ra (Outputs):
- [3:0] col_scan: Tín hiệu quét 4 cột (quét lần lượt từng cột 0)
- [3:0] key_code: Mã phím nhị phân từ 0 đến 15 của nút vừa bấm
- key_valid: Báo có phím hợp lệ vừa được nhấn

## 3. Hoạt động / Logic mong muốn:
- FSM quét xoay vòng 4 cột; khi phát hiện hàng có tín hiệu kích hoạt, chốt mã phím và bật key_valid = 1."""
        },

        # =========================================================================
        # NHÓM 6: GIAO TIẾP & NGOẠI VI CÔNG NGHIỆP [51 - 60]
        # =========================================================================
        {
            "id": 51,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Phát Truyền Nối Tiếp UART Transmitter 8-bit (uart_tx_8bit)",
            "module": "uart_tx_8bit",
            "spec_text": """# Bộ Phát UART TX 8-bit (uart_tx_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- tx_start: Xung kích hoạt truyền byte
- [7:0] tx_data: Dữ liệu 8-bit cần truyền

## 2. Đầu ra (Outputs):
- tx_serial: Đường truyền nối tiếp TX (mặc định mức 1 khi rảnh)
- tx_busy: Báo bộ phát đang bận truyền dữ liệu

## 3. Hoạt động / Logic mong muốn:
- Khung truyền chuẩn 8-N-1: 1 Start bit (mức 0), 8 Data bits (truyền từ LSB đến MSB), 1 Stop bit (mức 1).
- tx_busy = 1 trong suốt quá trình truyền."""
        },
        {
            "id": 52,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Nhận Truyền Nối Tiếp UART Receiver 8-bit (uart_rx_8bit)",
            "module": "uart_rx_8bit",
            "spec_text": """# Bộ Nhận UART RX 8-bit (uart_rx_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống (tần số lấy mẫu)
- rst: Reset hệ thống
- rx_serial: Đường truyền nối tiếp RX nhận về

## 2. Đầu ra (Outputs):
- [7:0] rx_data: Byte dữ liệu 8-bit thu nhận được
- rx_ready: Xung báo nhận xong 1 byte hợp lệ

## 3. Hoạt động / Logic mong muốn:
- Phát hiện cạnh xuống của Start bit, lấy mẫu dữ liệu tại tâm mỗi bit.
- Sau khi nhận đủ 8 bit dữ liệu và Stop bit, xuất byte dữ liệu ra rx_data và phát xung rx_ready = 1."""
        },
        {
            "id": 53,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Giao Diện Ngoại Vi SPI Slave (spi_slave_controller)",
            "module": "spi_slave_controller",
            "spec_text": """# Giao Diện SPI Slave (spi_slave_controller)

## 1. Đầu vào (Inputs):
- sclk: Xung clock từ SPI Master
- cs_n: Chọn chip (active-low, mức 0 là chọn)
- mosi: Dữ liệu nối tiếp Master Out Slave In
- [7:0] tx_byte: Dữ liệu Slave chuẩn bị gửi lên Master

## 2. Đầu ra (Outputs):
- miso: Dữ liệu nối tiếp Master In Slave Out
- [7:0] rx_byte: Dữ liệu Slave nhận được từ Master
- rx_ready: Báo nhận xong byte dữ liệu

## 3. Hoạt động / Logic mong muốn:
- Khi cs_n = 0: dịch dữ liệu vào rx_byte tại mỗi sườn dương sclk và đẩy tx_byte ra miso tại sườn âm sclk."""
        },
        {
            "id": 54,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Giao Diện SPI Master Cơ Bản (spi_master_basic)",
            "module": "spi_master_basic",
            "spec_text": """# Giao Diện SPI Master (spi_master_basic)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- start: Bắt đầu phiên truyền thông
- [7:0] data_in: Byte dữ liệu cần truyền
- miso: Tín hiệu từ Slave trả về

## 2. Đầu ra (Outputs):
- sclk_out: Xung clock cấp cho SPI Slave
- cs_n: Tín hiệu chọn chip active-low
- mosi: Dữ liệu nối tiếp phát đi
- busy: Cờ báo đang truyền nhận

## 3. Hoạt động / Logic mong muốn:
- Khi start = 1: kéo cs_n xuống 0, phát 8 xung sclk_out đồng bộ cùng dữ liệu trên chân mosi."""
        },
        {
            "id": 55,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Tạo Mã Kiểm Tra Lỗi CRC-8 Chuẩn ITU (crc8_generator)",
            "module": "crc8_generator",
            "spec_text": """# Bộ Tạo Mã CRC-8 (crc8_generator)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset bộ tính toán
- data_valid: Báo byte dữ liệu hợp lệ
- [7:0] data_byte: Byte dữ liệu ngõ vào

## 2. Đầu ra (Outputs):
- [7:0] crc_out: Giá trị mã kiểm tra CRC-8 hiện tại
- crc_valid: Báo mã CRC-8 đã sẵn sàng

## 3. Hoạt động / Logic mong muốn:
- Sử dụng đa thức sinh CRC-8 chuẩn ITU: x^8 + x^2 + x + 1 (đa thức 8'h07).
- Tính toán cập nhật checksum nối tiếp theo từng byte dữ liệu."""
        },
        {
            "id": 56,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Kiểm Tra Tính Chẵn Lẻ Parity 8-bit (parity_checker_8bit)",
            "module": "parity_checker_8bit",
            "spec_text": """# Bộ Kiểm Tra Tính Chẵn Lẻ Parity (parity_checker_8bit)

## 1. Đầu vào (Inputs):
- [7:0] data_in: Byte dữ liệu ngõ vào 8-bit
- parity_bit: Bit kiểm tra chẵn lẻ kèm theo
- odd_even: Chế độ kiểm tra (0: Chẵn - Even, 1: Lẻ - Odd)

## 2. Đầu ra (Outputs):
- parity_error: Bằng 1 nếu dữ liệu bị lỗi tính chẵn lẻ

## 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp kiểm tra tổng số bit 1 trong data_in và parity_bit theo chế độ odd_even được chọn."""
        },
        {
            "id": 57,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Đóng Gói Khung Truyền Packet Framer (packet_framer_sync)",
            "module": "packet_framer_sync",
            "spec_text": """# Bộ Đóng Gói Khung Tin (packet_framer_sync)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- send_packet: Kích hoạt gửi gói tin
- [7:0] payload_data: Dữ liệu cần gửi

## 2. Đầu ra (Outputs):
- [7:0] frame_out: Byte xuất ra trên đường truyền
- frame_valid: Báo byte xuất ra hợp lệ

## 3. Hoạt động / Logic mong muốn:
- Tự động đóng gói theo cấu trúc: Header (8'hAA) -> Payload -> Checksum (Header ^ Payload) -> End-of-frame (8'h55)."""
        },
        {
            "id": 58,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Giải Nén Khung Tin Packet Deframer (packet_deframer_sync)",
            "module": "packet_deframer_sync",
            "spec_text": """# Bộ Giải Nén Khung Tin (packet_deframer_sync)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- [7:0] byte_in: Byte nhận về từ đường truyền
- byte_valid: Byte ngõ vào hợp lệ

## 2. Đầu ra (Outputs):
- [7:0] payload_out: Dữ liệu hữu ích bóc tách được
- packet_ok: Báo nhận gói tin thành công và kiểm tra checksum đúng

## 3. Hoạt động / Logic mong muốn:
- Tìm byte Header 8'hAA, lưu Payload, so sánh Checksum; nếu đúng thì xuất packet_ok = 1."""
        },
        {
            "id": 59,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Đồng Bộ Tín Hiệu 2 Tầng Dual-Flop Synchronizer (dual_flop_sync)",
            "module": "dual_flop_sync",
            "spec_text": """# Bộ Đồng Bộ 2 Tầng Dual-Flop (dual_flop_sync)

## 1. Đầu vào (Inputs):
- clk_dest: Xung nhịp miền đồng hồ đích
- rst: Reset đồng bộ
- async_in: Tín hiệu bất đồng bộ từ miền đồng hồ khác sang

## 2. Đầu ra (Outputs):
- sync_out: Tín hiệu đã được đồng bộ hóa hoàn toàn, chống trạng thái siêu ổn định (Metastability)

## 3. Hoạt động / Logic mong muốn:
- Cho async_in đi qua liên tiếp 2 tầng D Flip-Flop kích bằng clk_dest trước khi xuất ra sync_out."""
        },
        {
            "id": 60,
            "group": "Nhóm 6: Giao Tiếp & Ngoại Vi",
            "name": "Bộ Chuyển Đổi RS-232 Sang Dữ Liệu Song Song (rs232_to_parallel)",
            "module": "rs232_to_parallel",
            "spec_text": """# Bộ Chuyển Đổi RS-232 Sang Song Song (rs232_to_parallel)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- rxd: Tín hiệu nối tiếp mức TTL từ chip MAX232

## 2. Đầu ra (Outputs):
- [7:0] parallel_data: 8-bit dữ liệu song song
- data_ready: Báo dữ liệu sẵn sàng đọc

## 3. Hoạt động / Logic mong muốn:
- Giải mã tín hiệu UART baudrate chuẩn và ghi nhận dữ liệu song song vào thanh ghi ngõ ra."""
        },

        # =========================================================================
        # NHÓM 7: ĐIỀU CHẾ XUNG PWM & ĐIỀU KHIỂN ĐỘNG CƠ [61 - 70]
        # =========================================================================
        {
            "id": 61,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Tạo Xung PWM 8-bit Điều Chỉnh Độ Rộng (pwm_generator_8bit)",
            "module": "pwm_generator_8bit",
            "spec_text": """# Bộ Tạo Xung PWM 8-bit (pwm_generator_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp định thời
- rst: Reset tích cực cao
- [7:0] duty_cycle: Giá trị chu kỳ nhiệm vụ (0 đến 255)

## 2. Đầu ra (Outputs):
- pwm_out: Xung PWM ngõ ra

## 3. Hoạt động / Logic mong muốn:
- Bộ đếm 8-bit tăng liên tục từ 0 đến 255 rồi quay vòng về 0.
- Nếu counter < duty_cycle: pwm_out = 1, ngược lại pwm_out = 0."""
        },
        {
            "id": 62,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Điều Khiển Động Cơ Bước 4 Pha Full-Step (stepper_motor_fullstep)",
            "module": "stepper_motor_fullstep",
            "spec_text": """# Động Cơ Bước 4 Pha Full-Step (stepper_motor_fullstep)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp bước (mỗi xung tương ứng 1 bước xoay)
- rst: Reset tích cực cao
- direction: Hướng quay (1: Quay thuận kim đồng hồ, 0: Quay ngược)
- enable: Cho phép động cơ hoạt động

## 2. Đầu ra (Outputs):
- [3:0] phase_out: Tín hiệu kích hoạt 4 cuộn dây pha (A, B, C, D)

## 3. Hoạt động / Logic mong muốn:
- Chế độ Full-step 4 bước: 4'b1000 -> 4'b0100 -> 4'b0010 -> 4'b0001 (hoặc ngược lại nếu direction = 0)."""
        },
        {
            "id": 63,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Điều Khiển Động Cơ Bước Chế Độ Nửa Bước Half-Step (stepper_motor_halfstep)",
            "module": "stepper_motor_halfstep",
            "spec_text": """# Động Cơ Bước Nửa Bước Half-Step (stepper_motor_halfstep)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp bước
- rst: Reset tích cực cao
- dir: Chiều quay
- en: Cho phép xoay

## 2. Đầu ra (Outputs):
- [3:0] phase: Tín hiệu kích từ 4 cuộn dây (chu kỳ 8 trạng thái)

## 3. Hoạt động / Logic mong muốn:
- Trình tự 8 bước: 1000 -> 1100 -> 0100 -> 0110 -> 0010 -> 0011 -> 0001 -> 1001."""
        },
        {
            "id": 64,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Điều Khiển Động Cơ DC Đảo Chiều Cầu H (hbridge_dc_motor)",
            "module": "hbridge_dc_motor",
            "spec_text": """# Động Cơ DC Cầu H (hbridge_dc_motor)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- forward_cmd: Lệnh quay thuận
- reverse_cmd: Lệnh quay ngược
- [7:0] speed_val: Tốc độ động cơ (0-255)

## 2. Đầu ra (Outputs):
- pwm_a: Tín hiệu điều khiển nhánh A cầu H
- pwm_b: Tín hiệu điều khiển nhánh B cầu H

## 3. Hoạt động / Logic mong muốn:
- Quay thuận: pwm_a phát xung PWM tỉ lệ theo speed_val, pwm_b = 0.
- Quay ngược: pwm_b phát xung PWM, pwm_a = 0.
- Khóa an toàn: Tuyệt đối không bật cả 2 nhánh cùng lúc (chống chập mạch cầu H)."""
        },
        {
            "id": 65,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Điều Khiển Góc Quay Động Cơ Servo PWM (servo_motor_pwm)",
            "module": "servo_motor_pwm",
            "spec_text": """# Bộ Điều Khiển Servo PWM (servo_motor_pwm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp định thời
- rst: Reset hệ thống
- [7:0] angle: Góc quay mong muốn từ 0 đến 180 độ

## 2. Đầu ra (Outputs):
- servo_pwm: Tín hiệu điều khiển servo chu kỳ 20ms, độ rộng xung dương từ 1ms (0 độ) đến 2ms (180 độ)

## 3. Hoạt động / Logic mong muốn:
- Ánh xạ tuyến tính giá trị angle sang độ rộng xung tương ứng từ 1ms đến 2ms."""
        },
        {
            "id": 66,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Điều Khiển Tốc Độ Quạt 4 Mức Tốc Độ (fan_speed_controller)",
            "module": "fan_speed_controller",
            "spec_text": """# Bộ Điều Khiển Quạt 4 Cấp Tốc Độ (fan_speed_controller)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- [1:0] speed_sel: Mức tốc độ (00: Tắt, 01: Chậm 33%, 10: Vừa 66%, 11: Nhanh 100%)

## 2. Đầu ra (Outputs):
- fan_pwm: Xung PWM điều khiển quạt

## 3. Hoạt động / Logic mong muốn:
- Điều chế xung PWM với duty cycle tương ứng với mức speed_sel được chọn."""
        },
        {
            "id": 67,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Mạch Tạo Xung PWM Tần Số Cố Định 1kHz (pwm_fixed_1khz)",
            "module": "pwm_fixed_1khz",
            "spec_text": """# Mạch PWM Tần Số Cố Định 1kHz (pwm_fixed_1khz)

## 1. Đầu vào (Inputs):
- clk_50m: Xung nhịp 50MHz
- rst: Reset tích cực cao
- [6:0] duty_percent: Phần trăm chu kỳ tích cực (0% đến 100%)

## 2. Đầu ra (Outputs):
- pwm_out: Xung PWM 1kHz

## 3. Hoạt động / Logic mong muốn:
- Chia xung nhịp tạo chu kỳ chuẩn 1ms (1kHz); kiểm soát thời gian xung cao theo duty_percent."""
        },
        {
            "id": 68,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Hãm Phanh Điện Tử Động Cơ DC (dc_motor_electronic_brake)",
            "module": "dc_motor_electronic_brake",
            "spec_text": """# Bộ Hãm Phanh Động Cơ DC (dc_motor_electronic_brake)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- run_cmd: Lệnh cho động cơ chạy
- emergency_brake: Lệnh phanh khẩn cấp

## 2. Đầu ra (Outputs):
- motor_drive: Tín hiệu kích chạy động cơ
- brake_active: Tín hiệu kích phanh điện tử ngắn mạch cuộn dây

## 3. Hoạt động / Logic mong muốn:
- Khi emergency_brake = 1: ngắt ngay lập tức motor_drive và kích hoạt brake_active = 1 trong 100 chu kỳ."""
        },
        {
            "id": 69,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Bộ Đọc Cảm Biến Xung Góc Quay Encoder A/B (quadrature_encoder_reader)",
            "module": "quadrature_encoder_reader",
            "spec_text": """# Bộ Đọc Encoder Trục Quay A/B (quadrature_encoder_reader)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp lấy mẫu
- rst: Reset tích cực cao
- enc_a: Tín hiệu xung kênh A
- enc_b: Tín hiệu xung kênh B

## 2. Đầu ra (Outputs):
- [15:0] position_count: Tọa độ vị trí góc quay
- dir_clockwise: Báo chiều quay (1: Thuận, 0: Nghịch)

## 3. Hoạt động / Logic mong muốn:
- Giải mã tín hiệu vuông pha 90 độ (Quadrature).
- Nếu kênh A dẫn trước kênh B: tăng position_count; nếu kênh B dẫn trước kênh A: giảm position_count."""
        },
        {
            "id": 70,
            "group": "Nhóm 7: Điều Chế Xung PWM & Động Cơ",
            "name": "Mạch Tạo Hiệu Ứng Đèn LED Thở Breathing PWM (breathing_led_pwm)",
            "module": "breathing_led_pwm",
            "spec_text": """# Đèn LED Thở Breathing PWM (breathing_led_pwm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- enable: Kích hoạt hiệu ứng

## 2. Đầu ra (Outputs):
- led_out: Xung PWM điều khiển độ sáng đèn LED

## 3. Hoạt động / Logic mong muốn:
- Độ rộng xung tăng dần từ 0% lên 100% rồi giảm dần về 0% theo chu kỳ tuần hoàn mượt mà."""
        },

        # =========================================================================
        # NHÓM 8: KHỬ NHIỄU, XỬ LÝ TÍN HIỆU & ĐO LƯỜNG [71 - 80]
        # =========================================================================
        {
            "id": 71,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Khử Rung Nhiễu Nút Bấm Button Debouncer (button_debouncer)",
            "module": "button_debouncer",
            "spec_text": """# Mạch Khử Rung Nút Bấm (button_debouncer)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- btn_in: Tín hiệu vật lý từ nút bấm cơ học (bị rung nảy nhiễu)

## 2. Đầu ra (Outputs):
- btn_clean: Tín hiệu nút bấm sạch sau khi lọc bỏ rung nhiễu
- btn_pressed_pulse: Xung kích 1 chu kỳ clk khi nút vừa được nhấn xuống

## 3. Hoạt động / Logic mong muốn:
- Đếm thời gian duy trì ổn định của tín hiệu (chờ 20ms liên tục không đổi).
- Chỉ cập nhật btn_clean khi tín hiệu ngõ vào đã hoàn toàn ổn định."""
        },
        {
            "id": 72,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Phát Hiện Cạnh Lên Sườn Dương Positive Edge Detector (pos_edge_detector)",
            "module": "pos_edge_detector",
            "spec_text": """# Mạch Dò Sườn Dương (pos_edge_detector)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng bộ
- rst: Reset tích cực cao
- sig_in: Tín hiệu ngõ vào cần giám sát

## 2. Đầu ra (Outputs):
- pos_edge: Xung tích cực mức cao trong đúng 1 chu kỳ clk khi sig_in chuyển từ 0 lên 1

## 3. Hoạt động / Logic mong muốn:
- Lưu giá trị sig_in của chu kỳ trước: pos_edge = sig_in & (~sig_in_prev)."""
        },
        {
            "id": 73,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Phát Hiện Cạnh Xuống Sườn Âm Negative Edge Detector (neg_edge_detector)",
            "module": "neg_edge_detector",
            "spec_text": """# Mạch Dò Sườn Âm (neg_edge_detector)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp đồng bộ
- rst: Reset tích cực cao
- sig_in: Tín hiệu ngõ vào

## 2. Đầu ra (Outputs):
- neg_edge: Xung ngõ ra bằng 1 trong đúng 1 chu kỳ clk khi sig_in chuyển từ 1 xuống 0

## 3. Hoạt động / Logic mong muốn:
- Lưu giá trị trễ 1 chu kỳ: neg_edge = (~sig_in) & sig_in_prev."""
        },
        {
            "id": 74,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Phát Hiện Cả Hai Cạnh Sườn Xung Dual Edge Detector (dual_edge_detector)",
            "module": "dual_edge_detector",
            "spec_text": """# Mạch Dò Cả Hai Cạnh Xung (dual_edge_detector)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- sig_in: Tín hiệu vào

## 2. Đầu ra (Outputs):
- any_edge: Phát xung 1 chu kỳ khi có bất kỳ sự thay đổi mức logic nào (0->1 hoặc 1->0)

## 3. Hoạt động / Logic mong muốn:
- any_edge = sig_in ^ sig_in_prev."""
        },
        {
            "id": 75,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Đo Độ Rộng Xung Tín Hiệu Pulse Width Measurer (pulse_width_measurer)",
            "module": "pulse_width_measurer",
            "spec_text": """# Mạch Đo Độ Rộng Xung (pulse_width_measurer)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp định thời chuẩn (ví dụ 1MHz)
- rst: Reset hệ thống
- pulse_in: Xung tín hiệu cần đo độ rộng mức cao

## 2. Đầu ra (Outputs):
- [15:0] pulse_width: Số chu kỳ xung clock mà pulse_in ở mức 1
- done: Cờ báo đo xong khi pulse_in vừa kết thúc mức 1

## 3. Hoạt động / Logic mong muốn:
- Khi pulse_in = 1: tăng biến đếm; khi pulse_in rơi xuống 0: chốt giá trị ra pulse_width và bật done = 1."""
        },
        {
            "id": 76,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Đo Tần Số Tín Hiệu Frequency Counter (frequency_measurer)",
            "module": "frequency_measurer",
            "spec_text": """# Mạch Đo Tần Số Tín Hiệu (frequency_measurer)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- sig_unknown: Tín hiệu cần đo tần số
- gate_1s: Cửa sổ lấy mẫu chuẩn 1 giây

## 2. Đầu ra (Outputs):
- [15:0] freq_hz: Giá trị tần số đo được tính theo Hertz (Hz)
- ready: Báo kết quả đo đã sẵn sàng

## 3. Hoạt động / Logic mong muốn:
- Đếm số chu kỳ của sig_unknown trong suốt khoảng thời gian gate_1s mở (1 giây), sau đó chốt kết quả ra freq_hz."""
        },
        {
            "id": 77,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Tạo Trễ Tín Hiệu Lập Trình Được (programmable_delay_timer)",
            "module": "programmable_delay_timer",
            "spec_text": """# Mạch Trễ Tín Hiệu Lập Trình (programmable_delay_timer)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- trigger_in: Tín hiệu kích hoạt bắt đầu tạo trễ
- [7:0] delay_cycles: Số chu kỳ trễ mong muốn (0-255)

## 2. Đầu ra (Outputs):
- delayed_out: Xung phát ra sau đúng delay_cycles chu kỳ kể từ lúc trigger_in kích hoạt

## 3. Hoạt động / Logic mong muốn:
- Khi nhận trigger_in, đếm đủ delay_cycles chu kỳ clk rồi kích hoạt delayed_out trong 1 chu kỳ."""
        },
        {
            "id": 78,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Lọc Số Trung Bình Cộng 4 Mẫu Moving Average Filter (moving_average_filter_4)",
            "module": "moving_average_filter_4",
            "spec_text": """# Mạch Lọc Trung Bình 4 Mẫu (moving_average_filter_4)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp lấy mẫu
- rst: Reset bộ lọc
- [7:0] sample_in: Mẫu tín hiệu mới nạp vào
- valid_in: Mẫu ngõ vào hợp lệ

## 2. Đầu ra (Outputs):
- [7:0] avg_out: Giá trị trung bình trượt của 4 mẫu gần nhất: (S0 + S1 + S2 + S3) / 4

## 3. Hoạt động / Logic mong muốn:
- Dùng thanh ghi dịch 4 tầng lưu 4 mẫu gần nhất; cộng tổng và dịch phải 2 bit để chia 4."""
        },
        {
            "id": 79,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch So Sánh Ngưỡng Cửa Sổ Số Window Comparator (window_level_comparator)",
            "module": "window_level_comparator",
            "spec_text": """# Mạch So Sánh Cửa Sổ Số (window_level_comparator)

## 1. Đầu vào (Inputs):
- [7:0] val_in: Giá trị tín hiệu số cần kiểm tra
- [7:0] lower_threshold: Ngưỡng dưới
- [7:0] upper_threshold: Ngưỡng trên

## 2. Đầu ra (Outputs):
- inside_window: Bằng 1 nếu lower_threshold <= val_in <= upper_threshold
- alarm_high: Bằng 1 nếu val_in > upper_threshold
- alarm_low: Bằng 1 nếu val_in < lower_threshold

## 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp phân loại giá trị ngõ vào so với vùng cửa sổ an toàn."""
        },
        {
            "id": 80,
            "group": "Nhóm 8: Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường",
            "name": "Mạch Giãn Xung Đơn Ổn Monostable Multivibrator (monostable_pulse_stretcher)",
            "module": "monostable_pulse_stretcher",
            "spec_text": """# Mạch Giãn Độ Rộng Xung (monostable_pulse_stretcher)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- narrow_pulse: Xung hẹp ngõ vào (chỉ 1 chu kỳ)
- [7:0] stretch_len: Độ rộng mong muốn cần giãn (số chu kỳ)

## 2. Đầu ra (Outputs):
- wide_pulse: Xung ngõ ra có độ rộng kéo dài đủ stretch_len chu kỳ clk

## 3. Hoạt động / Logic mong muốn:
- Nhận narrow_pulse, kích wide_pulse = 1 và duy trì liên tục trong đúng stretch_len chu kỳ."""
        },

        # =========================================================================
        # NHÓM 9: HỆ THỐNG TỰ ĐỘNG HÓA & THIẾT BỊ THÔNG MINH [81 - 90]
        # =========================================================================
        {
            "id": 81,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Máy Bán Nước Tự Động 15.000đ Có Trả Lại Tiền Thừa (vending_machine)",
            "module": "vending_machine",
            "spec_text": """# Máy Bán Nước Tự Động 15.000đ (vending_machine)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống tích cực cao
- coin_5k: Nhét tiền mệnh giá 5.000đ
- coin_10k: Nhét tiền mệnh giá 10.000đ
- cancel_btn: Nút bấm hủy giao dịch

## 2. Đầu ra (Outputs):
- dispense_drink: Nhả lon nước ngọt (khi nạp đủ >= 15.000đ)
- change_5k: Trả lại tiền thừa 5.000đ (khi khách nạp 20.000đ)
- [1:0] state_out: Trạng thái hiện tại của FSM

## 3. Hoạt động / Logic mong muốn:
- Máy nhận tiền tích lũy: 0đ -> 5k -> 10k -> 15k -> 20k.
- Khi đạt 15k: nhả lon nước, không thối tiền.
- Khi nạp 20k: nhả lon nước đồng thời phát xung change_5k = 1."""
        },
        {
            "id": 82,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Bộ Điều Khiển Đèn Giao Thông Ngã Tư Thông Minh (traffic_light_controller)",
            "module": "traffic_light_controller",
            "spec_text": """# Đèn Giao Thông Ngã Tư (traffic_light_controller)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp 1Hz (chu kỳ 1 giây)
- rst: Reset hệ thống tích cực cao
- pedestrian_req: Nút bấm xin qua đường của người đi bộ

## 2. Đầu ra (Outputs):
- [1:0] light_main: Đèn đường chính (00: Đỏ, 01: Vàng, 10: Xanh)
- [1:0] light_sub: Đèn đường phụ (00: Đỏ, 01: Vàng, 10: Xanh)
- ped_walk: Đèn báo người đi bộ được phép qua đường

## 3. Hoạt động / Logic mong muốn:
- Luân chuyển pha: Đường chính Xanh (30s) -> Vàng (5s) -> Đỏ.
- Đường phụ: Đỏ trong lúc đường chính Xanh/Vàng, sau đó chuyển sang Xanh (20s) -> Vàng (5s).
- An toàn tuyệt đối: Không bao giờ hai hướng cùng bật đèn Xanh."""
        },
        {
            "id": 83,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Bộ Điều Khiển Thang Máy 5 Tầng Thông Minh (elevator_5floor_controller)",
            "module": "elevator_5floor_controller",
            "spec_text": """# Bộ Điều Khiển Thang Máy 5 Tầng (elevator_5floor_controller)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset tích cực cao
- [4:0] floor_req: Tín hiệu gọi thang từ 5 tầng (bit 0: tầng 1, bit 4: tầng 5)
- door_blocked: Cảm biến phát hiện vật cản kẹt cửa

## 2. Đầu ra (Outputs):
- [2:0] current_floor: Tầng hiện tại của cabin thang máy (1 đến 5)
- motor_up: Động cơ kéo thang chạy lên
- motor_down: Động cơ hạ thang chạy xuống
- door_open: Tín hiệu mở cửa thang máy

## 3. Hoạt động / Logic mong muốn:
- Di chuyển cabin đến tầng được gọi theo khoảng cách gần nhất.
- Khi đến tầng: dừng động cơ, mở cửa cabin trong 5 giây nếu không có vật cản door_blocked."""
        },
        {
            "id": 84,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Bộ Điều Khiển Máy Giặt Tự Động 4 Giai Đoạn (washing_machine_controller)",
            "module": "washing_machine_controller",
            "spec_text": """# Máy Giặt Tự Động 4 Giai Đoạn (washing_machine_controller)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp định thời
- rst: Reset hệ thống
- start_btn: Nút bấm khởi động chu trình giặt
- water_level_full: Cảm biến nước đã nạp đầy lồng giặt
- lid_closed: Công tắc nắp máy giặt đã đóng kín

## 2. Đầu ra (Outputs):
- valve_water: Van xả nước vào lồng
- motor_wash: Động cơ quay đảo chiều chế độ Giặt/Xả
- motor_spin: Động cơ quay tốc độ cao chế độ Vắt khô
- valve_drain: Van xả nước thải ra ngoài
- [1:0] stage: Giai đoạn hiện tại (0: Cấp nước, 1: Giặt, 2: Xả sạch, 3: Vắt)

## 3. Hoạt động / Logic mong muốn:
- Tuần tự thực hiện 4 giai đoạn nếu nắp máy giặt luôn đóng kín.
- Tự động ngắt động cơ nếu mở nắp máy trong lúc đang vắt."""
        },
        {
            "id": 85,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Hệ Thống Báo Động Chống Trộm Cảm Biến PIR & Khói Gas (smart_home_alarm)",
            "module": "smart_home_alarm",
            "spec_text": """# Hệ Thống Báo Động Smart Home (smart_home_alarm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- pir_motion: Cảm biến hồng ngoại phát hiện chuyển động
- gas_smoke: Cảm biến phát hiện khói và rò rỉ khí gas
- door_sensor: Cảm biến từ cửa bị mở
- system_armed: Chế độ kích hoạt canh gác an ninh (1: Bật canh gác)

## 2. Đầu ra (Outputs):
- siren_alarm: Còi hú báo động
- sprinler_water: Vòi phun nước dập lửa (khi có khói gas)
- [1:0] alert_type: Mã cảnh báo (00: An toàn, 01: Có trộm, 10: Cháy nổ)

## 3. Hoạt động / Logic mong muốn:
- Khi có khói gas: siren_alarm = 1 và sprinler_water = 1 ngay lập tức.
- Khi system_armed = 1 mà có pir_motion hoặc door_sensor kích hoạt: bật còi siren_alarm = 1."""
        },
        {
            "id": 86,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Bộ Điều Khiển Lò Vi Sóng Đếm Ngược (microwave_timer_controller)",
            "module": "microwave_timer_controller",
            "spec_text": """# Bộ Điều Khiển Lò Vi Sóng (microwave_timer_controller)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp 1Hz
- rst: Reset hệ thống
- door_closed: Cảm biến cửa lò đã đóng kín
- add_30s: Nút cộng thêm 30 giây vào bộ đếm thời gian
- start: Nút bắt đầu hâm nóng thức ăn
- stop: Nút dừng hoặc hủy

## 2. Đầu ra (Outputs):
- magnetron_on: Đèn vi sóng phát nhiệt
- bell_done: Chuông báo ting ting khi hâm nóng hoàn tất
- [7:0] time_left: Thời gian nấu còn lại (tính bằng giây)

## 3. Hoạt động / Logic mong muốn:
- Chỉ phát nhiệt magnetron_on khi time_left > 0 và door_closed = 1.
- Mở cửa hoặc hết thời gian thì tắt ngay lập tức magnetron_on."""
        },
        {
            "id": 87,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Bộ Điều Khiển Bãi Đỗ Xe Thông Minh Smart Parking (smart_parking_lot_system)",
            "module": "smart_parking_lot_system",
            "spec_text": """# Bãi Đỗ Xe Thông Minh (smart_parking_lot_system)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- car_enter: Cảm biến có xe vào bãi
- car_exit: Cảm biến có xe rời bãi

## 2. Đầu ra (Outputs):
- [6:0] vacant_spaces: Số chỗ đỗ còn trống trong bãi (tổng dung lượng 100 chỗ)
- lot_full: Đèn báo bãi đỗ xe đã đầy (1 khi vacant_spaces == 0)
- gate_open: Tín hiệu mở cổng cho xe vào

## 3. Hoạt động / Logic mong muốn:
- Khi có xe vào: vacant_spaces giảm 1; khi có xe ra: vacant_spaces tăng 1.
- Chỉ mở cổng gate_open nếu bãi chưa đầy (lot_full == 0)."""
        },
        {
            "id": 88,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Bộ Điều Khiển Tưới Cây Tự Động Theo Độ Ẩm Đất (automatic_irrigation_controller)",
            "module": "automatic_irrigation_controller",
            "spec_text": """# Hệ Thống Tưới Cây Tự Động (automatic_irrigation_controller)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- [7:0] soil_moisture: Độ ẩm đất đo được từ cảm biến (0: Khô hạn, 100: Bão hòa nước)
- [7:0] dry_threshold: Ngưỡng khô cần kích hoạt tưới
- rain_detected: Cảm biến trời đang mưa

## 2. Đầu ra (Outputs):
- water_pump: Máy bơm nước tưới cây

## 3. Hoạt động / Logic mong muốn:
- Nếu rain_detected = 1: tắt máy bơm water_pump = 0.
- Nếu không mưa và soil_moisture < dry_threshold: bật máy bơm water_pump = 1 cho đến khi đất đủ ẩm."""
        },
        {
            "id": 89,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Hệ Thống Chấm Công Thẻ RFID Kiểm Soát Cửa (access_control_card_reader)",
            "module": "access_control_card_reader",
            "spec_text": """# Kiểm Soát Ra Vào Thẻ RFID (access_control_card_reader)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- card_present: Có thẻ RFID quẹt vào đầu đọc
- [7:0] card_id: Mã ID của thẻ

## 2. Đầu ra (Outputs):
- door_unlock: Mở khóa chốt điện tử cửa ra vào
- led_access_granted: Đèn xanh báo thẻ hợp lệ
- led_access_denied: Đèn đỏ báo thẻ không hợp lệ

## 3. Hoạt động / Logic mong muốn:
- So sánh card_id với danh sách mã nhân viên hợp lệ (ví dụ: 8'h3A, 8'h7B, 8'hA1).
- Nếu khớp: bật door_unlock và led_access_granted trong 3 giây.
- Nếu sai: chớp led_access_denied cảnh báo."""
        },
        {
            "id": 90,
            "group": "Nhóm 9: Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh",
            "name": "Hệ Thống Giám Sát Nhiệt Độ Phòng Máy Server (temperature_monitor_alarm)",
            "module": "temperature_monitor_alarm",
            "spec_text": """# Giám Sát Nhiệt Độ Phòng Server (temperature_monitor_alarm)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- [7:0] temp_celsius: Nhiệt độ hiện tại từ cảm biến số (tính theo độ C)
- [7:0] max_temp_limit: Ngưỡng nhiệt độ tối đa cho phép

## 2. Đầu ra (Outputs):
- fan_high_speed: Bật quạt làm mát công suất cực đại
- overtemp_alarm: Còi cảnh báo quá nhiệt phòng máy
- shutdown_signal: Tín hiệu hạ nguồn khẩn cấp phòng máy

## 3. Hoạt động / Logic mong muốn:
- Nếu temp_celsius >= max_temp_limit: bật fan_high_speed = 1 và overtemp_alarm = 1.
- Nếu vượt quá ngưỡng an toàn thêm 10 độ C: phát tín hiệu shutdown_signal = 1."""
        },

        # =========================================================================
        # NHÓM 10: HIỂN THỊ, TRỌNG TÀI & KHỐI TÍNH TOÁN SOC [91 - 100]
        # =========================================================================
        {
            "id": 91,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Mạch Quét Hiển Thị Đa Kênh 4 LED 7 Đoạn (mux_4digit_7seg_display)",
            "module": "mux_4digit_7seg_display",
            "spec_text": """# Quét Đa Kênh 4 LED 7 Đoạn (mux_4digit_7seg_display)

## 1. Đầu vào (Inputs):
- clk_scan: Xung nhịp quét hiển thị (khoảng 1kHz chống nhấp nháy mắt người)
- rst: Reset hệ thống
- [3:0] digit0: Giá trị số BCD hiển thị ở LED 0
- [3:0] digit1: Giá trị số BCD hiển thị ở LED 1
- [3:0] digit2: Giá trị số BCD hiển thị ở LED 2
- [3:0] digit3: Giá trị số BCD hiển thị ở LED 3

## 2. Đầu ra (Outputs):
- [3:0] an_select: Tín hiệu chọn 1 trong 4 LED Anode chung (quét lần lượt)
- [6:0] seg_data: Đoạn mã LED tương ứng của chữ số đang được chọn

## 3. Hoạt động / Logic mong muốn:
- Bộ đếm 2-bit xoay vòng liên tục để kích hoạt lần lượt an_select[0..3] và xuất mã seg_data tương ứng."""
        },
        {
            "id": 92,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Điều Khiển Quét Ma Trận LED 8x8 (led_matrix_8x8_scanner)",
            "module": "led_matrix_8x8_scanner",
            "spec_text": """# Quét Ma Trận LED 8x8 (led_matrix_8x8_scanner)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp quét ma trận
- rst: Reset hệ thống
- [63:0] frame_buffer: Khung hình ảnh nhị phân 64-bit hiển thị lên 64 điểm LED

## 2. Đầu ra (Outputs):
- [7:0] row_active: Kích hoạt lần lượt 8 hàng
- [7:0] col_data: Dữ liệu sáng/tối của 8 cột tương ứng

## 3. Hoạt động / Logic mong muốn:
- Quét lần lượt từng hàng row_active và nạp 8-bit dữ liệu cột tương ứng từ frame_buffer."""
        },
        {
            "id": 93,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Trọng Tài Bus Phân Xử Ưu Tiên Cố Định (fixed_priority_bus_arbiter)",
            "module": "fixed_priority_bus_arbiter",
            "spec_text": """# Trọng Tài Bus Ưu Tiên Cố Định (fixed_priority_bus_arbiter)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- [3:0] bus_req: 4 ngõ yêu cầu truy cập tuyến Bus từ 4 Master (Req 3 ưu tiên cao nhất, Req 0 thấp nhất)

## 2. Đầu ra (Outputs):
- [3:0] bus_grant: Tín hiệu cấp quyền chiếm tuyến Bus (chỉ có duy nhất 1 Master được cấp tại một thời điểm)

## 3. Hoạt động / Logic mong muốn:
- Luôn ưu tiên cấp bus cho Master có chỉ số cao nhất đang yêu cầu; nếu không có yêu cầu nào thì bus_grant = 0."""
        },
        {
            "id": 94,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Trọng Tài Phân Xử Công Bằng Round-Robin (round_robin_arbiter)",
            "module": "round_robin_arbiter",
            "spec_text": """# Trọng Tài Round-Robin Công Bằng (round_robin_arbiter)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- [3:0] req: Tuyến yêu cầu từ 4 Master

## 2. Đầu ra (Outputs):
- [3:0] grant: Quyền truy cập được cấp phát luân phiên xoay vòng

## 3. Hoạt động / Logic mong muốn:
- Phân xử theo thuật toán Round-Robin: sau khi Master N được phục vụ, lượt ưu tiên kế tiếp chuyển sang Master (N+1)%4."""
        },
        {
            "id": 95,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Mạch Tạo Xung Đồng Hồ Không Trùng Pha Non-overlapping Clock (non_overlapping_clock_gen)",
            "module": "non_overlapping_clock_gen",
            "spec_text": """# Bộ Tạo Xung Không Trùng Pha (non_overlapping_clock_gen)

## 1. Đầu vào (Inputs):
- clk_master: Xung clock gốc đầu vào
- rst: Reset hệ thống

## 2. Đầu ra (Outputs):
- phi1: Xung clock pha 1
- phi2: Xung clock pha 2

## 3. Hoạt động / Logic mong muốn:
- Tạo 2 xung clock phi1 và phi2 cùng tần số nhưng lệch pha, có khoảng thời gian chết (Dead-time) cách ly để chống trùng dẫn."""
        },
        {
            "id": 96,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Giải Mã Địa Chỉ Bộ Nhớ Memory Address Decoder 64KB (memory_address_decoder)",
            "module": "memory_address_decoder",
            "spec_text": """# Giải Mã Địa Chỉ Bộ Nhớ 64KB (memory_address_decoder)

## 1. Đầu vào (Inputs):
- [15:0] addr: Tuyến địa chỉ 16-bit (không gian 64KB)
- mem_en: Cho phép truy cập bộ nhớ

## 2. Đầu ra (Outputs):
- cs_ram: Chọn chip SRAM (vùng 0x0000 - 0x7FFF: 32KB)
- cs_rom: Chọn chip ROM (vùng 0x8000 - 0xBFFF: 16KB)
- cs_io: Chọn vùng ngoại vi I/O (vùng 0xC000 - 0xFFFF: 16KB)

## 3. Hoạt động / Logic mong muốn:
- Phân giải 2 bit địa chỉ cao addr[15:14] để kích hoạt chính xác tín hiệu chọn chip tương ứng."""
        },
        {
            "id": 97,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Đếm Số Bit 1 Population Count 8-bit (popcount_8bit)",
            "module": "popcount_8bit",
            "spec_text": """# Bộ Đếm Số Bit 1 PopCount (popcount_8bit)

## 1. Đầu vào (Inputs):
- [7:0] data_in: Từ dữ liệu 8-bit ngõ vào

## 2. Đầu ra (Outputs):
- [3:0] bit_count: Tổng số bit mang giá trị 1 có trong data_in (giá trị từ 0 đến 8)

## 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp cộng dồn số lượng bit 1: bit_count = data_in[0] + data_in[1] + ... + data_in[7]."""
        },
        {
            "id": 98,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Mạch Tính Toán Checksum 8-bit Kiểm Tra Dữ Liệu (checksum_calculator_8bit)",
            "module": "checksum_calculator_8bit",
            "spec_text": """# Mạch Tính Toán Checksum 8-bit (checksum_calculator_8bit)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Reset hệ thống
- start_calc: Bắt đầu tính checksum cho chuỗi dữ liệu mới
- data_valid: Byte dữ liệu hiện tại hợp lệ
- [7:0] data_byte: Byte dữ liệu thành phần

## 2. Đầu ra (Outputs):
- [7:0] checksum_val: Giá trị bù 2 của tổng các byte dữ liệu đã tích lũy

## 3. Hoạt động / Logic mong muốn:
- Cộng dồn tất cả các byte lại thành tổng sum; checksum_val = (~sum) + 1."""
        },
        {
            "id": 99,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Chuyển Đổi Nhị Phân Sang BCD Thuật Toán Double Dabble (bin_to_bcd_double_dabble)",
            "module": "bin_to_bcd_double_dabble",
            "spec_text": """# Bộ Chuyển Đổi Nhị Phân Sang BCD (bin_to_bcd_double_dabble)

## 1. Đầu vào (Inputs):
- [7:0] bin_val: Số nhị phân 8-bit không dấu (0 đến 255)

## 2. Đầu ra (Outputs):
- [3:0] bcd_hundreds: Hàng trăm BCD (0-2)
- [3:0] bcd_tens: Hàng chục BCD (0-9)
- [3:0] bcd_ones: Hàng đơn vị BCD (0-9)

## 3. Hoạt động / Logic mong muốn:
- Thực thi thuật toán Shift-Add-3 (Double Dabble) chuyển đổi nhị phân sang 3 chữ số BCD."""
        },
        {
            "id": 100,
            "group": "Nhóm 10: Hiển Thị, Trọng Tài & Tính Toán",
            "name": "Bộ Tạo Tín Hiệu Đồng Bộ Khung Hình Video VGA (vga_sync_generator)",
            "module": "vga_sync_generator",
            "spec_text": """# Bộ Tạo Xung Đồng Bộ VGA 640x480 (vga_sync_generator)

## 1. Đầu vào (Inputs):
- clk_25m: Xung nhịp đồng hồ điểm ảnh 25.175MHz (Pixel Clock)
- rst: Reset hệ thống tích cực cao

## 2. Đầu ra (Outputs):
- hsync: Tín hiệu đồng bộ dòng ngang Horizontal Sync (active-low)
- vsync: Tín hiệu đồng bộ khung dọc Vertical Sync (active-low)
- video_on: Báo điểm ảnh nằm trong vùng hiển thị tích cực (640 cột x 480 dòng)
- [9:0] pixel_x: Tọa độ điểm ảnh theo chiều ngang (0 đến 639)
- [9:0] pixel_y: Tọa độ điểm ảnh theo chiều dọc (0 đến 479)

## 3. Hoạt động / Logic mong muốn:
- Quét dòng ngang 800 chu kỳ (Sync 96, Back Porch 48, Active 640, Front Porch 16).
- Quét dòng dọc 525 dòng (Sync 2, Back Porch 33, Active 480, Front Porch 10)."""
        }
    ]
    return prompts


def tao_tai_lieu_pdf(DuongDanPdfXuat=None, output_pdf_path=None):
    """Bien tap va tao tai lieu PDF chua 100 de bai dac ta mach."""
    DuongDanXuat = output_pdf_path if output_pdf_path is not None else DuongDanPdfXuat
    os.makedirs(os.path.dirname(DuongDanXuat), exist_ok=True)

    TaiLieu = SimpleDocTemplate(
        DuongDanXuat,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm
    )

    TapKieu = getSampleStyleSheet()

    # Dinh nghia cac phong cach van ban
    KieuTieuDeBia = ParagraphStyle(
        "CoverTitle",
        fontName=PHONG_CHU_DAM,
        fontSize=24,
        leading=30,
        alignment=1,
        textColor=colors.HexColor("#0F2942")
    )
    KieuPhuBia = ParagraphStyle(
        "CoverSub",
        fontName=PHONG_CHU_THUONG,
        fontSize=12,
        leading=18,
        alignment=1,
        textColor=colors.HexColor("#334E68")
    )
    KieuTieuDeNhom = ParagraphStyle(
        "GroupHeader",
        fontName=PHONG_CHU_DAM,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0B69A3"),
        spaceBefore=14,
        spaceAfter=8
    )
    KieuTieuDePrompt = ParagraphStyle(
        "PromptTitle",
        fontName=PHONG_CHU_DAM,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1A202C")
    )
    KieuKhungMa = ParagraphStyle(
        "CodeBox",
        fontName=PHONG_CHU_THUONG,
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1F2937")
    )
    KieuGhiChu = ParagraphStyle(
        "CopyNote",
        fontName=PHONG_CHU_NGHIENG,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#6B7280")
    )
    KieuNoiDung = ParagraphStyle(
        "Body",
        fontName=PHONG_CHU_THUONG,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#2D3748")
    )

    DanhSachNoiDung = []

    # =========================================================================
    # TRANG BIA VA HUONG DAN
    # =========================================================================
    DanhSachNoiDung.append(Spacer(1, 1.5 * cm))
    DanhSachNoiDung.append(Paragraph("KHOA ĐIỆN - ĐIỆN TỬ | ĐỒ ÁN 3", KieuPhuBia))
    DanhSachNoiDung.append(Spacer(1, 0.4 * cm))
    DanhSachNoiDung.append(Paragraph("TUYỂN TẬP 100 ĐỀ BÀI ĐẶC TẢ VI MẠCH SỐ", KieuTieuDeBia))
    DanhSachNoiDung.append(Spacer(1, 0.3 * cm))
    DanhSachNoiDung.append(Paragraph("Dành Cho Hệ Thống Tác Tử Tự Động Hóa Spec2RTL & Prompt2Silicon", KieuPhuBia))
    DanhSachNoiDung.append(Spacer(1, 0.5 * cm))
    DanhSachNoiDung.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B69A3"), spaceBefore=5, spaceAfter=15))

    LoiGioiThieu1 = (
        "<b>Mục đích tài liệu:</b> Tài liệu này cung cấp <b>100 đề bài đặc tả phần cứng chuẩn hóa</b> "
        "được phân loại theo 10 nhóm chức năng vi mạch số kinh điển từ cơ bản đến nâng cao. "
        "Toàn bộ đề bài được trình bày dưới dạng <b>danh sách liệt kê tuần tự (từ Bài 01 đến Bài 100)</b>, "
        "mỗi đề bài là một khối văn bản độc lập chứa đầy đủ 3 thành phần kỹ thuật: "
        "<b>Tên Mạch</b>, <b>1. Đầu vào (Inputs)</b>, <b>2. Đầu ra (Outputs)</b> và <b>3. Hoạt động / Logic mong muốn</b>."
    )
    DanhSachNoiDung.append(Paragraph(LoiGioiThieu1, KieuNoiDung))
    DanhSachNoiDung.append(Spacer(1, 0.4 * cm))

    LoiGioiThieu2 = (
        "<b>Hướng dẫn sử dụng và kiểm tra nhanh:</b><br/>"
        "1. <b>Sao chép (Copy):</b> Chọn và copy toàn bộ nội dung trong khung viền của bất kỳ Prompt nào bên dưới.<br/>"
        "2. <b>Dán vào file đặc tả (Paste):</b> Tạo file văn bản trong thư mục <code>specs/</code> (ví dụ: <code>specs/test_mach.txt</code>) và dán nội dung vào.<br/>"
        "3. <b>Thực thi hệ thống:</b> Mở terminal và chạy lệnh:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>python agent/run_spec2rtl.py specs/test_mach.txt</code><br/>"
        "4. <b>Kiểm tra kết quả:</b> Hệ thống sẽ tự động tổng hợp mã Verilog RTL trong <code>src/</code>, "
        "chạy mô phỏng ModelSim trong <code>sim/</code>, và tự động vẽ sơ đồ nguyên lý BDF cũng như dạng sóng VWF trong <code>quartus/</code>."
    )
    DanhSachNoiDung.append(Paragraph(LoiGioiThieu2, KieuNoiDung))
    DanhSachNoiDung.append(Spacer(1, 0.5 * cm))

    DuLieuBang = [
        ["Nhóm", "Chủ Đề Chức Năng", "Số Lượng", "Phạm Vi Bài"],
        ["Nhóm 1", "Mạch Đếm & Định Thời (Counters & Timers)", "10 bài", "Bài 01 - Bài 10"],
        ["Nhóm 2", "Mạch Số Học & ALU (Arithmetic & ALU Units)", "10 bài", "Bài 11 - Bài 20"],
        ["Nhóm 3", "Mạch Thanh Ghi & Bộ Đệm Dữ Liệu (Registers & Buffers)", "10 bài", "Bài 21 - Bài 30"],
        ["Nhóm 4", "Mạch MUX, DEMUX, Mã Hóa & Giải Mã (Codecs)", "10 bài", "Bài 31 - Bài 40"],
        ["Nhóm 5", "Máy Trạng Thái Hữu Hạn FSM & Bộ Dò Chuỗi", "10 bài", "Bài 41 - Bài 50"],
        ["Nhóm 6", "Giao Tiếp & Ngoại Vi Công Nghiệp (UART, SPI, CRC)", "10 bài", "Bài 51 - Bài 60"],
        ["Nhóm 7", "Điều Chế Xung PWM & Điều Khiển Động Cơ", "10 bài", "Bài 61 - Bài 70"],
        ["Nhóm 8", "Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường", "10 bài", "Bài 71 - Bài 80"],
        ["Nhóm 9", "Hệ Thống Tự Động Hóa & Thiết Bị Thông Minh (IoT)", "10 bài", "Bài 81 - Bài 90"],
        ["Nhóm 10", "Mạch Hiển Thị, Trọng Tài Bus & Phân Hệ SoC", "10 bài", "Bài 91 - Bài 100"],
    ]
    BangTongHop = Table(DuLieuBang, colWidths=[1.8 * cm, 9.5 * cm, 2.2 * cm, 3.5 * cm])
    BangTongHop.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B69A3")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), PHONG_CHU_THUONG),
        ("FONTNAME", (0, 0), (-1, 0), PHONG_CHU_DAM),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (2, 0), (3, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5DD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    DanhSachNoiDung.append(BangTongHop)
    DanhSachNoiDung.append(PageBreak())

    # =========================================================================
    # XUAT DANH SACH 100 PROMPT
    # =========================================================================
    DanhSachPrompt = get_all_100_prompts()
    NhomHienTai = ""

    for MucPrompt in DanhSachPrompt:
        KhoiPhanTu = []

        if MucPrompt["group"] != NhomHienTai:
            NhomHienTai = MucPrompt["group"]
            KhoiPhanTu.append(Spacer(1, 0.4 * cm))
            KhoiPhanTu.append(Paragraph(NhomHienTai.upper(), KieuTieuDeNhom))
            KhoiPhanTu.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceBefore=2, spaceAfter=8))

        TieuDeMuc = f"<b>[PROMPT #{MucPrompt['id']:02d}] {MucPrompt['name']}</b>"
        KhoiPhanTu.append(Paragraph(TieuDeMuc, KieuTieuDePrompt))
        KhoiPhanTu.append(Spacer(1, 0.15 * cm))

        DanhSachDongSpec = MucPrompt["spec_text"].splitlines()
        DongDinhDang = []
        for Dong in DanhSachDongSpec:
            DongSach = Dong.strip()
            if not DongSach:
                DongDinhDang.append("")
                continue
            if DongSach.startswith("# "):
                DongDinhDang.append(f"<b>{DongSach}</b>")
            elif DongSach.startswith("## "):
                DongDinhDang.append(f"<b>{DongSach}</b>")
            elif DongSach.startswith("- "):
                DongDinhDang.append(f"&nbsp;&nbsp;• {DongSach[2:]}")
            else:
                DongDinhDang.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{DongSach}")

        NoiDungThe = "<br/>".join(DongDinhDang)
        TheDoanVan = Paragraph(NoiDungThe, KieuKhungMa)

        BangKhungThe = Table([[TheDoanVan]], colWidths=[17.0 * cm])
        BangKhungThe.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#D1D5DB")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        KhoiPhanTu.append(BangKhungThe)
        KhoiPhanTu.append(Spacer(1, 0.1 * cm))
        KhoiPhanTu.append(Paragraph(f"<i>👉 Sao chép khối nội dung trên và dán vào specs/*.txt để chạy thử nghiệm với Spec2RTL.</i>", KieuGhiChu))
        KhoiPhanTu.append(Spacer(1, 0.35 * cm))

        DanhSachNoiDung.append(KeepTogether(KhoiPhanTu))

    print(f"[PDF Builder]: Dang bien tap tai lieu voi {len(DanhSachPrompt)} de bai...")
    TaiLieu.build(DanhSachNoiDung, canvasmaker=NumberedCanvas)
    print(f"[PDF Builder]: Da xuat thanh cong PDF -> {DuongDanXuat}")

build_pdf = tao_tai_lieu_pdf

if __name__ == "__main__":
    ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    TepPdfXuat = os.path.join(ThuMucGoc, "docs", "100_Prompt_Thiet_Ke_Mach.pdf")
    tao_tai_lieu_pdf(TepPdfXuat)
