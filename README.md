# ĐỒ ÁN 3: HỆ THỐNG SPEC2RTL & PROMPT2SILICON
## Tác Tử AI Tự Động Hóa Thiết Kế và Kiểm Thử Vi Mạch Số Từ Đặc Tả Ngôn Ngữ Tự Nhiên

---

## 1. Tổng Quan & Bản Chất Dự Án (Executive Summary)

**Spec2RTL & Prompt2Silicon** là một hệ thống **Kỹ sư vi mạch ảo (Autonomous EDA Agent)**, có khả năng chuyển hóa các yêu cầu bài toán thiết kế phần cứng viết bằng ngôn ngữ tự nhiên (Tiếng Việt hoặc Tiếng Anh) thành:
1. **Mã nguồn phần cứng Verilog synthesizable** (`src/*.v`) đạt chuẩn công nghiệp IEEE 1364-2001.
2. **Bộ Testbench tự kiểm tra (Self-checking Testbench)** (`sim/tb_*.v`) với Verification Scoreboard.
3. **Mô phỏng EDA tự động trên ModelSim**: Khép kín vòng lặp phản xạ (Closed-Loop Reflection Loop) để bắt log lỗi và tự sửa mã nguồn cho tới khi đạt **100% Functional Pass**.
4. **Tự động sinh toàn bộ tài nguyên Altera Quartus II**: Khởi tạo Project (`.qpf`, `.qsf`), Khối linh kiện (`.bsf`), Sơ đồ nguyên lý nối dây Schematic (`.bdf`), và Dạng sóng Vector Waveform (`.vwf`) tương thích hoàn toàn với Quartus II 13.0sp1.

---

## 2. Kiến Trúc Hoạt Động (Pipeline Architecture)

![Kiến trúc hoạt động Spec2RTL (Horizontal Pipeline Architecture)](docs/images/pipeline_architecture_horizontal.png)

```mermaid
flowchart LR
    A["Đặc Tả Ngôn Ngữ Tự Nhiên<br/>(specs/*.txt, specs/*.md)"] --> B["1. Spec & Port Analyzer<br/>(spec_analyzer.py)<br/>• Trích xuất Port, Bus<br/>• Tra cứu Hardware DB"]
    B --> C["2. Dynamic Synthesis Engine<br/>(rtl_generator.py + tb_generator.py)<br/>• Sinh Verilog RTL synthesizable<br/>• Sinh Self-Checking Testbench"]
    C --> D["3. Verilog Static Linter<br/>(verilog_linter.py)<br/>• Làm sạch & Quét chốt ẩn"]
    D --> E["4. EDA Simulator in the Loop<br/>(simulator.py + ModelSim batch)"]
    E -->|Có lỗi syntax / Assertion fail| F["Reflection Self-Healing Loop<br/>(reflection_loop.py)<br/>Đọc log ns ➔ Tự động sửa RTL"]
    F --> C
    E -->|100% Functional Pass| G["5. Quartus Toolchain Integration<br/>(bdf_generator.py + vwf_generator.py)<br/>• Xuất Project (.qpf, .bsf, .bdf, .vwf)"]
    G --> H["Kiểm Toán Cổng & Báo Cáo Tài Nguyên<br/>(port_auditor.py + synthesis_profiler.py)<br/>• Bảo toàn chân 1:1 (Port Invariant)<br/>• Đo đạc LEs, FFs trên Cyclone II"]
```

1. **Bước 1 - Phân tích đặc tả (Ingestion & Port Analysis):** Bóc tách chính xác tên cổng, độ rộng bit (ví dụ: `[3:0] count`), hướng `input`/`output` và kiểm tra ranh giới kiến trúc qua `spec_analyzer.py`.
2. **Bước 2 - Tổng hợp RTL & Testbench:** Sinh mã nguồn Verilog chuẩn synthesizable (`rtl_generator.py`) và bộ testbench tự kiểm tra với Verification Scoreboard (`tb_generator.py`).
3. **Bước 3 - Kiểm tra tĩnh & Dọn dẹp:** Làm sạch mã nguồn, loại bỏ ký tự markdown rác và tiền kiểm tra cú pháp với `verilog_linter.py`.
4. **Bước 4 - Mô phỏng phản tư & Xuất Quartus II:** ModelSim biên dịch và kiểm thử qua `simulator.py` & `reflection_loop.py`. Khi đạt 100% PASS, hệ thống tự động xuất sơ đồ nguyên lý BDF (`bdf_generator.py`) và dạng sóng Vector Waveform VWF (`vwf_generator.py`) nạp sẵn vào Quartus II, đồng thời đối soát cổng (`port_auditor.py`) và đo đạc tài nguyên FPGA (`synthesis_profiler.py`).

