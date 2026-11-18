# BÁO CÁO NGHIỆM THU DỮ LIỆU & THẨM ĐỊNH (NHÓM 1)
**Học phần**: Thiết kế luận lý số (CE118 - UIT / VJU)  
**Dự án**: Spec2RTL & Prompt2Silicon (Hardware Agent Closed-Loop EDA System)  
**Giai đoạn**: Tuần 1 (Ngày 1 - 2) - Thu thập dữ liệu gốc, Tích hợp VeriPrefer & Khử trùng lặp  
**Ngày thực hiện**: 18/11/2026  

---

## 1. Mục Tiêu & Trách Nhiệm Của Nhóm 1
Nhóm 1 đóng vai trò **Bộ Thẩm Định Chân Lý Phần Cứng (Hardware Truth Oracle)** trong chuỗi giá trị dự án:
- Thu thập toàn bộ đặc tả phần cứng sơ bộ từ các kho mở uy tín:
  * **NVIDIA VerilogEval** (NVlabs)
  * **HKUST RTLLM** (Hồng Kông)
  * **CityU HK VeriPrefer** (Bài báo số 6 - arXiv:2504.15804)
  * **HuggingFace Verilog-Instruct**
  * **Tuyển tập 100 đề bài chuẩn hóa UIT / VJU & Benchmark Đồ án**
- Tiền xử lý, chuẩn hóa cấu trúc SFT (`instruction`, `input`, `output`) theo chuẩn IEEE 1364-2001.
- Áp dụng **Bộ lọc ModelSim Compiler (`vlog.exe`)** tự động: 100% mã Verilog bàn giao cho Nhóm 2 phải biên dịch không lỗi (`Errors: 0`), không tạo chốt ẩn (no inferred latches) và không có chân lơ lửng (no dangling pins).
- **Rà soát khử trùng lặp (Deduplication)**: Loại bỏ triệt để các module trùng tên hoặc trùng thuật toán (Code Hash MD5).

---

## 2. Kết Quả Thẩm Định & Rà Soát Chất Lượng Toàn Diện

| Tiêu chí | Số lượng mẫu | Tỷ lệ (%) | Ghi chú kỹ thuật |
| :--- | :---: | :---: | :--- |
| **Tổng số mẫu ứng viên ban đầu** | **1100** | 100.0% | Đã gộp từ 6 nguồn |
| **Mẫu trùng lặp đã loại bỏ (Duplicates)** | **2** | 0.2% | Rà soát bằng mã băm MD5 và tên module |
| **Mẫu lỗi linter / chốt ẩn đã loại** | **0** | 0.0% | Lọc bỏ trường hợp case thiếu default |
| **MẪU SẠCH CUỐI CÙNG (PASS MODELSIM 100%)** | **1098** | **99.8%** | **Độc nhất, 0 lỗi cú pháp, 0 chốt ẩn, sẵn sàng nạp Colab** |

---

## 3. Phân Bố Tập Dữ Liệu Sạch Bàn Giao Cho Nhóm 2

### 3.1. Phân bố theo nguồn dữ liệu (Sources)
| Nguồn dữ liệu | Số lượng mẫu đạt chuẩn | Mô tả đóng góp |
| :--- | :---: | :--- |
| Synthesized CE118 Augmentation Suite | **791** | Đạt chuẩn ModelSim & không trùng lặp |
| NVIDIA VerilogEval | **94** | Đạt chuẩn ModelSim & không trùng lặp |
| HuggingFace Verilog-Instruct-60k | **87** | Đạt chuẩn ModelSim & không trùng lặp |
| CityU HK VeriPrefer Benchmark (arXiv:2504.15804) | **75** | Đạt chuẩn ModelSim & không trùng lặp |
| HKUST RTLLM | **43** | Đạt chuẩn ModelSim & không trùng lặp |
| Spec2RTL Project Benchmarks | **6** | Đạt chuẩn ModelSim & không trùng lặp |
| Spec2RTL Verified Library | **2** | Đạt chuẩn ModelSim & không trùng lặp |

### 3.2. Phân bố theo họ vi mạch (Hardware Categories)
| Họ vi mạch | Số lượng mẫu | Tỷ lệ (%) |
| :--- | :---: | :---: |
| Arithmetic | **302** | 27.5% |
| Counter | **129** | 11.7% |
| Miscellaneous | **85** | 7.7% |
| Logic Gates | **84** | 7.7% |
| Clock & Timing | **70** | 6.4% |
| Shift Register | **62** | 5.6% |
| Memory / Storage | **58** | 5.3% |
| FSM | **45** | 4.1% |
| Advanced RTL / RTLLM2 | **44** | 4.0% |
| Multiplexer | **36** | 3.3% |
| Code Converter | **35** | 3.2% |
| Digital Logic | **29** | 2.6% |
| Signal Conditioning | **26** | 2.4% |
| Control / FSM | **21** | 1.9% |
| Memory / FIFO | **20** | 1.8% |
| Demultiplexer | **15** | 1.4% |
| Decoder | **9** | 0.8% |
| PWM | **9** | 0.8% |
| Communication / Serial | **7** | 0.6% |
| Interconnect | **4** | 0.4% |
| Encoder | **3** | 0.3% |
| SoC / Processor | **1** | 0.1% |
| Display / Decoder | **1** | 0.1% |
| System Control / Alarm | **1** | 0.1% |
| FSM / Security | **1** | 0.1% |
| Display / Video | **1** | 0.1% |

---

## 4. Hướng Dẫn Bàn Giao Sang Nhóm 2 (Fine-Tuning Integration)

Nhóm 2 chỉ cần mở notebook `training/train_spec2rtl_qwen3b_colab.ipynb` và thực hiện Bước 5 như sau:

```python
# [Nhóm 2 Integration]: Nạp trực tiếp dữ liệu sạch từ Nhóm 1 qua GitHub:
import json, urllib.request
url = "https://raw.githubusercontent.com/LamGianggg/TKLLS/main/training/dataset_clean_verified.json"
urllib.request.urlretrieve(url, "dataset_clean_verified.json")

with open("dataset_clean_verified.json", "r", encoding="utf-8") as f:
    clean_dataset = json.load(f)

print(f">>> Đã nạp thành công {len(clean_dataset)} mẫu Verilog sạch 100% từ Nhóm 1!")
```

---
*Báo cáo được khởi tạo tự động bởi hệ thống thẩm định ModelSim Truth Oracle của Nhóm 1.*
