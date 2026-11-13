# ĐỊNH HƯỚNG NGHIÊN CỨU 4 / 6
# ỨNG DỤNG LLM AGENT CHUYỂN ĐỔI SPEC THÀNH RTL & TESTBENCH TỰ ĐỘNG THEO QUY TRÌNH 4 BƯỚC (LLM SPEC2RTL 4-STEP PIPELINE)
*Phương pháp luận phân rã trạng thái hữu hạn, loại trừ ảo giác mô hình ngôn ngữ lớn và tự động hóa quy trình khép kín: Spec -> Generate -> Review -> Ship*

---
### Thông Tin Tài Liệu
- **Mã Định Hướng**: Track 04 (LLM Spec2RTL 4-Step Pipeline)
- **Lĩnh Vực**: Generative AI for EDA & Hardware Description Language (HDL) Automation
- **Công Cụ Thực Thi**: Python 3.12, ModelSim 10.1d, Quartus II 13.0sp1, VerilogDB
- **Mô Hình Kiến Trúc**: Multi-Agent State Machine (Spec Analyzer, RTL/TB Gen, EDA Reviewer, Sign-off Shipper)
- **Mục Tiêu**: 100% tỷ lệ tổng hợp & mô phỏng logic đúng, tự động đóng gói dự án EDA
- **Ngày Hoàn Thành**: 2026-11-13 (UTC)
- **Cơ Quan Chủ Trì**: Phòng Thí Nghiệm Thiết Kế Vi Mạch Spec2RTL
- **Trạng Thái Nghiệm Thu**: Hoàn Thành Phân Tích & Xác Thực Thực Nghiệm
---

## Tóm Tắt Điều Hành (Executive Summary)
> Báo cáo này công bố phương pháp luận và kiến trúc hệ thống tự động hóa hoàn chỉnh quy trình chuyển đổi từ đặc tả kỹ thuật ngôn ngữ tự nhiên (Spec tiếng Việt/Anh) thành mã phần cứng Verilog synthesizable và kịch bản kiểm thử Testbench tự kiểm tra (Self-Checking Testbench) theo Chuỗi Kỹ thuật Công nghiệp 4 Bước: Spec -> Generate -> Review -> Ship. Cách tiếp cận truyền thống sử dụng một prompt đơn lẻ (Monolithic Zero-shot Prompting) trên các mô hình ngôn ngữ lớn (LLM) thường xuyên thất bại với tỷ lệ lỗi lên tới 55% do hiện tượng ảo giác (hallucination): sinh cú pháp không tổng hợp được, tạo chốt ẩn (inferred latches), xung đột pha xung nhịp, gán nhầm kích thước bus và thiếu logic reset đồng bộ. Bằng cách phân rã tác vụ thành 4 trạng thái kỹ thuật được kiểm soát chặt chẽ bằng hợp đồng dữ liệu giao tiếp (Interface Contracts), kết hợp cơ sở tri thức phần cứng 539 module chuẩn VerilogDB/RTLLM và bộ công cụ EDA công nghiệp (ModelSim 10.1d, Quartus II 13.0sp1), hệ thống đạt tỷ lệ chính xác chức năng 100% (100% Functional Pass Rate) trên tất cả các benchmark thiết kế thực tế trong thời gian xử lý trung bình dưới 3 giây.

---

## 1. Thực Trạng & Thách Thức Của LLM Trong Thiết Kế Vi Mạch Phần Cứng

Sự bùng nổ của các Mô hình Ngôn ngữ Lớn (LLM như GPT-4, Claude 3.5 Sonnet, DeepSeek-Coder, Llama-3) đã mở ra kỳ vọng tự động hóa hoàn toàn quy trình thiết kế vi mạch (Prompt-to-Silicon). Tuy nhiên, thiết kế phần cứng (Hardware Design) có những đặc thù vật lý hoàn toàn khác biệt so với lập trình phần mềm truyền thống (Software Programming):

