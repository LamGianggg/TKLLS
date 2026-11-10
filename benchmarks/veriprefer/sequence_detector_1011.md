# Benchmark: VeriPrefer (CityU HK - arXiv:2504.15804)
## Module: sequence_detector_1011
Thiết kế máy trạng thái hữu hạn FSM phát hiện chuỗi bit '1011' (Non-overlapping Sequence Detector).

### 1. Mô tả hoạt động
- Nhận luồng dữ liệu nối tiếp từng bit tại đầu vào `din` đồng bộ theo xung clock `clk`.
- Khi 4 bit liên tiếp xuất hiện đúng mẫu '1-0-1-1', tín hiệu đầu ra `detected` sẽ bật lên mức cao (1) trong đúng 1 chu kỳ clock.
- Hỗ trợ reset đồng bộ `rst` để đưa máy trạng thái về trạng thái ban đầu `S_IDLE`.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset đồng bộ |
| `din` | Input | 1 bit | Luồng bit dữ liệu nối tiếp đầu vào |
| `detected` | Output | 1 bit | Báo hiệu phát hiện đúng chuỗi 1011 |
| `state_out` | Output | 3 bit | Giám sát trạng thái hiện tại của FSM |
