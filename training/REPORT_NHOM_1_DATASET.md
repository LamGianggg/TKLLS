# BÁO CÁO NGHIỆM THU DỮ LIỆU & CHƯNG CẤT TRI THỨC AI (NHÓM 1)
**Học phần**: Thiết kế luận lý số (CE118 - UIT / VJU)  
**Dự án**: Spec2RTL & Prompt2Silicon (Teacher-Student Distillation + ModelSim Truth Oracle)  
**Ngày cập nhật**: 27/11/2026 16:54  

---

## 1. Quy Trình Chưng Cất Tri Thức Thực Tế (Teacher $\rightarrow$ Truth Oracle $\rightarrow$ Student)
- **Teacher Model**: Google Gemini (`gemini-3.5-flash-lite,gemini-3-flash-preview,gemini-3.1-flash-lite,gemini-3.5-flash`) sinh chuỗi suy luận thiết kế phần cứng đặc thù (**Teacher CoT**) kèm mã Verilog IEEE 1364-2001.
- **Bộ lọc Chân lý (Truth Oracle)**:
  1. `SpecAnalyzer`: Đối soát khớp tên module và 100% danh sách cổng I/O từ đặc tả.
  2. `VerilogLinter` (`agent/verilog_linter.py`): 0 chốt ẩn (`Inferred Latch`), 0 chân lơ lửng (`Dangling Pin`), 0 lỗi gán blocking tuần tự.
  3. `ModelSim vlog.exe` (kèm tùy chọn `vsim.exe`): Biên dịch/mô phỏng thực tế không lỗi (`Errors: 0`).
- **Tập 100% Thuần Gemini Teacher CoT (`training/dataset_teacher_distilled.json`)**: **1637/1697 (96.5%)** mẫu vượt qua Truth Oracle (25 họ vi mạch, gồm đề CE118 + VerilogDB `Rohan-code/Verilog_DB_read`).
- **Tập SFT hợp nhất (`training/dataset_clean_verified.json`)**: **2724 mẫu sạch** (gồm **1637** mẫu CoT thật từ Gemini Teacher + **1087** mẫu đã thẩm định ModelSim từ kho gốc).

---

## 2. Phân Bố Nguồn Tập Thuần Teacher (`dataset_teacher_distilled.json`)
| Nguồn Teacher | Số lượng mẫu | Ghi chú |
| :--- | :---: | :--- |
| Google Gemini (gemini-3.1-flash-lite) Distillation | **790** | 100% CoT thật + Pass Truth Oracle |
| Google Gemini (gemini-3.5-flash-lite) Distillation | **786** | 100% CoT thật + Pass Truth Oracle |
| Google Gemini (gemini-3-flash-preview) Distillation | **50** | 100% CoT thật + Pass Truth Oracle |
| Google Gemini (gemini-2.5-flash) Distillation | **11** | 100% CoT thật + Pass Truth Oracle |

## 3. Phân Bố Nguồn Dữ Liệu SFT Hợp Nhất (`dataset_clean_verified.json`)
| Nguồn dữ liệu | Số lượng mẫu đạt chuẩn | Ghi chú |
| :--- | :---: | :--- |
| Google Gemini (gemini-3.1-flash-lite) Distillation | **790** | Pass 100% ModelSim & AST Linter |
| Google Gemini (gemini-3.5-flash-lite) Distillation | **786** | Pass 100% ModelSim & AST Linter |
| Synthesized CE118 Augmentation Suite | **786** | Pass 100% ModelSim & AST Linter |
| NVIDIA VerilogEval | **94** | Pass 100% ModelSim & AST Linter |
| HuggingFace Verilog-Instruct-60k | **87** | Pass 100% ModelSim & AST Linter |
| CityU HK VeriPrefer Benchmark (arXiv:2504.15804) | **75** | Pass 100% ModelSim & AST Linter |
| Google Gemini (gemini-3-flash-preview) Distillation | **50** | Pass 100% ModelSim & AST Linter |
| HKUST RTLLM | **43** | Pass 100% ModelSim & AST Linter |
| Google Gemini (gemini-2.5-flash) Distillation | **11** | Pass 100% ModelSim & AST Linter |
| Spec2RTL Verified Library | **1** | Pass 100% ModelSim & AST Linter |
| Spec2RTL Project Benchmarks | **1** | Pass 100% ModelSim & AST Linter |

## 4. Phân Bố Theo Họ Vi Mạch (Tập Thuần Teacher)
| Họ vi mạch | Số lượng mẫu | Tỷ lệ (%) |
| :--- | :---: | :---: |
| Combinational Logic Designs | **585** | 35.7% |
| Basic Digital Building Blocks | **487** | 29.7% |
| Sequential Logic Designs | **219** | 13.4% |
| Memory Components | **67** | 4.1% |
| Other | **39** | 2.4% |
| Custom Accelerators and IP Blocks | **39** | 2.4% |
| Security and Crypto Blocks | **36** | 2.2% |
| Clock and Power Management Units | **19** | 1.2% |
| SoC Integration Components | **16** | 1.0% |
| Communication Interfaces | **11** | 0.7% |
| Counter & Timer | **10** | 0.6% |
| Arithmetic & ALU | **10** | 0.6% |
| Register & Buffer | **10** | 0.6% |
| Codec & Multiplexer | **10** | 0.6% |
| FSM & Sequence Detector | **10** | 0.6% |
| Signal Conditioning & PWM | **10** | 0.6% |
| System Control & Display | **10** | 0.6% |
| Benchmark | **10** | 0.6% |
| Communication & Serial | **9** | 0.5% |
| Advanced RTL & Clocking | **9** | 0.5% |
| Memory & FIFO | **8** | 0.5% |
| Project Spec | **6** | 0.4% |
| Peripheral Interfaces | **5** | 0.3% |
| Processor and Core Subsystems | **1** | 0.1% |
| Verification-Only Designs | **1** | 0.1% |