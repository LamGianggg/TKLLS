# ĐỒ ÁN 3: HỆ THỐNG SPEC2RTL & PROMPT2SILICON
## Tự Động Hóa Thiết Kế và Kiểm Thử Vi Mạch AI Accelerator SoC & Digital Hardware Bằng Mô Hình Multi-Agent

---

## 1. Bối Cảnh Nghiên Cứu & Các Công Bố Khoa Học Kế Thừa
1. **NVIDIA Research & Cadence (arXiv:2506.13905 / GTC 2025 Session S72294):** 
   *"Spec2RTL-Agent: Automated Hardware Code Generation from Complex Specifications Using LLM Agent Systems"*.
2. **City University of Hong Kong & Partners (arXiv:2504.15804v1 / April 2025):**
   *"Insights from Verification: Training a Verilog Generation LLM with Reinforcement Learning with Testbench Feedback (VeriPrefer)"*.
3. **University of Florida (arXiv:2507.13369 / July 2025):**
   *"VerilogDB: The Largest, Highest-Quality Dataset with a Preprocessing Framework for LLM-based RTL Generation"*.
4. **ISCAS 2026 (arXiv:2601.13815v1) & RPTU Kaiserslautern:** 
   *"From RTL to Prompt Coding: Empowering the Next Generation of Chip Designers through LLMs"*.
5. **Mã nguồn mở Tiny Tapeout & OpenLane:** Chuẩn hóa quy trình từ Prompt $\to$ RTL $\to$ Simulation $\to$ ASIC GDSII.

---

## 2. Hướng Dẫn Thực Thi Đa Nền Tảng (Cross-Platform)

```bash
# Cập nhật mã nguồn mới nhất:
cd TKLLS
git pull origin main

# Chạy hệ thống:
python agent/run_spec2rtl.py        # Menu tương tác tự động quét mọi spec
python agent/run_spec2rtl.py all    # Chạy tự động toàn bộ bài toán
python agent/run_spec2rtl.py 2      # Chạy bài toán số 2
```
