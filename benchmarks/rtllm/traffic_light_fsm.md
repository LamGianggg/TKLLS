# Benchmark: RTLLM (HKUST)
## Module: traffic_light_fsm
Thiết kế bộ điều khiển đèn giao thông ngã tư thông minh (Intersection Traffic Light Controller with Sensor).

### 1. Mô tả hoạt động
- Điều khiển 2 luồng giao thông: Tuyến đường chính (Main street) và Tuyến đường phụ (Side street).
- Mỗi tuyến có 3 đèn: Đỏ (Red), Vàng (Yellow), Xanh (Green) được mã hóa bằng 2 bit: 2'b00 (Đỏ), 2'b01 (Vàng), 2'b10 (Xanh).
- Có cảm biến xe đường phụ `car_sensor`: Nếu đường chính đang xanh và có xe đường phụ tiếp cận, đèn chính sẽ chuyển sang vàng rồi nhường quyền ưu tiên cho đường phụ xanh.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset hệ thống |
| `car_sensor` | Input | 1 bit | Cảm biến phát hiện phương tiện đường phụ |
| `light_main` | Output | 2 bit | Trạng thái đèn đường chính (00:Red, 01:Yellow, 10:Green) |
| `light_side` | Output | 2 bit | Trạng thái đèn đường phụ (00:Red, 01:Yellow, 10:Green) |
