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

## 2. Kiến Trúc Hoạt Động 4 Bước (Pipeline Architecture)

```mermaid
flowchart TD
    A["Đặc Tả Ngôn Ngữ Tự Nhiên\n(specs/*.txt, specs/*.md)"] --> B["1. Spec & Port Analyzer\n(spec_analyzer.py)\nTrích xuất Port, Bus width, Phân loại mạch"]
    B --> C["2. Hardware RAG & Knowledge Matcher\n(knowledge_matcher.py)\nSo khớp 308+ Benchmark Designs"]
    C --> D["3. Dynamic Synthesis Engine\n(rtl_generator.py + tb_generator.py)\nSinh Verilog RTL & Self-Checking Testbench"]
    D --> E["4. EDA Simulator in the Loop\n(simulator.py + ModelSim batch)"]
    E -->|Có lỗi syntax / Assertion fail| F["Reflection Self-Healing Loop\n(reflection_loop.py)\nĐọc log -> Tự động sửa RTL"]
    F --> E
    E -->|100% Functional Pass| G["Quartus Toolchain Integration\n(bdf_generator.py + vwf_generator.py)"]
    G --> H["Project Hoàn Chỉnh (.qpf, .bsf, .bdf, .vwf)"]
```

1. **Bước 1 - Phân tích đặc tả (Ingestion & Port Analysis):** Bóc tách chính xác tên cổng, độ rộng bit (ví dụ: `[3:0] count`), hướng `input`/`output` và nhận diện loại mạch qua `spec_analyzer.py`.
2. **Bước 2 - Tra cứu tri thức phần cứng (Hardware RAG):** Truy vấn cơ sở tri thức để ánh xạ kiến trúc tối ưu qua `knowledge_matcher.py`.
3. **Bước 3 - Tổng hợp RTL & Testbench:** Sinh mã nguồn Verilog chuẩn synthesizable (`rtl_generator.py`) và bộ testbench tự kiểm tra với Verification Scoreboard (`tb_generator.py`).
4. **Bước 4 - Mô phỏng phản tư & Xuất Quartus II:** ModelSim biên dịch và kiểm thử qua `simulator.py` & `reflection_loop.py`. Khi đạt 100% PASS, hệ thống tự động xuất sơ đồ nguyên lý BDF (`bdf_generator.py`) và dạng sóng Vector Waveform VWF (`vwf_generator.py`) nạp sẵn vào Quartus II.

---

## 3. Cấu Trúc Mã Nguồn Thư Mục

```
TKLLS/
├── agent/                         # Lõi tác tử điều phối Spec2RTL
│   ├── run_spec2rtl.py            # Master CLI Orchestrator điều phối toàn bộ luồng
│   ├── spec_analyzer.py           # Phân tích đặc tả, trích xuất cổng I/O & phân loại mạch
│   ├── rtl_generator.py           # Bộ sinh mã Verilog RTL chuẩn synthesizable
│   ├── tb_generator.py            # Bộ sinh Testbench tự kiểm tra (VeriPrefer standard)
│   ├── knowledge_matcher.py       # RAG Engine truy vấn 308+ thiết kế mẫu
│   ├── simulator.py               # Trình điều khiển mô phỏng ModelSim / Icarus Verilog
│   ├── reflection_loop.py         # Vòng lặp phản tư tự sửa lỗi logic
│   ├── bdf_generator.py           # Tự động xuất Symbol BSF và Sơ đồ Schematic BDF
│   ├── vwf_generator.py           # Tự động tạo Vector Waveform VWF cho Quartus II
│   ├── port_auditor.py            # Kiểm toán toàn vẹn cổng I/O (Zero-Defect Invariant)
│   ├── eda_finder.py              # Tự động dò tìm ModelSim và Quartus trên ổ đĩa
│   ├── synthesis_profiler.py      # Đo đạc mức tiêu thụ tài nguyên FPGA (LEs, Registers, Pins)
│   ├── verilog_linter.py          # Tiền kiểm tra cú pháp và dọn dẹp mã Verilog
│   ├── harness_generator.py       # Sinh Hardware Test Harness và Watchdog an toàn
│   └── test_robustness_battery.py # Bộ kiểm thử hồi quy 20 bài toán toàn diện
├── knowledge_base/                # Cơ sở tri thức vi mạch (RTLLM, VerilogEval, VeriPrefer)
├── specs/                         # Thư mục chứa các đề bài đặc tả kỹ thuật (.txt, .md)
├── src/                           # Mã nguồn Verilog RTL tự động sinh
├── sim/                           # Môi trường mô phỏng (Testbench, file VCD, batch launcher)
├── quartus/                       # Project Quartus II (.qpf, .qsf), Symbol (.bsf), Sơ đồ (.bdf), Sóng (.vwf)
└── docs/                          # Tài liệu báo cáo, kịch bản thuyết trình, 100 Prompt tuyển tập (PDF)
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

## 6. Kết Quả Thực Nghiệm

Hệ thống đã vượt qua bộ kiểm thử tự động toàn diện:
* **20/20 Test Cases PASS (100.0%)** trên toàn bộ các lớp mạch: Bộ đếm (Up/Down, Gray, Ring, BCD), Khóa số FSM, Động cơ bước, UART TX, SPI Slave, CRC-8, Khử nhiễu phím (Debounce), Dò cạnh xung (Edge Detector), Đèn giao thông, Máy bán nước, ALU 4-bit, v.v.
* **100% Port Integrity**: Không xảy ra hiện tượng mất chân, sai độ rộng bus hoặc chân ma (*Phantom ports*).
