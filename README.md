# ĐỒ ÁN 3: HỆ THỐNG SPEC2RTL & PROMPT2SILICON
## Tự Động Hóa Thiết Kế và Kiểm Thử Vi Mạch AI Accelerator SoC & Digital Hardware Bằng Mô Hình Multi-Agent

---

## 1. Giới Thiệu & Bối Cảnh Nghiên Cứu (Literature Review)
Đồ án này nghiên cứu và hiện thực hóa phương pháp luận **AI-driven Electronic Design Automation (EDA)** theo trào lưu công nghệ vi mạch mới nhất (2025–2026), trực tiếp kế thừa và bám sát 4 công trình khoa học hàng đầu thế giới:

1. **NVIDIA Research & Cadence (arXiv:2506.13905 / GTC 2025 Session S72294):** 
   *"Spec2RTL-Agent: Automated Hardware Code Generation from Complex Specifications Using LLM Agent Systems"*.  
   $\to$ Cung cấp kiến trúc Multi-Agent phối hợp: Phân tích đặc tả $\to$ Sinh RTL $\to$ Đánh giá & Phản xạ.

2. **City University of Hong Kong & Research Partners (arXiv:2504.15804v1 / April 2025):**
   *"Insights from Verification: Training a Verilog Generation LLM with Reinforcement Learning with Testbench Feedback (VeriPrefer)"*.  
   $\to$ Chứng minh rằng việc chỉ dùng LLM sinh code thuần túy sẽ gặp lỗi ảo giác (hallucination); giải pháp then chốt là **tự động sinh Testbench** và **đưa phản hồi từ trình mô phỏng (EDA Simulator in the Loop)** để đảm bảo tính đúng đắn chức năng (Functional Correctness). Được hiện thực hóa trực tiếp tại `tb_generator.py`, `simulator.py` và `reflection_loop.py`.

3. **University of Florida (arXiv:2507.13369 / July 2025):**
   *"VerilogDB: The Largest, Highest-Quality Dataset with a Preprocessing Framework for LLM-based RTL Generation"*.  
   $\to$ Chuẩn hóa khung tiền xử lý đặc tả phần cứng (Preprocessing Framework), linter tĩnh và trích xuất chỉ số tài nguyên tổng hợp phần cứng vật lý (Logic Elements, Registers, Pins). Được hiện thực hóa tại `verilog_linter.py` và `synthesis_profiler.py`.

4. **NVIDIA Research (VerilogEval Benchmark):**
   *"VerilogEval: Evaluating Large Language Models for Verilog Code Generation"*.
   $\to$ Chuẩn benchmark công nghiệp đánh giá năng lực sinh mã RTL logic tổ hợp & tuần tự.

5. **HKUST (RTLLM Benchmark):**
   *"RTLLM: An Open-Source Benchmark for RTL Generation Using Large Language Models"*.
   $\to$ Bộ benchmark các khối thiết kế phần cứng phức tạp mức hệ thống (ALU, FIFO, FSM, Pulse Detector).

6. **ISCAS 2026 (arXiv:2601.13815v1) & RPTU Kaiserslautern:** 
   *"From RTL to Prompt Coding: Empowering the Next Generation of Chip Designers through LLMs"*.  
   $\to$ Định hình tương lai kỹ sư vi mạch: chuyển dịch từ viết RTL thủ công sang thiết kế bằng Prompt/Spec và tự động hóa toàn diện.

5. **Mã nguồn mở Tiny Tapeout & OpenLane:** Chuẩn hóa quy trình từ Prompt $\to$ RTL $\to$ Simulation $\to$ ASIC GDSII.

---

## 2. Khả Năng Tự Động Hóa Thiết Kế (Autonomous Spec2RTL)

Hệ thống được thiết kế theo kiến trúc **Mở và Tự Sinh (Fully Dynamic & Extensible)**:
- **4 Bài toán chuẩn (Golden Benchmarks):**
  1. `soc_ai_spec.md`: SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core)
  2. `thang_may_spec.md`: Bộ điều khiển Thang máy 5 tầng thông minh
  3. `traffic_light_spec.md`: Bộ điều khiển Đèn giao thông ngã tư
  4. `vendding_machine.md`: Máy bán nước tự động 15.000đ
- **Tự động sinh cho BẤT KỲ bài toán ngẫu nhiên nào bạn tự nghĩ ra:**
  - Chỉ cần tạo file đặc tả mới (ví dụ `specs/alu_4bit.md`, `specs/bo_dem.md`, `specs/pwm.md`, `specs/khoa_so.md`, v.v.) viết bằng tiếng Việt hoặc tiếng Anh.
  - Hệ thống sẽ **tự động phân tích đặc tả (`spec_analyzer.py`)**, **tự động sinh mã nguồn Verilog synthesizable (`rtl_generator.py`)**, **tự động sinh Testbench tự kiểm tra (`tb_generator.py`)**, **tự động mô phỏng waveform (`simulator.py`)** và **tự động vẽ sơ đồ nguyên lý Quartus BDF (`bdf_generator.py`)**.
  - **Tuyệt đối không bị gán cứng vào `top_soc`!** Mỗi bài toán sẽ sinh ra module riêng biệt tương ứng.