---

## 3. Cấu Trúc Mã Nguồn Thư Mục

```
TKLLS/
├── agent/                         # Lõi tác tử điều phối Spec2RTL (14 module sạch)
│   ├── run_spec2rtl.py            # Master CLI Orchestrator điều phối toàn bộ luồng
│   ├── spec_analyzer.py           # Phân tích đặc tả, trích xuất cổng I/O & ranh giới kiến trúc
│   ├── rtl_generator.py           # Bộ sinh mã Verilog RTL chuẩn synthesizable
│   ├── tb_generator.py            # Bộ sinh Testbench tự kiểm tra (VeriPrefer standard)
│   ├── simulator.py               # Trình điều khiển mô phỏng ModelSim / Icarus Verilog
│   ├── reflection_loop.py         # Vòng lặp phản tư tự sửa lỗi logic
│   ├── bdf_generator.py           # Tự động xuất Symbol BSF và Sơ đồ Schematic BDF
│   ├── vwf_generator.py           # Tự động tạo Vector Waveform VWF cho Quartus II
│   ├── port_auditor.py            # Kiểm toán toàn vẹn cổng I/O (Zero-Defect Invariant)
│   ├── eda_finder.py              # Tự động dò tìm ModelSim và Quartus trên ổ đĩa
│   ├── synthesis_profiler.py      # Đo đạc mức tiêu thụ tài nguyên FPGA (LEs, Registers, Pins)
│   ├── verilog_linter.py          # Tiền kiểm tra cú pháp và dọn dẹp mã Verilog
│   ├── knowledge_matcher.py       # Bộ nhớ tri thức so khớp ngữ nghĩa đặc tả vi mạch
│   └── test_robustness_battery.py # Bộ kiểm thử hồi quy các bài toán toàn diện
├── knowledge_base/                # Cơ sở tri thức vi mạch (RTLLM, VerilogEval, VeriPrefer)
├── specs/                         # Thư mục chứa các đề bài đặc tả kỹ thuật (.txt, .md)
├── src/                           # Mã nguồn Verilog RTL tự động sinh
├── sim/                           # Môi trường mô phỏng (Testbench, file VCD)
├── quartus/                       # Project Quartus II (.qpf, .qsf), Symbol (.bsf), Sơ đồ (.bdf), Sóng (.vwf)
└── docs/                          # Tài liệu báo cáo, giải thích luồng mã nguồn, 100 Prompt tuyển tập
```

---

## 4. Hướng Dẫn Sử Dụng & Thực Thi

### 4.1. Cài đặt môi trường
Hệ thống chạy trên nền Python 3.8+ và tương thích với công cụ EDA:
* **Altera Quartus II 13.0sp1** (Đường dẫn mặc định: `D:\altera\13.0sp1` hoặc `C:\altera\13.0sp1`)
* **ModelSim-Altera Starter Edition** (tích hợp sẵn trong bộ cài Quartus II)

### 4.2. Các câu lệnh chạy chính

```bash
# 1. Chạy bài toán mẫu có sẵn (ví dụ: Đồng hồ bấm giờ c.txt)
python agent/run_spec2rtl.py specs/c.txt

# 2. Chạy bài toán và tự động mở cửa sổ sóng đồ họa ModelSim GUI
python agent/run_spec2rtl.py specs/c.txt --gui

# 3. Chạy chế độ Menu tương tác tự động quét thư mục specs/
python agent/run_spec2rtl.py

# 4. Chạy toàn bộ 20 bài toán kiểm thử hồi quy toàn diện
python agent/test_robustness_battery.py
```

### 4.3. Cách kiểm tra bài toán mới bất kỳ
1. Tạo một file đặc tả trong `specs/` (ví dụ `specs/mach_moi.txt`) với định dạng:
   ```markdown
   # Tên Mạch (module_name)
   ## 1. Đầu vào (Inputs):
   - clk: Xung nhịp hệ thống
   - rst: Reset tích cực cao
   ## 2. Đầu ra (Outputs):
   - [3:0] out: Tín hiệu đầu ra
   ## 3. Hoạt động / Logic mong muốn:
   - Mô tả logic hoạt động ở đây...
   ```
