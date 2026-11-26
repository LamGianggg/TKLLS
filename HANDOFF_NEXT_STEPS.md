# HANDOFF GUIDE CHO ANTIGRAVITY TRÊN MÁY MỚI
**Dự án:** Spec2RTL & Prompt2Silicon — Đồ án 3 (CE118, UIT / VJU)  
**Giảng viên hướng dẫn:** TS. Nguyễn Văn Tình  
**Repository:** `https://github.com/LamGianggg/TKLLS`  
**Cập nhật lần cuối:** 26/11/2026

> **Hướng dẫn cho Agent mới:** Khi người dùng mở dự án trên máy mới, hãy đọc file này trước tiên để nắm trọn bối cảnh, những gì đã làm xong, và **5 bước tiếp theo cần thực hiện** để hoàn thiện hệ thống theo đúng yêu cầu của giảng viên.

---

## 1. Mục tiêu cốt lõi của người dùng & giảng viên
Giảng viên hướng dẫn (**TS. Nguyễn Văn Tình**) yêu cầu hệ thống phải thể hiện rõ và thực chất quy trình **Chưng cất Tri thức AI (Teacher–Student Knowledge Distillation)** từ dữ liệu chuẩn **VerilogDB gốc (`arXiv:2507.13369`)** + bộ đề **CE118**, huấn luyện mô hình cục bộ (**`Qwen2.5-Coder-3B`**), rồi ghép vào hệ thống kiểm chứng EDA khép kín (`AST Linter` + `ModelSim` + `Quartus II`) để chạy thực tế trên máy trường/máy mới.

Người dùng chuyển từ máy cũ (4 GB RAM, `i5-6200U`, không có GPU rời) sang **máy khác mạnh hơn** để chạy tiếp phần chưng cất VerilogDB, huấn luyện/tích hợp bản **`3B`** và kiểm thử toàn trình.

---

## 2. Những gì ĐÃ HOÀN THÀNH trên repo (không cần làm lại)

### A. Hạ tầng lõi (`agent/`, `benchmarks/`, `reports/`)
- Đã kiểm toán, sửa lỗi và dọn gọn cấu trúc thư mục:
  - `agent/`: 13 module điều phối/lõi (`run_spec2rtl.py`, `spec_analyzer.py`, `rtl_generator.py`, `tb_generator.py`, `verilog_linter.py`, `simulator.py`, `reflection_loop.py`, `bdf_generator.py`, `vwf_generator.py`, `port_auditor.py`, `synthesis_profiler.py`, `eda_finder.py`, `knowledge_matcher.py`) + 2 bộ test (`test_group3_linter.py`, `test_robustness_battery.py`).
  - `benchmarks/benchmark_week2_spec2rtl.py`: chạy benchmark 6 mạch mẫu trong `specs/`, xuất báo cáo về `reports/REPORT_TUAN_2_BENCHMARK.md`.
  - `benchmarks/benchmark_70_rag.py`: bộ benchmark truy vấn ngôn ngữ tự nhiên (né từ khóa) cho nhóm 70% khối hạ tầng phổ thông, so sánh `keyword` vs `bm25` vs `hybrid` (`Recall@1`, `Recall@3`, `MRR`) và xuất báo cáo tại `reports/REPORT_70_RAG_BENCHMARK.md`.
  - `agent/tb_generator.py`: đã nâng cấp **Self-Checking Testbench** chuẩn Verilog-2001 (ModelSim `vlog`) cho các họ mạch nhóm 70% (**Counter/Up-Down/BCD/Gray**, **FIFO/Buffer** full–empty–data order, **Shift Register/Barrel Shifter**, **Decoder/Mux/Priority Encoder**, **ALU/Adder/Subtractor/Multiplier/Comparator**, **PWM/Timer**, **Ready/Valid handshake**) — tự đối chiếu oracle theo cổng RTL thực tế và in `[SUCCESS]` / `[FAIL]` + `$finish`.
  - Kết quả kiểm chứng gần nhất trên máy cũ:
    - `python agent/test_group3_linter.py` $\rightarrow$ **5/5 PASS**.
    - `python agent/test_robustness_battery.py` $\rightarrow$ **20/20 PASS**.
    - `reports/REPORT_TUAN_2_BENCHMARK.md` $\rightarrow$ **6/6 (100% Pass@1)** trong **54.89s** *(đã đối soát `.map.summary` trên Cyclone II: `uart_tx_8bit` là **28 LEs**, không phải 59 LEs như typo cũ)*.