---

## 3. Kiến Trúc Cấu Trúc Dự Án (Cross-Platform)

```
TKLLS/
├── agent/                    # Hệ thống điều phối Multi-Agent (Spec2RTL Core)
│   ├── eda_finder.py         # Tự động dò tìm ModelSim / Quartus / Icarus Verilog trên mọi ổ đĩa (C:, D:, E:)
│   ├── spec_analyzer.py      # Phân tích đặc tả tự nhiên theo chuẩn VerilogDB (arXiv:2507.13369)
│   ├── rtl_generator.py      # Tự động sinh mã nguồn Verilog chuẩn synthesizable cho mọi bài toán
│   ├── tb_generator.py       # Tự động sinh Testbench theo phương pháp VeriPrefer (arXiv:2504.15804)
│   ├── verilog_linter.py     # Linter tĩnh & chuẩn hóa cú pháp theo VerilogDB (arXiv:2507.13369)
│   ├── synthesis_profiler.py # Đo đạc tài nguyên phần cứng (LEs, FFs, Pins) theo chuẩn VerilogDB
│   ├── simulator.py          # Bộ điều khiển mô phỏng 3 tầng (ModelSim -> Icarus -> Python Engine)
│   ├── bdf_generator.py      # Tự động trích xuất BSF Symbol và tạo sơ đồ Quartus BDF
│   ├── reflection_loop.py    # Vòng lặp phản xạ chuẩn đoán lỗi từ Simulator Feedback (arXiv:2504.15804)
│   └── run_spec2rtl.py       # Master script điều phối toàn bộ luồng
├── benchmarks/               # Các bộ Benchmark học thuật chuẩn quốc tế
│   ├── verilog_eval/         # NVIDIA Research Benchmark (4 thiết kế)
│   ├── rtllm/                # HKUST Benchmark (4 thiết kế)
│   └── veriprefer/           # CityU HK Benchmark - arXiv:2504.15804 (3 thiết kế)
├── specs/                    # Thư mục chứa các file đặc tả kỹ thuật phần cứng core
│   ├── soc_ai_spec.md
│   ├── thang_may_spec.md
│   ├── traffic_light_spec.md
│   └── vendding_machine.md
├── src/                      # Mã nguồn phần cứng Verilog synthesizable (SoC AI + Generated RTL)
├── sim/                      # Môi trường mô phỏng & kiểm thử tự động
└── quartus/                  # Thư mục chứa project Quartus II (.qpf, .qsf), symbol (.bsf) và sơ đồ (.bdf)
```

---

## 4. Hướng Dẫn Dành Cho Máy Khác (Clone / Pull & Thực Thi)

### 4.1. Đối với máy đã clone dự án về trước đó:
Mở terminal/PowerShell tại thư mục dự án đã clone (ví dụ: `d:\VRL\TKLLS`), chạy các lệnh sau:

```bash
# 1. Di chuyển vào thư mục dự án
cd TKLLS

# 2. Xóa bỏ hoặc lưu tạm các file xung đột cục bộ (nếu có)
git stash

# 3. Kéo bản cập nhật mới nhất từ GitHub
git pull origin main
```

### 4.2. Đối với máy mới hoàn toàn:
```bash
git clone https://github.com/LamGianggg/TKLLS.git
cd TKLLS
```

---

## 5. Cách Chạy Chương Trình

Hệ thống hỗ trợ chạy trên **mọi máy tính Windows (bất kể ổ C:, D:, hay E:)** và **tự động thích ứng**:
- Nếu máy có **ModelSim**: Chạy mô phỏng batch EDA native (`vlog`, `vsim -c`) và xuất file sóng `.vcd`.
- Nếu máy có **Icarus Verilog**: Chạy qua `iverilog` & `vvp`.
- Nếu máy **chưa cài đặt công cụ EDA**: Tự động kích hoạt **Python Behavioral Verification Engine**, kiểm thử đầy đủ 100% logic mà không báo lỗi `FileNotFoundError`.

