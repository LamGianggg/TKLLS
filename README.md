# ĐỒ ÁN 3: HỆ THỐNG SPEC2RTL & PROMPT2SILICON
## Tác Tử AI Tự Động Hóa Thiết Kế và Kiểm Thử Vi Mạch Số Từ Đặc Tả Ngôn Ngữ Tự Nhiên

---

## 1. Tổng Quan & Bản Chất Dự Án (Executive Summary)

**Spec2RTL & Prompt2Silicon** là một hệ thống **Kỹ sư vi mạch ảo (Autonomous EDA Agent)**, có khả năng chuyển hóa các yêu cầu bài toán thiết kế phần cứng viết bằng ngôn ngữ tự nhiên (Tiếng Việt hoặc Tiếng Anh) thành:
1. **Mã nguồn phần cứng Verilog synthesizable** (`src/*.v`) đạt chuẩn công nghiệp IEEE 1364-2001.
2. **Bộ Testbench tự kiểm tra (Self-checking Testbench)** (`sim/tb_*.v`) với Verification Scoreboard.
3. **Mô phỏng EDA tự động trên ModelSim**: Khép kín vòng lặp phản xạ (Closed-Loop Reflection Loop) để bắt log lỗi và tự sửa mã nguồn cho tới khi đạt **100% Functional Pass**.
4. **Tự động sinh toàn bộ tài nguyên Altera Quartus II**: Khởi tạo Project (`.qpf`, `.qsf`), Khối linh kiện (`.bsf`), Sơ đồ nguyên lý nối dây Schematic (`.bdf`), và Dạng sóng Vector Waveform (`.vwf`) tương thích hoàn toàn với Quartus II 13.0sp1.

---

## 2. Kiến Trúc Hoạt Động & Workflow Chi Tiết (Spec2RTL-Agent Fig. 3 Adapted)

![Kiến trúc hệ thống Spec2RTL & Prompt2Silicon (Bản địa hóa từ Spec2RTL-Agent Fig. 3)](docs/images/spec2rtl_fig3_adapted.png)

> *Nguyên tắc cốt lõi: **AI chịu trách nhiệm suy luận và viết mã Verilog, còn các công cụ phần cứng thật (`AST Linter`, `ModelSim`, `Quartus II`) làm trọng tài chấm bài và ép chuẩn.** Hệ thống chia thành **2 vòng chạy**: vòng chạy trực tuyến cho từng đề bài (Cụm 1 $\to$ `Implementation Plan` $\to$ Cụm 2 $\leftrightarrow$ Cụm 3 $\to$ Cụm 4) và vòng chưng cất ngoại tuyến chuẩn bị trọng số AI (Cụm 5).*

### 2.1. Đầu vào: `Đặc tả (Spec)` (Hộp vàng cam bên trái)
* Tiếp nhận file đặc tả mạch số (`.txt` / `.md` trong `specs/`, hoặc trích từ `docs/100_Prompt_Thiet_Ke_Mach.pdf`), hỗ trợ cả **Tiếng Việt có dấu / không dấu** lẫn **Tiếng Anh** (dạng bảng Markdown, gạch đầu dòng hoặc văn xuôi).
* Ba mũi tên xanh đẩy nguyên văn đặc tả song song vào 3 bước phân tích đầu tiên trong **Cụm 1**.

### 2.2. Cụm 1 — `1. Iterative Understanding & Planning` (`agent/spec_analyzer.py`, `agent/knowledge_matcher.py`)
Cụm này chạy tuần tự từ trên xuống qua **4 hộp kiểm chéo** để khóa chặt hợp đồng chân cắm và loại bỏ đề bài sai miền trước khi sinh code:
1. **`Spec & Port Analyzer` (`spec_analyzer.py`):**
   * Chuẩn hóa tiếng Việt không dấu (`remove_vietnamese_accents()`), bóc tên module (`extract_module_name()`), và trích danh sách cổng `input`/`output`/`inout` + độ rộng bus `[N-1:0]` theo **3 tầng ưu tiên** (`extract_ports()`: Bảng Markdown $\to$ Danh sách $\to$ Văn xuôi).
2. **`Domain & 30% Guard` (Lá chắn đầu vào theo chiến lược 70/30):**
   * **Trạng thái dừng `REJECTED (OUT OF SCOPE)` (`check_unsupported_domain()`):** Chặn sớm và giải thích lý do nếu đề thuộc mạch tương tự (`ANALOG_AMS`: `op-amp`, `analog`, `bandgap`, `analog pll`), khối vật lý cao tần (`HIGH_SPEED_PHY`: `pcie/ddr4/ddr5/serdes/usb3 phy`), hoặc văn bản không liên quan phần cứng (`IRRELEVANT_INPUT`).
   * **Trạng thái dừng `REJECTED (ARCHITECTURAL BOUNDARY)` (`is_30_percent_architecture()`):** Chặn sinh nguyên khối 1-prompt đối với **30% hệ thống lõi phức hợp** (`SOC_AI`, `top_soc`, `systolic array processor`, `ai accelerator core`, `npu_core`, `dma+relu+ai`), yêu cầu tách nhỏ thành từng khối phổ thông độc lập.
   * Nếu vượt qua 2 cửa này, bài toán thuộc **70% khối hạ tầng phổ thông** (Counter, Timer, UART/SPI/I2C, FIFO, ALU, Decoder, PWM, FSM…) và đi tiếp xuống bước 3.
3. **`Hybrid RAG Retrieval (DB)` (`knowledge_matcher.py`):**
   * Tra cứu thiết kế tham khảo trên kho tri thức gồm **`hardware_db.json` (690 mẫu sạch)** + các mẫu Teacher CoT nạp trong RAM từ **`dataset_teacher_distilled.json`**.
   * Dùng **RRF (Reciprocal Rank Fusion)** trộn 4 tín hiệu song song: từ điển `KHAI_NIEM_PHAN_CUNG` + **BM25** (khóa chặt tên giao thức, bit-width) + **Character 3-gram Jaccard** + **Semantic Vector** (tự động chọn `fastembed` ONNX CPU $\to$ cache `hardware_embeddings.npz` + `gemini-embedding-001` $\to$ fallback offline `TfidfVectorizer + TruncatedSVD`).
   * Xuất 2 nhánh: (a) đưa mức độ khớp (`EXACT` $\ge 0.70$, `SIMILAR` $\ge 0.35$, `CUSTOM` $< 0.35$) xuống hộp 4, và (b) **mũi tên đứt `RAG`** gọi `format_rag_context(spec_text, top_k=2)` (ngưỡng $\ge 0.28$, tối đa `45` dòng/mẫu) gửi sang `Qwen2.5-3B DPO`.
