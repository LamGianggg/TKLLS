# Benchmark: VerilogEval (NVIDIA Research)
## Module: counter_16bit
Thiết kế bộ đếm nhị phân đồng bộ 16 bit (16-bit Synchronous Binary Counter).

### 1. Mô tả hoạt động
- Hoạt động theo xung clock cạnh lên `clk`, có tín hiệu reset đồng bộ `rst`.
- Có tín hiệu cho phép đếm `enable`. Khi `enable = 1`, giá trị đếm tăng 1 sau mỗi chu kỳ clock. Khi `enable = 0`, giá trị đếm giữ nguyên.
- Cờ báo tràn `tc` (Terminal Count) tích cực mức cao (1) khi bộ đếm đạt giá trị cực đại 16'hFFFF và `enable = 1`.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Reset đồng bộ (tích cực mức cao) |
| `enable` | Input | 1 bit | Tín hiệu cho phép đếm |
| `count` | Output | 16 bit | Giá trị đếm hiện tại |
| `tc` | Output | 1 bit | Cờ báo giá trị cực đại (Terminal Count) |
