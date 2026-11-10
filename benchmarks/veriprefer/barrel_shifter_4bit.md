# Benchmark: VeriPrefer (CityU HK - arXiv:2504.15804)
## Module: barrel_shifter_4bit
Thiết kế bộ dịch vòng xoay tròn 4 bit (4-bit Barrel Shifter / Rotator).

### 1. Mô tả hoạt động
- Mạch tổ hợp dịch vòng bit dữ liệu đầu vào `data_in[3:0]` theo số bước dịch `shift_amt[1:0]` (từ 0 đến 3 vị trí).
- Tín hiệu `dir`:
  - `dir = 0`: Dịch vòng sang trái (Rotate Left).
  - `dir = 1`: Dịch vòng sang phải (Rotate Right).
- Hoạt động tức thời qua mạng mux tổ hợp tốc độ cao.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset đồng bộ |
| `data_in` | Input | 4 bit | Dữ liệu đầu vào 4-bit |
| `shift_amt` | Input | 2 bit | Số vị trí dịch (0, 1, 2, 3) |
| `dir` | Input | 1 bit | Hướng dịch (0: Trái, 1: Phải) |
| `data_out` | Output | 4 bit | Dữ liệu sau khi dịch vòng |