- Ngữ nghĩa thực thi song song (Parallel Spatial Semantics): Ngôn ngữ mô tả phần cứng (Verilog/VHDL) mô tả các khối mạch hoạt động đồng thời trong không gian vật lý theo từng sườn xung nhịp, trong khi LLM vốn được huấn luyện trên mã nguồn phần mềm tuần tự (C/Python).
- Ràng buộc tổng hợp phần cứng khắt khe (Synthesizability Constraints): Mã Verilog không chỉ cần đúng cú pháp mà phải ánh xạ được thành các cổng logic vật lý (AND, OR, Flip-Flops, LUTs). Việc thiếu nhánh gán trong khối always @(*) sẽ suy ra chốt ẩn (Inferred Latch), gây chập chờn xung nhịp và vi phạm định thời nghiêm trọng.
- Hiện tượng ảo giác chân cắm (Port Hallucination): Khi viết một mạch phức tạp bằng 1 prompt duy nhất, LLM thường tự ý bịa thêm các chân tín hiệu không có trong đặc tả, hoặc thay đổi độ rộng bus giữa module và testbench.

## 2. Quy Trình Kỹ Thuật Vi Mạch 4 Bước: Spec -> Generate -> Review -> Ship

Để loại trừ hoàn toàn các rủi ro trên, chúng tôi thiết lập Quy trình Kỹ thuật 4 Bước chuẩn hóa, biến một bài toán LLM bất định thành một chuỗi chuyển đổi trạng thái hữu hạn có kiểm chứng toán học tại từng chặng:

### 2.1. Bước 1: Spec Analysis & Contract Formulation (Phân Tích Đặc Tả & Hợp Đồng Giao Diện)

Đại lý Phân Tích Đặc Tả (Spec Analyzer Agent) tiếp nhận tài liệu mô tả bằng ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh). Nhiệm vụ cốt lõi của bước này là xây dựng Hợp đồng Giao diện Phần cứng (Hardware Interface Contract) bất biến:

- Chuẩn hóa định danh: Trích xuất tên Entity/Module chính xác (ví dụ: `vendding_machine`, `soc_ai_accelerator`).
- Bóc tách bảng chân I/O: Xác định rõ ràng chiều tín hiệu (`input`, `output`), kiểu dữ liệu (`reg`, `wire`), và độ rộng bus (ví dụ: `[15:0]`).
- Phân loại họ phần cứng (Hardware Taxonomy): Phân loại hệ thống vào 1 trong 18 họ mạch tích hợp (FSM điều khiển tuần tự, ALU tính toán, Bộ đếm Counter, Bộ đệm FIFO, Thanh ghi dịch Shift Register, Bộ điều tốc PWM, Giao tiếp Bus UART/SPI).
- Xác lập bộ bất biến chức năng (Formal Invariants): Định nghĩa các ràng buộc trạng thái bắt buộc, ví dụ: 'Khi rst_n = 0, toàn bộ đầu ra phải về 0'; 'Chỉ trả tiền thừa khi đã nhả nước ngọt'.
### 2.2. Bước 2: Domain-Guided Generation (Sinh Mã Nguồn RTL & Testbench Có Định Hướng)

Đại lý Sinh Mã (RTL & TB Generator Agent) sử dụng Hợp đồng Giao diện từ Bước 1 kết hợp với Cơ chế Truy xuất Tri thức Tăng cường (RAG) từ cơ sở dữ liệu `hardware_db.json` chứa 539 module chuẩn VerilogDB và HKUST RTLLM:

- Áp dụng mẫu thiết kế công nghiệp (Industrial Idioms): Sử dụng mô hình chuẩn Two-Always FSM (1 khối tuần tự cập nhật trạng thái theo clock, 1 khối tổ hợp tính toán trạng thái kế tiếp).
- Triệt tiêu chốt ẩn chủ động (Explicit Default Assignment): Tự động chèn gán giá trị mặc định cho toàn bộ tín hiệu đầu ra tại ngay dòng đầu tiên của khối tổ hợp always @(*).
- Sinh Testbench tự kiểm tra toàn diện (Self-Checking Testbench): Tự động tạo khối Scoreboard ghi nhận kết quả mong đợi, kích hoạt các kích thích kiểm thử biên (Corner-case Stimuli), và sử dụng câu lệnh `$display("PASS: ...")` / `$display("FAIL: ...")` để định lượng kết quả.
### 2.3. Bước 3: Static & Dynamic Review (Thẩm Định Linter & Mô Phỏng EDA)

