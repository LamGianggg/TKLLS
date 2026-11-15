# KỊCH BẢN SLIDE BÁO CÁO ĐỒ ÁN 3
## ĐỀ TÀI: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH SỐ SPEC2RTL & PROMPT2SILICON
**Dựa trên nghiên cứu của NVIDIA Research (arXiv:2506.13905) & CityU HK VeriPrefer (arXiv:2504.15804)**

---

### SLIDE 1: TRANG TIÊU ĐỀ (TITLE SLIDE)
* **Tiêu đề chính**: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH TỪ ĐẶC TẢ NGÔN NGỮ TỰ NHIÊN (SPEC2RTL)
* **Tiêu đề phụ**: Luồng Chuyển Đổi Khép Kín: SPEC $\rightarrow$ GENERATE $\rightarrow$ REVIEW $\rightarrow$ SHIP
* **Người thực hiện**: [Họ và tên Sinh viên]
* **Giảng viên hướng dẫn**: [Họ và tên Thầy giáo]
* **Môi trường EDA**: Altera Quartus II 13.0sp1 & Mentor Graphics ModelSim 10.1d
* **Lời thoại thuyết trình (30s)**:
  > *"Kính thưa Thầy và Hội đồng, đề tài của em tập trung giải quyết bài toán cốt tử trong kỷ nguyên vi mạch hiện đại: Làm sao để từ một yêu cầu đặc tả chức năng bằng văn bản tự nhiên, hệ thống AI có thể tự động sinh ra mã phần cứng Verilog, tự kiểm tra mô phỏng trên ModelSim và tự động xuất ra sơ đồ nguyên lý mạch BDF trong Quartus II mà bảo đảm đúng 100% không có lỗi ảo giác."*

---

### SLIDE 2: ĐẶT VẤN ĐỀ & THÁCH THỨC KỸ THUẬT
* **Tiêu đề**: Vì Sao LLM Truyền Thống Thất Bại Khi Thiết Kế Phần Cứng?
* **Nội dung 3 điểm nghẽn lớn**:
  1. **Khác biệt ngữ nghĩa (Spatial vs Temporal)**: LLM sinh văn bản tuần tự (như Python/C), trong khi phần cứng hoạt động song song trong không gian vật lý theo từng sườn xung nhịp.
  2. **Ảo giác chân cắm (Port Hallucination)**: LLM thường tự ý bịa thêm chân tín hiệu, sai độ rộng bus, hoặc sinh ra chốt ẩn (inferred latches) gây lỗi định thời phần cứng.
  3. **Tỷ lệ lỗi cao (55% Fail)**: Khảo sát của CityU Hong Kong cho thấy nếu chỉ dùng prompt đơn lẻ, code Verilog sinh ra bị lỗi mô phỏng hoặc deadlock tới hơn 45-55%.
* **Lời thoại (45s)**:
  > *"Nếu chúng ta chỉ đưa một prompt vào ChatGPT hay Claude để xin code Verilog, tỷ lệ lỗi lên tới 55%. Code có thể nhìn rất đẹp mắt nhưng khi đưa vào ModelSim hay Quartus thì bị lỗi chốt ẩn, sai bus, hoặc treo mạch vĩnh viễn. Để đưa AI vào công nghiệp bán dẫn, chúng ta không thể tin tưởng mù quáng vào xác suất sinh từ của LLM mà bắt buộc phải có một quy trình kỹ thuật có kiểm chứng khách quan."*

---

### SLIDE 3: MỤC TIÊU & ĐỊNH HƯỚNG CỦA ĐỒ ÁN
* **Tiêu đề**: Mục Tiêu Đề Tài & Định Hướng Phương Pháp
* **Nội dung**:
  * **Mục tiêu**: Xây dựng luồng tự động hóa hoàn toàn từ đặc tả văn bản (`.txt`) $\rightarrow$ Mạch tổng hợp hoàn chỉnh trên FPGA Altera Cyclone II.
  * **Định hướng tiếp cận**:
    - **Không pre-train mò mẫm**: Tiếp cận theo mô hình **Compound AI System** (Hệ thống AI đa thành phần).
    - **Chưng cất tri thức miền**: Tích hợp kho tri thức 539 vi mạch chuẩn công nghiệp (VerilogDB, RTLLM, VerilogEval).
    - **EDA-in-the-Loop**: Đưa trực tiếp ModelSim và Quartus II vào làm "Giám khảo chân lý" kiểm tra tự động.