4. **`Port & Plan Verifier` (kiểm chéo $\uparrow\downarrow$ với Hộp 3):**
   * Đối soát lại **Port Contract** với phân loại mạch và kết quả RAG để chốt chiến lược sinh mã (`VENDING`/`ELEVATOR`/`TRAFFIC`, luồng AI `--use-distilled`, hoặc `RTLGenerator`), rồi đẩy qua mũi tên **`Impl. Plan`**.

### 2.3. Thanh giữa trên — `Implementation Plan (Kế hoạch Thiết kế Trực tiếp)`
Thay thế hoàn toàn tầng `Sub-Func C++ / HLS` của bài báo gốc bằng **4 gói kế hoạch chốt cứng** đi thẳng xuống Verilog-2001:
1. **`1. Port Contract`:** Tên module và danh sách cổng/bit-width bất biến từ Cụm 1.
2. **`2. RAG Top-K Context`:** Tối đa 2 mẫu Verilog tham khảo gần nhất.
3. **`3. RTL Gen Strategy`:** Chọn `Qwen2.5-3B DPO` (`--use-distilled`) hoặc `RTLGenerator`.
4. **`4. Self-Check TB Spec`:** Kịch bản Testbench tự chấm điểm theo đúng họ mạch 70%.
*(Hai mũi tên đứt 2 chiều giữ cho Cụm 2 luôn bám sát hợp đồng thiết kế này.)*

### 2.4. Cụm 2 — `2. Direct RTL Coding & Dual-Verifier Harness`
* **Hàng trên (Sinh mã & Ép chuẩn):**
  1. **`Qwen2.5-3B DPO` (`models/run_inference.py`):** Khi bật `--use-distilled`, gọi `generate_verilog(use_rag=True)` (ưu tiên `.gguf` qua `llama_cpp` $\to$ PyTorch LoRA). Nếu chưa bật cờ, chưa có trọng số trong `models/`, hoặc output AI chưa có `module ... endmodule` hợp lệ (`_extract_verilog_code()`), hệ thống kích hoạt **trạng thái `FALLBACK`** chuyển êm về `RTLGenerator.generate_from_spec()`.
  2. **`RTLPortEnforcer` (`agent/rtl_generator.py`):** Đối chiếu với `Port Contract`, ép lại header `module ... (...);` khớp **100%** tên, hướng và độ rộng bit (nối nội bộ cổng thừa hoặc gán mặc định nếu thiếu).
  3. **`Self-Check TB (70%)` (`agent/tb_generator.py`):** Đọc cổng thật của RTL để sinh `sim/tb_<tên_mạch>.v` chuẩn IEEE 1364-2001 có chuỗi reset an toàn (`#22; ... #2;`), **Verification Scoreboard** tự kiểm chứng Đúng/Sai cho các họ mạch 70% (Counter/BCD/Gray, FIFO, Shift Register, Decoder/Mux/Priority Encoder, ALU/Adder/Multiplier/Comparator, PWM/Timer, Ready/Valid, Digital Lock), kèm Watchdog timeout, in `[PASS]` / `[FAIL]` / `[SUCCESS]` và `$finish`.
* **Hàng dưới (Hai trọng tài kiểm chứng `Dual Verifier`):**
  1. **`Verifier 1: AST Static Linter` (`agent/verilog_linter.py`):** Chuẩn hóa `$display("%!")` và dấu phẩy thừa (`sanitize_file()`), kiểm tra cân bằng `begin/end`, `case/endcase`, `module/endmodule`, và quét sạch **3 lỗi phần cứng chí mạng**: `DANGLING_INPUT` / `UNASSIGNED_OUTPUT`, `INFERRED_LATCH`, `BLOCKING_IN_SEQUENTIAL` / `NONBLOCKING_IN_COMBINATIONAL`.
  2. **`Verifier 2: ModelSim Oracle` (`agent/simulator.py`):** Biên dịch bằng `vlog.exe` và mô phỏng batch bằng `vsim.exe -c -do "run -all; quit"` (tự fallback `iverilog`/`vvp` nếu máy không có ModelSim).
     * **`PASS 100%` (Mũi tên xanh lên Cụm 4):** Kết thúc sạch (`$finish` hoặc `[SUCCESS]`/`PASSED`) và 0 lỗi (`** Error:`, `[FAIL]`, `MISMATCH`, `TIMEOUT`).
     * **`FAIL` (Mũi tên đỏ sang Cụm 3):** Lỗi biên dịch `stage="compile"`, timeout 60s, hoặc assertion báo `[FAIL]`.

### 2.5. Cụm 3 — `3. Adaptive Reflection (Max 3 vòng)` (`agent/reflection_loop.py`)
Khi ModelSim báo `FAIL`, hệ thống tự sửa lỗi tối đa **`max_retries = 3` vòng**:
1. **`Analysis Agent` (`diagnose_error()`):** Đọc log ModelSim, bắt đúng file/dòng lỗi và phân loại (`compile` syntax, `TIMEOUT` treo FSM, hoặc `MISMATCH`/`FAIL` sai logic).
2. **`Reflection Agent` (`apply_auto_repair()`) $\to$ `Candidate Actions (4 chiến lược)`:**
   * *1. Vá tên module instance lệch* (`Instantiation of '...' failed`).
   * *2. Sửa `$display(%!)` & lỗi cú pháp/dấu phẩy* + chạy lại `VerilogLinter.sanitize_verilog_code()`.
   * *3. Tái tạo TB khớp cổng* (`Port '...' not found` $\to$ gọi `TBGenerator.generate_generic_tb()`).
   * *4. Dừng nếu vượt phạm vi* (nếu không khớp mẫu tự vá hoặc hết 3 vòng $\to$ dừng và in chẩn đoán `stage / category / root_cause / suggested_fix`).
3. Mũi tên **`Tự vá RTL/TB`** đưa file vừa sửa quay lại Cụm 2 để mô phỏng lại.

