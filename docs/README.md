# ĐỒ ÁN 3: HỆ THỐNG SPEC2RTL & PROMPT2SILICON
## Tự Động Hóa Thiết Kế và Kiểm Thử Vi Mạch AI Accelerator SoC Bằng Mô Hình Multi-Agent

---

## 1. Giới Thiệu & Bối Cảnh Nghiên Cứu
Đồ án này nghiên cứu và hiện thực hóa phương pháp luận **AI-driven Electronic Design Automation (EDA)** theo trào lưu công nghệ vi mạch mới nhất (2025–2026), trực tiếp kế thừa và bám sát các công bố khoa học hàng đầu:
1. **NVIDIA Research & Cadence (arXiv:2506.13905 / GTC 2025 Session S72294):** *"Spec2RTL-Agent: Automated Hardware Code Generation from Complex Specifications Using LLM Agent Systems"*.
2. **ISCAS 2026 (arXiv:2601.13815v1) & RPTU Kaiserslautern:** *"From RTL to Prompt Coding: Empowering the Next Generation of Chip Designers through LLMs"*.
3. **Mã nguồn mở Tiny Tapeout & OpenLane:** Chuẩn hóa quy trình từ Prompt $\to$ RTL $\to$ Simulation $\to$ ASIC GDSII.

---

## 2. Kiến Trúc Hệ Thống Đồ Án

```
D:\altera\13.0sp1\BTVN\Do_An_3\
├── agent/                    # Hệ thống điều phối Multi-Agent (Spec2RTL Core)
│   ├── spec_analyzer.py      # Phân tích đặc tả tự nhiên thành danh sách module/port
│   ├── simulator.py          # Bộ điều khiển biên dịch & mô phỏng tự động (ModelSim)
│   ├── reflection_loop.py    # Vòng lặp phản xạ chuẩn đoán và tự sửa lỗi (Self-Healing)
│   └── run_spec2rtl.py       # Master script điều phối toàn bộ luồng
├── specs/                    # Tài liệu đặc tả kỹ thuật phần cứng (Golden Spec)
│   └── soc_ai_spec.md        # Đặc tả kiến trúc SoC CPU-RAM-DMA-AI MAC Core
├── src/                      # Mã nguồn phần cứng Verilog synthesizable
│   ├── mac_unit.v            # Khối nhân - tích lũy 8-bit (4x4 Mult + 8-bit Acc)
│   ├── relu.v                # Hàm kích hoạt phi tuyến ReLU
│   ├── vector_counter.v      # Bộ đếm chiều dài vector
│   ├── ai_datapath.v         # Đường truyền dữ liệu AI Core
│   ├── ai_fsm.v              # FSM điều khiển AI Core (T0..T6)
│   ├── ai_core.v             # Module AI Accelerator hoàn chỉnh
│   ├── ram_16x4.v            # Bộ nhớ SRAM 16x4 trên chip
│   ├── dma_8237.v            # Bộ điều khiển DMA tương thích 8237
│   ├── cpu_controller.v      # Bộ vi tuần tự CPU Micro-sequencer (S00..S10)
│   └── top_soc.v             # Module đỉnh tích hợp toàn bộ SoC và Bus MUX
├── sim/                      # Môi trường mô phỏng & kiểm thử tự động
│   ├── tb_top_soc.v          # Self-checking testbench đo kiểm toán hạng W*X=12
│   ├── dump.vcd              # Dạng sóng mô phỏng xuất chuẩn GTKWave/ModelSim
│   └── work/                 # Thư viện mô phỏng ModelSim
└── docs/                     # Tài liệu đồ án
    └── README.md
```

---

## 3. Kiến Trúc Phần Cứng SoC (Golden Reference Benchmark)