* **Lời thoại (45s)**:
  > *"Định hướng của đồ án không phải là cố gắng huấn luyện một mô hình ngôn ngữ từ đầu hàng tỷ tham số, mà là xây dựng một hệ thống AI kỹ thuật công nghiệp có kỷ luật. Hệ thống chưng cất các quy tắc phần cứng chuẩn thành bộ khung bất biến, và sử dụng chính các công cụ EDA tiêu chuẩn làm thước đo kiểm định."*

---

### SLIDE 4: KIẾN TRÚC TỔNG THỂ HỆ THỐNG
* **Tiêu đề**: Kiến Trúc Hệ Thống Spec2RTL 4 Bước Chuẩn Hóa
* **Hình vẽ / Sơ đồ luồng**:
  $$\text{SPEC (.txt)} \xrightarrow{\text{B1: Parse}} \text{Contract} \xrightarrow{\text{B2: Gen}} \text{RTL & TB} \xrightarrow{\text{B3: Review}} \text{EDA Simulator} \xrightarrow{\text{B4: Ship}} \text{BDF + Project}$$
* **Nội dung 4 khối chính**:
  1. **Spec Analyzer**: Trích xuất tên Entity, bảng chân I/O, độ rộng bus và phân loại họ mạch.
  2. **RTL & TB Generator**: Sinh mã Verilog synthesizable và Testbench tự kiểm tra (Self-checking Scoreboard).
  3. **EDA Reviewer**: Chạy batch mode ModelSim (`vlog/vsim`) và đo đạc tài nguyên Quartus II (`quartus_map`).
  4. **Packaging & Shipper**: Tạo tự động Symbol (`.bsf`), Schematic (`.bdf`), Waveform (`.vwf`), và Dự án Quartus (`.qpf/.qsf`).
* **Lời thoại (45s)**:
  > *"Kiến trúc của hệ thống chia thành 4 chặng độc lập. Mỗi chặng đều có hợp đồng giao diện chặt chẽ: Chặng 1 phân tích đề bài; Chặng 2 sinh code Verilog và Testbench; Chặng 3 đưa thẳng vào ModelSim biên dịch và chạy mô phỏng; và Chặng 4 tự động đóng gói toàn bộ dự án để kỹ sư có thể mở ngay trên Quartus II."*

---

### SLIDE 5: LUỒNG THỰC THI CHI TIẾT (DEEP DIVE PIPELINE)
* **Tiêu đề**: Chi Tiết Chu Trình Kỹ Thuật: Spec $\rightarrow$ Generate $\rightarrow$ Review $\rightarrow$ Ship
* **Bảng các bước thực thi**:
  | Chặng | Tên bước | Công cụ phụ trách | Đầu ra kỹ thuật |
  | :--- | :--- | :--- | :--- |
  | **Bước 1** | Spec Ingestion | `spec_analyzer.py` | Bảng chân I/O JSON bất biến (Hardware Contract) |
  | **Bước 2** | RTL & TB Gen | `rtl_generator.py`, `tb_generator.py` | `src/{entity}.v`, `sim/tb_{entity}.v`, Test Harness |
  | **Bước 3** | Review & Audit | `simulator.py`, `port_auditor.py` | Log ModelSim 10.1d, Bảng Scoreboard 100% PASS |
  | **Bước 4** | Packaging | `bdf_generator.py`, `vwf_generator.py` | `quartus/{entity}.bdf`, `.bsf`, `.qpf`, `.vwf`, HTML |