### 2.6. Cụm 4 — `4. EDA Synthesis & Visual Output` & Vòng nạp ngược DB
Mạch đạt **`PASS 100%`** được đóng gói thành hồ sơ FPGA hoàn chỉnh:
1. **`Port & Cyclone II` (`port_auditor.py`, `synthesis_profiler.py`):** Gọi `quartus_map.exe` tổng hợp thật lên **Altera Cyclone II** đọc `LEs`, `FFs`, `Pins` từ `.map.summary`; đồng thời kiểm toán chân tín hiệu **4 chiều** bảo đảm $\text{Spec} \equiv \text{RTL} \equiv \text{BSF} \equiv \text{BDF}$.
2. **`BDF & VWF Gen` (`bdf_generator.py`, `vwf_generator.py`):** Sinh Project Quartus (`.qpf`, `.qsf`), Symbol (`.bsf`), Schematic (`.bdf`), và Vector Waveform (`.vwf`) để mở trực quan trong Quartus II (hoặc ModelSim GUI với `--gui`).
3. **Vòng nạp ngược DB (`save_verified_design()` — mũi tên đứt xanh dương vòng ngoài cùng):** Nếu mô phỏng đạt `passed is True` **và** qua sạch `VerilogLinter.lint_file()`, hệ thống lưu ngược mẫu mới vào `knowledge_base/hardware_db.json` (lọc bỏ tên rác `test_`, `tc`, `web_spec_`, `custom_hw_module`, chống trùng tên & trùng hash **MD5**) để làm giàu trực tiếp cho **`Hybrid RAG Retrieval (DB)`** ở Cụm 1.

### 2.7. Cụm 5 — `5. Chưng cất Tri thức Offline & Nạp Trọng Số Student` (`training/`)
Pipeline chuẩn bị trọng số AI ngoại tuyến:
1. **`Nguồn Dữ liệu Gốc`:** **VerilogDB** (`Rohan-code/Verilog_DB_read`, 40.755 mẫu) + **100 Prompts CE118** (+ benchmarks).
2. **`Gemini Teacher (API)` (`training/distill_teacher_cot.py`):** `gemini-3.1-flash-lite` sinh suy luận CoT từng mạch + mã Verilog-2001.
3. **`Truth Oracle 3 tầng`:** Lọc qua `SpecAnalyzer` + `AST Linter` + `ModelSim vlog.exe` (tập hiện tại trên repo đạt **`1.637` mẫu Teacher CoT**, **`2.724` mẫu SFT** và **`2.881` cặp DPO**); các ca lần 1 lỗi được gửi cho Teacher tự sửa để thu cặp **DPO** thật.
4. **`Train Colab T4 (Qwen2.5-3B)`:** Chạy `train_spec2rtl_qwen3b_colab.ipynb` (SFT LoRA `r=16`) $\to$ `train_spec2rtl_qwen3b_dpo_colab.ipynb` (DPO `beta=0.1`), xuất LoRA Adapter & **GGUF** đặt vào `models/` (mũi tên **`Nạp trọng số 3B`**) để chạy offline qua `--use-distilled`.

### 2.8. Bảng tóm tắt 6 trạng thái kết thúc của một lượt chạy

| Trạng thái kết thúc | Nơi phát sinh | Ý nghĩa & Hành động |
| :--- | :--- | :--- |
| **`REJECTED (OUT OF SCOPE)`** | Cụm 1 (`Domain Guard`) | Đề là Analog / High-Speed PHY / văn bản phi kỹ thuật $\to$ từ chối an toàn. |
| **`REJECTED (ARCHITECTURAL BOUNDARY)`** | Cụm 1 (`30% Guard`) | Đề là hệ thống `SOC_AI` / Systolic Array quá lớn (`30%`) $\to$ yêu cầu tách nhỏ theo khối `70%`. |
| **`FALLBACK -> RTLGenerator`** | Cụm 2 (`Qwen2.5-3B DPO`) | Chưa bật `--use-distilled`, chưa có trọng số `models/`, hoặc output AI lỗi $\to$ tự chuyển sang bộ sinh RTL dự phòng. |
| **`FAIL -> ADAPTIVE REFLECTION`** | Cụm 2 $\to$ Cụm 3 | Lỗi biên dịch `vlog` hoặc sai assertion `vsim` $\to$ tự vá theo 4 chiến lược và chạy lại (tối đa 3 vòng). |
| **`FAILED` (sau 3 vòng Reflection)** | Cụm 3 (`ReflectionAgent`) | Hết 3 lần tự vá hoặc lỗi vượt mẫu vá $\to$ dừng và in báo cáo chẩn đoán gốc. |
| **`PASS 100%` + Lưu ngược DB** | Cụm 2 $\to$ Cụm 4 $\to$ Cụm 1 | Qua Linter + ModelSim + Quartus Cyclone II + Port Audit 4 chiều $\to$ xuất `.v`, `.bsf`, `.bdf`, `.vwf`, `LE/FF` và nạp ngược `hardware_db.json`. |

### 2.9. Bảng Ánh Xạ Hành Động $\leftrightarrow$ Đoạn Code Thực Thi (Code Traceability)

Mỗi hộp và mũi tên trạng thái trên sơ đồ đều gắn với hàm/đoạn code cụ thể trong dự án:

