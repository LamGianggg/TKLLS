# KỊCH BẢN SLIDE BÁO CÁO ĐỒ ÁN
## ĐỀ TÀI: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH TỪ ĐẶC TẢ NGÔN NGỮ TỰ NHIÊN (SPEC2RTL)
**Phương pháp: Ứng dụng Mô hình Phản hồi Khép kín EDA & Trực quan hóa Vi mạch**

---

### SƠ ĐỒ KIẾN TRÚC HOẠT ĐỘNG TOÀN TRÌNH (PIPELINE ARCHITECTURE - CHIỀU NGANG)

![Sơ đồ kiến trúc luồng hoạt động Spec2RTL (Chiều ngang)](images/pipeline_architecture_horizontal.png)

```mermaid
flowchart LR
    A["Đặc Tả Kỹ Thuật<br/>(specs/*.txt, prompt)"] --> B["Giai Đoạn 1: Phân Tích Cổng & Tri Thức<br/>• spec_analyzer.py (Bóc tách Port, Bus)<br/>• knowledge_matcher.py (Tra cứu DB)"]
    B --> C["Giai Đoạn 2: Sinh RTL & Testbench<br/>• rtl_generator.py (Verilog chuẩn)<br/>• tb_generator.py (Scoreboard test)<br/>• verilog_linter.py (Quét chốt ẩn)"]
    C --> D["Giai Đoạn 3: Mô Phỏng EDA ModelSim<br/>• simulator.py (vlog & vsim batch)<br/>• synthesis_profiler.py (Đo LEs, Pins)"]
    D -->|Lỗi syntax / Assert Fail| E["Phản Tư Tự Sửa Lỗi<br/>(reflection_loop.py)<br/>Đọc log ns ➔ Sửa code Verilog"]
    E --> C
    D -->|100% Functional Pass| F["Giai Đoạn 4: Bàn Giao & Trực Quan Hóa<br/>• bdf_generator.py (Sơ đồ Quartus BDF)<br/>• vwf_generator.py (Sóng Vector VWF)<br/>• port_auditor.py (Kiểm toán chân 1:1)"]

    classDef inputNode fill:#f1f5f9,stroke:#475569,stroke-width:2px;
    classDef stage1 fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
    classDef stage2 fill:#e0e7ff,stroke:#4338ca,stroke-width:2px;
    classDef stage3 fill:#fef3c7,stroke:#d97706,stroke-width:2px;
    classDef stage4 fill:#dcfce7,stroke:#16a34a,stroke-width:2px;
    classDef reflectNode fill:#fee2e2,stroke:#dc2626,stroke-width:2px;

    class A inputNode;
    class B stage1;
    class C stage2;
    class D stage3;
    class E reflectNode;
    class F stage4;
```