- `agent/spec_analyzer.py` đã có **Domain Guard** (`check_unsupported_domain()` chặn `ANALOG_AMS`, `HIGH_SPEED_PHY`, `IRRELEVANT_INPUT` và `is_30_percent_architecture()` chặn `SOC_AI`).
- **Tích hợp RAG & Cầu nối AI–EDA đã hoàn thiện sẵn:**
  - `agent/knowledge_matcher.py`: đã nâng cấp lên **Hybrid Retrieval bằng Reciprocal Rank Fusion (RRF)** kết hợp **Semantic Vector + BM25 + 3-gram Jaccard + `KHAI_NIEM_PHAN_CUNG`** (0% `torch`), tự động chọn 3 backend vector theo ưu tiên: (1) offline `fastembed` (ONNX CPU), (2) pre-computed cache `knowledge_base/hardware_embeddings.npz` (`numpy`) + `gemini-embedding-001` khi có `GEMINI_API_KEY` & mạng, (3) pure-offline `TfidfVectorizer + TruncatedSVD` (LSA fallback). Hỗ trợ `search_by_mode()`, `format_rag_context()` (Top-K từ `hardware_db.json` và `dataset_teacher_distilled.json`), và `save_verified_design()` (lưu ngược mẫu pass vào DB, chống trùng MD5).
  - `agent/run_spec2rtl.py`: đã tích hợp sẵn cờ `--use-distilled` nối vào `models/run_inference.py` (có fallback an toàn về `RTLGenerator`) và **vòng nạp ngược mẫu pass Linter + ModelSim + Quartus vào `knowledge_base/hardware_db.json`**.

### B. Chưng cất dữ liệu đợt 1 từ Gemini Teacher (`training/`)
- Đã tạo script [training/distill_teacher_cot.py](training/distill_teacher_cot.py) gọi Google Gemini API sinh **Teacher CoT phân tích riêng từng mạch + mã Verilog IEEE 1364-2001**, kiểm chứng qua **3 tầng Truth Oracle**:
  1. `SpecAnalyzer` (đối soát khớp tên module và đủ cổng I/O).
  2. `VerilogLinter.lint_check()` (0 chốt ẩn, 0 chân lơ lửng, 0 blocking `=` trong khối tuần tự).
  3. `ModelSim vlog.exe` (biên dịch thực tế `Errors: 0`), kèm **1 vòng Self-Correction** tự sửa nếu lần 1 lỗi và thu lại thành cặp DPO thật.
- Kết quả đợt 1 đã có trong repo:
  - [training/dataset_teacher_distilled.json](training/dataset_teacher_distilled.json): **104/108 (96.3%)** mẫu CoT thật từ Gemini *(93 mẫu từ `gemini-3.1-flash-lite` và 11 mẫu từ `gemini-2.5-flash`)* cho 100 đề `docs/100_Prompt_Thiet_Ke_Mach.pdf` + `specs/` + `benchmarks/`.
  - [training/dataset_clean_verified.json](training/dataset_clean_verified.json): **1,191 mẫu SFT** *(104 mẫu Gemini CoT thật + 1,087 mẫu sạch từ kho cũ)*.
  - [training/dataset_dpo_preference.json](training/dataset_dpo_preference.json): **1,200 cặp DPO** *(gồm 9 cặp thật từ Teacher Self-Correction + đột biến 3 lỗi RTL)*.
  - [training/REPORT_NHOM_1_DATASET.md](training/REPORT_NHOM_1_DATASET.md): báo cáo thống kê đã cập nhật.

