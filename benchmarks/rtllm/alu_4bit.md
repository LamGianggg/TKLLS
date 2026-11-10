# Benchmark: RTLLM (HKUST)
## Module: alu_4bit
Thiết kế đơn vị số học và logic 4-bit (4-bit Multi-function Arithmetic Logic Unit - ALU).

### 1. Mô tả hoạt động
- Thực hiện các phép toán số học và logic trên 2 toán hạng 4-bit `a[3:0]` và `b[3:0]` dựa trên mã lệnh `opcode[2:0]`:
  - `3'b000`: Phép cộng `a + b` (có tính cờ nhớ carry)
  - `3'b001`: Phép trừ `a - b` (có tính cờ mượn/nhớ)
  - `3'b010`: Phép logic AND `a & b`
  - `3'b011`: Phép logic OR `a | b`
  - `3'b100`: Phép logic XOR `a ^ b`
  - `3'b101`: Phép logic NOT `~a`
  - `3'b110`: Dịch trái số học `a << 1`
  - `3'b111`: So sánh bằng `a == b` (1 nếu bằng, 0 nếu khác)
- Cờ `zero`: Tích cực mức cao (1) khi kết quả `alu_out == 4'b0000`.
- Cờ `carry`: Báo cờ nhớ khi có tràn số học trong phép cộng hoặc phép trừ.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset đồng bộ |
| `a` | Input | 4 bit | Toán hạng A |
| `b` | Input | 4 bit | Toán hạng B |
| `opcode` | Input | 3 bit | Mã lệnh phép toán ALU |
| `alu_out` | Output | 4 bit | Kết quả phép toán |
| `zero` | Output | 1 bit | Cờ báo kết quả bằng 0 |
| `carry` | Output | 1 bit | Cờ nhớ số học |