2. Chạy lệnh:
   ```bash
   python agent/run_spec2rtl.py specs/mach_moi.txt
   ```
3. Xem kết quả tự động sinh trong `src/`, `sim/`, và `quartus/`.

---

## 5. Các Định Dạng Kết Quả Xuất Ra Nghiệm Thu

Sau khi hoàn tất, hệ thống cung cấp 4 hình thức kiểm tra trực quan cho kỹ sư và giảng viên:
1. **Quartus II Schematic Diagram (`quartus/<tên_mạch>/sch_<tên_mạch>.bdf`)**: Mở trong Quartus II (`File -> Open`) để xem sơ đồ khối nguyên lý mạch điện tử đã được vẽ sẵn và nối dây hoàn chỉnh.
2. **Quartus II Vector Waveform (`quartus/<tên_mạch>/Waveform.vwf`)**: Mở trực tiếp trong Quartus II Waveform Editor để xem dạng sóng xung nhịp và chạy Functional Simulation.
3. **ModelSim Waveform GUI (`--gui`)**: Thêm cờ `--gui` khi chạy lệnh (ví dụ: `python agent/run_spec2rtl.py specs/c.txt --gui`) để ModelSim tự động mở cửa sổ sóng đồ họa Waveform trực quan trên màn hình.
4. **Quartus RTL Netlist Viewer**: Mở project `.qpf` trong Quartus II $\to$ chọn `Tools -> Netlist Viewers -> RTL Viewer` để xem sơ đồ mức cổng logic và flip-flop tổng hợp vật lý.

---

## 6. Kết Quả Thực Nghiệm & Đánh Giá Giới Hạn

Hệ thống đã hoàn thiện toàn bộ luồng tự động hóa công cụ EDA:
* **Hạ tầng kiểm định khép kín (Closed-Loop EDA)**: Tự động chạy ModelSim, trích xuất log lỗi, tự động sửa mã Verilog (Reflection Loop), tự động xuất sơ đồ nguyên lý BDF và dạng sóng VWF cho Quartus II mà không cần thao tác thủ công trên giao diện.
* **Đánh giá trên bộ 100 đề bài chuẩn hóa (`docs/100_Prompt_Thiet_Ke_Mach.pdf`)**:
  * **~38% Bài toán đạt chuẩn 100%**: Bao phủ xuất sắc các bài toán thuộc 25 họ mạch kinh điển (Counter, Timer, ALU, FSM Vending Machine, Traffic Light, Elevator, UART TX, PWM...).
  * **~62% Bài toán bộc lộ giới hạn của phương pháp Template/Rule-based**: Với các mạch hoàn toàn mới (ví dụ: `button_debouncer`, MUX/DEMUX nhiều ngõ vào, SPI Master, Arbiter), cơ chế sinh generic rơi vào tình trạng sinh mạch giả lập hoặc bỏ quên ngõ vào (dangling input pins). Đây là bằng chứng thực nghiệm rõ ràng nhất chứng minh phương pháp mẫu cứng đã chạm trần giới hạn.

---

## 7. Định Hướng Phát Triển Tiếp Theo: Chưng Cất Tri Thức (Knowledge Distillation)