| Cụm / Khối trên sơ đồ | Hành động thực tế | File & Hàm / Dòng code thực thi |
| :--- | :--- | :--- |
| **Cụm 1 — `Spec & Port Analyzer`** | Chuẩn hóa tiếng Việt, bóc tên module & danh sách cổng 3 tầng (`Port Contract`) | [`agent/spec_analyzer.py`](agent/spec_analyzer.py): `remove_vietnamese_accents()` (`L12`), `extract_module_name()` (`L59`), `extract_ports()` (`L240`) |
| **Cụm 1 — `Domain & 30% Guard`** | Chặn `ANALOG_AMS` / `HIGH_SPEED_PHY` / `IRRELEVANT_INPUT` và chặn nguyên khối `SOC_AI` (`30%`) | [`agent/spec_analyzer.py`](agent/spec_analyzer.py): `is_30_percent_architecture()` (`L106`), `check_unsupported_domain()` (`L127`), `classify_system()` (`L174`); gọi kiểm tra tại [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py) (`L202-L226`) |
| **Cụm 1 — `Hybrid RAG Retrieval`** | Khởi tạo Vector Backend (`fastembed` / `.npz` + Gemini / `LSA SVD`), tính Hybrid RRF (`Concept + BM25 + 3-gram + Vector`), cắt ngữ cảnh Top-2 ($\le 45$ dòng) | [`agent/knowledge_matcher.py`](agent/knowledge_matcher.py): `_khoi_tao_vector_backend()` (`L584`), `_cham_diem_hybrid()` (`L1074`), `search_by_mode()` (`L1196`), `search()` (`L1240`), `format_rag_context()` (`L1246`) |
| **Cụm 1 $\to$ `Implementation Plan`** | Điều phối toàn trình, chọn nhánh `VENDING`/`ELEVATOR`/`TRAFFIC`, nhánh AI `--use-distilled`, hoặc `RTLGenerator` | [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py): `run_single_spec()` (`L162`), nhánh `BangMachMau` (`L196-L240`), nhánh động (`L242-L290`) |
| **Cụm 2 — `Qwen2.5-3B DPO` + Fallback** | Gọi `generate_verilog(use_rag=True)` (GGUF `llama_cpp` $\to$ PyTorch LoRA), trích code `module...endmodule` và fallback an toàn về `RTLGenerator` | [`models/run_inference.py`](models/run_inference.py): `generate_verilog()` (`L35`), `_fallback_rtl_generator()` (`L14`); hook `--use-distilled` tại [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py) (`_extract_verilog_code()` `L148`, `if DungAiChinh:` `L258-L283`) |
| **Cụm 2 — `RTLPortEnforcer`** | Ép phần khai báo `module (...);` khớp 100% cổng & bit-width của `Port Contract`, fallback sinh RTL theo họ mạch | [`agent/rtl_generator.py`](agent/rtl_generator.py): `RTLPortEnforcer.enforce()` (`L13-L83`), `RTLGenerator.generate_from_spec()` (`L105`); gọi tại [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py) (`L269`) |
| **Cụm 2 — `Self-Check TB (70%)`** | Sinh Testbench tự kiểm chứng (`[PASS]`/`[FAIL]` + `$finish`) với chuỗi reset `#22; ... #2;` chống trượt cạnh clock cho các họ mạch 70% | [`agent/tb_generator.py`](agent/tb_generator.py): `_build_reset_sequence()` (`L173`), `_emit_assert()` (`L194`), `generate_tb_from_spec()` (`L282`), `generate_generic_tb()` (`L2427`) |
| **Cụm 2 — `Verifier 1: AST Static Linter`** | Chuẩn hóa `$display("%!")`, kiểm tra cân bằng từ khóa & quét `DANGLING_INPUT`, `UNASSIGNED_OUTPUT`, `INFERRED_LATCH`, `BLOCKING_IN_SEQUENTIAL` | [`agent/verilog_linter.py`](agent/verilog_linter.py): `sanitize_verilog_code()` (`L19`), `extract_module_info()` (`L60`), `check_dangling_pins()` (`L106`), `check_inferred_latches_and_races()` (`L138`), `lint_check()` (`L185`), `lint_file()` (`L239`) |
| **Cụm 2 — `Verifier 2: ModelSim Oracle`** | Biên dịch `vlog.exe` & chạy `vsim.exe -c` (fallback `iverilog`/`vvp`), trả trạng thái `success`/`passed` (`PASS 100%` hay `FAIL`) | [`agent/simulator.py`](agent/simulator.py): `run_flow()` (`L198`), `run_modelsim_flow()` (`L115`), `run_iverilog_flow()` (`L28`) |
| **Cụm 3 — `Adaptive Reflection`** | Đọc log lỗi ModelSim, áp dụng 4 chiến lược tự vá lỗi (tên instance, `$display`/dấu phẩy, tái tạo TB, hoặc dừng), lặp tối đa 3 vòng | [`agent/reflection_loop.py`](agent/reflection_loop.py): `diagnose_error()` (`L15`), `apply_auto_repair()` (`L55`), `execute_closed_loop_flow()` (`L138`); gọi tại [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py) (`L329`) |
| **Cụm 4 — `Port & Cyclone II` + `BDF & VWF Gen`** | Sinh `.qpf`, `.bsf`, `.bdf`, `.vwf`, kiểm toán cổng 4 chiều ($\text{Spec} \equiv \text{RTL} \equiv \text{BSF} \equiv \text{BDF}$) & đo tài nguyên `quartus_map.exe` | [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py) (`setup_quartus_and_bdf()` `L54`, `L341-L367`); [`agent/bdf_generator.py`](agent/bdf_generator.py) (`generate_bdf()` `L126`); [`agent/vwf_generator.py`](agent/vwf_generator.py) (`generate_vwf()` `L141`); [`agent/port_auditor.py`](agent/port_auditor.py) (`audit()` `L12`); [`agent/synthesis_profiler.py`](agent/synthesis_profiler.py) (`parse_quartus_map_summary()` `L14`, `profile_module()` `L110`) |
| **Vòng nạp ngược DB (`save_verified_design`)** | Kiểm tra `passed is True` + `VerilogLinter.lint_file()`, lọc prefix test rác và lưu ngược chống trùng MD5 vào `hardware_db.json` | [`agent/run_spec2rtl.py`](agent/run_spec2rtl.py) (`L370-L384`) gọi `KnowledgeMatcher().save_verified_design()` tại [`agent/knowledge_matcher.py`](agent/knowledge_matcher.py) (`L1285`) |
| **Cụm 5 — Chưng cất & Train `3B`** | Gọi Gemini Teacher sinh CoT + Verilog, lọc qua Oracle 3 tầng (kèm self-correction DPO), đóng gói SFT/DPO và train Colab T4 | [`training/distill_teacher_cot.py`](training/distill_teacher_cot.py) (`call_gemini_teacher()` `L181`, `verify_with_truth_oracle()` `L274`, `merge_and_export()` `L413`); [`training/train_spec2rtl_qwen3b_colab.ipynb`](training/train_spec2rtl_qwen3b_colab.ipynb) & [`training/train_spec2rtl_qwen3b_dpo_colab.ipynb`](training/train_spec2rtl_qwen3b_dpo_colab.ipynb) |

---

## 3. Cấu Trúc Mã Nguồn Thư Mục

