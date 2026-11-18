# BÁO CÁO CÔNG VIỆC NHÓM 3: KỸ THUẬT VI MẠCH & BỘ PHÂN TÍCH AST (HARDWARE LINTER)

> **Dự án**: Spec2RTL & Prompt2Silicon - Đồ án 3 (CE118 - UIT / VJU)  
> **Giảng viên hướng dẫn**: TS. Nguyễn Văn Tình  
> **Thực hiện**: Nhóm 3 (Kỹ thuật Vi mạch & Kiểm soát Cú pháp AST)  
> **Phương pháp triển khai**: *Ponytail Senior Dev Mode* (Tối giản mã nguồn, Zero-dependency, 100% Assert-based Verification).

---

## 1. Nhiệm vụ & Vấn đề Cốt lõi (Core Problem)
1. **Chốt ẩn (Inferred Latches)**: Khối tổ hợp `always @(*)` thiếu nhánh `default:` trong `case` hoặc thiếu nhánh `else` trong `if`, khiến bộ tổng hợp phần cứng tự sinh Latch ngoài ý muốn, gây lãng phí tài nguyên và rủi ro timing hazard / glitch.
2. **Chân lơ lửng (Dangling Pins / Isolated Ports)**: Cổng `input` khai báo nhưng hoàn toàn bị cô lập (ví dụ điển hình: `btn_in` trong bài `button_debouncer` do thầy chỉ ra), hoặc cổng `output` không bao giờ được gán giá trị.
3. **Race Condition & Vi phạm RTL (Sequential vs Combinational Rules)**: Gán blocking `=` trong khối tuần tự `always @(posedge clk)` gây race condition giữa các Flip-Flop; gán non-blocking `<=` trong khối tổ hợp `always @(*)`.
4. **Đo đạc tài nguyên phần cứng (FPGA Synthesis Profiler)**: Tích hợp Quartus CLI (`quartus_map.exe`) và ước lượng tĩnh Logic Elements (LEs), Dedicated Registers (FFs), và I/O Pins.

---

## 2. Giải pháp Kỹ thuật (Ponytail Implementation)

### A. Bộ phân tích tĩnh AST không phụ thuộc thư viện nặng (`agent/verilog_linter.py`)
- **Thay vì** cài đặt PyVerilog (đòi hỏi build tool C++ Icarus/GCC phức tạp trên Windows dễ lỗi môi trường):
- **Áp dụng**: Bộ phân tích mẫu AST dựa trên Regex thuần Python (Zero external dependencies):
  - `extract_module_info`: Tách độc lập Header và Body, hỗ trợ cả 2 chuẩn Verilog ANSI (2001) và Legacy (1995).
  - `check_dangling_pins`: Đối soát danh sách chân vào/ra với toàn bộ biểu thức logic thực tế.
  - `check_inferred_latches_and_races`: Phát hiện `case` thiếu `default`, `if` thiếu `else` không có gán mặc định, và cảnh báo gán `=` trong `posedge clk`.
  - `format_linter_report`: Hiển thị bảng tổng kết thẻ phần cứng chuyên nghiệp.

### B. Tích hợp trực tiếp vào Pipeline (`agent/run_spec2rtl.py`)
- Tại **[Bước 2.5]**, ngay trước khi nạp vào vòng lặp phản hồi ModelSim và Quartus II, file RTL chính được quét qua AST Linter để cảnh báo lỗi vi mạch ngay lập tức.

### C. Đo đạc tài nguyên FPGA (`agent/synthesis_profiler.py`)
- Trích xuất tự động từ file báo cáo `.map.summary` của Quartus II (`quartus_map.exe`), dự phòng bộ ước lượng tĩnh cấu trúc (Static Structural Estimation) khi chạy môi trường không có Quartus CLI.

---

## 3. Kết quả Kiểm thử (100% Passed)

Chạy bộ kiểm thử tự động: `python training/test_group3_linter.py`

| Test Case | Mô tả kiểm thử | Kết quả | Ghi chú |
| :--- | :--- | :---: | :--- |
| **Test 1** | Mạch chuẩn `sync_counter` (4-bit counter) | **PASS** | 0 Latch, 0 Dangling Pin, 0 Race Condition |
| **Test 2** | Mạch lỗi `button_debouncer` (`btn_in` bị cô lập) | **PASS** | Bắt chính xác `DANGLING_INPUT: btn_in` & `UNASSIGNED_OUTPUT: btn_pressed_pulse` |
| **Test 3** | Khối tổ hợp `alu_comb` thiếu nhánh `default` & `else` | **PASS** | Bắt chính xác `INFERRED_LATCH: case` & `INFERRED_LATCH: if` |
| **Test 4** | Khối tuần tự `bad_pipeline` dùng gán blocking `=` | **PASS** | Bắt chính xác `BLOCKING_IN_SEQUENTIAL` |
| **Test 5** | Đo đạc tài nguyên phần cứng `synthesis_profiler` | **PASS** | Đo đạc thành công LEs, Registers, Pins cho FPGA Cyclone II |

---

## 4. Kiểm tra trên File Thực tế trong Kho
- Quét file thực tế [quartus/button_debouncer/button_debouncer.v](file:///D:/altera/13.0sp1/BTVN/Do_An_3/quartus/button_debouncer/button_debouncer.v):
  ```
  +----------------------------------------------------------------------------+
  |           BÁO CÁO PHÂN TÍCH TĨNH PHẦN CỨNG & AST (HARDWARE LINTER)         |
  +----------------------------------------------------------------------------+
  | Tên thiết kế               : button_debouncer.v                            |
  | Trạng thái kiểm tra        : WARNING / DETECTED ISSUES                     |
  | Chốt ẩn (Inferred Latches) : 0 lỗi                                         |
  | Chân lơ lửng (Dangling)    : 1 chân                                        |
  | Vi phạm gán / Race Cond    : 0 điểm                                        |
  | Lỗi cấu trúc cú pháp       : 0 lỗi                                         |
  +----------------------------------------------------------------------------+
  | CHI TIẾT CẢNH BÁO PHẦN CỨNG:
  |  * DANGLING_INPUT: Cổng vào 'btn_in' ở module 'button_debouncer' không được
  +----------------------------------------------------------------------------+
  ```
  => Bắt chính xác 100% lỗi thực tế mà thầy TS. Nguyễn Văn Tình chỉ ra!