### C. Notebook Colab, Inference & Slide báo cáo
- [training/train_spec2rtl_qwen3b_colab.ipynb](training/train_spec2rtl_qwen3b_colab.ipynb) & [training/train_spec2rtl_qwen3b_dpo_colab.ipynb](training/train_spec2rtl_qwen3b_dpo_colab.ipynb): đã đặt mặc định `MODEL_SIZE = "3B"` (có thể đổi `"0.5B"` / `"1.5B"` / `"3B"`), hỗ trợ nối tiếp SFT $\rightarrow$ DPO và tự động xuất cả **LoRA adapter** lẫn **GGUF (`q4_k_m`)**.
- [models/run_inference.py](models/run_inference.py): đã hỗ trợ ưu tiên **Domain Guard** $\rightarrow$ **Hybrid BM25 RAG (`use_rag=True`)** $\rightarrow$ **GGUF (`llama_cpp`)** $\rightarrow$ **PyTorch + PEFT** $\rightarrow$ **Fallback `RTLGenerator`**.
- [docs/Kich_Ban_Slide_Bao_Cao.md](docs/Kich_Ban_Slide_Bao_Cao.md) & [docs/Spec2RTL_Bao_Ve_Do_An_3.html](docs/Spec2RTL_Bao_Ve_Do_An_3.html): kịch bản 14 slide và bản trình chiếu HTML 16:9 tương tác (Slide 8 đã nhúng sơ đồ kiến trúc mới [docs/images/spec2rtl_fig3_adapted.png](docs/images/spec2rtl_fig3_adapted.png) bản địa hóa từ Fig. 3 *Spec2RTL-Agent*).

---

## 3. Khám phá quan trọng về VerilogDB gốc (`arXiv:2507.13369`)
- **Tình trạng hiện tại trên repo:** GitHub hiện tại **CHƯA CÓ dữ liệu từ VerilogDB gốc** (trong `knowledge_base/hardware_db.json` chỉ có 539 mẫu từ VerilogEval, CVDP, Verilog-Instruct-60k, VeriPrefer, RTLLM, Spec2RTL). Vì file gốc nặng (~301 MB nén / ~1.15 GB giải nén) nên chưa tải về máy cũ.
- Đã xác minh truy cập thành công tập dữ liệu công khai **`Rohan-code/Verilog_DB_read`** trên HuggingFace:
  - Quy mô: **40,755 mẫu** (`data/train-00000-of-00003.parquet` .. `00002`).
  - Các trường dữ liệu khớp chuẩn VerilogDB: `module_name`, `ports` (`name`, `direction`, `bit_width`), `comments`, `verilog_code`, `token_count`, `description`, `classification`.
  - **2 cách tải trên máy mới (Antigravity cần thực hiện ở Bước 2):**
    1. **Kéo chọn lọc qua REST API (nhanh, nhẹ ổ đĩa):**
       ```text
       https://datasets-server.huggingface.co/rows?dataset=Rohan-code/Verilog_DB_read&config=default&split=train&offset=0&length=100
       ```
    2. **Hoặc tải trực tiếp bộ `.parquet` từ HuggingFace** (`huggingface.co/datasets/Rohan-code/Verilog_DB_read`) nếu máy mới đủ dung lượng để lọc cục bộ nhiều mẫu hơn *(BẮT BUỘC thêm `*.parquet` / thư mục chứa file thô vào `.gitignore` vì file vượt giới hạn 100 MB của GitHub)*.

---

## 4. VIỆC CẦN LÀM TIẾP THEO (5 Bước Theo Thứ Tự)

