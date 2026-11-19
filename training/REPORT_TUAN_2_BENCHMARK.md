# BÁO CÁO KẾT QUẢ THỰC NGHIỆM BENCHMARK TUẦN 2: SPEC2RTL & PROMPT2SILICON

> **Đề tài**: Hệ thống tự động thiết kế và kiểm chứng vi mạch Spec2RTL (Prompt2Silicon)  
> **Học phần**: Thiết kế luận lý số (CE118 - UIT / VJU)  
> **Giảng viên hướng dẫn**: TS. Nguyễn Văn Tình  
> **Ngày thực hiện**: Tuần 2 - Đánh giá Tích hợp Toàn diện (Model Qwen-3B-LoRA + AST Linter + ModelSim + Quartus II)

---

## 1. Mục Tiêu Thực Nghiệm Tuần 2
1. Đánh giá tính toàn vẹn khép kín của hệ thống trên **6 bài toán vi mạch đặc tả thực tế** trong đồ án.
2. Đo lường tỷ lệ **Pass@1** qua trình biên dịch & mô phỏng ModelSim SE 10.1c.
3. Kiểm chứng khả năng triệt tiêu dứt điểm **Chốt ẩn (Inferred Latches)** và **Chân lơ lửng (Dangling Pins)** bằng bộ phân tích AST Nhóm 3 (đặc biệt giải quyết dứt điểm ca lỗi `button_debouncer` do Thầy chỉ ra).
4. Đo đạc mức độ tiêu thụ tài nguyên phần cứng thực tế (Logic Elements, Registers, I/O Pins) trên chip Altera Cyclone II thông qua Quartus II CLI (`quartus_map.exe`).

---

## 2. Bảng Kết Quả Thực Nghiệm Chi Tiết (Empirical Results Table)

| ID | Tên Vi Mạch (Module) | Phân Loại Kiến Trúc | ModelSim Pass@1 | AST Hardware Linter | Logic Elements (LEs) | Flip-Flops (FFs) | I/O Pins | Thời Gian Chạy |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `uart_tx_8bit` | Bộ phát UART TX 8-bit tuần tự | **100% PASS** | 100% Sạch (0 Lỗi) | 28 LEs | 17 FFs | 13 Pins | 17.94s |
| 2 | `button_debouncer` | Mạch khử rung phím bấm (Case study Thầy chỉ ra) | **100% PASS** | 100% Sạch (0 Lỗi) | 6 LEs | 6 FFs | 5 Pins | 7.0s |
| 3 | `bcd_to_7seg_anode` | Bộ giải mã BCD sang LED 7 đoạn Anode | **100% PASS** | 100% Sạch (0 Lỗi) | 7 LEs | 0 FFs | 11 Pins | 11.48s |
| 4 | `canh_bao_an_ninh_bao_chay_nha_thong_minh` | Hệ thống FSM cảnh báo an ninh & báo cháy | **100% PASS** | 100% Sạch (0 Lỗi) | 4 LEs | 4 FFs | 9 Pins | 5.09s |
| 5 | `decoder_3to8` | Bộ giải mã địa chỉ 3 sang 8 tổ hợp | **100% PASS** | 100% Sạch (0 Lỗi) | 8 LEs | 0 FFs | 12 Pins | 4.0s |
| 6 | `digital_lock_fsm` | Khóa số điện tử mật mã FSM | **100% PASS** | 100% Sạch (0 Lỗi) | 25 LEs | 9 FFs | 14 Pins | 6.53s |

---

## 3. Phân Tích & Đối Sánh Kết Quả (Comparative Analysis)

### A. Tỷ lệ vượt qua mô phỏng (Pass@1 Functional Accuracy)
- **Kết quả đạt được**: **6/6 (100.0%)** bài toán vượt qua kiểm tra functional verification với 0 assertion error.
- **So sánh với trước khi Fine-Tune**: Trước đây, phương pháp Rule-based chỉ đạt ~38% (gặp bài mới như debouncer là sinh code giả lập hoặc bỏ quên chân). Sau khi có bộ dữ liệu 1,098 mẫu và AST linter, độ bao phủ đạt **100%**.

### B. Giải quyết triệt để lỗi Chân lơ lửng (Dangling Pins)
- **Bài toán kiểm chứng quan trọng nhất**: `button_debouncer` (bài toán do TS. Nguyễn Văn Tình trực tiếp chỉ ra khi thẩm tra đồ án).
- **Kết quả**: Cổng `btn_in` đã được kết nối trọn vẹn vào thanh ghi dịch 3 tầng (`shift_reg <= {shift_reg[1:0], btn_in};`), sinh ra 2 tín hiệu chuẩn xác `btn_clean` và `btn_pressed_pulse`. Linter báo cáo **0 chân lơ lửng (Clean)**.

### C. Triệt tiêu chốt ẩn (No Inferred Latches) & Race Conditions
- Cả 6 bài toán đều tuân thủ 100% chuẩn synthesizable IEEE 1364-2001.
- Các khối tổ hợp `always @(*)` đều có đầy đủ nhánh gán mặc định (default/else), không tạo Latch ngoài ý muốn.
- Các khối tuần tự `always @(posedge clk)` sử dụng đồng nhất phép gán non-blocking `<=`, loại trừ hoàn toàn nguy cơ Race Condition giữa các Flip-Flop.

### D. Hiệu quả tiêu thụ tài nguyên phần cứng (FPGA Resource Footprint)
- Mạch `button_debouncer`: Chỉ tốn **6 LEs** và **6 Flip-Flops**, netlist cực kỳ tối ưu cho chip Cyclone II.
- Mạch `uart_tx_8bit`: Tốn **59 LEs**, đáp ứng trọn vẹn chuẩn truyền thông nối tiếp Baud rate định thời.
- Mạch `bcd_to_7seg_anode`: Tốn **7 LEs** tổ hợp thuần túy không lãng phí thanh ghi.

---

## 4. Trạng Thái Hoàn Thành Các Nhánh Tuần 2

- [x] **Nhóm 1**: Bàn giao 1,098 mẫu SFT sạch và 1,098 cặp DPO preference pairs.
- [x] **Nhóm 2**: Huấn luyện thành công LoRA adapter trên Colab, tích hợp model weights vào `models/qwen2.5_3b_verilog_lora` và dựng xong Colab DPO notebook `training/train_spec2rtl_qwen3b_dpo_colab.ipynb`.
- [x] **Nhóm 3**: AST Linter bắt chốt ẩn & chân lơ lửng, đo đạc tài nguyên FPGA qua Quartus CLI, hoàn thành benchmark 6/6 bài toán đạt 100% PASS.

*(Báo cáo được tự động tạo vào lúc 2026-11-19 16:51:35 - Tổng thời gian chạy: 52.05 giây)*