```
TKLLS/
├── agent/                         # Lõi tác tử Spec2RTL (13 module lõi & 2 bộ kiểm thử)
│   ├── run_spec2rtl.py            # Master CLI Orchestrator (--use-distilled, closed-loop DB)
│   ├── spec_analyzer.py           # Domain Guard (30%/70%) & bóc tách cổng I/O 3 tầng
│   ├── rtl_generator.py           # RTLPortEnforcer & bộ sinh RTL fallback synthesizable
│   ├── tb_generator.py            # Self-Checking Testbench cho các họ mạch 70%
│   ├── simulator.py               # Trình điều khiển mô phỏng ModelSim / Icarus Verilog
│   ├── reflection_loop.py         # Vòng lặp phản tư tự sửa lỗi logic (max 3 vòng)
│   ├── bdf_generator.py           # Tự động xuất Symbol BSF và Sơ đồ Schematic BDF
│   ├── vwf_generator.py           # Tự động tạo Vector Waveform VWF cho Quartus II
│   ├── port_auditor.py            # Kiểm toán toàn vẹn cổng I/O 4 chiều
│   ├── eda_finder.py              # Tự động dò tìm ModelSim và Quartus trên ổ đĩa
│   ├── synthesis_profiler.py      # Đo đạc mức tiêu thụ tài nguyên FPGA (LEs, Registers, Pins)
│   ├── verilog_linter.py          # Bộ phân tích tĩnh AST thuần Python (0 Latch/Dangling/Race)
│   ├── knowledge_matcher.py       # Hybrid RAG (Vector + BM25 + 3-gram RRF) & save_verified_design()
│   ├── test_group3_linter.py      # Kiểm thử AST Linter & Domain Guard (5/5)
│   └── test_robustness_battery.py # Bộ kiểm thử hồi quy 20 bài toán toàn diện (20/20)
├── models/                        # Suy luận AI cục bộ (run_inference.py: GGUF / PyTorch + RAG)
├── training/                      # Chưng cất Gemini Teacher CoT, dataset SFT/DPO & Colab 3B
├── benchmarks/                    # Benchmark toàn trình & bộ 28 truy vấn RAG nhóm 70%
├── reports/                       # Báo cáo thực nghiệm Linter, Tuần 2 & Benchmark RAG 70%
├── knowledge_base/                # Cơ sở tri thức vi mạch (hardware_db.json, reflection_db.json)
├── specs/                         # Thư mục chứa các đề bài đặc tả kỹ thuật (.txt, .md)
├── docs/                          # Slide HTML bảo vệ, kịch bản thuyết trình, sơ đồ kiến trúc, 100 Prompts
└── HANDOFF_NEXT_STEPS.md          # Hướng dẫn bàn giao chi tiết khi chuyển sang máy mới
```

---

## 4. Hướng Dẫn Sử Dụng & Thực Thi

### 4.1. Cài đặt môi trường
Hệ thống chạy trên nền Python 3.8+ và tương thích với công cụ EDA:
* **Altera Quartus II 13.0sp1** (Đường dẫn mặc định: `D:\altera\13.0sp1` hoặc `C:\altera\13.0sp1`)
* **ModelSim-Altera Starter Edition** (tích hợp sẵn trong bộ cài Quartus II)

### 4.2. Các câu lệnh chạy chính

```bash
# 1. Chạy bài toán mẫu có sẵn (ví dụ: Đồng hồ bấm giờ c.txt)
python agent/run_spec2rtl.py specs/c.txt

# 2. Chạy kèm AI chưng cất (Qwen2.5-3B + Hybrid Vector RAG, tự fallback RTLGenerator)
python agent/run_spec2rtl.py specs/c.txt --use-distilled

# 3. Chạy bài toán và tự động mở cửa sổ sóng đồ họa ModelSim GUI
python agent/run_spec2rtl.py specs/c.txt --gui

# 4. Chạy bộ kiểm thử AST Linter, 20 bài robustness và Benchmark RAG 70%
python agent/test_group3_linter.py
python agent/test_robustness_battery.py
python benchmarks/benchmark_70_rag.py
```

### 4.3. Cách kiểm tra bài toán mới bất kỳ
1. Tạo một file đặc tả trong `specs/` (ví dụ `specs/mach_moi.txt`) với định dạng:
   ```markdown
   # Tên Mạch (module_name)
   ## 1. Đầu vào (Inputs):
   - clk: Xung nhịp hệ thống
   - rst: Reset tích cực cao
   ## 2. Đầu ra (Outputs):
   - [3:0] out: Tín hiệu đầu ra
   ## 3. Hoạt động / Logic mong muốn:
   - Mô tả logic hoạt động ở đây...
   ```
2. Chạy lệnh:
   ```bash
   python agent/run_spec2rtl.py specs/mach_moi.txt
   ```
3. Xem kết quả tự động sinh trong `src/`, `sim/`, và `quartus/`.

---

## 5. Các Định Dạng Kết Quả Xuất Ra Nghiệm Thu

Sau khi hoàn tất, hệ thống cung cấp 4 hình thức kiểm tra trực quan cho kỹ sư và giảng viên:
1. **Quartus II Schematic Diagram (`quartus/<tên_mạch>/sch_<tên_mạch>.bdf`)**: Mở trong Quartus II (`File -> Open`) để xem sơ đồ khối nguyên lý mạch điện tử đã được vẽ sẵn và nối dây hoàn chỉnh.
2. **Quartus II Vector Waveform (`quartus/<tên_mạch>/Waveform.vwf`)**: Mở trực tiếp trong Quartus II Waveform Editor để xem dạng sóng xung nhịp và chạy Functional Simulation.
3. **ModelSim Waveform GUI (`--gui`)**: Thêm cờ `--gui` khi chạy lệnh (ví dụ: `python agent/run_spec2rtl.py specs/c.txt --gui`) để ModelSim tự động mở cửa sổ sóng đồ họa Waveform trực quan trên màn hình.
4. **Quartus RTL Netlist Viewer**: Mở project `.qpf` trong Quartus II $\to$ chọn `Tools -> Netlist Viewers -> RTL Viewer` để xem sơ đồ mức cổng logic và flip-flop tổng hợp vật lý.

---

## 6. Kết Quả Thực Nghiệm & Đánh Giá Giới Hạn