### Bước 1: Kiểm tra môi trường máy mới & Lấy API Key
1. Kiểm tra cấu hình máy mới (CPU, RAM, GPU CUDA), đường dẫn cài **Altera Quartus II 13.0sp1** & **ModelSim** bằng `python agent/eda_finder.py`, và chạy nhanh `python agent/test_group3_linter.py` để xác nhận môi trường chạy bình thường.
2. Yêu cầu người dùng cung cấp **Google Gemini API Key mới** *(lưu ý: key cũ đã lộ trong lịch sử chat cũ và cần bỏ, KHÔNG bao giờ lưu API key vào file được Git theo dõi — luôn truyền qua `$env:GEMINI_API_KEY` hoặc file `.env` đã có trong `.gitignore`)*.
3. **Model khuyên dùng cho Free Tier:** **`gemini-3.1-flash-lite`** (`15 RPM`, hạn mức ngày rất thoáng — đã test chạy thông >90 request liên tiếp không dính 429 ngày), dự phòng **`gemini-3-flash-preview`**. *(Không dùng `gemini-2.5-flash` làm chính vì Free Tier bị chặn ~20 req/ngày).*

### Bước 2: Chưng cất bổ sung từ VerilogDB gốc & Chốt bộ dữ liệu 100% Thuần Chưng Cất
*Người dùng muốn dự án đạt chuẩn **100% Chưng cất AI thật** (không bị pha loãng bởi 786 mẫu CoT văn mẫu cũ).*
1. Mở rộng `training/distill_teacher_cot.py` (hoặc tạo thêm hàm nguồn VerilogDB) để kéo chọn lọc **~150–250 mẫu đa dạng họ mạch** (`classification`) từ **`Rohan-code/Verilog_DB_read`** (lọc mẫu có `description` rõ nghĩa, `ports` đầy đủ, `token_count < 1500`, không trùng `module_name` với 104 mẫu đã có).
2. Cho `gemini-3.1-flash-lite` sinh **Teacher CoT phân tích mạch + Verilog IEEE 1364-2001**, lọc qua **Truth Oracle 3 tầng** (`SpecAnalyzer` + `VerilogLinter` + `ModelSim vlog.exe`, kèm cân nhắc thêm bước chạy `tb_generator` + `vsim` nếu muốn nâng từ Compile-Pass lên Simulation-Pass).
3. Xuất thành tập **100% thuần Gemini Teacher CoT** (~250–350+ mẫu tại `training/dataset_teacher_distilled.json`): gồm **104 mẫu CE118 + ~150–250 mẫu VerilogDB**.
4. Cập nhật `training/build_dpo_dataset.py` hỗ trợ xuất cặp DPO riêng cho tập thuần Teacher (ví dụ `training/dataset_teacher_dpo.json`, ưu tiên cặp Self-Correction thật từ Teacher + đột biến 3 lỗi RTL).
5. Cập nhật 2 notebook Colab trỏ URL vào `dataset_teacher_distilled.json` và `dataset_teacher_dpo.json` *(hoặc đặt cờ chọn `USE_PURE_TEACHER_DISTILL = True`)* rồi `git commit & push` lên GitHub.

### Bước 3: Train Student `Qwen2.5-Coder-3B` trên Google Colab (T4 GPU)
1. Người dùng mở Google Colab (`T4 GPU`), nạp từ GitHub `LamGianggg/TKLLS`.
2. Chạy nối tiếp `training/train_spec2rtl_qwen3b_colab.ipynb` (SFT) $\rightarrow$ `training/train_spec2rtl_qwen3b_dpo_colab.ipynb` (DPO + xuất LoRA `spec2rtl_3b_dpo_lora` + xuất GGUF `q4_k_m` + lưu ảnh `dpo_loss_convergence.png`).
3. Tranh thủ lúc Colab còn bật GPU, chạy thêm script đánh giá **Ablation Study** trên ~20–30 bài test chưa từng nằm trong tập train để đo thực tế:
   - **Teacher (`gemini-3.1-flash-lite`)** vs **Base Student (`Qwen2.5-Coder-3B` chưa train)** vs **Distilled Student (`Qwen2.5-Coder-3B` SFT + DPO)**.
4. Tải adapter/GGUF mới và biểu đồ loss mới về máy (`models/` và `docs/dpo_loss_convergence.png`).

