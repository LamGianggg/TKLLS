# 100 PROMPT THIẾT KẾ MẠCH SỐ SPEC2RTL & PROMPT2SILICON

> **Tài liệu chuẩn hóa**: Bộ 100 đề bài đặc tả kỹ thuật vi mạch hoàn chỉnh từ cơ bản đến phức tạp (NVIDIA Spec2RTL & ISCAS 2026 standard).
> **Cấu trúc chuẩn**: Mỗi đề bài gồm 3 phần độc lập: Tên Mạch -> 1. Đầu vào (Inputs) -> 2. Đầu ra (Outputs) -> 3. Hoạt động / Logic mong muốn.

---

## MỤC LỤC 10 NHÓM CHỦ ĐỀ THIẾT KẾ

- **Nhóm 1: Mạch Đếm & Định Thời (Counters & Timers)** (Bài 01 - 10)
- **Nhóm 2: Mạch Xử Lý Số Học & ALU (Arithmetic & ALU Units)** (Bài 11 - 20)
- **Nhóm 3: Mạch Thanh Ghi & Bộ Đệm Dữ Liệu (Registers & Buffers)** (Bài 21 - 30)
- **Nhóm 4: Mạch Ghép Kênh, Phân Kênh & Bộ Mã Hóa / Giải Mã (MUX, DEMUX & Codecs)** (Bài 31 - 40)
- **Nhóm 5: Máy Trạng Thái Hữu Hạn FSM & Bộ Dò Chuỗi (FSM & Sequence Detectors)** (Bài 41 - 50)
- **Nhóm 6: Mạch Giao Tiếp & Ngoại Vi Công Nghiệp (Communication & Protocols)** (Bài 51 - 60)
- **Nhóm 7: Mạch Điều Chế Xung PWM & Điều Khiển Động Cơ (PWM & Motor Control)** (Bài 61 - 70)
- **Nhóm 8: Mạch Khử Nhiễu, Xử Lý Tín Hiệu & Đo Lường (Signal Conditioning & Measurement)** (Bài 71 - 80)
- **Nhóm 9: Hệ Thống Tự Động Hóa, An Ninh & Nhà Thông Minh (Smart Systems & IoT)** (Bài 81 - 90)
- **Nhóm 10: Mạch Hiển Thị, Đồ Họa & Phân Hệ Vi Xử Lý SoC (Displays & SoC Units)** (Bài 91 - 100)

---


# NHÓM 1: MẠCH ĐẾM & ĐỊNH THỜI (COUNTERS & TIMERS)

## Bài 01: Bộ Đếm Nhị Phân 4-bit Đếm Lên / Xuống (4-bit Up/Down Binary Counter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset đồng bộ tích cực cao
- `up_down`: 1: Đếm lên 0->15, 0: Đếm xuống 15->0
- `enable`: 1: Cho phép đếm, 0: Tạm dừng giữ nguyên giá trị

### 2. Đầu ra (Outputs):
- `[3:0] count`: Giá trị số đếm nhị phân 4-bit
- `tc`: Cờ báo tràn Terminal Count (1 khi đếm lên đạt 15 hoặc đếm xuống đạt 0)

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: count = 4'b0000, tc = 0.
- Khi enable = 1: Mỗi sườn dương clk nếu up_down = 1 thì count tăng 1 đơn vị; nếu up_down = 0 thì count giảm 1 đơn vị.
- tc = 1 khi (up_down == 1 && count == 15) hoặc (up_down == 0 && count == 0).

---

## Bài 02: Đồng Hồ Bấm Giờ 0-9 Giây Kèm Giải Mã LED 7 Đoạn (Stopwatch)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1Hz (1 giây 1 xung)
- `rst`: Reset về 0 tích cực cao
- `start_stop`: Nút bấm chạy/tạm dừng (1: Đếm, 0: Tạm dừng)

