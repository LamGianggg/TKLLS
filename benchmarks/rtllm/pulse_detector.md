# Benchmark: RTLLM (HKUST)
## Module: pulse_detector
Thiết kế mạch phát hiện cạnh xung và phát xung đơn chu kỳ (Rising Edge Pulse Detector).

### 1. Mô tả hoạt động
- Theo dõi tín hiệu đầu vào không đồng bộ `din`.
- Khi phát hiện một bước chuyển từ mức logic thấp (0) lên mức logic cao (1) ở đầu vào (cạnh lên), mạch tạo ra một xung mức cao rộng đúng 1 chu kỳ clock tại đầu ra `pulse_out`.
- Sử dụng 2 tầng Flip-Flop để khử hiện tượng bất ổn định (metastability) và phát hiện cạnh xung chính xác.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset đồng bộ |
| `din` | Input | 1 bit | Tín hiệu logic đầu vào cần phát hiện cạnh |
| `pulse_out` | Output | 1 bit | Xung đơn chu kỳ clock đầu ra |