Hệ thống vi mạch SoC tích hợp 4 phân hệ chính:
- **CPU Micro-sequencer (`cpu_controller.v`)**: FSM 11 trạng thái ($S00 \to S10$), nạp trọng số $W=3$ và đầu vào $X=4$ vào RAM, lập trình thanh ghi MAR và WCR của DMA, nhường bus và chuyển sang chế độ chờ ngắt `SYSTEM_INTR` để chốt kết quả và kích hoạt `SYS_COMPLETE = 1`.
- **Bộ nhớ SRAM (`ram_16x4.v`)**: Lưu trữ ma trận trọng số và vector đầu vào.
- **DMA Controller 8237 (`dma_8237.v`)**: Đọc tự động dữ liệu từ RAM đẩy sang AI Core thông qua giao thức bắt tay `DREQ`/`DACK`.
- **AI Accelerator Core (`ai_core.v`)**: Khối tính toán tích chập/tích vô hướng vector $W \cdot X = 3 \times 4 = 12$ (`0x0C`), qua kích hoạt ReLU.

---

## 4. Bảng So Sánh Đối Chứng Khoa Học

| Tiêu Chí So Sánh | Phương Pháp Cũ (Manual BDF / Quartus II) | Phương Pháp Mới (Spec2RTL / Prompt2Silicon) |
| :--- | :--- | :--- |
| **Phương thức thiết kế** | Vẽ tay sơ đồ cổng rời rạc trên giao diện đồ họa. | **Đặc tả bằng ngôn ngữ tự nhiên $\to$ Sinh mã RTL tự động.** |
| **Ngôn ngữ phần cứng** | BDF độc quyền (không thể tổng hợp ASIC). | **Verilog chuẩn quốc tế (IEEE 1364-2001), sẵn sàng GDSII.** |
| **Quy mô & Mở rộng** | Rất khó mở rộng, dây nối chằng chịt, dễ lệch pixel. | **Dễ dàng mở rộng từ 1 neuron lên mạng nơ-ron nhiều lớp.** |
| **Thời gian chu kỳ test** | Tốn hàng giờ thao tác kiểm tra thủ công. | **1.64 giây để biên dịch và mô phỏng tự động 100%.** |
| **Kiểm soát phiên bản** | File binary/graphic không thể dùng Git hiệu quả. | **Quản lý phiên bản mã nguồn chuyên nghiệp bằng Git.** |

---

## 5. Hướng Dẫn Thực Thi

Mở terminal tại thư mục đồ án và chạy lệnh:
```powershell
python "D:\altera\13.0sp1\BTVN\Do_An_3\agent\run_spec2rtl.py"
```

### Kết quả đầu ra mẫu (Terminal output):
```text
================================================================================
   Spec2RTL & Prompt2Silicon Autonomous Hardware Generation Pipeline
   Based on NVIDIA Research (arXiv:2506.13905) & ISCAS 2026 (arXiv:2601.13815)
================================================================================

[Step 1] Ingesting and Parsing Specification...
 -> Found 10 interface ports defined.
 -> Golden Verification Target: 0x0C (12 decimal)

[Step 2] Found 11 Verilog files to compile:
    - ai_core.v
    - ai_datapath.v
    - ai_fsm.v
    - cpu_controller.v
    - dma_8237.v
    - mac_unit.v
    - ram_16x4.v
    - relu.v
    - top_soc.v
    - vector_counter.v
    - tb_top_soc.v

[Step 3] Invoking EDA Simulation Engine (ModelSim-Altera Batch Flow)...

============================================================================
  [SUCCESS] TEST VERIFICATION PASSED 100%!
  Dot Product: W (3) * X (4) = FINAL_RESULT: 0x0C (12 decimal)
  Hardware Handshake: DREQ -> DACK -> AI_DONE -> SYSTEM_INTR -> SYS_COMPLETE
============================================================================

>>> [SPEC2RTL STATUS: SUCCESS (100% PASS)] <<<
Execution Time: 1.64 seconds
Output files generated: D:\altera\13.0sp1\BTVN\Do_An_3\sim\dump.vcd
```
