# Benchmark: RTLLM (HKUST)
## Module: fifo_syn
Thiết kế bộ nhớ đệm hàng đợi đồng bộ (Synchronous FIFO Buffer 8x8).

### 1. Mô tả hoạt động
- Bộ nhớ FIFO độ sâu 8 ô nhớ, mỗi ô 8-bit dữ liệu, hoạt động theo xung clock `clk` và reset `rst`.
- Ghi dữ liệu: Khi `wr_en = 1` và bộ nhớ chưa đầy (`full = 0`), dữ liệu `data_in[7:0]` được ghi vào ô nhớ tại con trỏ ghi `wr_ptr`.
- Đọc dữ liệu: Khi `rd_en = 1` và bộ nhớ không rỗng (`empty = 0`), dữ liệu được đọc ra tại `data_out[7:0]` từ ô nhớ tại con trỏ đọc `rd_ptr`.
- Tín hiệu `full = 1` khi số phần tử đạt 8. Tín hiệu `empty = 1` khi số phần tử trong bộ nhớ bằng 0.

### 2. Bảng cổng kết nối (Port List)
| Tên cổng | Hướng | Độ rộng | Mô tả |
| :--- | :--- | :--- | :--- |
| `clk` | Input | 1 bit | Xung clock hệ thống |
| `rst` | Input | 1 bit | Tín hiệu reset đồng bộ |
| `wr_en` | Input | 1 bit | Tín hiệu cho phép ghi |
| `rd_en` | Input | 1 bit | Tín hiệu cho phép đọc |
| `data_in` | Input | 8 bit | Dữ liệu đầu vào cần ghi |
| `data_out` | Output | 8 bit | Dữ liệu đọc ra từ FIFO |
| `full` | Output | 1 bit | Cờ báo FIFO đã đầy |
| `empty` | Output | 1 bit | Cờ báo FIFO đang rỗng |
