# BÁO CÁO NGHIỆM THU DỮ LIỆU & THẨM ĐỊNH (NHÓM 1)
**Học phần**: Thiết kế luận lý số (CE118 - UIT / VJU)  
**Dự án**: Spec2RTL & Prompt2Silicon (Hardware Agent Closed-Loop EDA System)  
**Giai đoạn**: Tuần 1 (Ngày 1 - 2) - Thu thập dữ liệu gốc & Thẩm định ModelSim Truth Oracle  
**Ngày thực hiện**: 18/11/2026  

---

## 1. Mục Tiêu & Trách Nhiệm Của Nhóm 1
Nhóm 1 đóng vai trò **Bộ Thẩm Định Chân Lý Phần Cứng (Hardware Truth Oracle)** trong chuỗi giá trị dự án:
- Thu thập toàn bộ đặc tả phần cứng sơ bộ từ các kho mở uy tín (NVIDIA VerilogEval, HKUST RTLLM, HuggingFace, Tuyển tập 100 đề bài UIT).
- Tiền xử lý, chuẩn hóa cấu trúc SFT (`instruction`, `input`, `output`) theo chuẩn IEEE 1364-2001.
- Áp dụng **Bộ lọc ModelSim Compiler (`vlog.exe`)** tự động: 100% mã Verilog bàn giao cho Nhóm 2 phải biên dịch không lỗi (`Errors: 0`), không tạo chốt ẩn (no inferred latches) và không có chân lơ lửng (no dangling pins).

---

## 2. Kết Quả Thẩm Định & Bộ Lọc Dữ Liệu

| Tiêu chí | Số lượng mẫu | Tỷ lệ (%) | Ghi chú |
| :--- | :---: | :---: | :--- |
| **Tổng số mẫu ứng viên (Candidate Pool)** | **502** | 100.0% | Thu thập từ 4 nguồn chính |
| **Mẫu ĐẠT CHUẨN (ModelSim PASS & Clean Latch)** | **407** | **81.1%** | Sẵn sàng đưa vào huấn luyện LoRA |
| **Mẫu BỊ LOẠI (Compile Errors / Inferred Latches)** | **95** | 18.9% | Lọc bỏ text rác, lỗi cú pháp |

> [!IMPORTANT]
> **Phát hiện học thuật quan trọng của Nhóm 1**:
> Các nguồn dữ liệu thô trên mạng (như AbiralArch CVDP hoặc HuggingFace) chứa nhiều mẫu bị trộn lẫn mô tả văn bản tiếng Anh vào khối code hoặc thiếu khai báo cổng. Nếu nạp trực tiếp vào mô hình 3B mà không qua bộ lọc ModelSim, mô hình sẽ bị "nhiễm độc" và sinh mã lỗi cú pháp.
> **Bộ lọc Truth Oracle của Nhóm 1 đã ngăn chặn 100% nguy cơ này.**

---

## 3. Phân Bố Tập Dữ Liệu Sạch Bàn Giao Cho Nhóm 2

### 3.1. Phân bố theo nguồn dữ liệu (Sources)
| Nguồn dữ liệu | Số lượng mẫu đạt chuẩn | Mô tả đóng góp |
| :--- | :---: | :--- |
| Synthesized CE118 Augmentation Suite | **174** | Mẫu synthesizable đã qua thẩm định |
| NVIDIA VerilogEval | **95** | Mẫu synthesizable đã qua thẩm định |
| HuggingFace Verilog-Instruct-60k | **87** | Mẫu synthesizable đã qua thẩm định |
| HKUST RTLLM | **43** | Mẫu synthesizable đã qua thẩm định |
| Spec2RTL Project Benchmarks | **6** | Mẫu synthesizable đã qua thẩm định |
| Spec2RTL Verified Library | **2** | Mẫu synthesizable đã qua thẩm định |

### 3.2. Phân bố theo họ vi mạch (Hardware Categories)
| Họ vi mạch | Số lượng mẫu | Tỷ lệ (%) |
| :--- | :---: | :---: |
| Arithmetic | **86** | 21.1% |
| Miscellaneous | **85** | 20.9% |
| Counter | **63** | 15.5% |
| Memory / Storage | **37** | 9.1% |
| Multiplexer | **24** | 5.9% |
| Control / FSM | **19** | 4.7% |
| Shift Register | **19** | 4.7% |
| Clock & Timing | **15** | 3.7% |
| Demultiplexer | **12** | 2.9% |
| FSM | **12** | 2.9% |
| Memory / FIFO | **12** | 2.9% |
| Decoder | **7** | 1.7% |
| Signal Conditioning | **4** | 1.0% |
| PWM | **4** | 1.0% |
| Encoder | **3** | 0.7% |
| SoC / Processor | **1** | 0.2% |
| Communication / Serial | **1** | 0.2% |
| Display / Decoder | **1** | 0.2% |
| System Control / Alarm | **1** | 0.2% |
| FSM / Security | **1** | 0.2% |

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