Hệ thống đã hoàn thiện toàn bộ luồng tự động hóa công cụ EDA:
* **Hạ tầng kiểm định khép kín (Closed-Loop EDA)**: Tự động chạy ModelSim, trích xuất log lỗi, tự động sửa mã Verilog (Reflection Loop), tự động xuất sơ đồ nguyên lý BDF và dạng sóng VWF cho Quartus II mà không cần thao tác thủ công trên giao diện.
* **Đánh giá trên bộ 100 đề bài chuẩn hóa (`docs/100_Prompt_Thiet_Ke_Mach.pdf`)**:
  * **~38% Bài toán đạt chuẩn 100%**: Bao phủ xuất sắc các bài toán thuộc 25 họ mạch kinh điển (Counter, Timer, ALU, FSM Vending Machine, Traffic Light, Elevator, UART TX, PWM...).
  * **~62% Bài toán bộc lộ giới hạn của phương pháp Template/Rule-based**: Với các mạch hoàn toàn mới (ví dụ: `button_debouncer`, MUX/DEMUX nhiều ngõ vào, SPI Master, Arbiter), cơ chế sinh generic rơi vào tình trạng sinh mạch giả lập hoặc bỏ quên ngõ vào (dangling input pins). Đây là bằng chứng thực nghiệm rõ ràng nhất chứng minh phương pháp mẫu cứng đã chạm trần giới hạn.

---

## 7. Định Hướng Phát Triển Tiếp Theo: Chưng Cất Tri Thức (Knowledge Distillation) & Tinh Chỉnh Mô Hình (Fine-Tuning)

Để mở rộng hệ thống đạt độ bao phủ $100\%$ các bài toán vi mạch mà không cần viết tay hàng nghìn template, đồng thời triệt tiêu hoàn toàn lỗi chân lơ lửng (dangling pins) và chốt ẩn (inferred latches), nhóm triển khai **Kế hoạch 2 tuần với 6 thành viên (chia 3 nhóm song song, chi phí 0 VNĐ)**:

### 7.1. Ba Nhánh Triển Khai Song Song (Phân công 6 Thành viên)

