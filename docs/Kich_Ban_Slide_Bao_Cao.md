# KỊCH BẢN SLIDE BÁO CÁO ĐỒ ÁN
## ĐỀ TÀI: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH TỪ ĐẶC TẢ NGÔN NGỮ TỰ NHIÊN (SPEC2RTL)
**Phương pháp: Ứng dụng Mô hình Phản hồi Khép kín EDA & Trực quan hóa Vi mạch**

---

### SƠ ĐỒ LUỒNG HOẠT ĐỘNG & MỤC TIÊU CỐT LÕI (WORKFLOW & KEY MILESTONES)

```text
                     ĐẶC TẢ YÊU CẦU (Natural Language Spec: .txt, .md, prompt)
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 1: CHIẾN LƯỢC TỐI ƯU CÔNG SỨC - 70% Phổ Thông vs 30% Đột Phá]                     │
│  - 70% Khối mạch thông dụng (FSM, Counter, ALU, FIFO, Bus): Tự động hóa 100% bằng AI     │
│  - 30% Khối vi mạch cốt lõi (SoC AI Core, MAC Unit): Dành trọn thời gian cho kỹ sư      │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 2: ĐỘNG CƠ THỰC THI SPEC2RTL - Spec -> RTL -> Testbench]                          │
│  - Thay thế hàng tuần viết code tay bằng AI Agent thông minh                            │
│  - Tự động sinh mã Verilog + Testbench tự kiểm chứng (Self-checking) chỉ trong 1-2 giây │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 3: KIỂM CHỨNG & TỰ SỬA LỖI - Vòng Lặp Phản Hồi EDA Khép Kín (Closed-Loop)]        │
│  - Đưa trực tiếp ModelSim và Quartus vào làm trọng tài (EDA-in-the-loop)                │
│  - Đọc log lỗi mô phỏng -> Reflection Agent tự sửa code cho đến khi đúng 100%          │
│    (Kế thừa chuẩn nghiên cứu VeriPrefer - arXiv:2504.15804)                             │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 4: ĐẦU RA BÀN GIAO - "Trực Quan Hóa Để Kiểm Soát Thực Thể"]                       │
│  - Không chỉ dừng lại ở file code text vô hồn                                           │
│  - Tự động vẽ Sơ đồ nguyên lý mạch Quartus BDF + Xuất 4 định dạng sóng đồ họa trực quan │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### SLIDE 1: TRANG TIÊU ĐỀ & GIỚI THIỆU CHUNG
* **Tiêu đề lớn**: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH SỐ SPEC2RTL
* **Tiêu đề phụ**: Từ Yêu Cầu Văn Bản Tự Nhiên Đến Mạch Nguyên Lý Hoàn Chỉnh Trên FPGA
* **Thông tin thực hiện**:
  - Sinh viên thực hiện: [Họ và tên Sinh viên]
  - Giảng viên hướng dẫn: [Họ và tên Thầy giáo]
  - Công cụ EDA hỗ trợ: Altera Quartus II 13.0sp1 & ModelSim-Altera 10.1d
* **Nội dung hiển thị trên slide**:
  - Biểu tượng mũi tên chuyển đổi: `Mô tả tiếng Việt/tiếng Anh` $\rightarrow$ `Mã Verilog & Testbench` $\rightarrow$ `Sơ đồ nguyên lý BDF & Sóng ModelSim`.
  - Mục tiêu: Rút ngắn chu kỳ thiết kế phần cứng từ vài ngày xuống vài giây.
* **Lời thoại thuyết trình (Dễ hiểu, tự tin - 35s)**:
  > *"Kính thưa Thầy và quý Thầy Cô trong Hội đồng. Trong quy trình thiết kế vi mạch truyền thống, để biến một ý tưởng hay một bản mô tả chức năng thành một con chip hoạt động được, kỹ sư phần cứng phải mất từ vài ngày đến hàng tuần ngồi gõ từng dòng mã Verilog, viết hàng trăm dòng Testbench để kiểm tra, rồi vẽ sơ đồ nguyên lý trong Quartus.*  
  > *Đề tài của em xây dựng một **Hệ thống AI tự động hóa hoàn toàn luồng Spec2RTL**: Chỉ cần đưa vào một đoạn văn bản mô tả chức năng bình thường, hệ thống sẽ tự động tạo ra mã Verilog chuẩn, tự kiểm tra mô phỏng trên ModelSim, tự sửa lỗi nếu sai, và tự động vẽ ra sơ đồ mạch nguyên lý để nạp chạy ngay trên chip FPGA."*

---

### SLIDE 2: NỖI ĐAU THỰC TẾ & VÌ SAO CHATGPT KHÔNG THỂ THIẾT KẾ VI MẠCH?
* **Tiêu đề**: Nỗi Đau Ngành Bán Dẫn & Giới Hạn Của AI Sinh Văn Bản (LLM)
* **Nội dung hiển thị trên slide**:
  - **Nỗi đau ngành chip**: 70% thời gian của một dự án vi mạch bị chôn vùi vào khâu viết mã lặp lại và debug kiểm tra lỗi (Verification Bottleneck).
  - **Vì sao ChatGPT/Claude thông thường thất bại khi viết Verilog?**:
    1. *Ảo giác chân tín hiệu (Port Hallucination)*: Đề bài yêu cầu 5 chân, AI tự ý bịa thêm chân thứ 6 hoặc quên mất chân tín hiệu quan trọng.
    2. *Tạo ra chốt ẩn nguy hiểm (Inferred Latches)*: Code nhìn bên ngoài rất đúng cú pháp, nhưng nạp vào chip thì mạch bị chập chờn, tiêu tốn tài nguyên và sai lệch thời gian.
    3. *Không thể tự kiểm chứng*: AI văn bản chỉ đoán từ tiếp theo, nó không biết cách bấm nút biên dịch trong ModelSim hay Quartus để xem mạch có chạy thật hay không.
* **Lời thoại thuyết trình (45s)**:
  > *"Nhiều người sẽ hỏi: Bây giờ có ChatGPT hay Claude rồi, tại sao không copy đề bài vào đó rồi xin code Verilog?*  
  > *Thực tế nghiên cứu cho thấy, nếu chỉ dùng AI thông thường, tỷ lệ lỗi lên tới hơn 50%. Phần cứng rất khắt khe: chỉ cần AI bịa thêm một chân tín hiệu lạ, hoặc viết thiếu một trường hợp trong lệnh `case` tạo ra chốt ẩn, là toàn bộ chip sẽ bị cháy hoặc treo cứng.*  
  > *AI bình thường chỉ 'giỏi nói', nhưng không có công cụ để 'làm và kiểm tra'. Muốn ứng dụng AI vào thiết kế vi mạch thực tế, chúng ta bắt buộc phải có một phương pháp tiếp cận kỹ thuật bài bản và có kỷ luật."*

---

### SLIDE 3: CHIẾN LƯỢC TỐI ƯU CÔNG SỨC (70% PHỔ THÔNG VS 30% ĐỘT PHÁ)
* **Tiêu đề**: Chiến Lược Giải Phóng Kỹ Sư: 70% Tự Động Hóa vs 30% Sáng Tạo Cốt Lõi
* **Nội dung hiển thị trên slide (Chia 2 cột rõ ràng)**:
  - **70% Phần cứng phổ thông (AI làm thay 100%)**:
    * Các khối mạch lặp đi lặp lại: Bộ đếm (Counters), Máy trạng thái (FSM), Bộ số học (ALU), Hàng đợi (FIFO), Bộ giải mã LED, Giao tiếp UART/SPI.
    * *Đặc điểm*: Đã có quy chuẩn rõ ràng, nhưng tốn rất nhiều thời gian gõ code và kiểm thử lặp đi lặp lại.
    * *Giải pháp*: Để AI tự động sinh và kiểm chứng trong 1-2 giây.
  - **30% Phần cứng cốt lõi (Con người tập trung tối ưu)**:
    * Các khối kiến trúc đột phá: Lõi xử lý AI (NPU, Systolic Array, Khối nhân ma trận MAC), Tối ưu hóa tiêu thụ năng lượng và xung nhịp GHz.
    * *Giá trị mang lại*: Kỹ sư không còn phải làm việc "thợ gõ code", mà dành 100% chất xám cho phần tinh hoa nhất của dự án.
* **Lời thoại thuyết trình (45s)**:
  > *"Từ thực tế đó, kế hoạch của đồ án bắt đầu bằng **Chiến lược phân tách 70% và 30%**.*  
  > *Trong mọi hệ thống vi mạch hay đồ án vi xử lý, có tới 70% khối mạch là phần cứng phổ thông: ví dụ như bộ đếm thời gian, máy trạng thái FSM điều khiển, bộ chuyển đổi UART, hay giải mã LED 7 đoạn. Đây là những phần bắt buộc phải có, nhưng lại tốn hàng tuần làm thủ công.*  
  > *Hệ thống của em sinh ra để tự động hóa 100% phần 70% phổ thông này. Nhờ đó, người kỹ sư được giải phóng hoàn toàn khỏi những tác vụ lặp lại, để dành toàn bộ thời gian và trí tuệ tập trung vào 30% kiến trúc cốt lõi, ví dụ như thiết kế lõi tăng tốc AI hay bộ xử lý chuyên dụng."*

---

### SLIDE 4: ĐỘNG CƠ THỰC THI CHÍNH (SPEC $\rightarrow$ RTL $\rightarrow$ TESTBENCH)
* **Tiêu đề**: Động Cơ Thực Thi Spec2RTL: Biến Ý Tưởng Thành Phần Cứng Trong 2 Giây
* **Nội dung hiển thị trên slide**:
  - **Quy trình 3 pha tự động**:
    1. *Nhận dạng đặc tả (Spec Ingestion)*: Đọc yêu cầu bằng tiếng Việt hoặc tiếng Anh từ file `.txt`, `.md` hoặc prompt tự do. Trích xuất chính xác: Tên module, danh sách chân cắm, độ rộng bit (bus width), và chức năng hoạt động.
    2. *Sinh mã phần cứng (Synthesizable RTL)*: Tạo file Verilog chuẩn công nghiệp, bảo đảm 100% không chốt ẩn, tương thích hoàn toàn với Altera Quartus II.
    3. *Sinh Testbench tự kiểm tra (Self-checking Scoreboard)*: Tự động tạo kịch bản kích thích xung nhịp, reset, và tự so sánh kết quả đầu ra đúng/sai mà không cần người ngồi đọc dạng sóng bằng mắt.
  - **Thời gian xử lý**: Toàn bộ quá trình diễn ra chỉ từ **1 đến 2 giây**!
* **Lời thoại thuyết trình (45s)**:
  > *"Để hiện thực hóa chiến lược trên, trái tim của luồng chạy chính là **Động cơ thực thi Spec2RTL**.*  
  > *Quy trình cực kỳ đơn giản: Kỹ sư chỉ cần cung cấp một bản mô tả chức năng mạch bình thường bằng file txt hoặc markdown. Động cơ AI sẽ tự động phân tích tên mạch, tách bạch từng chân tín hiệu vào/ra.*  
  > *Điểm mấu chốt là hệ thống không chỉ sinh ra mã Verilog của mạch, mà còn sinh luôn cả một file Testbench tự kiểm chứng hoàn chỉnh. Testbench này có sẵn bảng chân lý để tự chấm điểm xem mạch chạy đúng hay sai, hoàn tất toàn bộ trong chưa đầy 2 giây."*

---

### SLIDE 5: VÒNG LẶP PHẢN HỒI THỰC TẾ EDA (CLOSED-LOOP VERIFICATION)
* **Tiêu đề**: Cơ Chế Kiểm Chứng & Tự Sửa Lỗi: Đưa ModelSim Vào Vòng Lặp Phản Hồi Khép Kín
* **Sơ đồ vòng lặp khép kín**:
  $$\text{AI Sinh Code Verilog} \longrightarrow \text{ModelSim Biên Dịch \& Chạy Thử} \longrightarrow \begin{cases} \text{Đúng 100\%} \rightarrow \text{Xuất mạch} \\ \text{Có lỗi} \rightarrow \text{Đọc Log} \rightarrow \text{AI Tự Sửa Lại} \end{cases}$$
* **Nội dung hiển thị trên slide**:
  - **Nguyên tắc "Không tin mù quáng vào AI"**: Lấy các phần mềm EDA tiêu chuẩn công nghiệp (ModelSim 10.1d, Quartus II) làm "Trọng tài chân lý".
  - **Cơ chế phản hồi thông minh (VeriPrefer Standard - arXiv:2504.15804)**:
    * Nếu biên dịch bị báo lỗi cú pháp hoặc chạy mô phỏng sai kết quả: Hệ thống tự động bắt chính xác dòng thông báo lỗi và thời điểm nano-giây sai lệch từ log ModelSim.
    * Gửi log đó ngược lại cho `Reflection Agent` để tự động sửa mã và biên dịch lại ngay lập tức.
    * Đảm bảo kết quả đầu ra luôn đạt **100% PASS** trước khi bàn giao cho người dùng.
* **Lời thoại thuyết trình (50s)**:
  > *"Nhưng làm sao để tin chắc rằng mã Verilog mà AI sinh ra chạy đúng 100%?*  
  > *Câu trả lời nằm ở **Khâu kiểm chứng thực tế với vòng lặp phản hồi khép kín (EDA-in-the-loop)**, kế thừa phương pháp nghiên cứu VeriPrefer.*  
  > *Chúng em không bao giờ tin tưởng mù quáng vào mã do AI viết ra. Ngay sau khi sinh code, hệ thống tự động gọi ngầm công cụ ModelSim lên để biên dịch và chạy mô phỏng thực tế. Nếu ModelSim báo lỗi cú pháp hoặc kết quả sai ở nano-giây nào, hệ thống sẽ trích xuất chính xác thông báo lỗi đó đưa ngược lại cho AI Agent để tự phân tích và sửa lại đúng dòng code bị lỗi. Vòng lặp này tự vận hành cho tới khi nào ModelSim trả về kết quả 100% PASS thì mới nghiệm thu."*

---

### SLIDE 6: ĐẦU RA BÀN GIAO: TRỰC QUAN HÓA ĐỂ KIỂM SOÁT THỰC THỂ
* **Tiêu đề**: Mục Tiêu Đầu Ra: "Trực Quan Hóa Để Kiểm Soát Thực Thể" (Sơ Đồ BDF & Sóng Đồ Họa)
* **Nội dung hiển thị trên slide (Hiển thị 2 giá trị vượt trội)**:
  1. **Tự động dựng Sơ đồ nguyên lý mạch Quartus BDF (`.bdf`)**:
     * Kỹ sư phần cứng không chỉ muốn nhìn mã text, họ muốn nhìn thấy sơ đồ mạch thật.
     * Hệ thống tự động tạo file Symbol (`.bsf`) và file sơ đồ khối (`.bdf`). Mở Quartus II lên là thấy đầy đủ khối linh kiện, cổng vào/ra, bus dây được nối thẳng hàng, không bị lỗi đứt dây hay chân ảo.
  2. **Bộ 4 định dạng dạng sóng Waveform trực quan**:
     * *ModelSim 1-Click Waveform (`view_waveform.bat`)*: Nhấp đúp chuột là tự bật cửa sổ sóng phóng to toàn màn hình.
     * *Quartus Waveform Editor (`.vwf`)*: Nạp sẵn chân tín hiệu và xung clock vào Quartus.
     * *Interactive Web Waveform (`waveform.html`)*: Xem dạng sóng tương tác bằng chuột ngay trên trình duyệt web mà không cần cài phần mềm nặng.
     * *Dữ liệu sóng chuẩn công nghiệp (`.vcd`)*: Tương thích với mọi công cụ phân tích khác.
* **Lời thoại thuyết trình (45s)**:
  > *"Điểm khác biệt lớn nhất và là **giá trị cốt lõi ở đầu ra của toàn bộ luồng chạy** chính là nguyên lý: 'Trực quan hóa để kiểm soát thực thể'.*  
  > *Một kỹ sư phần cứng hay giảng viên chấm bài sẽ không bao giờ yên tâm nếu chỉ nhìn vài dòng code chữ trên màn hình. Họ cần nhìn thấy con chip hoạt động như thế nào.*  
  > *Hệ thống của em tự động vẽ ra **Sơ đồ nguyên lý mạch BDF hoàn chỉnh trong Quartus II**, với từng chân cắm được đối chiếu khớp 100% với đề bài. Đồng thời, hệ thống xuất ra 4 định dạng dạng sóng trực quan: chỉ cần nhấp đúp chuột là ModelSim tự động mở sóng, hoặc có thể mở trực tiếp file HTML trên trình duyệt web để xem sóng nhảy theo từng xung nhịp clk."*

---

### SLIDE 7: KẾT QUẢ THỰC NGHIỆM ĐO ĐẠC TRÊN CHIP FPGA CYCLONE II
* **Tiêu đề**: Kết Quả Thực Nghiệm: Độ Chính Xác 100% & Đo Đạc Tài Nguyên Thật
* **Nội dung hiển thị trên slide (Bảng số liệu thực tế)**:
  - **Bộ kiểm thử hồi quy (Regression Test Battery)**:
    * Thử nghiệm trên **20 họ mạch chuẩn công nghiệp** (Đồng hồ 0-9, Khóa số điện tử, Động cơ bước, UART, ALU, Gray Counter, SPI, CRC...).
    * Tỷ lệ hoàn thành: **20/20 PASS (100.0%)**.
    * Lỗi chân cắm (Phantom/Missing Ports): **0 lỗi (Bảo toàn 100%)**.
  - **Tài nguyên đo đạc thực tế trên FPGA Cyclone II (EP2C35F672C6)**:
    | Mạch thí nghiệm | Số phần tử Logic (LEs) | Số Flip-Flop (FFs) | Chân I/O | Thời gian tổng hợp |
    | :--- | :--- | :--- | :--- | :--- |
    | **Đồng hồ bấm giờ 0-9 + LED 7 đoạn** | **11 LEs** | **4 FFs** | 14 Pins | **1.8 giây** |
    | **Khóa số mật mã 4 số an toàn** | **27 LEs** | **8 FFs** | 11 Pins | **2.1 giây** |
    | **Bộ điều khiển động cơ bước 4 pha** | **8 LEs** | **3 FFs** | 7 Pins | **1.7 giây** |
* **Lời thoại thuyết trình (40s)**:
  > *"Để chứng minh tính khả thi, em đã cho hệ thống chạy kiểm thử trên 20 họ mạch phần cứng từ cơ bản đến phức tạp. Kết quả đạt 100% thành công, không có bất kỳ chân cắm nào bị ảo giác hay mất tín hiệu.*  
  > *Khi tiến hành tổng hợp trên dòng chip FPGA Altera Cyclone II, các mạch đều tối ưu tài nguyên rất sạch: ví dụ mạch Đồng hồ bấm giờ chỉ tốn 11 Logic Elements và 4 Flip-Flop, thời gian sinh mạch và kiểm tra toàn trình chỉ mất chưa đầy 2 giây."*

---

### SLIDE 8: KỊCH BẢN TRÌNH DIỄN TRỰC TIẾP (LIVE DEMO 3 BƯỚC)
* **Tiêu đề**: Kịch Bản Trình Diễn Thực Tế Tại Chỗ (3 Bước Đơn Giản)
* **Nội dung hiển thị trên slide**:
  - **Bước 1: Soạn đề bài tự nhiên**:
    * Mở file đặc tả [specs/c.txt](file:///D:/altera/13.0sp1/BTVN/Do_An_3/specs/c.txt) (Đồng hồ bấm giờ 0-9 giây kèm giải mã LED 7 đoạn).
  - **Bước 2: Chạy hệ thống tự động**:
    * Mở file `demo.bat` $\rightarrow$ Nhập số `[3]` $\rightarrow$ Nhấn Enter.
    * Hệ thống chạy luồng khép kín: Tách chân $\rightarrow$ Sinh Verilog $\rightarrow$ ModelSim mô phỏng $\rightarrow$ Xuất BDF.
  - **Bước 3: Chiêm ngưỡng kết quả đa phương tiện**:
    * Màn hình ModelSim tự động mở cửa sổ Waveform: Xung nhịp đếm 0..9 và mã LED 7 đoạn chạy mượt mà.
    * Mở file `quartus/sch_stopwatch.bdf`: Xem sơ đồ mạch nguyên lý với các cổng I/O rõ ràng trên Quartus II.
* **Lời thoại thuyết trình (35s)**:
  > *"Sau đây em xin phép được thực hiện demo trực tiếp trên máy tính:  
  > Em chỉ cần mở file văn bản mô tả đề bài mạch Đồng hồ bấm giờ, nhấp đúp file launcher demo.bat và chọn bài số 3.  
  > Ngay lập tức, màn hình console sẽ hiển thị quá trình ModelSim chạy mô phỏng đạt 100% PASS, cửa sổ sóng ModelSim tự động bật lên, và file sơ đồ BDF đã được tạo sẵn để Thầy Cô kiểm tra trực tiếp trong Quartus II."*

---

### SLIDE 9: TỔNG KẾT & GIÁ TRỊ ĐÓNG GÓP
* **Tiêu đề**: Kết Luận: Hiện Thực Hóa Thiết Kế Vi Mạch Thông Minh
* **Nội dung hiển thị trên slide (3 đóng góp cốt lõi)**:
  1. **Khép kín quy trình**: Giải quyết trọn vẹn luồng từ văn bản mô tả $\rightarrow$ Code RTL $\rightarrow$ Testbench $\rightarrow$ Mô phỏng $\rightarrow$ Sơ đồ mạch BDF.
  2. **Tin cậy công nghiệp**: Triệt tiêu hoàn toàn ảo giác của AI nhờ đưa công cụ EDA ModelSim/Quartus vào làm trọng tài tự sửa lỗi (VeriPrefer).
  3. **Tiết kiệm thời gian vượt trội**: Cắt giảm 70% công việc thủ công nhàm chán, giúp sinh viên và kỹ sư tiếp cận thiết kế vi mạch nhanh chóng, trực quan.
* **Lời thoại thuyết trình kết thúc (30s)**:
  > *"Tóm lại, đề tài đã hiện thực hóa thành công một hệ thống tự động hóa thiết kế vi mạch tin cậy, biến những dòng mô tả ý tưởng thành sơ đồ mạch thực tế có thể nạp ngay lên FPGA. Hệ thống giải phóng kỹ sư khỏi 70% công việc chân tay lặp lại, mang lại cách tiếp cận trực quan và hiệu quả cho lĩnh vực bán dẫn.*  
  > *Em xin chân thành cảm ơn Thầy và quý Thầy Cô trong Hội đồng đã chú ý lắng nghe! Em rất mong nhận được câu hỏi và đóng góp từ Thầy Cô."*