Để mở rộng hệ thống đạt độ bao phủ $100\%$ mà không cần viết tay hàng nghìn template, giai đoạn tiếp theo tập trung vào:
1. **Chưng cất tri thức (Knowledge Distillation) sang Small Language Models (SLM)**:
   * Sử dụng các mô hình suy luận lớn (DeepSeek-R1 / Claude 3.5 Sonnet) làm Teacher để tạo tập dữ liệu huấn luyện chuỗi tư duy (Reasoning CoT) từ ngân hàng đề *VerilogDB* ([arXiv:2507.13369](https://arxiv.org/pdf/2507.13369)).
   * Dùng chính bộ khung ModelSim và Quartus hiện tại làm **Bộ lọc chân lý (Truth Oracle)**: chỉ giữ lại các mẫu đạt $100\%$ PASS.
   * Huấn luyện mô hình cục bộ **`Qwen2.5-Coder-3B`** bằng LoRA / DPO (*VeriPrefer* [arXiv:2504.15804](https://arxiv.org/pdf/2504.15804)) để chạy offline $100\%$ trong mạng nội bộ phòng lab, giải quyết bài toán **bảo mật sở hữu trí tuệ phần cứng (IP Security)**.
2. **Nâng cấp Linter từ Regex sang Cây Cú Pháp (AST Parser)**: Tích hợp PyVerilog hoặc Verilator Lint để kiểm tra cấu trúc cú pháp, triệt tiêu hoàn toàn lỗi chốt ẩn (latch) và chân lơ lửng.
3. **Kiểm định có kịch bản & SystemVerilog Assertions (SVA)**: Tự động phát sinh các thuộc tính an toàn phần cứng để chứng minh tính đúng đắn toán học của mạch.

---

## 8. Cơ Sở Khoa Học & Nguồn Gốc Ý Tưởng Từ Các Tài Liệu Nghiên Cứu (Academic References & Provenance)

Hệ thống **Spec2RTL & Prompt2Silicon** được thiết kế và hiện thực hóa dựa trên việc kế thừa, tổng hợp và bản địa hóa các ý tưởng nghiên cứu đỉnh cao từ **6 tài liệu khoa học nền tảng do Giảng viên hướng dẫn (TS. Nguyễn Văn Tình) định hướng**:

| STT | Tài Liệu / Bài Báo | Tác Giả & Tổ Chức | Ý Tưởng Kế Thừa Cốt Lõi | Module Hiện Thực Trong Hệ Thống |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Spec2RTL-Agent**<br/>([arXiv:2506.13905](https://arxiv.org/abs/2506.13905)) | NVIDIA Research, Cadence, Georgia Tech | Kiến trúc đa tác tử 3 pha: Understanding $\to$ Coding $\to$ Reflection | `spec_analyzer.py`, `rtl_generator.py`, `reflection_loop.py` |
| 2 | **From RTL to Prompt Coding**<br/>([arXiv:2601.13815](https://arxiv.org/html/2601.13815v1)) | RPTU Kaiserslautern-Landau, Tiny Tapeout (ISCAS 2026) | Triết lý "Prompt Coding" - Đưa yêu cầu tự nhiên thẳng tới phần cứng | `specs/*.txt`, `100_Prompt_Thiet_Ke_Mach.pdf` |
| 3 | **Prompt2Silicon Platform**<br/>([GitHub tukl-msd](https://github.com/tukl-msd/prompt2silicon)) | Microelectronic Systems Design Group (RPTU) | Trực quan hóa toàn trình (Visual EDA Verification: Schematic & Waveform) | `bdf_generator.py`, `vwf_generator.py`, `--gui` |
| 4 | **Autonomous Chip Design Agents**<br/>([NVIDIA GTC 2025 S72294](https://www.nvidia.com/en-us/on-demand/session/gtc25-S72294/)) | NVIDIA Research (Haoxing Ren, ChipNeMo Team) | Hardware Agent Harness: Tích hợp công cụ EDA làm "Trọng tài chân lý" | `simulator.py`, `synthesis_profiler.py`, `eda_finder.py` |
| 5 | **VerilogDB**<br/>([arXiv:2507.13369](https://arxiv.org/pdf/2507.13369)) | University of Florida | Ngân hàng thiết kế mẫu chuẩn hóa & Khung Linter lọc cú pháp nghiêm ngặt | `knowledge_base/`, `knowledge_matcher.py`, `verilog_linter.py` |
| 6 | **VeriPrefer**<br/>([arXiv:2504.15804](https://arxiv.org/pdf/2504.15804)) | Ning Wang, Zhe Jiang et al. | Tự động sinh Testbench tự kiểm tra (Scoreboard) & Tối ưu bằng phản hồi mô phỏng | `tb_generator.py`, `reflection_loop.py` (Vòng lặp sửa lỗi) |

---

### Chi Tiết Từng Tài Liệu & Vị Trí Kế Thừa Cụ Thể Trong Hệ Thống:

#### 1. Spec2RTL-Agent: Automated Hardware Code Generation from Complex Specifications Using LLM Agent Systems
* **Đường dẫn**: [https://arxiv.org/abs/2506.13905](https://arxiv.org/abs/2506.13905)
* **Tác giả & Tổ chức**: Zhongzhi Yu, Mingjie Liu, Michael Zimmer, Yingyan (Celine) Lin, Yong Liu, Haoxing Ren (NVIDIA Research, Cadence Design Systems, Georgia Institute of Technology).
* **Vị trí lấy trong bài báo**:
  * **Section III (Methodology & Agent Architecture)**: Mô hình hóa quy trình thiết kế phần cứng thành 3 vai trò tác tử tách biệt:
    1. *Understanding Agent*: Tiếp nhận đặc tả phi cấu trúc (PDF, Text), bóc tách danh sách cổng I/O, độ rộng bus và các ràng buộc logic.
    2. *Coding Agent*: Sinh mã phần cứng có cấu trúc chặt chẽ, loại bỏ hoàn toàn việc "bịa" chân tín hiệu (Port Hallucination).
    3. *Reflection Agent*: Quan sát lỗi biên dịch/mô phỏng để tự động sửa mã Verilog lặp đi lặp lại.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/spec_analyzer.py`: Đóng vai trò *Understanding Agent* trích xuất tên module, bảng chân cắm `inputs`/`outputs` kèm độ rộng bit.
  * `agent/rtl_generator.py`: Tích hợp cơ chế `RTLPortEnforcer` đóng vai trò *Coding Agent* ép mã Verilog sinh ra phải khớp 100% cổng với đặc tả.
  * `agent/reflection_loop.py`: Đóng vai trò *Reflection Agent* tự động bắt lỗi cú pháp và lỗi assertion để vá lại code.

---

#### 2. From RTL to Prompt Coding: Empowering the Next Generation of Chip Designers through LLMs
* **Đường dẫn**: [https://arxiv.org/html/2601.13815v1](https://arxiv.org/html/2601.13815v1)
* **Tác giả & Tổ chức**: Lukas Krupp, Matthew Venn, Norbert Wehn (RPTU Kaiserslautern-Landau, Tiny Tapeout, IEEE ISCAS 2026).
* **Vị trí lấy trong bài báo**:
  * **Section I & II (Introduction & The Concept of Prompt Coding)**: Đề xuất chuyển dịch phương pháp thiết kế vi mạch truyền thống (phải gõ thủ công từng dòng mã Verilog/VHDL) sang phương pháp **"Prompt Coding"** — người kỹ sư mô tả ý đồ thiết kế bằng câu lệnh văn bản tự nhiên, hệ thống tự động sinh code synthesizable và kết nối trực tiếp với backend băng từ.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * Chuẩn hóa cấu trúc Prompt đầu vào theo định dạng 3 phần độc lập (Inputs - Outputs - Logic) trong thư mục `specs/*.txt`, `specs/*.md`.
  * Xây dựng tuyển tập tài liệu `docs/100_Prompt_Thiet_Ke_Mach.pdf` gồm 100 đề bài vi mạch kinh điển chuẩn hóa phục vụ đo kiểm năng lực "Prompt Coding".

---

#### 3. Prompt2Silicon Platform (Open-Source Hardware Workflow)
* **Đường dẫn**: [https://github.com/tukl-msd/prompt2silicon](https://github.com/tukl-msd/prompt2silicon)
* **Tác giả & Tổ chức**: Microelectronic Systems Design Group (MSD - TU Kaiserslautern / RPTU).
* **Vị trí lấy trong dự án**:
  * **Triết lý thiết kế (Holistic Frontend-to-Backend & Visual Simulation)**: Không để kết quả dừng lại ở các đoạn mã Verilog dạng text rời rạc khó kiểm soát, mà phải cung cấp công cụ trực quan hóa (Visual EDA Feedback) tức thì để người thiết kế "nhìn thấy" mạch điện tử và dạng sóng logic.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/bdf_generator.py`: Tự động biên dịch file Symbol Altera Quartus (`.bsf`) và vẽ Sơ đồ nguyên lý mạch hoàn chỉnh (`.bdf`) để mở trực tiếp trong Quartus II Schematic Editor.
  * `agent/vwf_generator.py`: Tự động tạo file Vector Waveform (`.vwf`) và khởi chạy ModelSim Waveform GUI (`--gui`) để kỹ sư quan sát trực tiếp các xung nhịp nano-giây.

---

#### 4. Autonomous Chip Design Agents with LLMs (NVIDIA GTC 2025 Session S72294)
* **Đường dẫn**: [https://www.nvidia.com/en-us/on-demand/session/gtc25-S72294/](https://www.nvidia.com/en-us/on-demand/session/gtc25-S72294/)
* **Tác giả & Tổ chức**: Haoxing Ren, Mingjie Liu & Nhóm nghiên cứu ChipNeMo (NVIDIA Research).
* **Vị trí lấy trong phiên báo cáo**:
  * **Kiến trúc Hardware Agent Harness (EDA-in-the-Loop)**: Khẳng định mô hình ngôn ngữ lớn (LLM) không thể tự thiết kế vi mạch nếu thiếu môi trường thực thi phần mềm chuyên dụng (Software Harness). Phải đưa các công cụ EDA tiêu chuẩn công nghiệp vào làm "Trọng tài chân lý" để kiểm tra tính khả tổng hợp (synthesizability) và kiểm soát tài nguyên phần cứng.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/eda_finder.py`: Tự động phát hiện môi trường EDA công nghiệp Altera Quartus II và ModelSim trên máy tính.
  * `agent/simulator.py`: Tự động điều khiển luồng lệnh CLI batch của ModelSim (`vlog.exe`, `vsim.exe`) làm trọng tài mô phỏng.
  * `agent/synthesis_profiler.py`: Gọi ngầm `quartus_map.exe` để tổng hợp thực tế trên chip FPGA Altera Cyclone II, đo đạc chính xác số Logic Elements, Flip-Flops và Pins.

---

#### 5. VerilogDB: The Largest, Highest-Quality Dataset with a Preprocessing Framework for LLM-based RTL Generation
* **Đường dẫn**: [https://arxiv.org/pdf/2507.13369](https://arxiv.org/pdf/2507.13369)
* **Tác giả & Tổ chức**: Paul E. Calzada, Zahin Ibnat, Mark Tehranipoor et al. (Florida Institute for Cybersecurity Research, University of Florida).
* **Vị trí lấy trong bài báo**:
  * **Section III (Data Collection and Preprocessing Pipeline)**: Xây dựng quy trình làm sạch mã nguồn Verilog nghiêm ngặt (Syntax Sanitization, Inferred Latch Detection) và ngân hàng lưu trữ dữ liệu thiết kế có cấu trúc để phục vụ huấn luyện và truy xuất (Retrieval-Augmented Generation).
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/verilog_linter.py`: Xây dựng bộ quét tĩnh cú pháp, làm sạch các ký tự markdown rác và rà soát triệt tiêu chốt ẩn (inferred latches) trước khi mô phỏng.
  * `knowledge_base/` & `agent/knowledge_matcher.py`: Lưu trữ và so khớp ngữ nghĩa với cơ sở tri thức vi mạch chuẩn (`hardware_db.json`), phân loại mạch phổ thông để sinh mã chuẩn xác.
  * Định hướng sử dụng tập dữ liệu chuẩn VerilogDB (20.392 mẫu Verilog sạch) làm dữ liệu gốc cho tiến trình Chưng cất tri thức (Knowledge Distillation) ở giai đoạn tiếp theo.

---

#### 6. Insights from Verification: Training a Verilog Generation LLM with Reinforcement Learning with Testbench Feedback (VeriPrefer)
* **Đường dẫn**: [https://arxiv.org/pdf/2504.15804](https://arxiv.org/pdf/2504.15804) / [https://arxiv.org/html/2504.15804v1](https://arxiv.org/html/2504.15804v1)
* **Tác giả & Tổ chức**: Ning Wang, Bingkun Yao, Zhe Jiang et al.
* **Vị trí lấy trong bài báo**:
  * **Section III & IV (Automated Testbench Generation & DPO with Testbench Feedback)**: Nhấn mạnh rằng sinh mã Verilog mà không có Testbench tự kiểm tra (Self-checking Scoreboard) là vô nghĩa. Sử dụng chính kết quả kiểm thử (Testbench Outcomes / Assertions) làm tín hiệu phản hồi để đánh giá độ chính xác chức năng (Functional Accuracy) và hướng dẫn sửa lỗi logic.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/tb_generator.py`: Tự động sinh Testbench tự kiểm tra có gắn sẵn Verification Scoreboard theo chuẩn VeriPrefer, tự động so sánh ngõ ra và tính tỷ lệ chính xác chức năng (`Functional Accuracy: 100.0 PERCENT`).
  * `agent/reflection_loop.py`: Lấy trực tiếp thông báo lỗi assertion từ log ModelSim để xác định sai lệch nano-giây, làm căn cứ sửa mã Verilog tự động.
  * `agent/port_auditor.py`: Cơ chế kiểm toán toàn vẹn 4 chiều bảo đảm tính bất biến cổng (Port Invariant: $\text{Spec} \equiv \text{RTL} \equiv \text{BSF} \equiv \text{BDF}$).