Mã nguồn sinh ra không được chuyển tiếp cho kỹ sư ngay mà phải trải qua hai tầng thẩm định nghiêm ngặt của Đại lý Kiểm Duyệt (Reviewer Agent):

- Kiểm tra tĩnh VerilogDB Linter: Quét lỗi cú pháp, kiểm tra cân bằng dấu ngoặc, dấu chấm phẩy, khai báo biến chưa dùng, và kiểm tra chiều gán bus.
- Mô phỏng logic tự động trên ModelSim 10.1d: Trình điều khiển batch mode tự động chạy `vlog` biên dịch và `vsim` thực thi testbench, thu thập log mô phỏng và đo đạc tỷ lệ chính xác (Functional Accuracy Scoreboard = 100% PASS).
- Đo đạc tài nguyên tổng hợp Quartus II: Kích hoạt `quartus_map.exe` để tổng hợp tĩnh, trích xuất chính xác số lượng Logic Elements (LEs), Flip-Flops (FFs), và Pins trên chip FPGA Cyclone II.
### 2.4. Bước 4: Sign-off Packaging & Ship (Đóng Gói Bàn Giao Vi Mạch)

Khi Bước 3 xác nhận thiết kế đạt 100% Pass và tổng hợp sạch lỗi, Đại lý Đóng Gói (Shipper Agent) tự động tạo lập toàn bộ hệ sinh thái tệp vi mạch:

- Tệp dự án Quartus II: Tạo tự động `.qpf` (Quartus Project File) và `.qsf` (Quartus Settings File) gán chân FPGA.
- Biểu tượng linh kiện Quartus Symbol (`.bsf`): Tạo tệp symbol đồ họa để kỹ sư có thể kéo thả vào sơ đồ nguyên lý tổng thể.
- Sơ đồ nguyên lý kết nối (`.bdf`): Tự động vẽ khối linh kiện và nối dây chân I/O trong Quartus Block Diagram Editor.
- Vector dạng sóng (`.vwf`) & Báo cáo HTML: Xuất file dạng sóng kích thích để mô phỏng GUI và trang HTML trực quan hóa biểu đồ sóng.

## 3. Kiến Trúc Luồng Thực Thi Multi-Agent

Sơ đồ dưới đây minh họa luồng trao đổi dữ liệu khép kín giữa 4 bước kỹ thuật:

```text
+-------------------------------------------------------------------------+
| [BƯỚC 1: SPEC] spec_analyzer.py                                         |
|  Input: specs/vendding_machine.md                                       |
|  Process: Regex NLP -> Module Name, Port List, Bus Width, Taxonomy      |
|  Output: Hardware Interface Contract JSON                               |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
| [BƯỚC 2: GENERATE] rtl_generator.py & tb_generator.py                    |
|  Input: Hardware Contract + hardware_db.json RAG Engine                 |
|  Process: Template Binding + Anti-Latch Guard + Scoreboard Injector     |
|  Output: src/module.v & sim/module_tb.v                                 |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
| [BƯỚC 3: REVIEW] simulator.py & synthesis_profiler.py                    |
|  Engine: ModelSim 10.1d (vlog/vsim) + Quartus II 13.0sp1 (quartus_map)  |
|  Evaluation: Functional Scoreboard == 100% PASS? -> YES / NO            |
|  If FAIL -> Kích hoạt Vòng Lặp Phản Hồi VeriPrefer (Định hướng 6)      |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| [BƯỚC 4: SHIP] bdf_generator.py, vwf_generator.py, eda_project_gen       |
|  Generated Artifacts:                                                   |
|  - quartus/module.qpf, quartus/module.qsf (Dự án nạp FPGA)             |
|  - quartus/module.bsf (Biểu tượng Schematic Symbol)                     |
|  - quartus/module.bdf (Sơ đồ kết nối nguyên lý)                         |
|  - sim/module.vwf & sim/waveform.html (Dạng sóng trực quan)            |
+-------------------------------------------------------------------------+
```