* **Lời thoại (60s)**:
  > *"Điểm đặc biệt ở Bước 3 là bộ linter tĩnh VerilogDB sẽ quét triệt tiêu chốt ẩn trước khi nạp vào ModelSim. Nếu có bất kỳ vi phạm assertion nào, vòng lặp phản hồi VeriPrefer sẽ đọc log sai lệch nano giây và tự động sửa đúng dòng gây lỗi."*

---

### SLIDE 6: CÔNG NGHỆ ĐỘT PHÁ 1: BẢO TOÀN GIAO DIỆN CHÂN (PORT INVARIANT)
* **Tiêu đề**: Loại Trừ 100% Ảo Giác Chân Cắm (Zero-Defect Port Invariant)
* **Vấn đề giải quyết**: Tránh hiện tượng mạch sinh ra bị thiếu chân (như mất chân `seg` giải mã 7 đoạn) hoặc bịa thêm chân lạ.
* **Cơ chế hoạt động**:
  - **`RTLPortEnforcer`**: Ép buộc danh sách cổng của module Verilog phải khớp từng bit 1:1 với đặc tả người dùng.
  - **`PortAuditor`**: Thanh tra đối chiếu chéo 4 chiều độc lập:  
    $$\text{Spec Ports} \equiv \text{RTL Ports} \equiv \text{BSF Symbol} \equiv \text{BDF Schematic}$$
  - Nếu phát hiện bất kỳ cổng ma (phantom) hoặc thiếu chân: Tự động từ chối và tái đồng bộ hóa trước khi ship.
* **Lời thoại (45s)**:
  > *"Trước đây, các hệ thống AI thường bị lỗi khi sinh sơ đồ BDF trong Quartus: chân cắm trong code Verilog một đằng, mà chân trên sơ đồ nguyên lý một nẻo, khiến dây bị đứt hoặc báo lỗi Unconnected Port. Chúng em đã phát triển bộ đôi RTLPortEnforcer và PortAuditor để kiểm tra chéo 4 chiều, cam kết 100% cổng từ đề bài được giữ nguyên vẹn trên sơ đồ mạch BDF."*

---

### SLIDE 7: CÔNG NGHỆ ĐỘT PHÁ 2: HỆ SINH THÁI ĐỒ HỌA TRỰC QUAN ĐA NỀN TẢNG
* **Tiêu đề**: Đóng Gói Toàn Diện: Xem Sơ Đồ & Dạng Sóng Mọi Lúc Mọi Nơi
* **Hệ sinh thái bàn giao gồm 5 định dạng**:
  1. **Quartus Schematic (`.bdf`)**: Mở trực tiếp trong Quartus II Schematic Editor, đầy đủ chân pin, bus wire và tên khối.
  2. **Quartus Symbol (`.bsf`)**: Biểu tượng khối chuẩn để kéo thả vào các dự án lớn hơn.
  3. **Quartus Waveform (`.vwf`)**: Nạp sẵn các chân I/O và xung clock vào Quartus Waveform Simulator.
  4. **ModelSim 1-Click GUI (`view_waveform.bat`)**: Nhấp đúp chuột là tự động phóng to toàn màn hình dạng sóng trong ModelSim.
  5. **Interactive Web Waveform (`waveform.html`)**: Xem dạng sóng tương tác bằng SVG trực tiếp trên trình duyệt web không cần cài phần mềm nặng.
* **Lời thoại (45s)**:
  > *"Sau khi hoàn tất, hệ thống không chỉ trả về 1 file code trơ trọi, mà xuất ra toàn bộ hệ sinh thái đồ họa hoàn chỉnh. Thầy có thể xem sơ đồ khối BDF trong Quartus II, xem sóng trong ModelSim, hoặc mở ngay file HTML trên trình duyệt để kiểm tra dạng sóng trực quan."*

---

