# THƯ MỤC TÀI LIỆU DỰ ÁN (DOCS)

Thư mục này chứa toàn bộ tài liệu hướng dẫn, kịch bản thuyết trình bảo vệ đồ án và bộ 100 đề bài đặc tả mẫu cho hệ thống **Spec2RTL & Prompt2Silicon**.

---

## 1. Danh Mục Tài Liệu

| Tên Tài Liệu | Định Dạng | Mô Tả Chi Tiết |
| :--- | :--- | :--- |
| **100 Prompt Thiết Kế Mạch Số** | `100_Prompt_Thiet_Ke_Mach.pdf` | Tuyển tập 100 đề bài đặc tả kỹ thuật vi mạch số chuẩn hóa, phân loại theo 10 nhóm chủ đề. Trình bày dạng danh sách liệt kê kèm khối văn bản chuẩn để sao chép trực tiếp vào chạy thử nghiệm. |
| **Kịch Bản Slide Báo Cáo** | `Kich_Ban_Slide_Bao_Cao.md` | Kịch bản chi tiết cho buổi bảo vệ đồ án trước hội đồng: lời thoại thuyết trình từng slide, ánh xạ mã nguồn `.py`, đối sánh học thuật và giải trình phản biện. |

---

## 2. Cấu Trúc Chuẩn Của Một Prompt Kỹ Thuật

Mỗi đề bài trong tuyển tập `100_Prompt_Thiet_Ke_Mach.pdf` được thiết kế theo cấu trúc chuẩn hóa 3 phần độc lập, tương thích 100% với bộ phân tích `agent/PhanTichSpec.py`:

```markdown
# [Tên Mạch] (module_name)

## 1. Đầu vào (Inputs):
- clk: Xung nhịp hệ thống
- rst: Tín hiệu reset (nêu rõ active-high hay active-low)
- [N:0] signal_in: Tín hiệu ngõ vào kèm độ rộng bus (nếu có)

## 2. Đầu ra (Outputs):
- [M:0] signal_out: Tín hiệu ngõ ra kèm độ rộng bus

## 3. Hoạt động / Logic mong muốn:
- Mô tả chi tiết hành vi logic, điều kiện chuyển trạng thái, phương trình hoặc bảng chân trị.
```

---

## 3. Hướng Dẫn Sao Chép Prompt Để Chạy Thử Nghiệm

Để kiểm tra năng lực tự động sinh RTL và sơ đồ nguyên lý của bất kỳ đề bài nào:

1. **Mở file PDF**: Mở `100_Prompt_Thiet_Ke_Mach.pdf`.
2. **Chọn và Sao chép**: Chọn toàn bộ nội dung của một Prompt bất kỳ (từ dòng `# [Tên Mạch]` đến hết phần `## 3. Hoạt động`).
3. **Lưu vào thư mục `specs/`**: Dán nội dung vừa sao chép vào một file mới (ví dụ: `specs/test_mach.txt`).
4. **Chạy lệnh sinh vi mạch tự động**:
   ```bash
   python agent/ChayChinh.py specs/test_mach.txt
   ```
5. **Kiểm tra kết quả**:
   - Mã nguồn Verilog RTL: `src/`
   - Testbench mô phỏng: `sim/`
   - Sơ đồ BDF, Waveform VWF, Project Quartus: `quartus/`