1. **Nhóm 1: Chuẩn Bị Dữ Liệu & Thẩm Định Chân Lý (2 Thành viên)**
   * **Mục tiêu:** Xây dựng tập dữ liệu sạch gồm **1.000 mẫu vi mạch chuẩn hóa** từ *VerilogDB* ([arXiv:2507.13369](https://arxiv.org/pdf/2507.13369)) và ngân hàng 100 Prompt của đề tài.
   * **Cơ chế:** Dùng mô hình suy luận lớn (DeepSeek-R1 / Gemini) làm Teacher sinh chuỗi tư duy phần cứng (CoT: Phân tích I/O $\to$ FSM $\to$ Verilog synthesizable $\to$ Testbench).
   * **Bộ lọc chân lý (Truth Oracle):** Dùng chính `simulator.py` chạy ngầm ModelSim batch để thẩm định 100% mẫu; loại bỏ toàn bộ code lỗi cú pháp hoặc fail assertion.
   * **Định dạng bàn giao:** Đóng gói đúng cấu trúc 3 trường `(instruction, input, output)` tại [`training/dataset_clean_verified.json`](training/dataset_clean_verified.json).

2. **Nhóm 2: Huấn Luyện AI Cục Bộ & Fine-Tuning (2 Thành viên)**
   * **Mục tiêu:** Thực hiện **Chưng cất tri thức (Knowledge Distillation) thông qua kỹ thuật Fine-Tuning (Supervised Fine-Tuning - SFT với LoRA 4-bit)** để mô hình chạy offline $100\%$ bảo mật tuyệt đối tài sản trí tuệ (IP Security).
   * **Hạ tầng & Chi phí:** Dùng thư viện tối ưu **Unsloth** chạy trên **Google Colab GPU T4 miễn phí (0 VNĐ)**. Thời gian huấn luyện 1.000 mẫu chỉ mất **~15 đến 25 phút**.
   * **Notebook hoàn chỉnh:** Đã lập trình và kiểm thử thành công tại [`training/train_spec2rtl_qwen3b_colab.ipynb`](training/train_spec2rtl_qwen3b_colab.ipynb).
   * **Thực nghiệm đối sánh 2 phiên bản mô hình (Ablation Study):**
     * **Bản 1.5B (`Qwen2.5-Coder-1.5B`)**: Siêu nhẹ (~1GB RAM lượng tử hóa 4-bit), chạy trực tiếp trên CPU máy tính phòng lab trường hoặc nhúng lên kit FPGA/Raspberry Pi không cần card GPU rời.
     * **Bản 3B (`Qwen2.5-Coder-3B`)**: Tăng cường năng lực suy luận chuỗi dài (Reasoning) cho các khối vi kiến trúc phức tạp (FSM đa tầng, bộ điều khiển bus, FIFO).

3. **Nhóm 3: Kỹ Thuật Vi Mạch & AST Linter (2 Thành viên)**
   * **Mục tiêu:** Nâng cấp `agent/verilog_linter.py` từ Regex sang Cây cú pháp trừu tượng (**Abstract Syntax Tree - AST Parser**) sử dụng thư viện **PyVerilog**.
   * **Bộ phát hiện chân lơ lửng (Dangling Pin Detector):** Quét toàn bộ cây cú pháp trong khối `always`/`assign`, bắt chết lỗi cổng `input` bị cô lập (triệt tiêu dứt điểm ca lỗi như `button_debouncer`).
   * **Bộ triệt tiêu chốt ẩn (Inferred Latch Detector):** Duyệt các câu lệnh điều kiện `if/case` trong khối tổ hợp `always @(*)`, ép buộc phải có đầy đủ nhánh gán mặc định (`else` / `default`).
   * **Đo kiểm thực nghiệm:** Phối hợp đo đạc tỷ lệ Pass@1 trên toàn bộ 100 đề bài vi mạch và đo tài nguyên tiêu thụ trên chip Altera Cyclone II.

---

### 7.2. Lộ Trình 2 Tuần Về Đích (Roadmap)

| Thời Gian | Nhóm 1 (Dữ Liệu) | Nhóm 2 (Fine-Tuning AI) | Nhóm 3 (AST Linter & Vi Mạch) |
| :--- | :--- | :--- | :--- |
| **Tuần 1** | Lọc dữ liệu VerilogDB + ModelSim thẩm định ra 1.000 mẫu sạch. | Dựng xong Colab Unsloth LoRA & test dummy run thành công *(Đã xong)*. | Xây dựng bộ quét cây cú pháp PyVerilog AST bắt chốt ẩn & chân lơ lửng. |
| **Tuần 2** | Bàn giao file `dataset_1000_clean.json`. | Bấm nút Fine-Tune mô hình 1.5B & 3B trên Colab (15-20 phút), xuất GGUF. | Tích hợp model đã train vào `agent/run_spec2rtl.py`, chạy benchmark 100 bài toán. |
| **Nghiệm thu** | \multicolumn{3}{c|}{Tổng hợp số liệu thực nghiệm, hoàn thiện Slide báo cáo và file báo cáo đồ án nộp Thầy.} |

---

## 8. Cơ Sở Khoa Học & Nguồn Gốc Ý Tưởng Từ Các Tài Liệu Nghiên Cứu (Academic References & Provenance)

Hệ thống **Spec2RTL & Prompt2Silicon** được thiết kế và hiện thực hóa dựa trên việc kế thừa, tổng hợp và bản địa hóa các ý tưởng nghiên cứu đỉnh cao từ **6 tài liệu khoa học nền tảng do Giảng viên hướng dẫn (TS. Nguyễn Văn Tình) định hướng**:

| STT | Tài Liệu / Bài Báo | Tác Giả & Tổ Chức | Ý Tưởng Kế Thừa Cốt Lõi | Module Hiện Thực Trong Hệ Thống |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Spec2RTL-Agent**<br/>([arXiv:2506.13905](https://arxiv.org/abs/2506.13905)) | NVIDIA Research, Cadence, Georgia Tech | Kiến trúc đa tác tử 3 pha: Understanding $\to$ Coding $\to$ Reflection | `spec_analyzer.py`, `rtl_generator.py`, `reflection_loop.py` |
| 2 | **From RTL to Prompt Coding**<br/>([arXiv:2601.13815](https://arxiv.org/html/2601.13815v1)) | RPTU Kaiserslautern-Landau, Tiny Tapeout (ISCAS 2026) | Triết lý "Prompt Coding" - Đưa yêu cầu tự nhiên thẳng tới phần cứng | `specs/*.txt`, `100_Prompt_Thiet_Ke_Mach.pdf` |
| 3 | **Prompt2Silicon Platform**<br/>([GitHub tukl-msd](https://github.com/tukl-msd/prompt2silicon)) | Microelectronic Systems Design Group (RPTU) | Trực quan hóa toàn trình (Visual EDA Verification: Schematic & Waveform) | `bdf_generator.py`, `vwf_generator.py`, `--gui` |
| 4 | **Autonomous Chip Design Agents**<br/>([NVIDIA GTC 2025 S72294](https://www.nvidia.com/en-us/on-demand/session/gtc25-S72294/)) | NVIDIA Research (Haoxing Ren, ChipNeMo Team) | Hardware Agent Harness: Tích hợp công cụ EDA làm "Trọng tài chân lý" | `simulator.py`, `synthesis_profiler.py`, `eda_finder.py` |
| 5 | **VerilogDB**<br/>([arXiv:2507.13369](https://arxiv.org/pdf/2507.13369)) | University of Florida | Ngân hàng thiết kế mẫu chuẩn hóa & Khung Linter lọc cú pháp nghiêm ngặt | `knowledge_base/`, `knowledge_matcher.py`, `verilog_linter.py` |
| 6 | **VeriPrefer**<br/>([arXiv:2504.15804](https://arxiv.org/pdf/2504.15804)) | Ning Wang, Zhe Jiang et al. | Tự động sinh Testbench tự kiểm tra (Scoreboard) & Tối ưu bằng phản hồi mô phỏng | `tb_generator.py`, `reflection_loop.py` (Vòng lặp sửa lỗi) |

---

### Chi Tiết Từng Tài Liệu & Vị Trí Kế Thừa Cụ Thể Trong Hệ Thống:

#### 1. Spec2RTL-Agent: Automated Hardware Code Generation from Complex Specifications Using LLM Agent Systems
* **Đường dẫn**: [https://arxiv.org/abs/2506.13905](https://arxiv.org/abs/2506.13905)
* **Tác giả & Tổ chức**: Zhongzhi Yu, Mingjie Liu, Michael Zimmer, Yingyan (Celine) Lin, Yong Liu, Haoxing Ren (NVIDIA Research, Cadence Design Systems, Georgia Institute of Technology).
* **Vị trí lấy trong bài báo**:
  * **Section III (Methodology & Agent Architecture)**: Mô hình hóa quy trình thiết kế phần cứng thành 3 vai trò tác tử tách biệt:
    1. *Understanding Agent*: Tiếp nhận đặc tả phi cấu trúc (PDF, Text), bóc tách danh sách cổng I/O, độ rộng bus và các ràng buộc logic.
    2. *Coding Agent*: Sinh mã phần cứng có cấu trúc chặt chẽ, loại bỏ hoàn toàn việc "bịa" chân tín hiệu (Port Hallucination).
    3. *Reflection Agent*: Quan sát lỗi biên dịch/mô phỏng để tự động sửa mã Verilog lặp đi lặp lại.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/spec_analyzer.py`: Đóng vai trò *Understanding Agent* trích xuất tên module, bảng chân cắm `inputs`/`outputs` kèm độ rộng bit.
  * `agent/rtl_generator.py`: Tích hợp cơ chế `RTLPortEnforcer` đóng vai trò *Coding Agent* ép mã Verilog sinh ra phải khớp 100% cổng với đặc tả.
  * `agent/reflection_loop.py`: Đóng vai trò *Reflection Agent* tự động bắt lỗi cú pháp và lỗi assertion để vá lại code.

---

#### 2. From RTL to Prompt Coding: Empowering the Next Generation of Chip Designers through LLMs
* **Đường dẫn**: [https://arxiv.org/html/2601.13815v1](https://arxiv.org/html/2601.13815v1)
* **Tác giả & Tổ chức**: Lukas Krupp, Matthew Venn, Norbert Wehn (RPTU Kaiserslautern-Landau, Tiny Tapeout, IEEE ISCAS 2026).
* **Vị trí lấy trong bài báo**:
  * **Section I & II (Introduction & The Concept of Prompt Coding)**: Đề xuất chuyển dịch phương pháp thiết kế vi mạch truyền thống (phải gõ thủ công từng dòng mã Verilog/VHDL) sang phương pháp **"Prompt Coding"** — người kỹ sư mô tả ý đồ thiết kế bằng câu lệnh văn bản tự nhiên, hệ thống tự động sinh code synthesizable và kết nối trực tiếp với backend băng từ.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * Chuẩn hóa cấu trúc Prompt đầu vào theo định dạng 3 phần độc lập (Inputs - Outputs - Logic) trong thư mục `specs/*.txt`, `specs/*.md`.
  * Xây dựng tuyển tập tài liệu `docs/100_Prompt_Thiet_Ke_Mach.pdf` gồm 100 đề bài vi mạch kinh điển chuẩn hóa phục vụ đo kiểm năng lực "Prompt Coding".

---

#### 3. Prompt2Silicon Platform (Open-Source Hardware Workflow)
* **Đường dẫn**: [https://github.com/tukl-msd/prompt2silicon](https://github.com/tukl-msd/prompt2silicon)
* **Tác giả & Tổ chức**: Microelectronic Systems Design Group (MSD - TU Kaiserslautern / RPTU).
* **Vị trí lấy trong dự án**:
  * **Triết lý thiết kế (Holistic Frontend-to-Backend & Visual Simulation)**: Không để kết quả dừng lại ở các đoạn mã Verilog dạng text rời rạc khó kiểm soát, mà phải cung cấp công cụ trực quan hóa (Visual EDA Feedback) tức thì để người thiết kế "nhìn thấy" mạch điện tử và dạng sóng logic.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/bdf_generator.py`: Tự động biên dịch file Symbol Altera Quartus (`.bsf`) và vẽ Sơ đồ nguyên lý mạch hoàn chỉnh (`.bdf`) để mở trực tiếp trong Quartus II Schematic Editor.
  * `agent/vwf_generator.py`: Tự động tạo file Vector Waveform (`.vwf`) và khởi chạy ModelSim Waveform GUI (`--gui`) để kỹ sư quan sát trực tiếp các xung nhịp nano-giây.

---

#### 4. Autonomous Chip Design Agents with LLMs (NVIDIA GTC 2025 Session S72294)
* **Đường dẫn**: [https://www.nvidia.com/en-us/on-demand/session/gtc25-S72294/](https://www.nvidia.com/en-us/on-demand/session/gtc25-S72294/)
* **Tác giả & Tổ chức**: Haoxing Ren, Mingjie Liu & Nhóm nghiên cứu ChipNeMo (NVIDIA Research).
* **Vị trí lấy trong phiên báo cáo**:
  * **Kiến trúc Hardware Agent Harness (EDA-in-the-Loop)**: Khẳng định mô hình ngôn ngữ lớn (LLM) không thể tự thiết kế vi mạch nếu thiếu môi trường thực thi phần mềm chuyên dụng (Software Harness). Phải đưa các công cụ EDA tiêu chuẩn công nghiệp vào làm "Trọng tài chân lý" để kiểm tra tính khả tổng hợp (synthesizability) và kiểm soát tài nguyên phần cứng.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/eda_finder.py`: Tự động phát hiện môi trường EDA công nghiệp Altera Quartus II và ModelSim trên máy tính.
  * `agent/simulator.py`: Tự động điều khiển luồng lệnh CLI batch của ModelSim (`vlog.exe`, `vsim.exe`) làm trọng tài mô phỏng.
  * `agent/synthesis_profiler.py`: Gọi ngầm `quartus_map.exe` để tổng hợp thực tế trên chip FPGA Altera Cyclone II, đo đạc chính xác số Logic Elements, Flip-Flops và Pins.

---

#### 5. VerilogDB: The Largest, Highest-Quality Dataset with a Preprocessing Framework for LLM-based RTL Generation
* **Đường dẫn**: [https://arxiv.org/pdf/2507.13369](https://arxiv.org/pdf/2507.13369)
* **Tác giả & Tổ chức**: Paul E. Calzada, Zahin Ibnat, Mark Tehranipoor et al. (Florida Institute for Cybersecurity Research, University of Florida).
* **Vị trí lấy trong bài báo**:
  * **Section III (Data Collection and Preprocessing Pipeline)**: Xây dựng quy trình làm sạch mã nguồn Verilog nghiêm ngặt (Syntax Sanitization, Inferred Latch Detection) và ngân hàng lưu trữ dữ liệu thiết kế có cấu trúc để phục vụ huấn luyện và truy xuất (Retrieval-Augmented Generation).
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/verilog_linter.py`: Xây dựng bộ quét tĩnh cú pháp, làm sạch các ký tự markdown rác và rà soát triệt tiêu chốt ẩn (inferred latches) trước khi mô phỏng.
  * `knowledge_base/` & `agent/knowledge_matcher.py`: Lưu trữ và so khớp ngữ nghĩa với cơ sở tri thức vi mạch chuẩn (`hardware_db.json`), phân loại mạch phổ thông để sinh mã chuẩn xác.
  * Định hướng sử dụng tập dữ liệu chuẩn VerilogDB (20.392 mẫu Verilog sạch) làm dữ liệu gốc cho tiến trình Chưng cất tri thức (Knowledge Distillation) ở giai đoạn tiếp theo.

---

#### 6. Insights from Verification: Training a Verilog Generation LLM with Reinforcement Learning with Testbench Feedback (VeriPrefer)
* **Đường dẫn**: [https://arxiv.org/pdf/2504.15804](https://arxiv.org/pdf/2504.15804) / [https://arxiv.org/html/2504.15804v1](https://arxiv.org/html/2504.15804v1)
* **Tác giả & Tổ chức**: Ning Wang, Bingkun Yao, Zhe Jiang et al.
* **Vị trí lấy trong bài báo**:
  * **Section III & IV (Automated Testbench Generation & DPO with Testbench Feedback)**: Nhấn mạnh rằng sinh mã Verilog mà không có Testbench tự kiểm tra (Self-checking Scoreboard) là vô nghĩa. Sử dụng chính kết quả kiểm thử (Testbench Outcomes / Assertions) làm tín hiệu phản hồi để đánh giá độ chính xác chức năng (Functional Accuracy) và hướng dẫn sửa lỗi logic.
* **Hiện thực hóa trong hệ thống của nhóm**:
  * `agent/tb_generator.py`: Tự động sinh Testbench tự kiểm tra có gắn sẵn Verification Scoreboard theo chuẩn VeriPrefer, tự động so sánh ngõ ra và tính tỷ lệ chính xác chức năng (`Functional Accuracy: 100.0 PERCENT`).
  * `agent/reflection_loop.py`: Lấy trực tiếp thông báo lỗi assertion từ log ModelSim để xác định sai lệch nano-giây, làm căn cứ sửa mã Verilog tự động.
  * `agent/port_auditor.py`: Cơ chế kiểm toán toàn vẹn 4 chiều bảo đảm tính bất biến cổng (Port Invariant: $\text{Spec} \equiv \text{RTL} \equiv \text{BSF} \equiv \text{BDF}$).

