# Benchmark: VerilogEval (NVIDIA Research)
## Module: shift_reg_universal
Thiết kế thanh ghi dịch vạn năng 4 bit (4-bit Universal Shift Register).

### 1. Mô tả hoạt động
- Hỗ trợ 4 chế độ hoạt động được lựa chọn bằng tín hiệu `mode[1:0]`:
  - `2'b00`: Giữ nguyên giá trị (Hold).
  - `2'b01`: Dịch trái 1 bit (Shift Left), bit `sin_left` được đưa vào vị trí LSB.
  - `2'b10`: Dịch phải 1 bit (Shift Right), bit `sin_right` được đưa vào vị trí MSB.
  - `2'b11`: Nạp song song (Parallel Load) dữ liệu từ `d_in[3:0]`.
- Đồng bộ theo cạnh lên của clock `clk`, reset `rst` đưa đầu ra về 0.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset |
| `mode` | Input | 2 bit | Lựa chọn chế độ (Hold/Left/Right/Load) |
| `sin_left` | Input | 1 bit | Dữ liệu nối tiếp dịch trái |
| `sin_right` | Input | 1 bit | Dữ liệu nối tiếp dịch phải |
| `d_in` | Input | 4 bit | Dữ liệu nạp song song |
| `q_out` | Output | 4 bit | Đầu ra song song |