```text
===========================================================================================================================================================
                                              SƠ ĐỒ LUỒNG THIẾT KẾ VI MẠCH CHIỀU NGANG (PANORAMIC WIDESCREEN PIPELINE)
===========================================================================================================================================================
[ ĐẶC TẢ KỸ THUẬT ] ──► [ GĐ 1: PHÂN TÍCH CỔNG ] ──► [ GĐ 2: SINH RTL & TB ] ──► [ GĐ 3: MÔ PHỎNG MODELSIM ] ──────(100% PASS)──────► [ GĐ 4: BÀN GIAO QUARTUS ]
 (specs/*.txt, prompt)    spec_analyzer.py             rtl_generator.py            simulator.py (vlog/vsim)                                 bdf_generator.py (.bdf)
                          knowledge_matcher.py         tb_generator.py             synthesis_profiler.py (LEs/Pins)                         vwf_generator.py (.vwf)
                                                       verilog_linter.py                         │                                          port_auditor.py (1:1)
                                                              ▲                                  │ (Lỗi mô phỏng / Assertion Failed)
                                                              └──────────────────────────────────┘
                                                                    [ PHẢN TƯ TỰ SỬA LỖI ]
                                                                      reflection_loop.py
===========================================================================================================================================================
                                [ ĐIỀU PHỐI TOÀN TRÌNH: run_spec2rtl.py  |  TỰ TÌM CÔNG CỤ EDA: eda_finder.py ]
===========================================================================================================================================================
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
    3. *Sinh Testbench tự kiểm tra [`tb_generator.py`]*: Tự động tạo kịch bản kích thích xung nhịp, reset, và tự so sánh kết quả đầu ra đúng/sai (Self-checking Scoreboard).
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

### SLIDE 7: DEMO
* **Tiêu đề**: DEMO
* **Nội dung hiển thị trên slide**:
  # DEMO
* **Kịch bản thực thi trực tiếp**:
  1. Mở file đặc tả [specs/c.txt](file:///D:/altera/13.0sp1/BTVN/Do_An_3/specs/c.txt).
  2. Chạy lệnh: `python agent/run_spec2rtl.py specs/c.txt --gui`
  3. Quan sát: Cửa sổ ModelSim Waveform GUI tự động hiển thị dạng sóng xung nhịp.
  4. Mở Quartus II xem sơ đồ mạch nguyên lý: `quartus/bcd_to_7seg_anode/sch_bcd_to_7seg_anode.bdf`.
* **Lời thoại thuyết trình (15s)**:
  > *"Sau đây em xin phép được thực hiện demo trực tiếp toàn bộ luồng chạy của hệ thống trên máy tính."*

---

### SLIDE 8: PHÂN TÍCH GIỚI HẠN THỰC NGHIỆM & CA THẤT BẠI ĐIỂN HÌNH
* **Tiêu đề**: Giới Hạn Của Phương Pháp Mẫu Cứng & Phân Tích Hiện Tượng "Chân Lơ Lửng"
* **Nội dung hiển thị trên slide**:
  - **Khảo sát trên 100 đề bài chuẩn hóa (`100_Prompt_Thiet_Ke_Mach.pdf`)**:
    * **~38% bài toán thành công hoàn hảo**: Nằm trong 25 mẫu mạch kinh điển (Counter, Timer, ALU, FSM Vending...).
    * **~62% bài toán rơi vào giới hạn**: Các mạch mới (như `button_debouncer`, MUX/DEMUX đa ngõ vào, SPI...) rơi vào hàm sinh generic.
  - **Bằng chứng thực nghiệm trên Quartus Netlist Viewer (`button_debouncer` do TS. Nguyễn Văn Tình chỉ ra)**:
    * Chân `btn_in` bị cô lập hoàn toàn (dangling pin), không có dây nối vào logic mạch.
    * Hai Flip-Flop ngõ ra chỉ tự đảo trạng thái theo clock ($Q \Leftarrow \sim Q$).
    * Testbench ngây thơ vẫn báo **PASS 100% giả tạo** vì không có kiểm tra ngữ nghĩa.
* **Lời thoại thuyết trình (45s)**:
  > *"Tuy nhiên, với tinh thần nghiên cứu khoa học trung thực và sự phản biện sâu sắc của Thầy TS. Nguyễn Văn Tình, nhóm nhận thấy phương pháp sinh mã theo mẫu cứng (Template) đã chạm trần giới hạn. Khi thử nghiệm trên 100 đề bài chuẩn hóa, hệ thống giải quyết rất tốt khoảng 38% bài toán quen thuộc, nhưng với 62% bài toán mới lạ, hệ thống bộc lộ nhược điểm.*  
  > *Điển hình như mạch khử rung phím `button_debouncer` trên hình: Chân `btn_in` bị cô lập trơ trọi một mình, Flip-Flop tự lật vô nghĩa, nhưng Testbench vẫn báo PASS giả. Điều này chứng minh rằng: **Chúng ta không thể ngồi viết tay hàng nghìn template, mà bắt buộc phải có AI hiểu ngữ nghĩa phần cứng và một bộ Linter bắt chốt ẩn, chân lơ lửng**."*

---

### SLIDE 9: HIỆN THỰC HÓA CHƯNG CẤT TRI THỨC (KNOWLEDGE DISTILLATION & LORA)
* **Tiêu đề**: Đột Phá Kỹ Thuật: Chưng Cất Tri Thức Sang Mô Hình Cục Bộ Qwen2.5-Coder-3B
* **Nội dung hiển thị trên slide (3 Trụ cột hoàn thành 100%)**:
  1. **Nhóm 1 (Dữ liệu & Thẩm định ModelSim)**:
     - Chưng cất tri thức suy luận phần cứng (Hardware CoT) thành **1,098 mẫu sạch**, 100% vượt qua trình biên dịch EDA ModelSim SE 10.1c (`dataset_clean_verified.json`).
     - Đóng gói **1,098 cặp dữ liệu DPO** (Chosen vs Rejected) để căn chỉnh mô hình phạt code có lỗi phần cứng.
  2. **Nhóm 2 (Huấn luyện AI Cục bộ LoRA)**:
     - Tinh chỉnh mô hình `Qwen2.5-Coder-3B` trên Google Colab GPU T4 bằng **Unsloth LoRA 4-bit** (chi phí **0 VNĐ**).
     - Huấn luyện trọn vẹn 1,098 mẫu trong **138 bước (~12 phút)**, xuất file trọng số LoRA adapter 119 MB sẵn sàng chạy offline bảo mật IP.
  3. **Nhóm 3 (Bộ phân tích tĩnh AST Linter)**:
     - Nâng cấp `verilog_linter.py` quét cấu trúc cây cú pháp AST: Bắt chết lỗi chốt ẩn (`case` thiếu `default`, `if` thiếu `else`), chân lơ lửng (dangling input/output) và gán blocking `=` trong `posedge clk`.
* **Lời thoại thuyết trình (50s)**:
  > *"Trước thách thức đó, nhóm đã không dừng lại ở lý thuyết mà lập tức triển khai **Kế hoạch Chưng cất Tri thức (Knowledge Distillation)** chia làm 3 nhánh song song:*  
  > *Nhóm 1 dùng chính ModelSim làm 'Bộ lọc chân lý' để tinh lọc ra 1,098 mẫu vi mạch synthesizable chuẩn mực và 1,098 cặp sở thích DPO. Nhóm 2 sử dụng thư viện tối ưu Unsloth để huấn luyện mô hình Qwen-3B trên GPU T4 Colab hoàn toàn miễn phí, hoàn thành 138 bước train chỉ trong 12 phút. Và Nhóm 3 xây dựng bộ phân tích AST bắt chết lỗi chốt ẩn và chân lơ lửng.*  
  > *Nhờ đó, mô hình nhỏ 3B có thể chạy 100% offline tại phòng lab mà vẫn sở hữu năng lực thiết kế vi mạch chuẩn xác của mô hình lớn."*

---

### SLIDE 10: KẾT QUẢ THỰC NGHIỆM ĐỘT PHÁ (BENCHMARK TUẦN 2)
* **Tiêu đề**: Đánh Giá Thực Nghiệm Toàn Diện: Tỷ Lệ Pass@1 Đạt 100%
* **Bảng kết quả benchmark trên 6 bài toán vi mạch đặc tả thực tế**:

| ID | Tên Vi Mạch (Module) | Phân Loại Kiến Trúc | ModelSim Pass@1 | AST Linter | Logic Elements (LEs) | Flip-Flops (FFs) | Chân I/O | Thời Gian Chạy |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `uart_tx_8bit` | Giao tiếp nối tiếp định thời | **100% PASS** | 100% Sạch | 28 LEs | 17 FFs | 13 Pins | 17.94s |
| 2 | `button_debouncer` | Khử rung phím bấm (Ca của Thầy) | **100% PASS** | 100% Sạch | 6 LEs | 6 FFs | 5 Pins | 7.00s |
| 3 | `bcd_to_7seg_anode` | Giải mã LED 7 đoạn Anode | **100% PASS** | 100% Sạch | 7 LEs | 0 FFs | 11 Pins | 11.48s |
| 4 | `smart_alarm_fsm` | Cảnh báo cháy & an ninh FSM | **100% PASS** | 100% Sạch | 4 LEs | 4 FFs | 9 Pins | 5.09s |
| 5 | `decoder_3to8` | Giải mã địa chỉ 3 sang 8 | **100% PASS** | 100% Sạch | 8 LEs | 0 FFs | 12 Pins | 4.00s |
| 6 | `digital_lock_fsm` | Khóa số điện tử mật mã FSM | **100% PASS** | 100% Sạch | 25 LEs | 9 FFs | 14 Pins | 6.53s |

* **Đối chuẩn Before vs After**:
  - *Tỷ lệ vượt qua mô phỏng (Pass@1)*: Nâng từ **~38%** (Rule-based) lên **100.0% (6/6 bài toán)**.
  - *Giải quyết dứt điểm ca lỗi `button_debouncer`*: Chân `btn_in` được nối 100% vào thanh ghi dịch 3 tầng (`shift_reg <= {shift_reg[1:0], btn_in};`), triệt tiêu hoàn toàn chân lơ lửng!
  - *Tổng thời gian xử lý toàn bộ 6 bài toán*: Chỉ mất **52.05 giây**!
* **Lời thoại thuyết trình (50s)**:
  > *"Và đây là kết quả thực nghiệm minh chứng cho sự đột phá của hệ thống:*  
  > *Khi nhóm đưa 6 bài toán vi mạch đặc tả đa dạng vào kiểm thử toàn trình: Từ UART, giải mã LED, hệ thống cảnh báo FSM, khóa mật mã cho đến mạch khử rung nút bấm.*  
  > *Hệ thống đã đạt **Tỷ lệ Pass@1 tuyệt đối 100%**, và bộ AST Linter xác nhận **100% sạch chốt ẩn và chân lơ lửng**. Đặc biệt, ở bài toán `button_debouncer` do Thầy chỉ ra: Cổng `btn_in` đã được kết nối chuẩn mực vào thanh ghi dịch 3 tầng, mạch chỉ tiêu tốn đúng 6 Logic Elements và 6 Flip-Flops trên chip Cyclone II. Toàn bộ 6 bài toán được phân tích, sinh mã, mô phỏng và xuất sơ đồ Quartus chỉ trong vỏn vẹn 52 giây!"*

---

### SLIDE 11: DEMO MẠCH KHỬ RUNG NÚT BẤM (BUTTON_DEBOUNCER)
* **Tiêu đề**: Demo Trực Quan: Khắc Phục Hoàn Toàn Lỗi Chân Lơ Lửng Trên Quartus II & ModelSim
* **Nội dung demo trực tiếp**:
  1. Mở file đặc tả [specs/b.txt](file:///D:/altera/13.0sp1/BTVN/Do_An_3/specs/b.txt).
  2. Chạy lệnh: `python agent/run_spec2rtl.py specs/b.txt --gui`
  3. **Minh chứng 1**: Báo cáo AST Linter tại Bước 2.5 hiển thị: `PASS (100% SẠCH LATCH & DANGLING)`.
  4. **Minh chứng 2**: ModelSim Waveform GUI hiển thị dạng sóng khử rung: Khi `btn_in` nảy nhiễu, tín hiệu `btn_clean` giữ nguyên ổn định, và xuất đúng 1 xung kích `btn_pressed_pulse`.
  5. **Minh chứng 3**: Mở Quartus II xem file sơ đồ nguyên lý [quartus/button_debouncer/sch_button_debouncer.bdf](file:///D:/altera/13.0sp1/BTVN/Do_An_3/quartus/button_debouncer/sch_button_debouncer.bdf) kết nối thẳng hàng hoàn hảo.
* **Lời thoại thuyết trình (45s)**:
  > *"Sau đây em xin demo trực tiếp ca kiểm thử quan trọng nhất: bài toán `button_debouncer`.*  
  > *Như Thầy Cô thấy trên màn hình: Khi chạy lệnh `run_spec2rtl.py specs/b.txt --gui`, hệ thống chỉ mất 5 giây để hoàn tất toàn bộ quy trình. Bộ Linter báo cáo 0 lỗi chân lơ lửng. Cửa sổ sóng ModelSim mở lên cho thấy khi tín hiệu nút bấm bị rung nảy, mạch lọc sạch hoàn toàn và xuất xung kích chính xác 1 chu kỳ clock. Mở file sơ đồ BDF trong Quartus II, chân `btn_in` được nối dây đầy đủ vào lõi logic. Đây là bằng chứng rõ ràng nhất cho thấy hệ thống đã khắc phục triệt để hạn chế trước đây."*

---

### SLIDE 12: TỔNG KẾT & GIÁ TRỊ ĐÓNG GÓP
* **Tiêu đề**: Kết Luận: Hiện Thực Hóa Thiết Kế Vi Mạch Thông Minh & Tự Chủ
* **Nội dung hiển thị trên slide (4 đóng góp cốt lõi)**:
  1. **Khép kín quy trình từ A $\rightarrow$ Z**: Biến văn bản mô tả tự nhiên thành Code Verilog $\rightarrow$ Testbench $\rightarrow$ Mô phỏng ModelSim $\rightarrow$ Sơ đồ Quartus BDF & Sóng VWF.
  2. **Trọng tài EDA công nghiệp (EDA-in-the-loop)**: Triệt tiêu hoàn toàn ảo giác của AI; đảm bảo mọi dòng mã sinh ra đều synthesizable và verified 100%.
  3. **Chưng cất tri thức thành công (Knowledge Distillation)**: Huấn luyện mô hình cục bộ Qwen-3B với 1,098 mẫu sạch, chạy offline bảo mật IP, chi phí **0 VNĐ**.
  4. **Kiểm soát phần cứng chuyên sâu**: Bộ phân tích AST Linter loại trừ chốt ẩn, chân lơ lửng, đưa tỷ lệ Pass@1 thực nghiệm lên **100%**.
* **Lời thoại thuyết trình kết thúc (30s)**:
  > *"Kính thưa Thầy và quý Thầy Cô trong Hội đồng. Đề tài đã hiện thực hóa thành công một hệ thống tự động hóa thiết kế vi mạch đáng tin cậy. Chúng em không chỉ tạo ra một công cụ sinh mã, mà xây dựng một hạ tầng kỹ thuật khép kín có trọng tài EDA kiểm chứng, có mô hình AI được tinh chỉnh chuẩn công nghiệp và bảo mật tuyệt đối tài sản trí tuệ.*  
  > *Hệ thống giúp giải phóng kỹ sư khỏi phần lớn công việc thủ công lặp lại, mở ra cách tiếp cận trực quan, hiện đại cho sinh viên và kỹ sư trong kỷ nguyên vi mạch bán dẫn.*  
  > *Em xin chân thành cảm ơn Thầy TS. Nguyễn Văn Tình đã luôn định hướng sâu sát và cảm ơn quý Thầy Cô đã chú ý lắng nghe! Em rất mong nhận được câu hỏi và đóng góp từ Hội đồng."*
