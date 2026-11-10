# Prompt Đặc Tả: Bộ Điều Khiển Đèn Giao Thông Ngã Tư (Traffic Light Controller)

## Yêu cầu thiết kế:
Thiết kế một bộ điều khiển đèn giao thông cho ngã tư gồm 2 trục đường: Đường Chính (Main Street) và Đường Phụ (Side Street).

### 1. Đầu vào (Inputs):
- `clk`: Xung nhịp hệ thống.
- `clr`: Tín hiệu reset tích cực mức cao (active-high).
- `car_sensor`: Cảm biến phát hiện có xe ở đường phụ (1 = có xe, 0 = không có xe).

### 2. Đầu ra (Outputs):
- `light_main [2:0]`: Đèn đường chính theo mã 3-bit {Red, Yellow, Green} (Ví dụ: 3'b001 = Xanh, 3'b010 = Vàng, 3'b100 = Đỏ).
- `light_side [2:0]`: Đèn đường phụ theo mã 3-bit {Red, Yellow, Green}.

### 3. Chu trình trạng thái (FSM Cycle):
1. **Trạng thái S0 (Main GREEN, Side RED):** `light_main = 3'b001`, `light_side = 3'b100`. Duy trì ít nhất 10 chu kỳ. Sau 10 chu kỳ, nếu có xe ở đường phụ (`car_sensor == 1`), chuyển sang S1.
2. **Trạng thái S1 (Main YELLOW, Side RED):** `light_main = 3'b010`, `light_side = 3'b100`. Duy trì 3 chu kỳ, sau đó chuyển sang S2.
3. **Trạng thái S2 (Main RED, Side GREEN):** `light_main = 3'b100`, `light_side = 3'b001`. Duy trì 10 chu kỳ, sau đó chuyển sang S3.
4. **Trạng thái S3 (Main RED, Side YELLOW):** `light_main = 3'b100`, `light_side = 3'b010`. Duy trì 3 chu kỳ, sau đó quay trở lại S0.

Khi có tín hiệu `clr == 1`, mạch lập tức reset về trạng thái S0.