### 2. Đầu ra (Outputs):
- `[3:0] count`: Giá trị số đếm nhị phân 0-9
- `[6:0] seg`: Mã LED 7 đoạn Anode chung (active-low: a, b, c, d, e, f, g)

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: count = 0, seg = 7'b1000000 (số 0).
- Khi start_stop = 1: Mỗi xung clk count tăng 1 từ 0 lên 9; khi đạt 9 chu kỳ sau quay về 0.
- seg giải mã trực tiếp từ count (0: 7'b1000000, 1: 7'b1111001, ..., 9: 7'b0010000).

---

## Bài 03: Bộ Đếm BCD 00 Đến 59 Đếm Giây/Phút (BCD 00-59 Counter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1Hz
- `rst`: Reset tích cực cao
- `en`: Cho phép đếm

### 2. Đầu ra (Outputs):
- `[3:0] sec_ones`: Hàng đơn vị BCD (0-9)
- `[3:0] sec_tens`: Hàng chục BCD (0-5)
- `rollover`: Xung tràn 1 chu kỳ khi đạt 59 quay về 00

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: sec_ones = 0, sec_tens = 0, rollover = 0.
- Khi en = 1: sec_ones đếm 0->9 rồi quay về 0 và tăng sec_tens 1 đơn vị.
- Khi đạt 59, chu kỳ kế tiếp về 00 và phát xung rollover = 1.

---

## Bài 04: Bộ Đếm Mã Gray 4-bit Không Nhiễu Trạng Thái (4-bit Gray Counter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset bất đồng bộ tích cực cao
- `enable`: Cho phép đếm

### 2. Đầu ra (Outputs):
- `[3:0] gray_out`: Mã Gray 4-bit đầu ra (chỉ 1 bit đổi trạng thái giữa 2 chu kỳ liên tiếp)

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: gray_out = 4'b0000.
- Khi enable = 1: Bộ đếm nhị phân nội bộ tăng 1 mỗi chu kỳ clk.
- gray_out chuyển đổi theo công thức: gray_out = bin_cnt ^ (bin_cnt >> 1).

---

## Bài 05: Bộ Đếm Vòng 8-bit Di Chuyển Điểm Sáng LED (8-bit Ring Counter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp quét
- `rst`: Reset tích cực cao

### 2. Đầu ra (Outputs):
- `[7:0] q`: Đầu ra One-Hot 8-bit

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: q = 8'b00000001.
- Tại mỗi sườn dương clk: q <= {q[6:0], q[7]} (dịch trái xoay vòng liên tục).

---

## Bài 06: Bộ Đếm Johnson 4-bit Sinh 8 Trạng Thái (4-bit Johnson Counter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp đồng hồ
- `rst`: Reset tích cực cao

### 2. Đầu ra (Outputs):
- `[3:0] q`: Trạng thái đếm Johnson 4-bit

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: q = 4'b0000.
- Tại mỗi sườn clk: q <= {~q[0], q[3:1]} tạo chuỗi 8 trạng thái không trùng lặp.

---

## Bài 07: Bộ Chia Tần Số Xung Nhịp Tham Số Hóa (Configurable Clock Divider)

### 1. Đầu vào (Inputs):
- `clk_in`: Xung nhịp gốc 50MHz
- `rst`: Reset tích cực cao
- `[15:0] div_factor`: Hệ số chia tần số N (N >= 2)

### 2. Đầu ra (Outputs):
- `clk_out`: Xung nhịp đầu ra với chu kỳ bằng N lần clk_in, duty cycle 50%

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm nội bộ tăng mỗi chu kỳ clk_in.
- Khi đếm tới (div_factor / 2 - 1), clk_out đảo trạng thái và biến đếm reset về 0.

---

## Bài 08: Bộ Định Thời Watchdog An Toàn Vi Xử Lý (Watchdog Timer)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset phần cứng ban đầu
- `kick_wd`: Xung làm mới (kick) từ vi xử lý

### 2. Đầu ra (Outputs):
- `sys_reset`: Xung cưỡng chế reset hệ thống khi CPU bị treo

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm tăng liên tục theo clk.
- Nếu kick_wd = 1, bộ đếm về 0.
- Nếu bộ đếm chạm ngưỡng tối đa mà không được kick, sys_reset = 1 trong 1 chu kỳ để khởi động lại hệ thống.

---

## Bài 09: Bộ Tạo Độ Trễ Đếm Chu Kỳ Xung (Programmable Delay Generator)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset tích cực cao
- `trigger`: Xung kích hoạt bắt đầu tạo trễ
- `[7:0] delay_cycles`: Số chu kỳ xung cần trễ

### 2. Đầu ra (Outputs):
- `busy`: Báo đang trong thời gian tạo trễ
- `delayed_pulse`: Xung đầu ra xuất hiện sau đúng delay_cycles chu kỳ

### 3. Hoạt động / Logic mong muốn:
- Khi trigger = 1 và busy = 0: busy = 1, nạp delay_cycles vào bộ đếm lùi.
- Bộ đếm giảm 1 mỗi chu kỳ clk; khi về 0, phát delayed_pulse = 1 và hạ busy = 0.

---

## Bài 10: Bộ Đo Tần Số Tín Hiệu Đầu Vào (Pulse Frequency Counter)

### 1. Đầu vào (Inputs):
- `clk_ref`: Xung chuẩn 1MHz
- `rst`: Reset tích cực cao
- `signal_in`: Tín hiệu xung cần đo tần số
- `gate_1s`: Cửa sổ thời gian đo 1 giây

### 2. Đầu ra (Outputs):
- `[19:0] freq_hz`: Giá trị tần số đo được (Hz)
- `data_ready`: Cờ báo dữ liệu đo đã sẵn sàng

### 3. Hoạt động / Logic mong muốn:
- Khi gate_1s = 1: Đếm số sườn lên của signal_in.
- Khi gate_1s chuyển từ 1 về 0: Chốt giá trị đếm vào freq_hz và bật data_ready = 1.

---


# NHÓM 2: MẠCH XỬ LÝ SỐ HỌC & ALU (ARITHMETIC & ALU UNITS)

## Bài 11: Bộ Số Học & Logic ALU 8-bit Đa Chức Năng (8-bit Multi-Function ALU)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset tích cực cao
- `[7:0] a`: Toán hạng thứ nhất 8-bit
- `[7:0] b`: Toán hạng thứ hai 8-bit
- `[2:0] alu_op`: Mã lệnh chọn phép toán (0: ADD, 1: SUB, 2: AND, 3: OR, 4: XOR, 5: NOT A, 6: Dịch trái A, 7: Dịch phải A)

### 2. Đầu ra (Outputs):
- `[7:0] alu_out`: Kết quả tính toán 8-bit
- `zero`: Cờ báo kết quả bằng 0
- `carry_out`: Cờ nhớ phép cộng/mượn phép trừ

### 3. Hoạt động / Logic mong muốn:
- Tại sườn lên clk: Thực thi phép toán theo alu_op trên hai toán hạng a và b.
- zero = 1 khi alu_out == 8'b00000000.
- carry_out lưu bit nhớ thứ 9 của phép cộng hoặc bit mượn của phép trừ.

---

## Bài 12: Bộ Cộng/Trừ Bù 2 8-bit Kèm Cờ Nhớ & Tràn (8-bit 2's Complement Adder/Subtractor)

### 1. Đầu vào (Inputs):
- `[7:0] a`: Số hạng A 8-bit
- `[7:0] b`: Số hạng B 8-bit
- `sub_mode`: 0: Phép cộng (A + B), 1: Phép trừ (A - B)

### 2. Đầu ra (Outputs):
- `[7:0] result`: Kết quả 8-bit
- `c_out`: Cờ nhớ số học
- `overflow`: Cờ báo tràn số có dấu (Signed Overflow)

### 3. Hoạt động / Logic mong muốn:
- Thực hiện cộng hoặc trừ theo phương pháp bù 2.
- overflow = 1 khi hai số cùng dấu cộng lại sinh kết quả trái dấu, hoặc số dương trừ số âm ra số âm.

---

## Bài 13: Bộ Nhân Nhị Phân 4x4 bit Song Song Mảng Cổng (4x4 Parallel Array Multiplier)

### 1. Đầu vào (Inputs):
- `[3:0] a`: Số nhân 4-bit
- `[3:0] b`: Số bị nhân 4-bit

### 2. Đầu ra (Outputs):
- `[7:0] product`: Tích số nhị phân 8-bit

### 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp tính toán tích hai số không dấu 4-bit thông qua mảng cổng AND và các bộ cộng Full Adder.
- product = a * b, không có độ trễ chu kỳ clock.

---

## Bài 14: Bộ Nhân Dồn Tích Lũy MAC 8-bit Cho AI Core (8-bit Multiply-Accumulate MAC Unit)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp tính toán
- `rst`: Reset thanh ghi tích lũy về 0
- `clr_acc`: Xóa giá trị tích lũy
- `en`: Cho phép tích lũy
- `[3:0] weight`: Trọng số W (4-bit)
- `[3:0] feature`: Đặc trưng đầu vào X (4-bit)

### 2. Đầu ra (Outputs):
- `[15:0] acc_out`: Giá trị tích lũy sau MAC (Acc = Acc + W * X)

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1 hoặc clr_acc = 1: acc_out <= 0.
- Khi en = 1: acc_out <= acc_out + (weight * feature) tại mỗi chu kỳ clk.

---

## Bài 15: Bộ So Sánh Độ Lớn 8-bit (8-bit Magnitude Comparator)

### 1. Đầu vào (Inputs):
- `[7:0] a`: Số nhị phân A 8-bit
- `[7:0] b`: Số nhị phân B 8-bit

### 2. Đầu ra (Outputs):
- `a_gt_b`: Mức 1 khi A > B
- `a_eq_b`: Mức 1 khi A == B
- `a_lt_b`: Mức 1 khi A < B

### 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp so sánh hai giá trị nhị phân không dấu.
- Chỉ duy nhất một trong ba đầu ra mang giá trị 1 tại bất kỳ thời điểm nào.

---

## Bài 16: Bộ Dịch Thùng 8-bit (8-bit Barrel Shifter)

### 1. Đầu vào (Inputs):
- `[7:0] data_in`: Dữ liệu 8-bit đầu vào
- `[2:0] shift_amt`: Số bit cần dịch (0 đến 7)
- `shift_dir`: 0: Dịch trái, 1: Dịch phải
- `arith_mode`: 0: Dịch logic chèn 0, 1: Dịch số học giữ bit dấu

### 2. Đầu ra (Outputs):
- `[7:0] data_out`: Dữ liệu sau khi dịch trong đúng 1 chu kỳ tổ hợp

### 3. Hoạt động / Logic mong muốn:
- Dịch chuyển data_in theo hướng shift_dir với khoảng cách shift_amt.
- Nếu arith_mode = 1 và shift_dir = 1 thì chèn bit dấu data_in[7] vào phía bên trái.

---

## Bài 17: Bộ Tính Giá Trị Tuyệt Đối & Đổi Dấu Bù 2 (Absolute Value & Negation Unit)

### 1. Đầu vào (Inputs):
- `[7:0] val_in`: Số nguyên có dấu 8-bit bù 2
- `mode_neg`: 1: Đổi dấu (-val_in), 0: Lấy giá trị tuyệt đối (|val_in|)

### 2. Đầu ra (Outputs):
- `[7:0] val_out`: Kết quả đầu ra 8-bit

### 3. Hoạt động / Logic mong muốn:
- Nếu mode_neg = 1: val_out = -val_in = ~val_in + 1.
- Nếu mode_neg = 0: nếu val_in < 0 thì val_out = -val_in, ngược lại val_out = val_in.

---

## Bài 18: Bộ Tạo & Kiểm Tra Mã Chẵn Lẻ Parity 16-bit (16-bit Parity Generator & Checker)

### 1. Đầu vào (Inputs):
- `[15:0] data_in`: Dữ liệu 16-bit
- `even_odd_n`: 1: Chế độ chẵn (Even), 0: Chế độ lẻ (Odd)

### 2. Đầu ra (Outputs):
- `parity_bit`: Bit kiểm tra Parity sinh ra
- `parity_error`: Cờ báo dữ liệu có lỗi khi kiểm tra

### 3. Hoạt động / Logic mong muốn:
- parity_bit tính bằng XOR toàn bộ 16 bit của data_in (hiệu chỉnh theo even_odd_n).
- parity_error = 1 nếu số lượng bit 1 không thỏa mãn quy tắc chẵn/lẻ đã chọn.

---

## Bài 19: Bộ Tính Mã Dư Thừa Tuần Hoàn CRC-8 (CRC-8 Checksum Generator)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp tính toán
- `rst`: Reset thanh ghi CRC về 8'h00
- `data_valid`: 1: Dữ liệu đầu vào hợp lệ
- `[7:0] data_byte`: Byte dữ liệu cần tính CRC

### 2. Đầu ra (Outputs):
- `[7:0] crc_out`: Mã CRC-8 tích lũy theo đa thức x^8 + x^2 + x + 1 (0x07)
- `crc_ready`: Báo mã CRC sẵn sàng

### 3. Hoạt động / Logic mong muốn:
- Khi data_valid = 1: Thực hiện dịch từng bit và XOR với đa thức sinh để cập nhật crc_out.
- crc_ready = 1 sau khi hoàn thành 8 chu kỳ dịch bit.

---

## Bài 20: Bộ Kích Hoạt Phi Tuyến ReLU Cho Mạng Nơ-ron (Neural Network ReLU Unit)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp đồng bộ
- `rst`: Reset tích cực cao
- `[7:0] x_in`: Dữ liệu đầu vào 8-bit số bù 2 (-128 đến +127)

### 2. Đầu ra (Outputs):
- `[7:0] y_out`: Đầu ra phi tuyến: y = max(0, x)

### 3. Hoạt động / Logic mong muốn:
- Tại mỗi sườn clk: Nếu x_in[7] = 1 (số âm) thì y_out = 8'b00000000; nếu x_in[7] = 0 (số dương) thì y_out = x_in.

---


# NHÓM 3: MẠCH THANH GHI & BỘ ĐỆM DỮ LIỆU (REGISTERS & BUFFERS)

## Bài 21: Thanh Ghi Dịch Vạn Năng 8-bit (8-bit Universal Shift Register)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset tích cực cao
- `[1:0] mode`: 00: Giữ nguyên, 01: Dịch phải, 10: Dịch trái, 11: Nạp song song
- `s_in_left`: Dữ liệu nối tiếp dịch từ trái vào
- `s_in_right`: Dữ liệu nối tiếp dịch từ phải vào
- `[7:0] p_in`: Dữ liệu song song nạp vào

### 2. Đầu ra (Outputs):
- `[7:0] q`: Đầu ra song song 8-bit

### 3. Hoạt động / Logic mong muốn:
- Tại sườn clk: mode=00: q giữ nguyên; mode=01: q <= {s_in_left, q[7:1]}; mode=10: q <= {q[6:0], s_in_right}; mode=11: q <= p_in.

---

## Bài 22: Bộ Đệm Hàng Đợi FIFO Đồng Bộ 16x8 (16x8 Synchronous FIFO Buffer)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp đồng bộ
- `rst`: Reset rỗng FIFO
- `wr_en`: Lệnh ghi dữ liệu
- `rd_en`: Lệnh đọc dữ liệu
- `[7:0] data_in`: Dữ liệu ghi vào

### 2. Đầu ra (Outputs):
- `[7:0] data_out`: Dữ liệu đọc ra
- `full`: Cờ báo bộ đệm đầy (16 phần tử)
- `empty`: Cờ báo bộ đệm rỗng

### 3. Hoạt động / Logic mong muốn:
- Quản lý con trỏ ghi wr_ptr và con trỏ đọc rd_ptr vòng tròn 16 vị trí.
- Ghi khi wr_en=1 && !full; đọc khi rd_en=1 && !empty.
- empty = 1 khi wr_ptr == rd_ptr; full = 1 khi con trỏ ghi đuổi kịp con trỏ đọc.

---

## Bài 23: Bộ Nhớ RAM Đơn Cổng 16x8 Đồng Bộ (16x8 Single-Port RAM)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `we`: Ghi/Đọc (1: Ghi, 0: Đọc)
- `[3:0] addr`: Địa chỉ ô nhớ 4-bit (0 đến 15)
- `[7:0] din`: Dữ liệu ghi vào

### 2. Đầu ra (Outputs):
- `[7:0] dout`: Dữ liệu đọc ra

### 3. Hoạt động / Logic mong muốn:
- Khi we = 1: Ghi din vào mem[addr] tại sườn dương clk.
- Khi we = 0: dout xuất dữ liệu từ mem[addr].

---

## Bài 24: Bộ Nhớ RAM Kép Cổng Dual-Port 32x8 (32x8 Dual-Port RAM)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp chung
- `we_a`: Cho phép ghi cổng A
- `[4:0] addr_a`: Địa chỉ cổng A
- `[7:0] din_a`: Dữ liệu ghi cổng A
- `[4:0] addr_b`: Địa chỉ đọc cổng B

### 2. Đầu ra (Outputs):
- `[7:0] dout_b`: Dữ liệu đọc ra tại cổng B

### 3. Hoạt động / Logic mong muốn:
- Cổng A chuyên ghi dữ liệu khi we_a = 1.
- Cổng B cho phép đọc độc lập dữ liệu tại addr_b mà không cản trở cổng A.

---

## Bài 25: Bộ Nhớ ROM Bảng Tra Cứu Sine 16x8 (16x8 Sine Look-Up Table ROM)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `en`: Cho phép đọc ROM
- `[3:0] phase_addr`: Góc pha từ 0 đến 15 (0 đến 360 độ)

### 2. Đầu ra (Outputs):
- `[7:0] sin_val`: Giá trị biên độ sóng sin 8-bit chuẩn hóa

### 3. Hoạt động / Logic mong muốn:
- Khi en = 1: Tại sườn clk, sin_val xuất giá trị sin được lưu sẵn trong bảng ROM 16 mẫu.

---

## Bài 26: Ngăn Xếp LIFO 8x8 (8-word Hardware Stack LIFO)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset ngăn xếp
- `push`: Đẩy phần tử vào stack
- `pop`: Lấy phần tử ra khỏi stack
- `[7:0] din`: Dữ liệu nạp vào

### 2. Đầu ra (Outputs):
- `[7:0] dout`: Dữ liệu lấy ra ở đỉnh stack
- `stack_full`: Báo ngăn xếp đầy
- `stack_empty`: Báo ngăn xếp rỗng

### 3. Hoạt động / Logic mong muốn:
- Quản lý con trỏ stack_ptr 3-bit.
- push: ghi din vào vị trí đỉnh và tăng stack_ptr.
- pop: giảm stack_ptr và xuất dữ liệu đỉnh ra dout.

---

## Bài 27: Thanh Ghi PIPO 8-bit Kèm Cho Phép Latch (8-bit PIPO Register with Clock Enable)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset tích cực cao
- `load_en`: Cho phép nạp dữ liệu
- `[7:0] d`: Dữ liệu đầu vào 8-bit

### 2. Đầu ra (Outputs):
- `[7:0] q`: Dữ liệu chốt đầu ra 8-bit

### 3. Hoạt động / Logic mong muốn:
- Khi rst = 1: q = 8'h00.
- Tại sườn lên clk: Nếu load_en = 1 thì q <= d; ngược lại q giữ nguyên.

---

## Bài 28: Thanh Ghi Dịch Nối Tiếp Sang Song Song SIPO 8-bit (8-bit SIPO Shift Register)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp dịch
- `rst`: Reset tích cực cao
- `shift_en`: Cho phép dịch
- `s_in`: Bit dữ liệu nối tiếp vào

### 2. Đầu ra (Outputs):
- `[7:0] p_out`: Byte dữ liệu song song đầu ra
- `valid`: Báo đã đủ 8 bit

### 3. Hoạt động / Logic mong muốn:
- Khi shift_en = 1: p_out <= {p_out[6:0], s_in}.
- Sau mỗi 8 xung dịch thành công, valid phát mức 1 trong 1 chu kỳ.

---

## Bài 29: Thanh Ghi Dịch Song Song Sang Nối Tiếp PISO 8-bit (8-bit PISO Shift Register)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp dịch
- `rst`: Reset tích cực cao
- `load`: Nạp dữ liệu song song
- `shift_en`: Cho phép dịch
- `[7:0] p_in`: Byte song song đầu vào

### 2. Đầu ra (Outputs):
- `s_out`: Bit nối tiếp đầu ra
- `busy`: Báo đang trong quá trình dịch byte

### 3. Hoạt động / Logic mong muốn:
- Khi load = 1: Chốt p_in vào thanh ghi nội bộ và bật busy = 1.
- Khi shift_en = 1: Dịch từng bit ra s_out bắt đầu từ bit MSB. Sau 8 bit, hạ busy = 0.

---

## Bài 30: Thanh Ghi Dịch Tuyến Tính LFSR 8-bit Tạo Số Ngẫu Nhiên (8-bit LFSR PRNG)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset về giá trị hạt giống Seed non-zero
- `en`: Cho phép sinh số

### 2. Đầu ra (Outputs):
- `[7:0] rand_out`: Số giả ngẫu nhiên 8-bit

### 3. Hoạt động / Logic mong muốn:
- Đa thức phản hồi: x^8 + x^6 + x^5 + x^4 + 1.
- Khi en = 1: rand_out <= {rand_out[6:0], feedback} với feedback = rand_out[7] ^ rand_out[5] ^ rand_out[4] ^ rand_out[3].

---


# NHÓM 4: MẠCH GHÉP KÊNH, PHÂN KÊNH & BỘ MÃ HÓA / GIẢI MÃ (MUX, DEMUX & CODECS)

## Bài 31: Bộ Ghép Kênh 8 Sang 1 (8-to-1 Multiplexer)

### 1. Đầu vào (Inputs):
- `[7:0] d_in`: 8 đường dữ liệu đầu vào 1-bit
- `[2:0] sel`: 3 đường điều khiển chọn kênh (000 đến 111)

### 2. Đầu ra (Outputs):
- `y_out`: Đường dữ liệu đầu ra được chọn

### 3. Hoạt động / Logic mong muốn:
- Mạch tổ hợp ghép kênh: y_out = d_in[sel]. Trễ lan truyền cổng cực nhỏ.

---

## Bài 32: Bộ Phân Kênh 1 Sang 8 (1-to-8 Demultiplexer)

### 1. Đầu vào (Inputs):
- `data_in`: 1 đường dữ liệu đầu vào
- `[2:0] sel`: 3 đường chọn kênh đầu ra
- `enable`: Cho phép phân kênh (active-high)

### 2. Đầu ra (Outputs):
- `[7:0] y_out`: 8 đường dữ liệu đầu ra

### 3. Hoạt động / Logic mong muốn:
- Nếu enable = 1: y_out[sel] = data_in, các kênh còn lại bằng 0.
- Nếu enable = 0: Toàn bộ 8 kênh y_out = 8'b00000000.

---

## Bài 33: Bộ Mã Hóa Ưu Tiên 8 Sang 3 (8-to-3 Priority Encoder)

### 1. Đầu vào (Inputs):
- `[7:0] req_in`: 8 đường yêu cầu ngắt vào (bit 7 có ưu tiên cao nhất)

### 2. Đầu ra (Outputs):
- `[2:0] code_out`: Mã nhị phân 3-bit của kênh có ưu tiên cao nhất
- `valid`: Báo có ít nhất một đường yêu cầu tích cực

### 3. Hoạt động / Logic mong muốn:
- Nếu có nhiều bit trong req_in cùng mức 1: code_out xuất chỉ số của bit 1 cao nhất.
- valid = 1 nếu req_in != 8'h00, ngược lại valid = 0.

---

## Bài 34: Bộ Giải Mã Nhị Phân 3 Sang 8 Tích Cực Thấp (3-to-8 Active-Low Decoder)

### 1. Đầu vào (Inputs):
- `[2:0] in_code`: Mã nhị phân 3-bit đầu vào
- `en_n`: Cho phép giải mã (tích cực thấp)

### 2. Đầu ra (Outputs):
- `[7:0] out_n`: 8 đường chọn chip đầu ra (Active-Low)

### 3. Hoạt động / Logic mong muốn:
- Khi en_n = 0: out_n[in_code] = 0, tất cả 7 đường còn lại bằng 1.
- Khi en_n = 1: Toàn bộ 8 đường out_n đều bằng 8'hFF (vô hiệu hóa).

---

## Bài 35: Bộ Giải Mã BCD Sang LED 7 Đoạn Anode Chung (BCD to 7-Segment Anode Decoder)

### 1. Đầu vào (Inputs):
- `[3:0] bcd_in`: Chữ số BCD 4-bit (0 đến 9)

### 2. Đầu ra (Outputs):
- `[6:0] seg_anode`: Mã điều khiển 7 thanh {a,b,c,d,e,f,g} Anode chung (active-low)

### 3. Hoạt động / Logic mong muốn:
- Giải mã chữ số BCD thành mã led tương ứng.
- 0 -> 7'b1000000, 1 -> 7'b1111001, ..., 9 -> 7'b0010000.
- Với giá trị không hợp lệ (10-15): seg_anode = 7'b1111111 (tắt led).

---

## Bài 36: Bộ Giải Mã BCD Sang LED 7 Đoạn Cathode Chung (BCD to 7-Segment Cathode Decoder)

### 1. Đầu vào (Inputs):
- `[3:0] bcd_in`: Chữ số BCD 4-bit (0 đến 9)

### 2. Đầu ra (Outputs):
- `[6:0] seg_cathode`: Mã điều khiển 7 thanh Cathode chung (active-high: mức 1 là sáng)

### 3. Hoạt động / Logic mong muốn:
- Mã hóa đảo của Anode chung: 0 -> 7'b0111111, 1 -> 7'b0000110, ..., 9 -> 7'b1101111.
- Giá trị ngoài 0-9 xuất 7'b0000000.

---

## Bài 37: Bộ Chuyển Đổi Nhị Phân Sang Mã Gray 4-bit (4-bit Binary to Gray Converter)

### 1. Đầu vào (Inputs):
- `[3:0] bin_in`: Số nhị phân 4-bit

### 2. Đầu ra (Outputs):
- `[3:0] gray_out`: Mã Gray tương ứng

### 3. Hoạt động / Logic mong muốn:
- Công thức logic tổ hợp: gray_out[3] = bin_in[3]; gray_out[2] = bin_in[3] ^ bin_in[2]; gray_out[1] = bin_in[2] ^ bin_in[1]; gray_out[0] = bin_in[1] ^ bin_in[0].

---

## Bài 38: Bộ Chuyển Đổi Mã Gray Sang Nhị Phân 4-bit (4-bit Gray to Binary Converter)

### 1. Đầu vào (Inputs):
- `[3:0] gray_in`: Mã Gray 4-bit

### 2. Đầu ra (Outputs):
- `[3:0] bin_out`: Số nhị phân tương ứng

### 3. Hoạt động / Logic mong muốn:
- Công thức logic: bin_out[3] = gray_in[3]; bin_out[2] = bin_out[3] ^ gray_in[2]; bin_out[1] = bin_out[2] ^ gray_in[1]; bin_out[0] = bin_out[1] ^ gray_in[0].

---

## Bài 39: Bộ Quét & Giải Mã Ma Trận Bàn Phím 4x4 (4x4 Keypad Matrix Scanner)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp quét quét hàng (1kHz)
- `rst`: Reset hệ thống
- `[3:0] col_in`: Tín hiệu 4 cột đọc về (tích cực thấp)

### 2. Đầu ra (Outputs):
- `[3:0] row_out`: Tín hiệu quét 4 hàng (tích cực thấp lần lượt)
- `[3:0] key_code`: Mã phím bấm được giải mã (0 đến 15)
- `key_pressed`: Cờ báo có phím đang được ấn

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm quét lần lượt 4 hàng: row_out kích mức 0 từng hàng một.
- Nếu phát hiện col_in có bit bằng 0: giải mã ra tọa độ (row, col) thành key_code và bật key_pressed = 1.

---

## Bài 40: Bộ Ghép Kênh Bus Dữ Liệu 4 Kênh 8-bit (4-Channel 8-bit Bus Multiplexer)

### 1. Đầu vào (Inputs):
- `[7:0] ch0`: Kênh dữ liệu 0
- `[7:0] ch1`: Kênh dữ liệu 1
- `[7:0] ch2`: Kênh dữ liệu 2
- `[7:0] ch3`: Kênh dữ liệu 3
- `[1:0] sel`: 2-bit chọn kênh

### 2. Đầu ra (Outputs):
- `[7:0] bus_out`: Bus dữ liệu đầu ra 8-bit

### 3. Hoạt động / Logic mong muốn:
- Bus multiplexer tổ hợp: sel=00 -> ch0; sel=01 -> ch1; sel=10 -> ch2; sel=11 -> ch3.

---


# NHÓM 5: MÁY TRẠNG THÁI HỮU HẠN FSM & BỘ DÒ CHUỖI (FSM & SEQUENCE DETECTORS)

## Bài 41: Bộ Dò Chuỗi Bit 1011 Dạng Mealy Cho Phép Gối Đầu (Mealy 1011 Sequence Detector)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset tích cực cao
- `bit_in`: Dòng bit nối tiếp vào

### 2. Đầu ra (Outputs):
- `det_out`: Đầu ra phát hiện chuỗi (mức 1 đúng 1 chu kỳ khi nhận đủ 1011)

### 3. Hoạt động / Logic mong muốn:
- Mô hình Mealy 4 trạng thái: S0 (chờ '1'), S1 (đã có '1'), S2 (đã có '10'), S3 (đã có '101').
- Tại S3 nếu bit_in = 1: det_out = 1 và chuyển về S1 (gối đầu chuỗi).

---

## Bài 42: Bộ Dò Chuỗi Bit 1101 Dạng Moore Không Gối Đầu (Moore 1101 Sequence Detector)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset tích cực cao
- `data_bit`: Bit nối tiếp đầu vào

### 2. Đầu ra (Outputs):
- `pattern_found`: Đầu ra phát hiện (mức 1 ở trạng thái đích)

### 3. Hoạt động / Logic mong muốn:
- Mô hình Moore 5 trạng thái (S_IDLE, S_1, S_11, S_110, S_MATCH).
- pattern_found = 1 chỉ khi FSM ở trạng thái S_MATCH.
- Sau khi phát hiện, chu kỳ kế tiếp bắt buộc quay về S_IDLE để dò chuỗi mới (không gối đầu).

---

## Bài 43: Bộ Điều Khiển Đèn Giao Thông Ngã Tư Thông Minh (Smart Traffic Light Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1Hz
- `rst`: Reset khẩn cấp về trạng thái mặc định
- `side_car_sensor`: Cảm biến có xe ở đường nhánh phụ

### 2. Đầu ra (Outputs):
- `[2:0] light_main`: Đèn đường chính {Đỏ, Vàng, Xanh}
- `[2:0] light_side`: Đèn đường nhánh {Đỏ, Vàng, Xanh}

### 3. Hoạt động / Logic mong muốn:
- Chu kỳ FSM: Đường chính Xanh 30s. Sau 30s nếu có xe đường nhánh -> chuyển Vàng 5s -> Đỏ.
- Đường nhánh Xanh 15s -> Vàng 5s -> Đỏ rồi trả lại quyền ưu tiên cho đường chính.

---

## Bài 44: Bộ Điều Khiển Thang Máy 4 Tầng Tự Động (4-Floor Elevator Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp đồng bộ
- `rst`: Reset về tầng 1
- `[3:0] call_req`: Nút bấm gọi tầng (bit 0: T1, ..., bit 3: T4)
- `[3:0] floor_sensor`: Cảm biến vị trí thang đang ở tầng

### 2. Đầu ra (Outputs):
- `motor_up`: Động cơ kéo thang lên
- `motor_down`: Động cơ kéo thang xuống
- `door_open`: Mở cửa khi đã đến tầng gọi

### 3. Hoạt động / Logic mong muốn:
- FSM so sánh tầng hiện tại và tầng yêu cầu.
- Nếu tầng yêu cầu > tầng hiện tại: bật motor_up.
- Nếu tầng yêu cầu < tầng hiện tại: bật motor_down.
- Khi tới đúng tầng: dừng motor và bật door_open trong 5 chu kỳ clock.

---

## Bài 45: Khóa Mã Số Điện Tử 4 Chữ Số Bảo Mật (Digital Safe Lock)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset khóa
- `[3:0] key_digit`: Chữ số nhập vào (0-9)
- `enter_pulse`: Xung xác nhận nhập 1 số

### 2. Đầu ra (Outputs):
- `unlock`: Mở khóa thành công
- `alarm`: Còi báo động khi nhập sai quá 3 lần
- `[1:0] fail_count`: Số lần nhập sai liên tiếp

### 3. Hoạt động / Logic mong muốn:
- Mật mã mẫu: 4 -> 2 -> 7 -> 9.
- Người dùng ấn enter_pulse 4 lần liên tiếp.
- Nếu đúng cả 4: unlock = 1. Nếu sai bất kỳ chữ số nào: tăng fail_count. fail_count = 3 -> bật alarm.

---

## Bài 46: Máy Bán Nước Tự Động Nhả Nước & Thối Tiền (Vending Machine Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset hệ thống
- `coin_5k`: Nhét đồng tiền 5.000đ
- `coin_10k`: Nhét đồng tiền 10.000đ

### 2. Đầu ra (Outputs):
- `dispense_can`: Nhả lon nước (giá 15.000đ)
- `return_5k`: Thối lại tiền thừa 5.000đ

### 3. Hoạt động / Logic mong muốn:
- FSM tích lũy số tiền: 0k -> 5k -> 10k -> 15k -> 20k.
- Khi nạp đủ 15k: dispense_can = 1, quay về 0k.
- Khi nạp đạt 20k: dispense_can = 1, return_5k = 1, quay về 0k.

---

## Bài 47: Máy Giặt Tự Động 4 Chu Trình (Automatic Washing Machine Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1Hz
- `rst`: Reset chu trình
- `start_btn`: Nút bấm bắt đầu giặt
- `water_level_full`: Cảm biến nước đã đầy lồng giặt

### 2. Đầu ra (Outputs):
- `inlet_valve`: Mở van cấp nước
- `motor_wash`: Động cơ quay đảo giặt
- `drain_pump`: Bơm xả nước bẩn
- `motor_spin`: Động cơ quay vắt tốc độ cao
- `done_buzzer`: Còi báo hoàn tất giặt

### 3. Hoạt động / Logic mong muốn:
- Trạng thái 1 (Cấp nước): mở inlet_valve cho tới khi water_level_full = 1.
- Trạng thái 2 (Giặt): chạy motor_wash trong 60s.
- Trạng thái 3 (Xả): chạy drain_pump trong 30s.
- Trạng thái 4 (Vắt): chạy motor_spin 45s rồi bật done_buzzer.

---

## Bài 48: Bộ Điều Khiển Cửa Cuốn Tự Động Đảo Chiều (Roller Shutter Door Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset ban đầu
- `btn_up`: Nút bấm mở cửa
- `btn_down`: Nút bấm đóng cửa
- `btn_stop`: Nút dừng
- `limit_top`: Công tắc hành trình đỉnh
- `limit_bottom`: Công tắc hành trình đáy
- `obstacle_sensor`: Cảm biến vật cản hồng ngoại

### 2. Đầu ra (Outputs):
- `motor_open`: Mô tơ kéo cửa mở
- `motor_close`: Mô tơ kéo cửa đóng
- `lamp_warning`: Đèn chớp cảnh báo khi cửa di chuyển

### 3. Hoạt động / Logic mong muốn:
- Khi btn_up = 1: chạy motor_open cho tới khi chạm limit_top hoặc gặp btn_stop.
- Khi btn_down = 1: chạy motor_close cho tới khi chạm limit_bottom.
- ĐẶC BIỆT: Nếu đang đóng mà obstacle_sensor = 1: lập tức dừng motor_close và tự động đảo chiều mở motor_open để tránh kẹp.

---

## Bài 49: Bộ Đếm Vé & Kiểm Soát Cổng Xoay Barrier (Turnstile Barrier Gate Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset bộ đếm
- `ticket_valid`: Xác thực vé hợp lệ
- `passage_sensor`: Cảm biến người đã đi qua

### 2. Đầu ra (Outputs):
- `unlock_barrier`: Mở chốt cơ khí cho phép đi qua
- `[11:0] total_passengers`: Tổng số lượt khách đã đi qua

### 3. Hoạt động / Logic mong muốn:
- Khi ticket_valid = 1: unlock_barrier = 1.
- Khi khách bước qua kích passage_sensor = 1: khóa lại unlock_barrier = 0 và tăng total_passengers lên 1.

---

## Bài 50: Bộ Điều Khiển Đèn Cầu Thang Cảm Ứng Thông Minh (Motion Staircase Light Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1Hz
- `rst`: Reset
- `pir_bottom`: Cảm biến PIR ở chân cầu thang
- `pir_top`: Cảm biến PIR ở đỉnh cầu thang

### 2. Đầu ra (Outputs):
- `[7:0] leds_stair`: Dải 8 bậc đèn LED cầu thang

### 3. Hoạt động / Logic mong muốn:
- Khi pir_bottom = 1: Bật sáng tuần tự từng bậc từ dưới lên trên (bậc 0 đến bậc 7). Duy trì sáng 10s rồi tắt dần.
- Khi pir_top = 1: Bật sáng tuần tự từng bậc từ trên xuống dưới (bậc 7 xuống bậc 0).

---


# NHÓM 6: MẠCH GIAO TIẾP & NGOẠI VI CÔNG NGHIỆP (COMMUNICATION & PROTOCOLS)

## Bài 51: Bộ Truyền Dữ Liệu Nối Tiếp UART TX 8-N-1 (UART Transmitter 8-N-1)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset tích cực cao
- `tx_start`: Xung kích phát byte dữ liệu
- `[7:0] tx_data`: Byte dữ liệu cần truyền
- `baud_pulse`: Xung kích tốc độ baudrate

### 2. Đầu ra (Outputs):
- `tx_serial`: Đường truyền nối tiếp TX (mặc định mức 1 khi rảnh)
- `tx_busy`: Báo đang bận truyền khung dữ liệu

### 3. Hoạt động / Logic mong muốn:
- Khung truyền chuẩn 10-bit: 1 Start bit (mức 0), 8 Data bits (truyền bit LSB trước), 1 Stop bit (mức 1).
- tx_busy = 1 trong suốt quá trình truyền 10 bit.

---

## Bài 52: Bộ Nhận Dữ Liệu Nối Tiếp UART RX Lấy Mẫu 16x (UART Receiver 16x)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset
- `rx_serial`: Đường truyền nối tiếp RX
- `baud_x16`: Xung lấy mẫu nhanh gấp 16 lần tốc độ baud

### 2. Đầu ra (Outputs):
- `[7:0] rx_data`: Byte dữ liệu nhận được
- `rx_ready`: Xung báo đã nhận xong 1 byte hoàn chỉnh
- `framing_error`: Báo lỗi cấu trúc khung truyền

### 3. Hoạt động / Logic mong muốn:
- Dò sườn xuống của Start bit.
- Bộ đếm lấy mẫu tại chu kỳ thứ 8 (giữa bit) để loại trừ nhiễu.
- Nhận đủ 8 bit dữ liệu, kiểm tra Stop bit = 1. Nếu Stop bit = 0 -> bật framing_error.

---

## Bài 53: Bộ Điều Khiển Giao Tiếp SPI Master Chế Độ 0 (SPI Master Mode 0)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset
- `start_transfer`: Lệnh bắt đầu truyền
- `[7:0] tx_byte`: Byte dữ liệu cần gửi đi
- `miso`: Đường Master-In Slave-Out

### 2. Đầu ra (Outputs):
- `sclk`: Xung nhịp đồng hồ SPI xuất ra ngoại vi
- `mosi`: Đường Master-Out Slave-In
- `cs_n`: Chọn chip ngoại vi (active-low)
- `[7:0] rx_byte`: Byte dữ liệu đọc về từ Slave
- `transfer_done`: Báo hoàn tất trao đổi 1 byte

### 3. Hoạt động / Logic mong muốn:
- SPI Mode 0: CPOL = 0 (sclk mức 0 khi nghỉ), CPHA = 0 (lấy mẫu tại sườn lên sclk).
- cs_n hạ mức 0 khi truyền, phát 8 xung sclk để đẩy tx_byte ra mosi và đồng thời thu miso vào rx_byte.

---

## Bài 54: Bộ Điều Khiển Giao Tiếp SPI Slave 8-bit (SPI Slave 8-bit)

### 1. Đầu vào (Inputs):
- `sclk`: Xung nhịp từ Master cấp
- `cs_n`: Tín hiệu chọn chip từ Master
- `mosi`: Dữ liệu Master gửi sang
- `[7:0] reply_byte`: Byte Slave chuẩn bị gửi lại cho Master

### 2. Đầu ra (Outputs):
- `miso`: Dữ liệu Slave gửi về Master
- `[7:0] received_byte`: Byte nhận từ Master
- `data_valid`: Cờ báo đã nhận đủ byte

### 3. Hoạt động / Logic mong muốn:
- Khi cs_n = 0: Thanh ghi dịch nhận từng bit từ mosi tại sườn lên sclk, và đẩy từng bit từ reply_byte ra miso tại sườn xuống sclk.
- Đủ 8 bit -> data_valid = 1.

---

## Bài 55: Bộ Điều Khiển Bus I2C Master Truyền 1 Byte (I2C Master Single-Byte)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `send_req`: Lệnh gửi
- `[6:0] slave_addr`: Địa chỉ Slave 7-bit
- `[7:0] data_byte`: Dữ liệu cần gửi
- `sda_in`: Đường SDA chiều nhận

### 2. Đầu ra (Outputs):
- `scl`: Xung nhịp I2C (100kHz)
- `sda_out`: Đường SDA chiều xuất
- `sda_oe`: Cho phép lái bus SDA
- `ack_error`: Cờ báo Slave không phản hồi NACK

### 3. Hoạt động / Logic mong muốn:
- Sinh điều kiện START (SDA xuống trước SCL).
- Phát 7-bit địa chỉ + 1 bit R/W=0.
- Đọc bit ACK từ sda_in. Sau đó phát 8-bit data_byte, đọc ACK và sinh điều kiện STOP.

---

## Bài 56: Bộ Đệm Ghép Nối Bus Dữ Liệu 3 Trạng Thái Tri-State (8-bit Tri-State Transceiver)

### 1. Đầu vào (Inputs):
- `[7:0] a_bus`: Cổng bus A
- `oe_n`: Cho phép xuất (Output Enable, active-low)
- `dir`: Hướng truyền (1: A sang B, 0: B sang A)

### 2. Đầu ra (Outputs):
- `[7:0] b_bus`: Cổng bus B (inout tri-state)

### 3. Hoạt động / Logic mong muốn:
- Khi oe_n = 1: b_bus ở trạng thái trở kháng cao (High-Z: 8'bzzzzzzzz).
- Khi oe_n = 0: nếu dir = 1 thì b_bus = a_bus; nếu dir = 0 thì a_bus đọc từ b_bus.

---

## Bài 57: Bộ Đóng Gói Khung Truyền UART Kèm Checksum (UART Frame Packetizer)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `pack_start`: Bắt đầu đóng gói
- `[7:0] payload_data`: Dữ liệu gói tin

### 2. Đầu ra (Outputs):
- `tx_stream`: Dòng dữ liệu nối tiếp
- `packet_busy`: Báo đang bận gửi gói

### 3. Hoạt động / Logic mong muốn:
- Cấu trúc gói tin 4 byte: [0xAA (Header)] -> [Length (0x01)] -> [Payload] -> [Checksum = Header ^ Length ^ Payload].
- Tự động kích hoạt truyền lần lượt 4 byte qua UART.

---

## Bài 58: Bộ Sinh Xung Baudrate Đa Tốc Độ UART (UART Baudrate Generator)

### 1. Đầu vào (Inputs):
- `clk_50mhz`: Xung nhịp gốc 50MHz
- `rst`: Reset
- `[1:0] baud_sel`: Chọn tốc độ (00: 9600, 01: 19200, 10: 57600, 11: 115200)

### 2. Đầu ra (Outputs):
- `baud_tick`: Xung hẹp 1 chu kỳ clock tại mỗi nhịp baudrate chuẩn

### 3. Hoạt động / Logic mong muốn:
- Bộ chia tần số nạp hệ số chia tương ứng: 9600 -> 5208; 19200 -> 2604; 57600 -> 868; 115200 -> 434.
- Mỗi khi đếm đủ chu kỳ, phát baud_tick = 1.

---

## Bài 59: Bộ Nhận Giao Tiếp Bàn Phím PS/2 (PS/2 Keyboard Protocol Receiver)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset
- `ps2_clk`: Đường xung nhịp từ bàn phím PS/2
- `ps2_data`: Đường dữ liệu nối tiếp từ bàn phím

### 2. Đầu ra (Outputs):
- `[7:0] scan_code`: Mã quét phím Make/Break code nhận được
- `code_ready`: Xung báo mã phím hợp lệ

### 3. Hoạt động / Logic mong muốn:
- Bắt sườn xuống của ps2_clk.
- Dịch khung truyền 11 bit: 1 Start bit, 8 Data bits, 1 Parity bit, 1 Stop bit.
- Kiểm tra tính đúng đắn của bit Parity rồi trích xuất scan_code.

---

## Bài 60: Bộ Giải Mã Tín Hiệu Hồng Ngoại Điều Khiển Từ Xa NEC (NEC IR Protocol Decoder)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1MHz (1us 1 nhịp)
- `rst`: Reset
- `ir_rx_raw`: Tín hiệu hồng ngoại nhận từ mắt thu IR (tích cực thấp)

### 2. Đầu ra (Outputs):
- `[7:0] address_code`: Mã địa chỉ thiết bị
- `[7:0] command_code`: Mã lệnh phím bấm
- `cmd_valid`: Cờ báo lệnh hợp lệ

### 3. Hoạt động / Logic mong muốn:
- Đo độ rộng xung Leader Code (9ms mức thấp + 4.5ms mức cao).
- Giải mã 32-bit dữ liệu theo chuẩn NEC: bit 0 (562us thấp + 562us cao), bit 1 (562us thấp + 1.68ms cao).
- Kiểm tra Command và ~Command bù 1 để xác thực cmd_valid.

---


# NHÓM 7: MẠCH ĐIỀU CHẾ XUNG PWM & ĐIỀU KHIỂN ĐỘNG CƠ (PWM & MOTOR CONTROL)

## Bài 61: Bộ Điều Chế Độ Rộng Xung PWM 8-bit (8-bit Variable Duty Cycle PWM)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp đồng hồ
- `rst`: Reset tích cực cao
- `[7:0] duty`: Giá trị chu kỳ nhiệm vụ (0 đến 255)

### 2. Đầu ra (Outputs):
- `pwm_out`: Tín hiệu điều chế độ rộng xung đầu ra

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm tự do counter 8-bit tăng liên tục từ 0 đến 255 rồi tự tràn về 0.
- pwm_out = (counter < duty) ? 1'b1 : 1'b0.

---

## Bài 62: Bộ Điều Khiển Động Cơ Bước 4 Pha Đơn/Kép (4-Phase Stepper Motor Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp điều khiển bước
- `rst`: Reset động cơ
- `enable`: Cho phép chạy
- `direction`: Chiều quay (1: Thuận CW, 0: Nghịch CCW)
- `half_step_mode`: 1: Vi bước nửa bước (8 trạng thái), 0: Bước đủ (4 trạng thái)

### 2. Đầu ra (Outputs):
- `[3:0] phase_coils`: Tín hiệu kích 4 cuộn dây động cơ {A, B, C, D}

### 3. Hoạt động / Logic mong muốn:
- Full-step: kích lần lượt 4 cuộn theo chuỗi 1000 -> 0100 -> 0010 -> 0001.
- Half-step: kích xen kẽ 1000 -> 1100 -> 0100 -> 0110 -> ... để tăng gấp đôi độ phân giải bước quay.

---

## Bài 63: Bộ Điều Khiển Động Cơ DC Cầu H Quay Thuận / Nghịch (H-Bridge DC Motor Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `run_fwd`: Lệnh quay thuận
- `run_rev`: Lệnh quay nghịch
- `[7:0] speed_val`: Tốc độ động cơ (0 đến 255)
- `brake_emergency`: Phanh hãm khẩn cấp

### 2. Đầu ra (Outputs):
- `in1`: Lái cầu H nửa cầu 1
- `in2`: Lái cầu H nửa cầu 2
- `en_pwm`: Tín hiệu băm xung PWM điều khiển tốc độ

### 3. Hoạt động / Logic mong muốn:
- Quay thuận: in1 = 1, in2 = 0, en_pwm = băm xung PWM theo speed_val.
- Quay nghịch: in1 = 0, in2 = 1, en_pwm = băm xung.
- Khi brake_emergency = 1 hoặc run_fwd và run_rev cùng bật: in1 = in2 = 1 (ngắn mạch hãm tái sinh an toàn, chống cháy cầu H).

---

## Bài 64: Bộ Điều Khiển Động Cơ Servo RC Góc 0-180 Độ (RC Servo 50Hz Pulse Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1MHz (1us)
- `rst`: Reset
- `[7:0] angle_deg`: Góc đặt từ 0 đến 180 độ

### 2. Đầu ra (Outputs):
- `servo_pwm`: Xung điều khiển chu kỳ 20ms (tần số 50Hz)

### 3. Hoạt động / Logic mong muốn:
- Góc 0 độ: độ rộng xung mức cao là 1000us (1.0ms).
- Góc 180 độ: độ rộng xung mức cao là 2000us (2.0ms).
- Nội suy tuyến tính độ rộng xung mức cao: T_high = 1000 + (angle_deg * 1000 / 180) (us).

---

## Bài 65: Bộ Phát Xung SPWM Cho Nghịch Lưu Sóng Sin (Sinusoidal SPWM Generator)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp sóng mang tam giác
- `rst`: Reset
- `[7:0] modulation_idx`: Chỉ số điều chế biên độ

### 2. Đầu ra (Outputs):
- `spwm_pos`: Xung kích van bán dẫn bán kỳ dương
- `spwm_neg`: Xung kích van bán dẫn bán kỳ âm (kèm Deadtime chống trùng dẫn)

### 3. Hoạt động / Logic mong muốn:
- So sánh sóng mang tam giác đối xứng với bảng tra cứu sóng sin 8-bit.
- Tự động chèn khoảng thời gian chết (Deadtime 2us) giữa hai kênh để bảo vệ mạch nghịch lưu IGBT.

---

## Bài 66: Bộ Điều Khiển Băm Xung Đèn LED RGB Đổi Màu (RGB LED Color Cycling PWM)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp quét PWM
- `rst`: Reset
- `[1:0] mode_sel`: Chế độ (00: Đổi màu cầu vồng tự động, 01: Đỏ, 10: Xanh lá, 11: Xanh dương)

### 2. Đầu ra (Outputs):
- `pwm_r`: PWM điều khiển LED Đỏ
- `pwm_g`: PWM điều khiển LED Xanh lá
- `pwm_b`: PWM điều khiển LED Xanh dương

### 3. Hoạt động / Logic mong muốn:
- Chế độ tự động: FSM chuyển đổi tuần tự sắc độ màu (Red -> Yellow -> Green -> Cyan -> Blue -> Magenta -> Red) bằng cách tăng giảm duty cycle của 3 kênh PWM theo hàm sin.

---

## Bài 67: Bộ Điều Khiển Tốc Độ Quạt Tản Nhiệt Thông Minh (Smart Temperature-Based Fan PWM)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `[7:0] temp_celsius`: Nhiệt độ đo được từ cảm biến (độ C)

### 2. Đầu ra (Outputs):
- `fan_pwm`: Tín hiệu PWM lái quạt
- `overheat_warning`: Cờ báo động quá nhiệt

### 3. Hoạt động / Logic mong muốn:
- Dưới 35 độ C: Quạt tắt (duty = 0%).
- Từ 35 đến 70 độ C: Quạt quay tăng dần tuyến tính từ 30% lên 100% duty.
- Trên 80 độ C: Quạt chạy tối đa 100% và bật overheat_warning = 1.

---

## Bài 68: Mạch Phát Tín Hiệu Còi Báo Động Đa Âm Sắc (Multi-Tone Siren Tone Generator)

### 1. Đầu vào (Inputs):
- `clk_50mhz`: Xung nhịp 50MHz
- `rst`: Reset
- `siren_en`: Bật còi báo động
- `alarm_type`: Loại còi (0: Còi xe cứu hỏa quét tần số, 1: Còi xe cứu thương 2 âm điệu)

### 2. Đầu ra (Outputs):
- `buzzer_out`: Tín hiệu xung vuông lái loa piezo

### 3. Hoạt động / Logic mong muốn:
- Loại 0: Quét tần số liên tục từ 600Hz lên 1500Hz rồi lặp lại mỗi 2 giây.
- Loại 1: Luân phiên phát tần số 700Hz và 1000Hz mỗi 500ms.

---

## Bài 69: Bộ Tạo Xung Đồng Hồ Nhịp Tim Cho Mạch Y Tế (Medical Pulse Heartbeat Generator)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp chuẩn
- `rst`: Reset
- `[7:0] bpm_target`: Nhịp tim mục tiêu (ví dụ 60 đến 180 nhịp/phút)

### 2. Đầu ra (Outputs):
- `heartbeat_pulse`: Xung nhịp tim đầu ra
- `tachycardia_flag`: Cờ cảnh báo nhịp tim nhanh (>120 bpm)
- `bradycardia_flag`: Cờ cảnh báo nhịp tim chậm (<50 bpm)

### 3. Hoạt động / Logic mong muốn:
- Tính chu kỳ xung theo công thức: T = (60 / bpm_target) giây.
- Bật cờ cảnh báo tương ứng nếu bpm_target vượt các ngưỡng an toàn y tế.

---

## Bài 70: Mạch Điều Khiển Khởi Động Mềm Soft-Start Nguồn Điện (Power Soft-Start Ramp Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `power_good_in`: Tín hiệu nguồn đầu vào ổn định

### 2. Đầu ra (Outputs):
- `pwm_softstart`: Duty cycle tăng từ từ từ 0% lên 100%
- `system_ready`: Báo hệ thống đã khởi động êm hoàn tất

### 3. Hoạt động / Logic mong muốn:
- Khi power_good_in = 1: Bắt đầu tăng dần duty cycle mỗi 10ms thêm 1%.
- Sau đúng 1 giây khi duty đạt 100%, bật system_ready = 1.

---


# NHÓM 8: MẠCH KHỬ NHIỄU, XỬ LÝ TÍN HIỆU & ĐO LƯỜNG (SIGNAL CONDITIONING & MEASUREMENT)

## Bài 71: Bộ Lọc Khử Rung Phím Bấm Debounce 20ms (20ms Pushbutton Debouncer)

### 1. Đầu vào (Inputs):
- `clk_1khz`: Xung nhịp lấy mẫu 1kHz (1ms)
- `rst`: Reset
- `raw_button`: Tín hiệu nút bấm thô bị rung cơ khí

### 2. Đầu ra (Outputs):
- `clean_button`: Tín hiệu nút bấm sạch nhiễu
- `btn_click_pulse`: Xung kích 1 chu kỳ khi phát hiện vừa bấm phím

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm tăng khi raw_button giữ nguyên trạng thái mới.
- Chỉ khi tín hiệu ổn định liên tục trong 20 chu kỳ (20ms), clean_button mới cập nhật trạng thái.
- Phát xung btn_click_pulse đúng 1 nhịp clock tại sườn lên của clean_button.

---

## Bài 72: Bộ Dò Sườn Xung Cạnh Lên & Cạnh Xuống (Rising & Falling Edge Detector)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp lấy mẫu nhanh
- `rst`: Reset
- `sig_in`: Tín hiệu đầu vào bất kỳ

### 2. Đầu ra (Outputs):
- `pe_edge`: Xung 1 chu kỳ khi có cạnh lên (Positive Edge)
- `ne_edge`: Xung 1 chu kỳ khi có cạnh xuống (Negative Edge)
- `any_edge`: Xung khi có bất kỳ cạnh nào biến đổi

### 3. Hoạt động / Logic mong muốn:
- Sử dụng 2 Flip-Flop nối tiếp để ghi nhận trạng thái hiện tại và trạng thái chu kỳ trước.
- pe_edge = sig_q0 && ~sig_q1; ne_edge = ~sig_q0 && sig_q1; any_edge = sig_q0 ^ sig_q1.

---

## Bài 73: Bộ Kéo Dài Độ Rộng Xung Ngắn (Short Pulse Stretcher)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `narrow_pulse`: Xung đầu vào cực ngắn (có thể chỉ rộng 1 vài ns)
- `[7:0] stretch_cycles`: Số chu kỳ xung cần kéo dài

### 2. Đầu ra (Outputs):
- `stretched_pulse`: Xung đầu ra được kéo dài đủ độ rộng

### 3. Hoạt động / Logic mong muốn:
- Bắt sườn dương của narrow_pulse bằng mạch chốt bất đồng bộ.
- Giữ stretched_pulse = 1 trong đúng stretch_cycles chu kỳ clock rồi tự động xóa mạch chốt.

---

## Bài 74: Bộ Đo Độ Rộng Xung Đầu Vào (Input Pulse Width Measurement Unit)

### 1. Đầu vào (Inputs):
- `clk_1mhz`: Xung chuẩn 1MHz (độ phân giải 1us)
- `rst`: Reset
- `pulse_in`: Xung cần đo độ rộng

### 2. Đầu ra (Outputs):
- `[15:0] pulse_width_us`: Độ rộng xung mức cao đo được (micro-giây)
- `meas_done`: Cờ báo hoàn thành đo

### 3. Hoạt động / Logic mong muốn:
- Khi pulse_in lên mức 1: Bắt đầu đếm nhịp clk_1mhz.
- Khi pulse_in xuống mức 0: Dừng đếm, chuyển kết quả sang pulse_width_us và bật meas_done = 1.

---

## Bài 75: Bộ Đồng Bộ Hóa Xung Đa Miền Clock 2 Tầng (2-Stage Clock Domain Crossing Synchronizer)

### 1. Đầu vào (Inputs):
- `clk_dest`: Xung nhịp miền đích
- `rst_dest`: Reset miền đích
- `async_sig_in`: Tín hiệu từ miền xung khác gửi sang

### 2. Đầu ra (Outputs):
- `sync_sig_out`: Tín hiệu sau khi đã đồng bộ hóa vào clk_dest, triệt tiêu trạng thái siêu ổn định Metastability

### 3. Hoạt động / Logic mong muốn:
- Sử dụng 2 Flip-Flop D mắc nối tiếp trong miền clk_dest để lọc trạng thái chập chờn siêu ổn định.

---

## Bài 76: Bộ Giao Tiếp Cảm Biến Siêu Âm HC-SR04 (HC-SR04 Ultrasonic Distance Interface)

### 1. Đầu vào (Inputs):
- `clk_1mhz`: Xung chuẩn 1MHz
- `rst`: Reset
- `start_meas`: Lệnh kích hoạt đo
- `echo_in`: Tín hiệu Echo phản hồi từ cảm biến

### 2. Đầu ra (Outputs):
- `trig_out`: Phát xung Trigger 10us cho cảm biến
- `[11:0] distance_cm`: Khoảng cách đo được (cm)
- `meas_valid`: Cờ báo kết quả đo hợp lệ

### 3. Hoạt động / Logic mong muốn:
- Phát xung trig_out mức cao 10us.
- Đo thời gian Echo ở mức cao (T_us).
- Tính khoảng cách: distance_cm = T_us / 58. Cập nhật meas_valid = 1.

---

## Bài 77: Bộ Điều Chế Mã Hóa Băng Thông Manchester (Manchester Signal Encoder)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp truyền dữ liệu (tần số gấp 2 lần baudrate)
- `rst`: Reset
- `nrz_data_in`: Dữ liệu nhị phân chuẩn NRZ

### 2. Đầu ra (Outputs):
- `manchester_out`: Tín hiệu mã hóa Manchester (tự chứa xung nhịp Clock)

### 3. Hoạt động / Logic mong muốn:
- Bit '0' được mã hóa thành bước nhảy từ thấp lên cao (0 -> 1) ở giữa chu kỳ bit.
- Bit '1' được mã hóa thành bước nhảy từ cao xuống thấp (1 -> 0).

---

## Bài 78: Bộ Giải Mã Tín Hiệu Manchester (Manchester Signal Decoder)

### 1. Đầu vào (Inputs):
- `clk_fast`: Xung nhịp lấy mẫu nhanh 8x
- `rst`: Reset
- `manchester_in`: Dòng tín hiệu Manchester

### 2. Đầu ra (Outputs):
- `recovered_data`: Dữ liệu nhị phân NRZ phục hồi
- `recovered_clk`: Xung nhịp phục hồi từ đường truyền
- `sync_err`: Báo lỗi vi phạm mã hóa

### 3. Hoạt động / Logic mong muốn:
- Tự động khóa pha vào các bước nhảy ở giữa chu kỳ bit để khôi phục xung nhịp và dữ liệu gốc.

---

## Bài 79: Bộ Lọc Số Trung Bình Trượt 4 Mẫu (4-Tap Moving Average Digital Filter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp lấy mẫu
- `rst`: Reset bộ lọc
- `sample_valid`: Mẫu mới hợp lệ
- `[7:0] raw_sample`: Giá trị mẫu đo thô 8-bit

### 2. Đầu ra (Outputs):
- `[7:0] filtered_sample`: Giá trị sau khi lọc trung bình trượt 4 mẫu gần nhất

### 3. Hoạt động / Logic mong muốn:
- Lưu trữ 4 mẫu gần nhất vào hàng đợi thanh ghi: x[n], x[n-1], x[n-2], x[n-3].
- filtered_sample = (x[n] + x[n-1] + x[n-2] + x[n-3]) >> 2 (chia 4 bằng cách dịch phải 2 bit).

---

## Bài 80: Bộ Khóa Pha Kỹ Thuật Số DPLL Phát Hiện Sai Pha (Digital Phase Detector)

### 1. Đầu vào (Inputs):
- `clk_ref`: Tín hiệu xung chuẩn tham chiếu
- `clk_feedback`: Tín hiệu xung phản hồi

### 2. Đầu ra (Outputs):
- `phase_lead`: Báo phản hồi nhanh pha hơn tham chiếu
- `phase_lag`: Báo phản hồi chậm pha hơn
- `in_phase`: Báo hai tín hiệu đã đồng pha (sai số < 5%)

### 3. Hoạt động / Logic mong muốn:
- So sánh thời điểm xuất hiện sườn lên giữa hai tín hiệu và lượng hóa độ lệch pha bằng bộ đếm tốc độ cao.

---


# NHÓM 9: HỆ THỐNG TỰ ĐỘNG HÓA, AN NINH & NHÀ THÔNG MINH (SMART SYSTEMS & IOT)

## Bài 81: Hệ Thống Cảnh Báo An Ninh & Báo Cháy Nhà Thông Minh (Smart Home Security & Fire Alarm)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống
- `rst`: Reset tích cực cao
- `motion_pir`: Cảm biến chuyển động PIR
- `smoke_gas`: Cảm biến khói/khí gas
- `arm_mode`: Chế độ kích hoạt an ninh (1: Bật bảo vệ, 0: Tắt)

### 2. Đầu ra (Outputs):
- `siren`: Còi hú báo động
- `sprinkler`: Van xả nước dập lửa
- `[1:0] status_code`: Mã trạng thái an ninh (00: An toàn, 01: Đột nhập, 10: Cháy nổ)

### 3. Hoạt động / Logic mong muốn:
- Ưu tiên tuyệt đối: Khi smoke_gas = 1 -> Lập tức bật siren = 1, mở van dập lửa sprinkler = 1, status_code = 2'b10.
- Khi arm_mode = 1 và motion_pir = 1: Bật siren = 1, status_code = 2'b01.
- Khi an toàn: siren = 0, sprinkler = 0, status_code = 2'b00.

---

## Bài 82: Hệ Thống Báo Động Chống Trộm Cảm Biến Cửa & Chuyển Động (Intruder Alarm System)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `door_magnetic`: Cảm biến từ mở cửa (0: Cửa đóng, 1: Cửa mở)
- `pir_indoor`: Cảm biến chuyển động trong nhà
- `key_disarm`: Khóa ngắt báo động hợp lệ

### 2. Đầu ra (Outputs):
- `alarm_strobe`: Đèn chớp xua đuổi trộm
- `silent_alarm`: Tín hiệu gọi cảnh sát ngầm

### 3. Hoạt động / Logic mong muốn:
- Khi có xâm nhập (door_magnetic = 1 hoặc pir_indoor = 1) mà không có key_disarm: Kích hoạt đếm trễ 10s.
- Sau 10s nếu không nhập mã giải phóng: Bật còi đèn alarm_strobe và gửi silent_alarm.

---

## Bài 83: Bộ Kiểm Soát Khí Hậu Nhà Kính Nông Nghiệp (Greenhouse Climate Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp 1Hz
- `rst`: Reset
- `[7:0] temp_val`: Nhiệt độ hiện tại (°C)
- `[7:0] humidity_val`: Độ ẩm không khí (%)

### 2. Đầu ra (Outputs):
- `heater_relay`: Rơ-le bật máy sưởi
- `exhaust_fan`: Quạt hút thông gió
- `mist_nozzle`: Hệ thống phun sương tạo ẩm

### 3. Hoạt động / Logic mong muốn:
- Nếu temp_val < 18°C: bật heater_relay.
- Nếu temp_val > 32°C: bật exhaust_fan.
- Nếu humidity_val < 60%: mở mist_nozzle.

---

## Bài 84: Bộ Điều Khiển Tưới Cây Tự Động Theo Độ Ẩm Đất (Soil Moisture Irrigation Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `[7:0] soil_moisture`: Độ ẩm đất (0-100%)
- `rain_detected`: Cảm biến trời đang mưa
- `water_tank_empty`: Cảm biến bồn nước đã cạn

### 2. Đầu ra (Outputs):
- `pump_relay`: Rơ-le đóng máy bơm tưới
- `tank_alert`: Đèn báo cạn nước bồn

### 3. Hoạt động / Logic mong muốn:
- Nếu water_tank_empty = 1: Ngắt tuyệt đối pump_relay và bật tank_alert = 1.
- Nếu rain_detected = 0 và soil_moisture < 40%: Bật pump_relay tưới cây cho đến khi soil_moisture đạt 75% thì ngắt bơm.

---

## Bài 85: Hệ Thống Bãi Đỗ Xe Thông Minh Đếm Chỗ Trống (Smart Parking Space Counter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset bãi đỗ
- `car_enter_sensor`: Cảm biến xe vào cổng
- `car_exit_sensor`: Cảm biến xe rời bãi

### 2. Đầu ra (Outputs):
- `[7:0] free_spaces`: Số chỗ đỗ còn trống (tối đa 100 xe)
- `gate_barrier`: Mở cổng barie cho xe vào
- `full_sign`: Bảng LED báo bãi đỗ đã hết chỗ

### 3. Hoạt động / Logic mong muốn:
- Ban đầu free_spaces = 100, full_sign = 0.
- Khi có xe vào (car_enter_sensor = 1) và free_spaces > 0: mở gate_barrier và giảm free_spaces đi 1.
- Khi có xe ra: tăng free_spaces thêm 1.
- Khi free_spaces == 0: full_sign = 1, đóng barie không cho xe vào.

---

## Bài 86: Hệ Thống Đèn Chiếu Sáng Công Cộng Tự Động (Smart Street Lighting System)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `ldr_dark`: Cảm biến quang (1: Trời tối, 0: Trời sáng)
- `radar_motion`: Cảm biến phát hiện có người/xe đi tới

### 2. Đầu ra (Outputs):
- `[7:0] light_pwm`: Cường độ sáng đèn LED đường phố

### 3. Hoạt động / Logic mong muốn:
- Trời sáng (ldr_dark = 0): light_pwm = 0 (tắt đèn tiết kiệm điện).
- Trời tối không có người: light_pwm = 20% (sáng mờ dẫn đường).
- Trời tối có người/xe tiếp cận (radar_motion = 1): light_pwm = 100% (sáng cực đại trong 60 giây).

---

## Bài 87: Hệ Thống Cảnh Báo Rò Rỉ Khí Gas & Ngắt Van An Toàn (Gas Leak Detector with Auto Shut-Off)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset hệ thống
- `gas_sensor_trip`: Cảm biến nồng độ khí gas vượt ngưỡng nguy hiểm

### 2. Đầu ra (Outputs):
- `solenoid_valve_cut`: Đóng van điện từ cắt nguồn gas lập tức
- `exhaust_fan_safe`: Bật quạt thông gió phòng nổ
- `buzzer_gas`: Còi báo động rò rỉ khí gas

### 3. Hoạt động / Logic mong muốn:
- Khi gas_sensor_trip = 1: Tự động khóa van solenoid_valve_cut = 1, bật quạt exhaust_fan_safe và rú còi buzzer_gas liên tục cho đến khi người dùng reset mạch.

---

## Bài 88: Bộ Khóa Cửa Bằng Thẻ Từ RFID / Mã PIN (RFID/PIN Door Access Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `[31:0] rfid_uid`: Mã thẻ RFID quét được
- `rfid_card_present`: Cờ có thẻ đang quét
- `pin_authorized`: Mã PIN nhập đúng

### 2. Đầu ra (Outputs):
- `door_solenoid`: Mở chốt khóa cửa điện từ (mở trong 5 giây)
- `access_granted_led`: Đèn xanh báo quyền truy cập thành công
- `access_denied_led`: Đèn đỏ từ chối

### 3. Hoạt động / Logic mong muốn:
- So sánh rfid_uid với danh sách thẻ hợp lệ lưu sẵn.
- Nếu đúng thẻ hoặc pin_authorized = 1: mở door_solenoid = 1 và bật access_granted_led trong 5 giây rồi tự khóa lại.
- Nếu sai: chớp access_denied_led.

---

## Bài 89: Bộ Giám Sát Điện Áp Quá Áp & Thấp Áp Nguồn (Over/Under Voltage Supervisor)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp
- `rst`: Reset
- `[7:0] v_adc_in`: Giá trị điện áp lưới đo từ ADC (V_norm = 120)

### 2. Đầu ra (Outputs):
- `power_disconnect`: Cắt rơ-le nguồn bảo vệ thiết bị
- `under_v_err`: Cảnh báo sụt áp
- `over_v_err`: Cảnh báo quá áp sét lan truyền

### 3. Hoạt động / Logic mong muốn:
- Ngưỡng an toàn: 90 <= v_adc_in <= 140.
- Nếu v_adc_in < 90: bật under_v_err = 1 và power_disconnect = 1.
- Nếu v_adc_in > 140: bật over_v_err = 1 và power_disconnect = 1 ngay tức thì.

---

## Bài 90: Máy Cho Thú Cưng Ăn Tự Động Theo Lập Trình (Scheduled Pet Feeder Controller)

### 1. Đầu vào (Inputs):
- `clk_1hz`: Xung nhịp 1Hz
- `rst`: Reset
- `[15:0] feed_time_match`: Tín hiệu khớp thời gian cho ăn từ đồng hồ RTC
- `dispense_manual`: Nút bấm nhả thức ăn thủ công

### 2. Đầu ra (Outputs):
- `dispense_motor`: Kích động cơ xoay khay thức ăn đúng 1 vòng (3 giây)
- `food_empty_alert`: Đèn báo khay thức ăn đã hết

### 3. Hoạt động / Logic mong muốn:
- Khi tới giờ (feed_time_match = 1) hoặc có nút bấm dispense_manual: Bật dispense_motor trong đúng 3 giây rồi dừng.
- Nếu cảm biến phát hiện khay trống: chớp food_empty_alert.

---


# NHÓM 10: MẠCH HIỂN THỊ, ĐỒ HỌA & PHÂN HỆ VI XỬ LÝ SOC (DISPLAYS & SOC UNITS)

## Bài 91: Bộ Quét Ma Trận LED 8x8 Hiển Thị Ký Tự (8x8 LED Matrix Display Scanner)

### 1. Đầu vào (Inputs):
- `clk_scan`: Xung nhịp quét hàng 1kHz
- `rst`: Reset
- `[63:0] bitmap_char`: Ma trận điểm ảnh 64-bit của ký tự

### 2. Đầu ra (Outputs):
- `[7:0] row_scan`: Quét 8 hàng (active-low lần lượt)
- `[7:0] col_data`: Dữ liệu 8 cột tương ứng (active-high)

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm vòng 3-bit quét lần lượt từ hàng 0 đến hàng 7.
- Tại mỗi hàng: row_scan hạ mức 0 ở hàng đó, đồng thời trích xuất 8 bit tương ứng từ bitmap_char ra col_data.

---

## Bài 92: Bộ Quét Đa Kênh 4 LED 7 Đoạn Ghép Kênh Thời Gian (4-Digit Time-Multiplexed 7-Segment)

### 1. Đầu vào (Inputs):
- `clk_1khz`: Xung nhịp quét
- `rst`: Reset
- `[3:0] d3`: Số hàng nghìn
- `[3:0] d2`: Số hàng trăm
- `[3:0] d1`: Số hàng chục
- `[3:0] d0`: Số hàng đơn vị

### 2. Đầu ra (Outputs):
- `[3:0] digit_sel_n`: Chọn bật 1 trong 4 LED 7 đoạn (active-low)
- `[6:0] seg_out`: Mã 7 thanh hiển thị

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm quét 2-bit xoay vòng liên tục 4 trạng thái: 00 -> bật d0, 01 -> d1, 10 -> d2, 11 -> d3.
- Tần số quét 1kHz loại trừ hoàn toàn hiện tượng nhấp nháy mắt người (Persistence of Vision).

---

## Bài 93: Bộ Tạo Tín Hiệu Đồng Bộ Màn Hình VGA 640x480 (VGA 640x480 Timing Generator)

### 1. Đầu vào (Inputs):
- `clk_25mhz`: Xung nhịp điểm ảnh Pixel Clock 25.175MHz
- `rst`: Reset

### 2. Đầu ra (Outputs):
- `hsync`: Xung đồng bộ dòng ngang
- `vsync`: Xung đồng bộ khung dọc
- `[9:0] pixel_x`: Tọa độ điểm ảnh ngang (0-639)
- `[9:0] pixel_y`: Tọa độ điểm ảnh dọc (0-479)
- `video_on`: Cờ cho phép hiển thị màu trong vùng nhìn thấy

### 3. Hoạt động / Logic mong muốn:
- Bộ đếm dòng ngang H-Counter đếm tới 800 chu kỳ (Sync: 96, Back Porch: 48, Display: 640, Front Porch: 16).
- Bộ đếm dòng dọc V-Counter đếm tới 525 dòng.
- video_on = 1 khi pixel_x < 640 và pixel_y < 480.

---

## Bài 94: Bộ Phát Điệu Nhạc Chuông 8 Nốt Đồ Rê Mi (8-Note Music Melody Generator)

### 1. Đầu vào (Inputs):
- `clk_50mhz`: Xung nhịp hệ thống
- `rst`: Reset
- `play_btn`: Nút bấm phát nhạc

### 2. Đầu ra (Outputs):
- `speaker_pwm`: Tín hiệu băm xung lái loa phát các nốt nhạc
- `melody_busy`: Báo đang phát nhạc

### 3. Hoạt động / Logic mong muốn:
- Bảng ROM lưu tần số 8 nốt nhạc cơ bản: C4 (261Hz), D4 (294Hz), E4 (329Hz), F4 (349Hz), G4 (392Hz), A4 (440Hz), B4 (493Hz), C5 (523Hz).
- Khi play_btn = 1: Tự động đổi nốt mỗi 300ms rồi kết thúc hạ melody_busy = 0.

---

## Bài 95: Bộ Trọng Tài Bus Ưu Tiên 4 Master Round-Robin (4-Master Round-Robin Bus Arbiter)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp bus
- `rst`: Reset
- `[3:0] req_in`: Tín hiệu yêu cầu chiếm bus từ 4 Master (M0..M3)

### 2. Đầu ra (Outputs):
- `[3:0] grant_out`: Tín hiệu cấp quyền chiếm bus (chỉ duy nhất 1 bit One-Hot)
- `bus_busy`: Báo bus đang được sử dụng

### 3. Hoạt động / Logic mong muốn:
- Sử dụng thuật toán công bằng Round-Robin: Không một Master nào bị bỏ đói (Starvation).
- Sau khi Master được cấp quyền nhả bus, quyền ưu tiên kế tiếp tự động xoay chuyển sang Master tiếp theo.

---

## Bài 96: Bộ Điều Khiển Ngắt Ngoại Vi Ưu Tiên 4 Kênh (4-Channel Priority Interrupt Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp CPU
- `rst`: Reset
- `[3:0] irq_req`: 4 đường ngắt ngoại vi (IRQ3 có độ ưu tiên cao nhất)
- `cpu_ack`: Xung báo CPU đã chấp nhận xử lý ngắt

### 2. Đầu ra (Outputs):
- `irq_to_cpu`: Đường báo ngắt tổng hợp gửi tới CPU
- `[1:0] irq_vector`: Mã vector ngắt của nguồn có ưu tiên cao nhất

### 3. Hoạt động / Logic mong muốn:
- Lập tức nâng irq_to_cpu = 1 khi có bất kỳ IRQ nào tích cực.
- irq_vector trỏ tới ngắt có số hiệu cao nhất chưa được phục vụ. Khi cpu_ack = 1: xóa cờ ngắt tương ứng.

---

## Bài 97: Bộ Điều Khiển Truy Cập Bộ Nhớ Trực Tiếp DMA Kênh Đơn (Single-Channel DMA Controller)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp bus
- `rst`: Reset
- `dma_req`: Yêu cầu truyền từ thiết bị ngoại vi
- `bus_grant`: CPU cấp quyền làm chủ bus
- `[15:0] src_addr_init`: Địa chỉ nguồn ban đầu
- `[15:0] dst_addr_init`: Địa chỉ đích ban đầu
- `[7:0] block_length`: Số byte cần truyền

### 2. Đầu ra (Outputs):
- `dma_ack`: Xác nhận với ngoại vi
- `bus_req`: Xin CPU quyền chiếm bus
- `[15:0] mem_addr`: Địa chỉ phát lên bus
- `dma_done`: Cờ báo hoàn tất khối truyền

### 3. Hoạt động / Logic mong muốn:
- Khi có dma_req: DMA phát bus_req tới CPU.
- Khi nhận bus_grant = 1: DMA trực tiếp đọc từ địa chỉ nguồn và ghi sang địa chỉ đích không qua CPU, tự tăng con trỏ địa chỉ cho tới khi đủ block_length rồi trả bus.

---

## Bài 98: Bộ Giải Mã Vị Trí Trục Động Cơ Encoder Cầu Phương (Quadrature Rotary Encoder Decoder)

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp lấy mẫu
- `rst`: Reset vị trí
- `enc_a`: Kênh pha A của Encoder
- `enc_b`: Kênh pha B của Encoder

### 2. Đầu ra (Outputs):
- `[15:0] position_count`: Giá trị tọa độ vị trí góc quay (tăng/giảm theo chiều quay)
- `dir_flag`: Cờ báo chiều quay (1: Thuận chiều kim đồng hồ, 0: Ngược chiều)

### 3. Hoạt động / Logic mong muốn:
- Lấy mẫu 2 kênh A và B lệch pha 90 độ.
- Giải mã trạng thái: nếu A dẫn trước B -> quay thuận (tăng position_count); nếu B dẫn trước A -> quay ngược (giảm position_count).

---

## Bài 99: Bộ Đếm Thời Gian Thực RTC Giờ:Phút:Giây (Real-Time Clock Counter)

### 1. Đầu vào (Inputs):
- `clk_1hz`: Xung chuẩn 1Hz
- `rst`: Reset về 00:00:00
- `set_time_en`: Chế độ cài đặt giờ
- `[4:0] set_hours`: Giờ nạp vào (0-23)
- `[5:0] set_mins`: Phút nạp vào (0-59)
- `[5:0] set_secs`: Giây nạp vào (0-59)

### 2. Đầu ra (Outputs):
- `[4:0] hours`: Giờ hiện tại (0-23)
- `[5:0] minutes`: Phút hiện tại (0-59)
- `[5:0] seconds`: Giây hiện tại (0-59)

### 3. Hoạt động / Logic mong muốn:
- Khi set_time_en = 1: nạp trực tiếp giá trị cài đặt.
- Khi bình thường: seconds tăng mỗi giây từ 0->59; khi tràn thì tăng minutes từ 0->59; khi tràn phút tăng hours từ 0->23.

---

## Bài 100: Bộ Giải Mã Địa Chỉ Bộ Nhớ Cho Hệ Vi Xử Lý SoC (Memory Address Decoder)

### 1. Đầu vào (Inputs):
- `[15:0] cpu_addr`: Bus địa chỉ 16-bit từ vi xử lý (0x0000 đến 0xFFFF)
- `mem_read`: Lệnh đọc bộ nhớ
- `mem_write`: Lệnh ghi bộ nhớ

### 2. Đầu ra (Outputs):
- `cs_boot_rom`: Chọn chip ROM khởi động (vùng 0x0000 - 0x3FFF, 16KB)
- `cs_sram`: Chọn chip SRAM dữ liệu (vùng 0x4000 - 0xBFFF, 32KB)
- `cs_io_ports`: Chọn thanh ghi ngoại vi I/O (vùng 0xC000 - 0xFFFF, 16KB)

### 3. Hoạt động / Logic mong muốn:
- Mạch giải mã địa chỉ tổ hợp phân mảnh không gian bộ nhớ: 2 bit cao nhất của cpu_addr (A15, A14) định tuyến trực tiếp tới đúng linh kiện phần cứng tương ứng.

---