### SLIDE 8: THỰC NGHIỆM & ĐO ĐẠC TRÊN BENCHMARK QUỐC TẾ
* **Tiêu đề**: Kết Quả Thực Nghiệm Trên 3 Bộ Benchmark Quốc Tế
* **Số liệu thực tế**:
  * **Test Battery (20 họ mạch chuẩn)**: Đạt **20/20 PASS (100.0%)** với 0 chân ma, 0 lỗi cú pháp.
  * **NVIDIA VerilogEval Benchmark**: 100% qua các bài kiểm thử cơ sở.
  * **HKUST RTLLM Benchmark**: Tổng hợp thành công các mạch hệ thống phức tạp (ALU, BCD, FSM, Multiplier).
  * **Tài nguyên tổng hợp trên FPGA Altera Cyclone II (EP2C35F672C6)**:
    - Module Đồng hồ bấm giờ 0-9: tốn **11 LEs, 4 Flip-Flops, 14 Pins**.
    - Module Khóa số bảo mật: tốn **27 LEs, 8 Flip-Flops**.
    - Thời gian tổng hợp và mô phỏng trung bình: **3.5 đến 4.5 giây/mạch**.
* **Lời thoại (45s)**:
  > *"Để chứng minh tính tổng quát, hệ thống đã được thử nghiệm trên 20 họ mạch phần cứng từ dễ đến phức tạp và đo đạc tài nguyên trên FPGA Cyclone II. Toàn bộ các mạch đều tổng hợp ra netlist sạch, không chốt ẩn, thời gian xử lý toàn trình chỉ từ 3 đến 5 giây."*

---

### SLIDE 9: KỊCH BẢN DEMO THỰC TẾ TRÊN MÁY (LIVE DEMO WORKFLOW)
* **Tiêu đề**: Kịch Bản Trình Diễn Trực Tiếp (Live Demo)
* **Quy trình 3 bước demo cho Hội đồng**:
  1. **Bước 1**: Mở file đặc tả [specs/c.txt](file:///D:/altera/13.0sp1/BTVN/Do_An_3/specs/c.txt) (Đồng hồ bấm giờ 0-9 kèm LED 7 đoạn).
  2. **Bước 2**: Chạy lệnh `demo.bat` $\rightarrow$ chọn bài [3].
  3. **Bước 3**: Xem trực tiếp kết quả:
     - Console ModelSim in ra: `Functional Accuracy: 100.0 PERCENT (PASS)`.
     - Cửa sổ dạng sóng ModelSim tự động bật lên hiển thị rõ xung clk, giá trị count 0..9 và mã seg LED 7 đoạn.
     - Mở tệp `quartus/sch_stopwatch.bdf` trong Quartus II để thấy sơ đồ khối linh kiện hoàn chỉnh.
* **Lời thoại (30s)**:
  > *"Sau đây em xin phép được trình diễn trực tiếp kịch bản demo: Em khởi động launcher demo.bat, chọn mạch Đồng hồ bấm giờ. Chỉ sau 4 giây, ModelSim tự động mở cửa sổ sóng và Quartus II đã sẵn sàng sơ đồ nguyên lý mạch."*

---

### SLIDE 10: KẾT LUẬN & HƯỚNG PHÁT TRIỂN TIẾP THEO
* **Tiêu đề**: Kết Luận & Hướng Mở Rộng
* **Kết luận**:
  - Đã xây dựng thành công luồng tự động hóa thiết kế vi mạch Spec2RTL loại trừ 100% ảo giác chân cắm.
  - Tương thích hoàn toàn với bộ công cụ công nghiệp Quartus II 13.0sp1 và ModelSim 10.1d.
  - Đóng gói ngân hàng 100 đề bài đặc tả kỹ thuật chuẩn hóa (`100_Promt_Thiet_Ke_Mach.pdf`).
* **Hướng phát triển**:
  - Mở rộng hỗ trợ chuẩn giao tiếp AXI4 / Avalon Bus cho các SoC đa lõi.
  - Tích hợp thêm khâu bố trí và định tuyến tự động Place & Route vật lý.
* **Lời thoại (30s)**:
  > *"Em xin chân thành cảm ơn Thầy và quý Thầy Cô trong Hội đồng đã lắng nghe. Em rất mong nhận được những nhận xét và câu hỏi đóng góp của Thầy Cô!"*
