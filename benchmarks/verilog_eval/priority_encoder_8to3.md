# Benchmark: VerilogEval (NVIDIA Research)
## Module: priority_encoder_8to3
Thiết kế bộ mã hóa ưu tiên 8 sang 3 (8-to-3 Priority Encoder).

### 1. Mô tả hoạt động
- Đầu vào gồm 8 đường dữ liệu `d_in[7:0]`, bit trọng số cao nhất (bit 7) có mức ưu tiên cao nhất.
- Đầu ra mã hóa `binary_out[2:0]` biểu diễn vị trí của bit đầu vào tích cực (1) có mức ưu tiên cao nhất.
- Tín hiệu `valid` tích cực mức cao (1) khi có ít nhất một bit đầu vào bằng 1. Khi toàn bộ đầu vào bằng 0, `valid = 0` và `binary_out = 3'b000`.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset |
| `d_in` | Input | 8 bit | 8 đường dữ liệu yêu cầu đầu vào |
| `binary_out` | Output | 3 bit | Mã nhị phân đầu ra (0-7) |
| `valid` | Output | 1 bit | Báo hiệu có dữ liệu hợp lệ |