### Bước 4: Kích hoạt Student `--use-distilled` & Đo kiểm toàn trình trên máy mới
- **Đã tích hợp sẵn trong repo (không cần code lại cầu nối):**
  - `Hybrid BM25 RAG` (`agent/knowledge_matcher.py`), tham số `use_rag=True` trong `models/run_inference.py`, cờ `--use-distilled` + vòng nạp ngược DB trong `agent/run_spec2rtl.py`, và sơ đồ kiến trúc `docs/images/spec2rtl_fig3_adapted.png` đã được tích hợp hoàn chỉnh.
- **Việc cần chạy trên máy mới sau Bước 1–3** *(khi đã kéo `VerilogDB`, train `Qwen2.5-Coder-3B` trên Colab và thả trọng số GGUF/LoRA vào `models/`)*:
  1. Chạy thử luồng AI chưng cất + RAG + EDA khép kín qua `python agent/run_spec2rtl.py specs/<file>.txt --use-distilled` (hệ thống sẽ tự qua `RTLPortEnforcer` $\rightarrow$ `VerilogLinter` $\rightarrow$ `EDASimulator` + `ReflectionAgent` $\rightarrow$ `bdf_generator`/`vwf_generator` và nạp ngược mẫu pass vào `knowledge_base/hardware_db.json`).
  2. Chạy kiểm chứng lại `agent/test_group3_linter.py`, `agent/test_robustness_battery.py`, `benchmarks/benchmark_week2_spec2rtl.py` (cả chế độ `--use-distilled`) và đo bảng **Ablation Study**.

### Bước 5: Đồng bộ Slide & Báo cáo trước khi bảo vệ
- Cập nhật số liệu chưng cất VerilogDB mới, kết quả Ablation Study (Teacher vs Base vs Distilled 3B), và kiến trúc đã nối AI vào luồng chính trong:
  - [docs/Kich_Ban_Slide_Bao_Cao.md](docs/Kich_Ban_Slide_Bao_Cao.md)
  - [docs/Spec2RTL_Bao_Ve_Do_An_3.html](docs/Spec2RTL_Bao_Ve_Do_An_3.html)
  - [README.md](README.md)

---

## 5. Lưu ý kỹ thuật & Cạm bẫy đã gặp (tránh lặp lại lỗi)
1. **API trả về của các module trong `agent/`:**
   - `VerilogLinter.extract_module_info(code)` trả về **tuple 4 phần tử** `(mod_name, inputs, outputs, body)` (không phải dict). Luôn strip comment bằng `VerilogLinter.strip_comments_and_strings(code)` trước khi gọi để tránh lỗi nhận nhầm comment cuối dòng cổng.
   - `SpecAnalyzer(text).extract_ports()` trả về **list of dicts** `[{"name": ..., "direction": ..., "width": ...}]` (không phải dict có key `"inputs"`).
2. **Tham số khi gọi Gemini REST API (`2.5` / `3.x`):**
   - Luôn set `"thinkingConfig": {"thinkingBudget": 512}` và `"maxOutputTokens": 8192`, `timeout=30`. Nếu bỏ `thinkingConfig`, model thinking có thể ngốn hết token budget và cắt cụt code trước `endmodule`.
   - Khi gặp `HTTP 503` (high demand) thì chờ 10–20s thử lại; khi gặp `HTTP 429` phân biệt rõ `PerDay` (chuyển model hoặc dừng lưu checkpoint) với `RPM` (chờ theo `retry in Xs`).
3. **PowerShell trên Windows:**
   - Không dùng pipe `@' ... '@ | & { ...; python - }` trong PowerShell vì scriptblock không truyền stdin vào `python -` khiến lệnh treo. Dùng `@' ... '@ | python -` trực tiếp hoặc chạy file `.py`.
   - Với `urllib` gọi HuggingFace/GitHub trên một số máy Windows có thể cần `ssl._create_unverified_context()`.
4. **Git & Bảo mật:**
   - `training/distill_checkpoint.json`, `.env`, `*.gguf`, `*.safetensors` đã được đưa vào `.gitignore`. Trước khi `git push`, luôn kiểm tra bằng `git grep` đảm bảo không dính API key nào.