### Cách 1: Chế độ Menu tương tác trực quan (Khuyên dùng)
```bash
python agent/run_spec2rtl.py
```
Hệ thống sẽ quét toàn bộ các bài toán trong `specs/` (kể cả bài toán mới tạo) và hiển thị menu:
```text
[DANH SÁCH CÁC BÀI TOÁN CÓ SẴN TRONG specs/]:
  [1] soc_ai_spec.md        -> Autonomous SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core)
  [2] thang_may_spec.md     -> Bộ điều khiển Thang máy 5 tầng (5-Floor Intelligent Elevator FSM)
  [3] traffic_light_spec.md -> Bộ điều khiển Đèn giao thông ngã tư (Intersection Traffic Light FSM)
  [4] vendding_machine.md   -> Máy bán nước tự động 15.000đ (Vending Machine FSM)
  [A] Chạy TẤT CẢ (các bài toán lần lượt)

👉 Vui lòng chọn bài toán muốn chạy [1-4 hoặc A, mặc định: A]:
```

### Cách 2: Chạy TẤT CẢ các bài toán bằng 1 lệnh duy nhất
```bash
python agent/run_spec2rtl.py all
```

### Cách 3: Chạy trực tiếp một bài toán cụ thể
```bash
# Chạy bài toán số 2:
python agent/run_spec2rtl.py 2

# Hoặc truyền đường dẫn file spec:
python agent/run_spec2rtl.py specs/vendding_machine.md
```

### Cách 4: Chạy Toàn Bộ 3 Bộ Benchmark Học Thuật (VerilogEval, RTLLM, VeriPrefer)
```bash
# Chạy toàn bộ 11 thiết kế benchmark:
python agent/run_spec2rtl.py benchmark

# Hoặc chạy riêng lẻ từng bộ benchmark:
python agent/run_spec2rtl.py --benchmark verilog_eval   # Bộ của NVIDIA
python agent/run_spec2rtl.py --benchmark rtllm          # Bộ của HKUST
python agent/run_spec2rtl.py --benchmark veriprefer     # Bộ của CityU HK (Bài Thầy gửi)
```

---

## 6. Kết Quả Thực Nghiệm Trên 3 Bộ Benchmark Chuẩn Quốc Tế

Bảng tổng hợp thực nghiệm đo lường trên 11 thiết kế thuộc cả 3 bộ dataset chuẩn học thuật:

| Dataset / Suite | Specification File | Top Entity | Logic Elements (LEs) | Dedicated FFs | Trạng Thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VerilogEval** (NVIDIA) | `counter_16bit.md` | `counter_16bit` | 27 LEs | 16 FFs | **100% PASS** |
| **VerilogEval** (NVIDIA) | `gray_counter_4bit.md` | `gray_counter_4bit` | 8 LEs | 8 FFs | **100% PASS** |
| **VerilogEval** (NVIDIA) | `priority_encoder_8to3.md` | `priority_encoder_8to3` | 7 LEs | 4 FFs | **100% PASS** |
| **VerilogEval** (NVIDIA) | `shift_reg_universal.md` | `shift_reg_universal` | 5 LEs | 4 FFs | **100% PASS** |
| **RTLLM** (HKUST) | `alu_4bit.md` | `alu_4bit` | 40 LEs | 6 FFs | **100% PASS** |
| **RTLLM** (HKUST) | `fifo_syn.md` | `fifo_syn` | 132 LEs | 82 FFs | **100% PASS** |
| **RTLLM** (HKUST) | `pulse_detector.md` | `pulse_detector` | 3 LEs | 3 FFs | **100% PASS** |
| **RTLLM** (HKUST) | `traffic_light_fsm.md` | `traffic_light` | 28 LEs | 8 FFs | **100% PASS** |
| **VeriPrefer** (CityU HK) | `barrel_shifter_4bit.md` | `barrel_shifter_4bit` | 9 LEs | 4 FFs | **100% PASS** |
| **VeriPrefer** (CityU HK) | `digital_lock_fsm.md` | `digital_lock_fsm` | 6 LEs | 3 FFs | **100% PASS** |
| **VeriPrefer** (CityU HK) | `sequence_detector_1011.md` | `sequence_detector_1011` | 7 LEs | 5 FFs | **100% PASS** |

> **Tổng kết thực nghiệm:** 11/11 thiết kế tổng hợp và mô phỏng thành công (**Tỷ lệ chính xác chức năng đạt 100.0%**).

---

## 7. Xem Kết Quả Trực Quan
Sau khi chạy xong:
1. **Sơ đồ nguyên lý khối (BDF)**: Mở Quartus II $\to$ `File` $\to$ `Open` $\to$ chọn file `.bdf` tương ứng trong thư mục `quartus/`.
2. **RTL Schematic Netlist**: Mở project `.qpf` trong Quartus II $\to$ `Tools` $\to$ `Netlist Viewers` $\to$ `RTL Viewer`.
3. **Dạng sóng mô phỏng**: Mở ModelSim $\to$ `File` $\to$ `Open` $\to$ chọn file `.vcd` trong thư mục `sim/`.
