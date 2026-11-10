# Benchmark: VerilogEval (NVIDIA Research)
## Module: gray_counter_4bit
Thiết kế bộ đếm mã Gray 4 bit (4-bit Gray Code Counter).

### 1. Mô tả hoạt động
- Bộ đếm tuần tự chuyển đổi qua các trạng thái sao cho giữa 2 chu kỳ clock liên tiếp chỉ có duy nhất 1 bit thay đổi trạng thái (đặc tính mã Gray chống xung nhiễu glitch).
- Khi reset `rst = 1`, bộ đếm được đưa về giá trị `gray_out = 4'b0000`.
- Khi `enable = 1`, bộ đếm tăng dần chu kỳ mã Gray 16 trạng thái.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset đồng bộ |
| `enable` | Input | 1 bit | Tín hiệu cho phép đếm |
| `gray_out` | Output | 4 bit | Giá trị đếm mã Gray 4-bit |
