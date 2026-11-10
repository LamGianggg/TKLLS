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

## 3. Hướng Dẫn Thực Thi Đa Nền Tảng (Cross-Platform)

```bash
# Cập nhật mã nguồn mới nhất:
cd TKLLS
git pull origin main

# Chạy hệ thống:
python agent/run_spec2rtl.py        # Menu tương tác
python agent/run_spec2rtl.py all    # Chạy tự động cả 4 bài toán
python agent/run_spec2rtl.py 2      # Chạy bài toán số 2 (Thang máy)
```
