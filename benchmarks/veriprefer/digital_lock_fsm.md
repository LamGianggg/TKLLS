# Benchmark: VeriPrefer (CityU HK - arXiv:2504.15804)
## Module: digital_lock_fsm
Thiết kế khóa số điện tử thông minh có giới hạn số lần nhập sai (Digital Security Combination Lock).

### 1. Mô tả hoạt động
- Nhận mật khẩu 3 chữ số lần lượt (ví dụ: 1 - 2 - 3) qua cổng `key_code[3:0]` và nút xác nhận `enter_btn`.
- Nếu nhập đúng cả 3 chữ số liên tiếp, tín hiệu `unlocked` sẽ bật lên mức cao (1).
- Nếu nhập sai bất kỳ số nào, số lần thử còn lại `attempts_left` sẽ bị trừ 1.
- Nếu nhập sai quá 3 lần, còi báo động `alarm` sẽ kích hoạt lên mức cao (1) và khóa hoàn toàn hệ thống.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset hệ thống |
| `key_code` | Input | 4 bit | Mã phím số nhập vào (0 - 9) |
| `enter_btn` | Input | 1 bit | Nút nhấn xác nhận nhập số |
| `unlocked` | Output | 1 bit | Trạng thái mở khóa thành công |
| `alarm` | Output | 1 bit | Còi báo động khi nhập sai quá 3 lần |
| `attempts_left` | Output | 2 bit | Số lần thử còn lại (ban đầu là 3) |
| `state_out` | Output | 3 bit | Giám sát trạng thái FSM |
