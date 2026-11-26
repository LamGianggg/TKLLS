# BÁO CÁO NGHIỆM THU DỮ LIỆU & CHƯNG CẤT TRI THỨC AI (NHÓM 1)
**Học phần**: Thiết kế luận lý số (CE118 - UIT / VJU)  
**Dự án**: Spec2RTL & Prompt2Silicon (Teacher-Student Distillation + ModelSim Truth Oracle)  
**Ngày cập nhật**: 26/11/2026 09:00  

---

## 1. Quy Trình Chưng Cất Tri Thức Thực Tế (Teacher $\rightarrow$ Truth Oracle $\rightarrow$ Student)
- **Teacher Model**: Google Gemini (`gemini-3.1-flash-lite,gemini-3-flash-preview`) sinh chuỗi suy luận thiết kế phần cứng đặc thù (**Teacher CoT**) kèm mã Verilog IEEE 1364-2001.
- **Bộ lọc Chân lý (3 tầng kiểm chứng)**:
  1. `SpecAnalyzer`: Đối soát khớp tên module và 100% danh sách cổng I/O từ đặc tả.
  2. `VerilogLinter` (`agent/verilog_linter.py`): 0 chốt ẩn (`Inferred Latch`), 0 chân lơ lửng (`Dangling Pin`), 0 lỗi gán blocking tuần tự.
  3. `ModelSim vlog.exe`: Biên dịch thực tế không lỗi (`Errors: 0`).
- **Kết quả Chưng cất từ `gemini-3.1-flash-lite,gemini-3-flash-preview`**: **104/108 (96.3%)** mẫu vượt qua toàn bộ 3 tầng kiểm chứng (`training/dataset_teacher_distilled.json`).
- **Tập SFT hợp nhất cuối cùng (`training/dataset_clean_verified.json`)**: **1191 mẫu sạch** (gồm **104** mẫu CoT thật từ Gemini Teacher + **1087** mẫu đã thẩm định ModelSim từ kho gốc).

---

## 2. Phân Bố Nguồn Dữ Liệu Sạch Hiện Tại
| Nguồn dữ liệu | Số lượng mẫu đạt chuẩn | Ghi chú |
| :--- | :---: | :--- |
| Synthesized CE118 Augmentation Suite | **786** | Pass 100% ModelSim & AST Linter |
| NVIDIA VerilogEval | **94** | Pass 100% ModelSim & AST Linter |
| Google Gemini (gemini-3.1-flash-lite) Distillation | **93** | Pass 100% ModelSim & AST Linter |
| HuggingFace Verilog-Instruct-60k | **87** | Pass 100% ModelSim & AST Linter |
| CityU HK VeriPrefer Benchmark (arXiv:2504.15804) | **75** | Pass 100% ModelSim & AST Linter |
| HKUST RTLLM | **43** | Pass 100% ModelSim & AST Linter |
| Google Gemini (gemini-3.1-flash-lite,gemini-3-flash-preview) Distillation | **11** | Pass 100% ModelSim & AST Linter |
| Spec2RTL Verified Library | **1** | Pass 100% ModelSim & AST Linter |
| Spec2RTL Project Benchmarks | **1** | Pass 100% ModelSim & AST Linter |

## 3. Phân Bố Theo Họ Vi Mạch
| Họ vi mạch | Số lượng mẫu | Tỷ lệ (%) |
| :--- | :---: | :---: |
| Arithmetic | **301** | 25.3% |
| Counter | **128** | 10.7% |
| Miscellaneous | **85** | 7.1% |
| Logic Gates | **84** | 7.1% |
| Clock & Timing | **70** | 5.9% |
| Shift Register | **62** | 5.2% |
| Memory / Storage | **58** | 4.9% |
| FSM | **45** | 3.8% |
| Advanced RTL / RTLLM2 | **44** | 3.7% |
| Multiplexer | **36** | 3.0% |
| Code Converter | **34** | 2.9% |
| Digital Logic | **29** | 2.4% |
| Signal Conditioning | **25** | 2.1% |
| Control / FSM | **20** | 1.7% |
| Memory / FIFO | **20** | 1.7% |
| Demultiplexer | **15** | 1.3% |
| Counter & Timer | **10** | 0.8% |
| Arithmetic & ALU | **10** | 0.8% |
| Register & Buffer | **10** | 0.8% |
| Codec & Multiplexer | **10** | 0.8% |
| FSM & Sequence Detector | **10** | 0.8% |
| Signal Conditioning & PWM | **10** | 0.8% |
| System Control & Display | **10** | 0.8% |
| Communication & Serial | **9** | 0.8% |
| Advanced RTL & Clocking | **9** | 0.8% |
| PWM | **9** | 0.8% |
| Memory & FIFO | **8** | 0.7% |
| Decoder | **8** | 0.7% |
| Benchmark | **6** | 0.5% |
| Communication / Serial | **5** | 0.4% |
| Interconnect | **4** | 0.3% |
| Encoder | **3** | 0.3% |
| Project Spec | **2** | 0.2% |
| SoC / Processor | **1** | 0.1% |
| System Control / Alarm | **1** | 0.1% |