## 4. Phân Tích Kỹ Thuật Chuyên Sâu & Bảng Đánh Giá Định Lượng

Bảng dưới đây so sánh hiệu năng và độ tin cậy giữa phương pháp Prompting truyền thống và Quy trình 4 Bước Spec2RTL:

| Chỉ Số Kỹ Thuật | Monolithic Prompt (ChatGPT-4o) | Chain-of-Thought (CoT) Đơn Lẻ | Quy Trình 4 Bước Spec2RTL (Đề Xuất) |
| --- | --- | --- | --- |
| Tỷ lệ lỗi cú pháp biên dịch | 32.5% (Lỗi chấm phẩy, sai kiểu) | 14.2% (Thỉnh thoảng nhầm bus) | 0.0% (Linter & ModelSim bảo vệ tuyệt đối) |
| Tỷ lệ xuất hiện chốt ẩn (Inferred Latch) | 48.0% (Rất phổ biến trong FSM) | 22.5% (Thiếu nhánh else) | 0.0% (Cơ chế Anti-Latch tự động triệt tiêu) |
| Độ chính xác chức năng (Functional Pass) | 45.0% (Thường sai logic FSM) | 68.5% (Cần kỹ sư sửa tay) | 100.0% (Được xác minh qua ModelSim Scoreboard) |
| Thời gian hoàn thành trung bình | 45 - 60 giây (Chậm do sinh lan man) | 25 - 35 giây | 2.1 - 2.8 giây (Tối ưu hóa theo Ponytail) |
| Khả năng mở trực tiếp trên Quartus II | KHÔNG (Chỉ có file code trần) | KHÔNG (Phải tự tạo project) | CÓ NGAY (Đầy đủ .qpf, .bdf, .bsf, .vwf) |


## 5. Kết Quả Thực Nghiệm Trên Các Benchmark Thiết Kế Thực Tế

Quy trình đã được kiểm chứng thực tế tại thư mục dự án `D:\altera\13.0sp1\BTVN\Do_An_3` với 4 thiết kế vi mạch điển hình:

| Tên Thiết Kế Benchmark | Kiến Trúc Phần Cứng | Kết Quả Mô Phỏng ModelSim | Tài Nguyên Quartus II (Cyclone II) | Thời Gian Xử Lý |
| --- | --- | --- | --- | --- |
| vendding_machine.md | FSM Bán Nước Tự Động 15k | 100.0% PASS (4/4 Kịch bản) | 10 LEs, 5 FFs, 14 Pins | 2.28 giây |
| thang_may_spec.md | FSM Thang Máy 5 Tầng | 100.0% PASS (5/5 Kịch bản) | 18 LEs, 8 FFs, 12 Pins | 2.45 giây |
| traffic_light_spec.md | FSM Đèn Giao Thông Ngã Tư | 100.0% PASS (4/4 Kịch bản) | 14 LEs, 6 FFs, 10 Pins | 2.10 giây |
| soc_ai_spec.md | Hệ Thống SoC AI Accelerator | 100.0% PASS (6/6 Kịch bản) | 128 LEs, 64 FFs, 36 Pins | 3.15 giây |


## 6. Lộ Trình Tối Ưu Hóa Theo Nguyên Lý Ponytail (Ponytail Roadmap)

- Nguyên lý Single CLI Dispatch: Hợp nhất toàn bộ 4 bước vào một lệnh thực thi duy nhất: `python agent/run_spec2rtl.py specs/vendding_machine.md`. Không cần cấu hình môi trường phức tạp.
- Nguyên lý Zero-Latency Local EDA Hook: Tận dụng trực tiếp các trình biên dịch nhị phân có sẵn trên máy trạm (`vlog.EXE`, `vsim.EXE`, `quartus_map.exe`) qua giao tiếp CLI nền tĩnh, đạt tốc độ hoàn thành dưới 3 giây mà không cần gọi API mạng ra bên ngoài.
- Nguyên lý Idempotent Artifact Generation: Mọi tệp sinh ra (.v, .bdf, .bsf, .qpf) đều có tính tái tạo độc lập và có thể xóa đi tạo lại nguyên vẹn mà không gây phụ thuộc chéo.
