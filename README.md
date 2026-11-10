# ĐỒ ÁN 3: HỆ THỐNG SPEC2RTL & PROMPT2SILICON
## Tự Động Hóa Thiết Kế và Kiểm Thử Vi Mạch AI Accelerator SoC & Digital Hardware Bằng Mô Hình Multi-Agent

---

## 1. Giới Thiệu & Bối Cảnh Nghiên Cứu
Đồ án này nghiên cứu và hiện thực hóa phương pháp luận **AI-driven Electronic Design Automation (EDA)** theo trào lưu công nghệ vi mạch mới nhất (2025–2026), trực tiếp kế thừa và bám sát các công bố khoa học hàng đầu:
1. **NVIDIA Research & Cadence (arXiv:2506.13905 / GTC 2025 Session S72294):** *"Spec2RTL-Agent: Automated Hardware Code Generation from Complex Specifications Using LLM Agent Systems"*.
2. **ISCAS 2026 (arXiv:2601.13815v1) & RPTU Kaiserslautern:** *"From RTL to Prompt Coding: Empowering the Next Generation of Chip Designers through LLMs"*.
3. **Mã nguồn mở Tiny Tapeout & OpenLane:** Chuẩn hóa quy trình từ Prompt $\to$ RTL $\to$ Simulation $\to$ ASIC GDSII.

---

## 2. Danh Sách Các Bài Toán Phần Cứng Được Hỗ Trợ (trong `specs/`)
Hệ thống tự động hóa chuyển đổi từ ngôn ngữ tự nhiên sang mã RTL Verilog, Testbench, mô phỏng waveform và sơ đồ nguyên lý Quartus BDF cho 4 bài toán:

| STT | Tên Spec | Mô Tả Hệ Thống Phần Cứng | Module Entity Đỉnh |
| :---: | :--- | :--- | :--- |
| **1** | `soc_ai_spec.md` | Autonomous SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core) | `top_soc` |
| **2** | `thang_may_spec.md` | Bộ điều khiển Thang máy 5 tầng (5-Floor Intelligent Elevator FSM) | `elevator_controller` |
| **3** | `traffic_light_spec.md` | Bộ điều khiển Đèn giao thông ngã tư thông minh (Intersection FSM) | `traffic_light` |
| **4** | `vendding_machine.md` | Máy bán nước tự động 15.000đ nhận mệnh giá 5k/10k và thối tiền | `vending_machine` |

---

## 3. Kiến Trúc Cấu Trúc Dự Án (Cross-Platform)

```
TKLLS/
├── agent/                    # Hệ thống điều phối Multi-Agent (Spec2RTL Core)
│   ├── eda_finder.py         # Tự động dò tìm ModelSim / Quartus / Icarus Verilog trên mọi ổ đĩa (C:, D:, E:)
│   ├── spec_analyzer.py      # Phân tích đặc tả tự nhiên thành danh sách module/port
│   ├── rtl_generator.py      # Tự động sinh mã nguồn Verilog chuẩn synthesizable
│   ├── tb_generator.py       # Tự động sinh Testbench tự kiểm tra (Self-checking)
│   ├── simulator.py          # Bộ điều khiển mô phỏng 3 tầng (ModelSim -> Icarus -> Python Engine)
│   ├── bdf_generator.py      # Tự động trích xuất BSF Symbol và tạo sơ đồ Quartus BDF
│   ├── reflection_loop.py    # Vòng lặp phản xạ chuẩn đoán và tự sửa lỗi (Self-Healing)
│   └── run_spec2rtl.py       # Master script điều phối toàn bộ luồng
├── specs/                    # Tài liệu đặc tả kỹ thuật phần cứng (Golden Specs)
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
Mở terminal/PowerShell tại thư mục dự án đã clone (ví dụ: `d:\VRL\TKLLS`), chạy các lệnh sau để cập nhật phiên bản mới nhất:

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
Hệ thống sẽ hiển thị menu:
```text
[DANH SÁCH CÁC BÀI TOÁN CÓ SẴN TRONG specs/]:
  [1] soc_ai_spec.md        -> Autonomous SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core)
  [2] thang_may_spec.md     -> Bộ điều khiển Thang máy 5 tầng (5-Floor Intelligent Elevator FSM)
  [3] traffic_light_spec.md -> Bộ điều khiển Đèn giao thông ngã tư (Intersection Traffic Light FSM)
  [4] vendding_machine.md   -> Máy bán nước tự động 15.000đ (Vending Machine FSM)
  [A] Chạy TẤT CẢ (4 bài toán lần lượt)

👉 Vui lòng chọn bài toán muốn chạy [1-4 hoặc A, mặc định: A]:
```

### Cách 2: Chạy TẤT CẢ các bài toán bằng 1 lệnh duy nhất
```bash
python agent/run_spec2rtl.py all
```

### Cách 3: Chạy trực tiếp một bài toán cụ thể theo số thứ tự hoặc tên file
```bash
# Chạy bài toán Thang máy 5 tầng:
python agent/run_spec2rtl.py 2

# Chạy bài toán Máy bán nước:
python agent/run_spec2rtl.py 4

# Hoặc truyền tên file spec:
python agent/run_spec2rtl.py specs/traffic_light_spec.md
```

---

## 6. Xem Kết Quả Trực Quan
Sau khi chạy xong:
1. **Sơ đồ nguyên lý khối (BDF)**: Mở Quartus II $\to$ `File` $\to$ `Open` $\to$ chọn file `.bdf` tương ứng trong thư mục `quartus/`.
2. **RTL Schematic Netlist**: Mở project `.qpf` trong Quartus II $\to$ `Tools` $\to$ `Netlist Viewers` $\to$ `RTL Viewer`.
3. **Dạng sóng mô phỏng**: Mở ModelSim $\to$ `File` $\to$ `Open` $\to$ chọn file `.vcd` trong thư mục `sim/`.
