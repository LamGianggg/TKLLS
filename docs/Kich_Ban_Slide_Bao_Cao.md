# KỊCH BẢN SLIDE BÁO CÁO ĐỒ ÁN
## ĐỀ TÀI: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH TỪ ĐẶC TẢ NGÔN NGỮ TỰ NHIÊN (SPEC2RTL)
**Phương pháp: Ứng dụng Mô hình Phản hồi Khép kín EDA & Trực quan hóa Vi mạch**

---

### SƠ ĐỒ LUỒNG HOẠT ĐỘNG & CÁC MODULE PHẦN MỀM (.PY) ĐẢM NHIỆM

```text
                     ĐẶC TẢ YÊU CẦU (Natural Language Spec: .txt, .md, prompt)
                                                │
                                                ▼ [spec_analyzer.py]
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 1: CHIẾN LƯỢC TỐI ƯU CÔNG SỨC - Phân Tách Hạ Tầng Phổ Thông vs Kiến Trúc Cốt Lõi] │
│  - Phân loại vi mạch: [knowledge_matcher.py] tra cứu kho vi mạch chuẩn (hardware_db)   │
│  - Khối phổ thông (FSM, Counter, ALU, FIFO, Bus): Tự động hóa hoàn toàn bằng AI         │
│  - Khối vi kiến trúc cốt lõi (SoC AI Core, MAC Unit): Dành trọn thời gian cho kỹ sư    │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                ▼ [rtl_generator.py, tb_generator.py]
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 2: ĐỘNG CƠ THỰC THI SPEC2RTL - Spec -> RTL -> Testbench]                          │
│  - Sinh Verilog synthesizable chuẩn sạch không chốt ẩn: [rtl_generator.py]              │
│  - Sinh Testbench tự kiểm tra (Self-checking Scoreboard): [tb_generator.py]            │
│  - Quét cú pháp tĩnh chuẩn VerilogDB: [verilog_linter.py]                               │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                ▼ [simulator.py, reflection_loop.py]
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 3: KIỂM CHỨNG & TỰ SỬA LỖI - Vòng Lặp Phản Hồi EDA Khép Kín (Closed-Loop)]        │
│  - Gọi ModelSim biên dịch và mô phỏng ngầm (CLI batch): [simulator.py]                  │
│  - Đọc log lỗi sai lệch nano-giây -> Tự động sửa mã Verilog: [reflection_loop.py]       │
│  - Đo đạc tài nguyên thực tế trên chip Cyclone II: [synthesis_profiler.py]              │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                ▼ [bdf_generator.py, waveform_visualizer.py]
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ [BƯỚC 4: ĐẦU RA BÀN GIAO - "Trực Quan Hóa Để Kiểm Soát Thực Thể"]                       │
│  - Tự động dựng Sơ đồ nguyên lý mạch Quartus BDF + Tạo Symbol: [bdf_generator.py]       │
│  - Thanh tra đối chiếu chéo 4 chiều bảo toàn chân cắm 1:1: [port_auditor.py]           │
│  - Xuất file sóng Quartus: [vwf_generator.py] & Giao diện sóng Web/GUI: [waveform_...py]│
└─────────────────────────────────────────────────────────────────────────────────────────┘
               [Tổng điều phối luồng toàn trình: run_spec2rtl.py & eda_finder.py]
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
  - Biểu tượng mũi tên chuyển đổi: `Mô tả tự nhiên (.txt, .md)` $\rightarrow$ `Mã Verilog & Testbench` $\rightarrow$ `Sơ đồ nguyên lý BDF & Dạng sóng ModelSim`.
  - Mục tiêu: Rút ngắn chu kỳ thiết kế phần cứng, tự động hóa quy trình viết mã và kiểm thử.
  - **Module điều phối trung tâm**: `run_spec2rtl.py` (Bộ não kết nối toàn bộ tiến trình) & `eda_finder.py` (Tự động nhận diện công cụ EDA).
* **Lời thoại thuyết trình (Dễ hiểu, tự tin - 35s)**:
  > *"Kính thưa Thầy và quý Thầy Cô trong Hội đồng. Trong quy trình thiết kế vi mạch truyền thống, để biến một ý tưởng hay một bản mô tả chức năng thành một con chip hoạt động được, kỹ sư phần cứng phải mất rất nhiều thời gian ngồi gõ từng dòng mã Verilog, viết hàng trăm dòng Testbench để kiểm tra, rồi vẽ sơ đồ nguyên lý trong Quartus.*  
  > *Đề tài của em xây dựng một **Hệ thống AI tự động hóa hoàn toàn luồng Spec2RTL**: Chỉ cần đưa vào một đoạn văn bản mô tả chức năng bình thường, hệ thống sẽ tự động tạo ra mã Verilog chuẩn, tự kiểm tra mô phỏng trên ModelSim, tự sửa lỗi nếu sai, và tự động vẽ ra sơ đồ mạch nguyên lý để nạp chạy ngay trên chip FPGA."*

---

### SLIDE 2: NỖI ĐAU THỰC TẾ & VÌ SAO CHATGPT KHÔNG THỂ THIẾT KẾ VI MẠCH?
* **Tiêu đề**: Nỗi Đau Ngành Bán Dẫn & Giới Hạn Của AI Sinh Văn Bản (LLM)
* **Nội dung hiển thị trên slide**:
  - **Nỗi đau ngành chip**: Phần lớn thời gian của một dự án vi mạch bị chôn vùi vào khâu viết mã lặp đi lặp lại và debug kiểm tra lỗi (Verification Bottleneck).
  - **Vì sao ChatGPT/Claude thông thường thất bại khi viết Verilog?**:
    1. *Ảo giác chân tín hiệu (Port Hallucination)*: Đề bài yêu cầu các chân xác định, AI tự ý bịa thêm chân lạ hoặc bỏ quên chân tín hiệu quan trọng.
    2. *Tạo ra chốt ẩn nguy hiểm (Inferred Latches)*: Code nhìn bên ngoài rất đúng cú pháp, nhưng nạp vào chip thì mạch bị chập chờn, tiêu tốn tài nguyên và sai lệch thời gian.
    3. *Không thể tự kiểm chứng*: AI văn bản chỉ đoán từ tiếp theo, nó không biết cách bấm nút biên dịch trong ModelSim hay Quartus để xem mạch có chạy thật hay không.
* **Lời thoại thuyết trình (45s)**:
  > *"Nhiều người sẽ hỏi: Bây giờ có ChatGPT hay Claude rồi, tại sao không copy đề bài vào đó rồi xin code Verilog?*  
  > *Thực tế nghiên cứu cho thấy, nếu chỉ dùng AI thông thường, tỷ lệ lỗi phần cứng là rất cao. Phần cứng rất khắt khe: chỉ cần AI bịa thêm một chân tín hiệu lạ, hoặc viết thiếu một trường hợp trong lệnh `case` tạo ra chốt ẩn, là toàn bộ chip sẽ bị sai lệch hoặc treo cứng.*  
  > *AI bình thường chỉ 'giỏi nói', nhưng không có công cụ để 'làm và kiểm tra'. Muốn ứng dụng AI vào thiết kế vi mạch thực tế, chúng ta bắt buộc phải có một phương pháp tiếp cận kỹ thuật bài bản và có kỷ luật."*

---

### SLIDE 3: CHIẾN LƯỢC TỐI ƯU CÔNG SỨC: HẠ TẦNG PHỔ THÔNG VS KIẾN TRÚC CỐT LÕI
* **Tiêu đề**: Chiến Lược Giải Phóng Kỹ Sư: Tự Động Hóa Khối Phổ Thông vs Tập Trung Sáng Tạo Cốt Lõi
* **Nội dung hiển thị trên slide (Chia 2 cột rõ ràng)**:
  - **Phần cứng phổ thông & Khối giao tiếp (AI làm thay hoàn toàn)**:
    * Các khối mạch lặp đi lặp lại: Bộ đếm (Counters), Máy trạng thái (FSM), Bộ số học (ALU), Hàng đợi (FIFO), Bộ giải mã LED, Giao tiếp UART/SPI.
    * *Cơ chế xử lý*: Module `knowledge_matcher.py` truy vấn kho vi mạch chuẩn (`hardware_db.json`) để tự động nhận dạng mẫu thiết kế chuẩn công nghiệp.
    * *Giải pháp*: Tự động sinh mã và kiểm chứng hoàn chỉnh tức thì.
  - **Vi kiến trúc đột phá & Lõi tính toán chuyên sâu (Con người tập trung tối ưu)**:
    * Các khối kiến trúc đột phá: Lõi xử lý AI (NPU, Systolic Array, Khối nhân ma trận MAC), Tối ưu hóa tiêu thụ năng lượng và đường trễ tín hiệu.
    * *Giá trị mang lại*: Kỹ sư không còn phải làm việc "thợ gõ code", mà dành toàn bộ chất xám cho phần tinh hoa nhất của dự án.
* **Lời thoại thuyết trình (45s)**:
  > *"Từ thực tế đó, kế hoạch của đồ án bắt đầu bằng **Chiến lược phân tách giữa hạ tầng phần cứng phổ thông và kiến trúc cốt lõi**.*  
  > *Trong mọi hệ thống vi mạch hay đồ án vi xử lý, khối lượng lớn công việc thường rơi vào các khối mạch phổ thông lặp đi lặp lại: ví dụ như bộ đếm thời gian, máy trạng thái FSM điều khiển, bộ chuyển đổi UART, hay giải mã LED 7 đoạn. Đây là những phần bắt buộc phải có, nhưng lại tốn rất nhiều thời gian làm thủ công.*  
  > *Hệ thống của em tích hợp module `knowledge_matcher.py` với cơ sở tri thức vi mạch chuẩn để tự động hóa toàn bộ các khối phổ thông này. Nhờ đó, người kỹ sư được giải phóng hoàn toàn khỏi những tác vụ lặp lại, để dành toàn bộ thời gian và trí tuệ tập trung vào kiến trúc cốt lõi, ví dụ như thiết kế lõi tăng tốc AI hay bộ xử lý chuyên dụng."*

---

### SLIDE 4: ĐỘNG CƠ THỰC THI CHÍNH (SPEC $\rightarrow$ RTL $\rightarrow$ TESTBENCH)
* **Tiêu đề**: Động Cơ Thực Thi Spec2RTL: Biến Ý Tưởng Thành Phần Cứng Tự Động & Nhanh Chóng
* **Nội dung hiển thị trên slide (Kèm các module phần mềm phụ trách)**:
  - **Quy trình 3 pha tự động**:
    1. *Nhận dạng đặc tả [`spec_analyzer.py`]*: Đọc yêu cầu từ file `.txt`, `.md` hoặc văn bản tự do. Tự động bóc tách: Tên module, danh sách chân cắm, độ rộng bus bit, và chức năng hoạt động.
    2. *Sinh mã phần cứng [`rtl_generator.py`]*: Tạo mã Verilog synthesizable chuẩn công nghiệp. Kích hoạt cơ chế `RTLPortEnforcer` ép buộc danh sách chân cắm phải khớp từng cổng với đề bài, loại trừ hoàn toàn chân ma.
    3. *Sinh Testbench tự kiểm tra [`tb_generator.py` & `harness_generator.py`]*: Tự động tạo kịch bản kích thích xung nhịp, reset, và tự so sánh kết quả đầu ra đúng/sai (Self-checking Scoreboard).
    4. *Quét tĩnh cú pháp [`verilog_linter.py`]*: Rà soát triệt tiêu sớm chốt ẩn (inferred latches) trước khi nạp vào bộ mô phỏng.
  - **Thời gian xử lý**: Toàn bộ quá trình diễn ra hoàn toàn tự động chỉ trong vài giây!
* **Lời thoại thuyết trình (45s)**:
  > *"Để hiện thực hóa chiến lược trên, trái tim của luồng chạy chính là **Động cơ thực thi Spec2RTL** với các module chuyên trách.*  
  > *Quy trình cực kỳ đơn giản: Kỹ sư chỉ cần đưa vào file mô tả đề bài (.txt hoặc .md). Module `spec_analyzer.py` sẽ phân tích bóc tách tên mạch và từng chân tín hiệu.*  
  > *Tiếp theo, `rtl_generator.py` sinh mã Verilog chuẩn và kích hoạt bộ ép chân RTLPortEnforcer để đảm bảo không sai lệch một bit nào so với đề bài. Đồng thời, `tb_generator.py` sinh ngay Testbench tự kiểm chứng hoàn chỉnh, và `verilog_linter.py` rà quét sạch chốt ẩn. Toàn bộ khâu này diễn ra tự động chỉ trong vài giây."*

---

### SLIDE 5: VÒNG LẶP PHẢN HỒI THỰC TẾ EDA (CLOSED-LOOP VERIFICATION)
* **Tiêu đề**: Cơ Chế Kiểm Chứng & Tự Sửa Lỗi: Đưa ModelSim Vào Vòng Lặp Phản Hồi Khép Kín
* **Sơ đồ vòng lặp khép kín**:
  $$\text{AI Sinh Code Verilog} \longrightarrow \text{ModelSim Biên Dịch \& Chạy Thử} \longrightarrow \begin{cases} \text{Đạt yêu cầu} \rightarrow \text{Xuất mạch} \\ \text{Có lỗi} \rightarrow \text{Đọc Log} \rightarrow \text{AI Tự Sửa Lại} \end{cases}$$
* **Nội dung hiển thị trên slide (Kèm các module phụ trách)**:
  - **Nguyên tắc "Không tin mù quáng vào AI"**: Lấy các phần mềm EDA tiêu chuẩn công nghiệp (ModelSim 10.1d, Quartus II) làm "Trọng tài chân lý".
  - **Cơ chế phản hồi thông minh (Chuẩn nghiên cứu VeriPrefer - arXiv:2504.15804)**:
    * *Mô phỏng ngầm tự động [`simulator.py`]*: Gọi ModelSim chạy `vlog` và `vsim` ở chế độ batch mode để kiểm tra toàn bộ kịch bản kiểm thử.
    * *Đặc vụ tự sửa lỗi [`reflection_loop.py`]*: Nếu phát hiện lỗi mô phỏng hoặc sai lệch assertion, module sẽ trích xuất chính xác thời điểm nano-giây sai lệch từ log ModelSim, đưa ngược lại cho Reflection Agent tự sửa đúng dòng code bị lỗi.
    * *Đo đạc tài nguyên thực tế [`synthesis_profiler.py`]*: Tự động chạy `quartus_map` để đo số Logic Elements, Flip-Flops và Pin tiêu thụ trên chip FPGA.
    * Đảm bảo mạch xuất ra luôn đạt chuẩn kiểm định trước khi bàn giao.
* **Lời thoại thuyết trình (50s)**:
  > *"Nhưng làm sao để tin chắc rằng mã Verilog mà AI sinh ra chạy đúng tuyệt đối?*  
  > *Câu trả lời nằm ở **Khâu kiểm chứng thực tế với vòng lặp phản hồi khép kín (EDA-in-the-loop)**.*  
  > *Chúng em không bao giờ tin tưởng mù quáng vào mã do AI viết ra. Ngay sau khi sinh code, module `simulator.py` tự động gọi ngầm ModelSim lên biên dịch và chạy mô phỏng. Nếu có lỗi, module `reflection_loop.py` sẽ đọc chính xác dòng thông báo lỗi và thời điểm nano-giây sai lệch từ log ModelSim, rồi tự động sửa lại mã Verilog. Vòng lặp này tự vận hành khép kín cho tới khi nào ModelSim xác nhận toàn bộ test case đều đạt thì mới nghiệm thu."*

---

### SLIDE 6: ĐẦU RA BÀN GIAO: TRỰC QUAN HÓA ĐỂ KIỂM SOÁT THỰC THỂ
* **Tiêu đề**: Mục Tiêu Đầu Ra: "Trực Quan Hóa Để Kiểm Soát Thực Thể" (Sơ Đồ BDF & Sóng Đồ Họa)
* **Nội dung hiển thị trên slide (Kèm các module phụ trách)**:
  1. **Tự động dựng Sơ đồ nguyên lý mạch Quartus BDF [`bdf_generator.py` & `port_auditor.py`]**:
     * Kỹ sư phần cứng cần nhìn thấy sơ đồ mạch thật để kiểm soát kết nối thực thể.
     * `bdf_generator.py`: Tự động tạo file Symbol (`.bsf`) và file sơ đồ khối nguyên lý (`.bdf`). Mở Quartus II lên là thấy đầy đủ khối linh kiện, cổng vào/ra, bus dây được nối thẳng hàng, không bị lỗi đứt dây hay chân lơ lửng.
     * `port_auditor.py`: Thanh tra đối chiếu chéo 4 chiều độc lập: $\text{Spec} \equiv \text{RTL} \equiv \text{BSF} \equiv \text{BDF}$ (Cam kết bảo toàn toàn vẹn cổng tín hiệu).
  2. **Bộ định dạng dạng sóng Waveform trực quan chuẩn EDA [`vwf_generator.py`]**:
     * *ModelSim Waveform GUI (cờ `--gui`)*: Tự động khởi động cửa sổ sóng đồ họa ModelSim phóng to toàn màn hình.
     * *Quartus Waveform Editor [`vwf_generator.py`]*: Tạo file `.vwf` nạp sẵn chân tín hiệu và xung clock vào Quartus II.
     * *Dữ liệu sóng chuẩn công nghiệp*: Xuất file `.vcd` (Value Change Dump) tương thích với mọi công cụ phân tích EDA.
* **Lời thoại thuyết trình (45s)**:
  > *"Điểm khác biệt lớn nhất và là **giá trị cốt lõi ở đầu ra của toàn bộ luồng chạy** chính là nguyên lý: 'Trực quan hóa để kiểm soát thực thể'.*  
  > *Một kỹ sư phần cứng hay thầy cô chấm bài sẽ không bao giờ yên tâm nếu chỉ nhìn vài dòng code chữ trên màn hình. Họ cần nhìn thấy con chip hoạt động như thế nào.*  
  > *Nhờ module `bdf_generator.py` và `port_auditor.py`, hệ thống tự động vẽ ra **Sơ đồ nguyên lý mạch BDF hoàn chỉnh trong Quartus II**, với từng chân cắm được đối chiếu khớp hoàn toàn với đề bài. Đồng thời, hệ thống xuất file sóng Quartus `.vwf` và tự động kích hoạt ModelSim GUI để kiểm tra trực tiếp dạng sóng xung nhịp trên màn hình."*

---

### SLIDE 7: KẾT QUẢ THỰC NGHIỆM ĐO ĐẠC TRÊN CHIP FPGA CYCLONE II
* **Tiêu đề**: Kết Quả Thực Nghiệm: Bảo Toàn Cổng & Đo Đạc Tài Nguyên Thật
* **Nội dung hiển thị trên slide (Kèm công cụ kiểm định)**:
  - **Bộ kiểm thử hồi quy tự động [`test_robustness_battery.py`]**:
    * Thử nghiệm tự động trên đa dạng các họ mạch chuẩn công nghiệp (Đồng hồ số, Khóa số điện tử, Động cơ bước, UART, ALU, Gray Counter, SPI, CRC...).
    * Tỷ lệ hoàn thành: **Toàn bộ kịch bản kiểm thử đều đạt yêu cầu (PASS)**.
    * Lỗi chân cắm (Phantom/Missing Ports): **0 lỗi (Bảo toàn 100% cổng giao tiếp)**.
  - **Tài nguyên đo đạc thực tế trên FPGA Cyclone II (EP2C35F672C6)**:
    | Mạch thí nghiệm | Số phần tử Logic (LEs) | Số Flip-Flop (FFs) | Chân I/O | Trạng thái tổng hợp Quartus |
    | :--- | :--- | :--- | :--- | :--- |
    | **Đồng hồ bấm giờ 0-9 + LED 7 đoạn** | **11 LEs** | **4 FFs** | 14 Pins | **Tối ưu, Netlist sạch, 0 chốt ẩn** |
    | **Khóa số mật mã an toàn** | **27 LEs** | **8 FFs** | 11 Pins | **Tối ưu, Netlist sạch, 0 chốt ẩn** |
    | **Bộ điều khiển động cơ bước 4 pha** | **8 LEs** | **3 FFs** | 7 Pins | **Tối ưu, Netlist sạch, 0 chốt ẩn** |
* **Lời thoại thuyết trình (40s)**:
  > *"Để chứng minh tính khả thi, em đã cho chạy bộ kiểm thử tự động `test_robustness_battery.py` trên nhiều họ mạch phần cứng từ cơ bản đến phức tạp. Kết quả đạt độ chính xác cao, không có bất kỳ chân cắm nào bị ảo giác hay mất tín hiệu.*  
  > *Khi tiến hành tổng hợp trên dòng chip FPGA Altera Cyclone II, các mạch đều tối ưu tài nguyên rất sạch: ví dụ mạch Đồng hồ bấm giờ chỉ tốn 11 Logic Elements và 4 Flip-Flop, không sinh ra chốt ẩn, thời gian sinh mạch và kiểm tra toàn trình diễn ra tức thì."*

---

### SLIDE 8: KỊCH BẢN TRÌNH DIỄN TRỰC TIẾP (LIVE DEMO 3 BƯỚC)
* **Tiêu đề**: Kịch Bản Trình Diễn Thực Tế Tại Chỗ (3 Bước Đơn Giản)
* **Nội dung hiển thị trên slide**:
  - **Bước 1: Soạn đề bài tự nhiên**:
    * Mở file đặc tả [specs/c.txt](file:///D:/altera/13.0sp1/BTVN/Do_An_3/specs/c.txt) (Đồng hồ bấm giờ 0-9 giây kèm giải mã LED 7 đoạn).
  - **Bước 2: Chạy hệ thống tự động**:
    * Chạy lệnh: `python agent/run_spec2rtl.py specs/c.txt --gui`
    * Các module được kích hoạt tự động theo chuỗi: `spec_analyzer` $\rightarrow$ `rtl_generator` $\rightarrow$ `simulator` (ModelSim) $\rightarrow$ `bdf_generator` (Quartus).
  - **Bước 3: Chiêm ngưỡng kết quả đa phương tiện**:
    * Màn hình ModelSim tự động mở cửa sổ Waveform: Xung nhịp đếm 0..9 và mã LED 7 đoạn chạy mượt mà.
    * Mở file `quartus/sch_stopwatch.bdf`: Xem sơ đồ mạch nguyên lý với các cổng I/O rõ ràng trên Quartus II.
* **Lời thoại thuyết trình (35s)**:
  > *"Sau đây em xin phép được thực hiện demo trực tiếp trên máy tính:  
  > Em chỉ cần mở file văn bản mô tả đề bài mạch Đồng hồ bấm giờ và chạy một câu lệnh ngắn: `python agent/run_spec2rtl.py specs/c.txt --gui`.  
  > Ngay lập tức, màn hình console sẽ hiển thị quá trình ModelSim chạy mô phỏng đạt kết quả PASS, cửa sổ sóng ModelSim tự động bật lên, và file sơ đồ BDF đã được tạo sẵn để Thầy Cô kiểm tra trực tiếp trong Quartus II."*

---

### SLIDE 9: TỔNG KẾT & GIÁ TRỊ ĐÓNG GÓP
* **Tiêu đề**: Kết Luận: Hiện Thực Hóa Thiết Kế Vi Mạch Thông Minh
* **Nội dung hiển thị trên slide (3 đóng góp cốt lõi)**:
  1. **Khép kín quy trình**: Giải quyết trọn vẹn luồng từ văn bản mô tả $\rightarrow$ Code RTL $\rightarrow$ Testbench $\rightarrow$ Mô phỏng $\rightarrow$ Sơ đồ mạch BDF.
  2. **Tin cậy công nghiệp**: Triệt tiêu hoàn toàn ảo giác của AI nhờ đưa công cụ EDA ModelSim/Quartus vào làm trọng tài tự sửa lỗi (VeriPrefer).
  3. **Tiết kiệm thời gian vượt trội**: Giải phóng kỹ sư khỏi phần lớn các công việc thủ công lặp lại nhàm chán, giúp sinh viên và kỹ sư tiếp cận thiết kế vi mạch nhanh chóng, trực quan.
* **Lời thoại thuyết trình kết thúc (30s)**:
  > *"Tóm lại, đề tài đã hiện thực hóa thành công một hệ thống tự động hóa thiết kế vi mạch tin cậy, biến những dòng mô tả ý tưởng thành sơ đồ mạch thực tế có thể nạp ngay lên FPGA. Hệ thống giải phóng kỹ sư khỏi phần lớn các công việc chân tay lặp lại, mang lại cách tiếp cận trực quan và hiệu quả cho lĩnh vực bán dẫn.*  
  > *Em xin chân thành cảm ơn Thầy và quý Thầy Cô trong Hội đồng đã chú ý lắng nghe! Em rất mong nhận được câu hỏi và đóng góp từ Thầy Cô."*
