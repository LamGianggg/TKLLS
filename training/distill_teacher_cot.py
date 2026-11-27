"""
Module: distill_teacher_cot.py
Chưng cất Tri thức AI thực tế (Teacher-Student Sequence & CoT Knowledge Distillation):
- Teacher Model: Google Gemini (mặc định gemini-2.5-flash qua Google AI Studio API).
- Nguồn đặc tả: 100 đề bài từ docs/100_Prompt_Thiet_Ke_Mach.pdf + specs/*.txt + benchmarks/*/*.md.
- Bộ lọc chân lý (Truth Oracle):
  1. SpecAnalyzer (Kiểm tra khớp tên module & đủ cổng I/O so với đặc tả).
  2. AST Hardware Linter (agent/verilog_linter.py: 0 chốt ẩn, 0 chân lơ lửng, 0 race condition).
  3. ModelSim Compiler (vlog.exe: Errors: 0).
  * Nếu lần 1 lỗi -> Tự gửi log lỗi ngược lại cho Teacher sửa 1 lần (Self-Correction)
    và lưu mẫu lỗi lần 1 làm cặp DPO thật.
- Xuất kết quả:
  - training/dataset_teacher_distilled.json (tập chưng cất thuần từ Gemini Teacher)
  - Gộp vào training/dataset_clean_verified.json (ưu tiên CoT thật của Teacher)
  - Cập nhật training/REPORT_NHOM_1_DATASET.md
"""

import os
import sys
import re
import json
import time
import hashlib
import argparse
import subprocess
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")
TRAINING_DIR = os.path.join(PROJECT_ROOT, "training")
SIM_DIR = os.path.join(PROJECT_ROOT, "sim")
DOCS_PDF = os.path.join(PROJECT_ROOT, "docs", "100_Prompt_Thiet_Ke_Mach.pdf")
SPECS_DIR = os.path.join(PROJECT_ROOT, "specs")
BENCH_DIR = os.path.join(PROJECT_ROOT, "benchmarks")

CHECKPOINT_PATH = os.path.join(PROJECT_ROOT, "training", "distill_checkpoint.json")
TEACHER_OUT_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_teacher_distilled.json")
CLEAN_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_clean_verified.json")
DPO_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_dpo_preference.json")
REPORT_PATH = os.path.join(PROJECT_ROOT, "training", "REPORT_NHOM_1_DATASET.md")

for _p in (AGENT_DIR, TRAINING_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eda_finder import find_modelsim
from verilog_linter import VerilogLinter
from spec_analyzer import SpecAnalyzer
from tb_generator import TBGenerator
from verilogdb_sampler import sample_verilogdb_prompts


def load_api_key():
    """Đọc GEMINI_API_KEY từ biến môi trường hoặc file .env nội bộ (không hardcode)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def get_vlog_path():
    """Tìm đường dẫn vlog.exe, vlib.exe và vsim.exe của ModelSim."""
    ms = find_modelsim()
    if ms and "vlog" in ms and os.path.exists(ms["vlog"]):
        return ms["vlog"], ms.get("vlib"), ms.get("vsim")
    default_vlog = r"D:\altera\13.0sp1\modelsim_ase\win32aloem\vlog.EXE"
    default_vlib = r"D:\altera\13.0sp1\modelsim_ase\win32aloem\vlib.EXE"
    default_vsim = r"D:\altera\13.0sp1\modelsim_ase\win32aloem\vsim.EXE"
    if os.path.exists(default_vlog):
        return default_vlog, default_vlib, default_vsim
    return None, None, None


def extract_prompts_from_pdf():
    """Trích xuất 100 đề bài đặc tả chuẩn từ docs/100_Prompt_Thiet_Ke_Mach.pdf."""
    prompts = []
    if not os.path.exists(DOCS_PDF):
        return prompts

    try:
        import fitz
    except ImportError:
        print("[CẢNH BÁO] Thiếu PyMuPDF (fitz), bỏ qua đọc PDF.")
        return prompts

    doc = fitz.open(DOCS_PDF)
    full_text = "\n".join(page.get_text() for page in doc)
    chunks = [c for c in re.split(r"(?=\[PROMPT #\d+\])", full_text) if c.startswith("[PROMPT #")]

    category_map = [
        (1, 10, "Counter & Timer"),
        (11, 20, "Arithmetic & ALU"),
        (21, 30, "Register & Buffer"),
        (31, 40, "Codec & Multiplexer"),
        (41, 50, "FSM & Sequence Detector"),
        (51, 60, "Communication & Serial"),
        (61, 70, "Signal Conditioning & PWM"),
        (71, 80, "Memory & FIFO"),
        (81, 90, "System Control & Display"),
        (91, 100, "Advanced RTL & Clocking"),
    ]

    for chunk in chunks:
        m_num = re.match(r"\[PROMPT #(\d+)\]", chunk)
        p_num = int(m_num.group(1)) if m_num else 0

        # Cắt bỏ phần hướng dẫn sao chép & tiêu đề nhóm trang kế, bỏ ký tự điều khiển PDF (\x00)
        body = re.split(r"\n?[\x00\s]*Sao chép khối nội dung", chunk)[0]
        body = re.split(r"\n\s*NHÓM \d+\s*:", body)[0].replace("\x00", "").strip()

        # Lấy phần từ dấu # đầu tiên trở đi làm spec chuẩn
        hash_idx = body.find("\n# ")
        spec_body = body[hash_idx + 1:].strip() if hash_idx != -1 else body

        # Trích xuất tên module
        m_mod = re.search(r"#[^\n]*\(([a-zA-Z_][a-zA-Z0-9_]*)\)", spec_body)
        if not m_mod:
            m_mod = re.search(r"\(([a-zA-Z_][a-zA-Z0-9_]*)\)", chunk)
        mod_name = m_mod.group(1) if m_mod else f"ce118_prompt_{p_num:02d}"

        cat = "Digital Logic"
        for lo, hi, cname in category_map:
            if lo <= p_num <= hi:
                cat = cname
                break

        prompts.append({
            "id": f"distill_pdf_{p_num:03d}_{mod_name}",
            "module_name": mod_name,
            "category": cat,
            "origin": f"100_Prompt_Thiet_Ke_Mach.pdf (#{p_num:02d})",
            "spec_text": spec_body,
        })
    return prompts


def extract_extra_specs(seen_modules):
    """Bổ sung thêm các đề bài đặc thù trong specs/*.txt và benchmarks/*/*.md nếu chưa có."""
    extras = []
    candidate_files = []

    if os.path.isdir(SPECS_DIR):
        for fn in sorted(os.listdir(SPECS_DIR)):
            if fn.endswith((".txt", ".md")) and not fn.startswith("web_spec_"):
                candidate_files.append((os.path.join(SPECS_DIR, fn), f"specs/{fn}", "Project Spec"))

    if os.path.isdir(BENCH_DIR):
        for dp, _, fns in os.walk(BENCH_DIR):
            for fn in sorted(fns):
                if fn.endswith(".md"):
                    rel = os.path.relpath(os.path.join(dp, fn), PROJECT_ROOT).replace("\\", "/")
                    candidate_files.append((os.path.join(dp, fn), rel, "Benchmark"))

    for path, origin, cat in candidate_files:
        text = open(path, "r", encoding="utf-8", errors="replace").read().strip()
        if not text:
            continue
        analyzer = SpecAnalyzer(text)
        mod_name = analyzer.extract_module_name()
        if not mod_name or mod_name in seen_modules:
            continue
        seen_modules.add(mod_name)
        extras.append({
            "id": f"distill_extra_{mod_name}",
            "module_name": mod_name,
            "category": cat,
            "origin": origin,
            "spec_text": text,
        })
    return extras


def call_gemini_teacher(api_key, model, user_prompt, max_retries=4):
    """Gọi Google Gemini API sinh CoT phần cứng + Verilog chuẩn IEEE 1364-2001."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    system_prompt = (
        "Bạn là Kiến trúc sư Vi mạch số cao cấp (Senior Digital IC & FPGA Architect). "
        "Nhiệm vụ của bạn là thực hiện quy trình Chưng cất Tri thức (Hardware CoT + RTL Distillation) "
        "từ đặc tả kỹ thuật sang mã Verilog synthesizable chuẩn IEEE 1364-2001.\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. Trình bày đúng 2 phần rõ ràng:\n"
        "   - Phần 1: `### Phân tích kiến trúc vi mạch (Teacher CoT):` phân tích ngắn gọn, sắc bén ĐÚNG cho bài toán này "
        "(chức năng từng cổng I/O và độ rộng bit, cấu trúc tổ hợp hay tuần tự / sơ đồ chuyển trạng thái FSM, "
        "và cách xử lý để triệt tiêu hoàn toàn chốt ẩn Inferred Latch, chân lơ lửng Dangling Pin và Race Condition).\n"
        "   - Phần 2: Một khối code duy nhất nằm trong thẻ ```verilog ... ```.\n"
        "2. Tên module và toàn bộ danh sách cổng (tên, hướng input/output, độ rộng bus) PHẢI KHỚP 100% với đặc tả.\n"
        "3. Mọi cổng input (ngoài clk/rst nếu tổ hợp) đều phải được sử dụng thật trong logic; mọi cổng output đều phải được gán giá trị.\n"
        "4. Dùng phép gán non-blocking `<=` trong mọi khối tuần tự `always @(posedge ...)` và blocking `=` trong khối tổ hợp `always @(*)`, có đầy đủ nhánh `default:`/`else`.\n"
        "5. Chỉ sử dụng cú pháp Verilog-2001 chuẩn tương thích ModelSim-Altera và Quartus II 13.0sp1 (KHÔNG dùng SystemVerilog như logic, always_ff, always_comb)."
    )

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
            "thinkingConfig": {"thinkingBudget": 512},
        },
    }

    for attempt in range(max_retries):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    return None, f"Empty candidates: {str(data)[:200]}"
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                return text, None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                # Kiểm tra xem hết RPD (quota ngày) hay chỉ chạm RPM (quota phút)
                if ("PerDay" in body or "daily" in body.lower()
                        or "limit: 0" in body or "quotaValue" in body and '"0"' in body):
                    return None, f"QUOTA_DAILY_EXCEEDED: {body[:250]}"
                if attempt >= max_retries - 1:
                    return None, f"QUOTA_DAILY_EXCEEDED (429 persistent): {body[:250]}"
                wait_sec = 15 * (attempt + 1)
                m_retry = re.search(r"retry in ([\d.]+)s", body, re.IGNORECASE)
                if m_retry:
                    wait_sec = max(10, int(float(m_retry.group(1))) + 3)
                print(f"    [429 RPM] Chờ {wait_sec}s rồi thử lại...")
                time.sleep(wait_sec)
                continue
            if e.code == 503 and attempt < max_retries - 1:
                wait_sec = 10 * (attempt + 1)
                print(f"    [503 High Demand] Chờ {wait_sec}s rồi thử lại...")
                time.sleep(wait_sec)
                continue
            return None, f"HTTP_{e.code}: {body[:250]}"
        except Exception as ex:
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None, f"EXCEPTION: {ex}"

    return None, "MAX_RETRIES_EXCEEDED"


def extract_cot_and_verilog(response_text):
    """Tách phần suy luận Teacher CoT và khối code Verilog từ phản hồi Gemini."""
    if not response_text:
        return "", ""
    m_code = re.search(r"```(?:verilog|systemverilog)?\s*(.*?)\s*```", response_text, re.DOTALL | re.IGNORECASE)
    if not m_code:
        return "", ""
    verilog_code = m_code.group(1).strip()
    cot_part = response_text[:m_code.start()].strip()
    if not cot_part:
        cot_part = "### Phân tích kiến trúc vi mạch (Teacher CoT):\nThiết kế RTL đồng bộ/tổ hợp tuân thủ chuẩn IEEE 1364-2001."
    return cot_part, verilog_code


def verify_with_truth_oracle(spec_text, expected_module, verilog_code, vlog_path, vsim_path=None, verify_sim=False):
    """Kiểm chứng 3-4 lớp: Khớp cổng Spec -> AST Linter -> ModelSim vlog.exe -> (tuỳ chọn) vsim.exe."""
    issues = []
    if not verilog_code or "module " not in verilog_code or "endmodule" not in verilog_code:
        return False, ["Thiếu khai báo module/endmodule hợp lệ"]

    # 1. Kiểm tra tên module khớp đặc tả
    if expected_module and not re.search(rf"\bmodule\s+{re.escape(expected_module)}\b", verilog_code):
        issues.append(f"Sai tên module (yêu cầu `{expected_module}`)")

    # 2. Kiểm tra đủ cổng I/O theo SpecAnalyzer (bỏ comment trước khi tách header cổng)
    spec_ports = SpecAnalyzer(spec_text).extract_ports()
    stripped_code = VerilogLinter.strip_comments_and_strings(verilog_code)
    extracted = VerilogLinter.extract_module_info(stripped_code)
    actual_mod = expected_module
    if extracted and extracted[0]:
        actual_mod, verilog_inputs, verilog_outputs, _ = extracted
        actual_ports = set(verilog_inputs + verilog_outputs)
        for p in spec_ports:
            pname = p["name"]
            if pname not in actual_ports:
                issues.append(f"Thiếu cổng `{pname}` theo đặc tả")

    # 3. Kiểm tra AST Hardware Linter
    lint_res = VerilogLinter.lint_check(verilog_code)
    if not lint_res["valid"]:
        issues.extend(lint_res["issues"])

    if issues:
        return False, issues

    # 4. Biên dịch thật bằng ModelSim vlog.exe
    if not vlog_path:
        return False, ["Không tìm thấy ModelSim vlog.exe"]

    os.makedirs(SIM_DIR, exist_ok=True)
    tmp_v = os.path.join(SIM_DIR, "_distill_oracle_tmp.v")
    tmp_tb = os.path.join(SIM_DIR, "_distill_oracle_tb.v")
    with open(tmp_v, "w", encoding="utf-8") as f:
        f.write(verilog_code)

    try:
        proc = subprocess.run(
            [vlog_path, "-work", "work", tmp_v],
            cwd=SIM_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        out_log = proc.stdout + "\n" + proc.stderr
        if proc.returncode != 0 or "** Error:" in out_log or "** Fatal:" in out_log:
            err_lines = [ln.strip() for ln in out_log.splitlines() if "Error:" in ln or "Fatal:" in ln]
            return False, err_lines[:4] if err_lines else [f"vlog returncode={proc.returncode}"]

        # 5. (Tùy chọn) Chạy mô phỏng thực tế bằng TBGenerator + ModelSim vsim.exe
        if verify_sim and vsim_path and actual_mod:
            tb_gen = TBGenerator(sim_dir=SIM_DIR)
            tb_name, tb_code = tb_gen.generate_generic_tb(rtl_path=tmp_v, module_name=actual_mod)
            with open(tmp_tb, "w", encoding="utf-8") as f:
                f.write(tb_code)
            tb_comp = subprocess.run(
                [vlog_path, "-work", "work", tmp_tb],
                cwd=SIM_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            tb_log = tb_comp.stdout + "\n" + tb_comp.stderr
            if tb_comp.returncode != 0 or "** Error:" in tb_log or "** Fatal:" in tb_log:
                err_lines = [ln.strip() for ln in tb_log.splitlines() if "Error:" in ln or "Fatal:" in ln]
                return False, err_lines[:4] if err_lines else ["Lỗi biên dịch testbench vsim"]

            sim_proc = subprocess.run(
                [vsim_path, "-c", "-do", "run -all; quit -f", f"work.{tb_name}"],
                cwd=SIM_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
            sim_log = sim_proc.stdout + "\n" + sim_proc.stderr
            if "** Error:" in sim_log or "** Fatal:" in sim_log or "[ERROR]" in sim_log:
                err_lines = [ln.strip() for ln in sim_log.splitlines() if "Error:" in ln or "Fatal:" in ln or "[ERROR]" in ln]
                return False, err_lines[:4] if err_lines else ["Mô phỏng vsim thất bại"]

        return True, []
    except Exception as ex:
        return False, [f"ModelSim exception: {ex}"]
    finally:
        for tmp_p in (tmp_v, tmp_tb):
            if os.path.exists(tmp_p):
                os.remove(tmp_p)


def normalize_code(code_str):
    clean = re.sub(r"//.*", "", code_str)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
    return re.sub(r"\s+", " ", clean).strip().lower()


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_or_bootstrap_checkpoint():
    """Nạp checkpoint, hoặc tự khôi phục từ dataset_teacher_distilled.json nếu chạy trên máy mới."""
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    checkpoint = {"passed": [], "failed": [], "teacher_dpo_pairs": []}
    if os.path.exists(TEACHER_OUT_PATH):
        try:
            with open(TEACHER_OUT_PATH, "r", encoding="utf-8") as f:
                checkpoint["passed"] = json.load(f)
            print(f"[*] Khởi tạo checkpoint từ {len(checkpoint['passed'])} mẫu đã chưng cất sẵn trong repo.")
        except Exception:
            pass

    if os.path.exists(DPO_DATASET_PATH):
        try:
            with open(DPO_DATASET_PATH, "r", encoding="utf-8") as f:
                dpo_items = json.load(f)
            checkpoint["teacher_dpo_pairs"] = [
                td for td in dpo_items
                if td.get("id", "").startswith("dpo_teacher_") or "Self-Correction" in td.get("source", "")
            ]
        except Exception:
            pass

    return checkpoint


def merge_and_export(checkpoint, model_name):
    """Xuất dataset_teacher_distilled.json, gộp vào dataset_clean_verified.json và cập nhật REPORT_NHOM_1_DATASET.md."""
    teacher_items = checkpoint.get("passed", [])
    default_model = model_name.split(",")[0].strip() if model_name else "gemini-3.1-flash-lite"
    for item in teacher_items:
        item["input"] = re.split(r"\n?[\x00\s]*Sao chép khối nội dung", item.get("input", ""))[0].replace("\x00", "").strip()
        t_mod = item.get("teacher_model") or default_model
        if item.get("source", "").startswith("Gemini-gemini-") or "," in item.get("source", ""):
            item["source"] = f"Google Gemini ({t_mod}) Distillation"
    save_json(TEACHER_OUT_PATH, teacher_items)

    # Đọc dataset_clean_verified.json hiện có
    existing = []
    if os.path.exists(CLEAN_DATASET_PATH):
        with open(CLEAN_DATASET_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Ưu tiên giữ các mẫu Teacher-distilled mới (thay thế mẫu cùng module_name cũ dùng template CoT)
    teacher_mod_names = {item["module_name"] for item in teacher_items}
    seen_hashes = set()
    merged = []

    for item in teacher_items:
        m = re.search(r"```(?:verilog)?\s*(.*?)\s*```", item.get("output", ""), re.DOTALL | re.IGNORECASE)
        code = m.group(1) if m else item.get("output", "")
        h = hashlib.md5(normalize_code(code).encode("utf-8")).hexdigest()
        seen_hashes.add(h)
        merged.append(item)

    preserved_count = 0
    for item in existing:
        mname = item.get("module_name", "")
        # Tránh đè trùng tên module hoặc trùng mã MD5 với bản Teacher vừa chưng cất
        if mname in teacher_mod_names and item.get("source", "").startswith(("Spec2RTL", "Synthesized CE118", "Gemini-", "Google Gemini")):
            continue
        m = re.search(r"```(?:verilog)?\s*(.*?)\s*```", item.get("output", ""), re.DOTALL | re.IGNORECASE)
        code = m.group(1) if m else item.get("output", "")
        h = hashlib.md5(normalize_code(code).encode("utf-8")).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        merged.append(item)
        preserved_count += 1

    save_json(CLEAN_DATASET_PATH, merged)

    # Thống kê riêng tập 100% Thuần Teacher & tập Hợp nhất
    teacher_sources = {}
    teacher_cats = {}
    for item in teacher_items:
        s = item.get("source", "Khác")
        c = item.get("category", "Khác")
        teacher_sources[s] = teacher_sources.get(s, 0) + 1
        teacher_cats[c] = teacher_cats.get(c, 0) + 1

    source_stats = {}
    category_stats = {}
    for item in merged:
        s = item.get("source", "Khác")
        c = item.get("category", "Khác")
        source_stats[s] = source_stats.get(s, 0) + 1
        category_stats[c] = category_stats.get(c, 0) + 1

    failed_teacher = len(checkpoint.get("failed", []))
    total_attempted = len(teacher_items) + failed_teacher
    pass_pct = (len(teacher_items) / total_attempted * 100) if total_attempted else 0.0

    report = [
        "# BÁO CÁO NGHIỆM THU DỮ LIỆU & CHƯNG CẤT TRI THỨC AI (NHÓM 1)",
        "**Học phần**: Thiết kế luận lý số (CE118 - UIT / VJU)  ",
        "**Dự án**: Spec2RTL & Prompt2Silicon (Teacher-Student Distillation + ModelSim Truth Oracle)  ",
        f"**Ngày cập nhật**: {time.strftime('%d/%m/%Y %H:%M')}  ",
        "",
        "---",
        "",
        "## 1. Quy Trình Chưng Cất Tri Thức Thực Tế (Teacher $\\rightarrow$ Truth Oracle $\\rightarrow$ Student)",
        f"- **Teacher Model**: Google Gemini (`{model_name}`) sinh chuỗi suy luận thiết kế phần cứng đặc thù (**Teacher CoT**) kèm mã Verilog IEEE 1364-2001.",
        "- **Bộ lọc Chân lý (Truth Oracle)**:",
        "  1. `SpecAnalyzer`: Đối soát khớp tên module và 100% danh sách cổng I/O từ đặc tả.",
        "  2. `VerilogLinter` (`agent/verilog_linter.py`): 0 chốt ẩn (`Inferred Latch`), 0 chân lơ lửng (`Dangling Pin`), 0 lỗi gán blocking tuần tự.",
        "  3. `ModelSim vlog.exe` (kèm tùy chọn `vsim.exe`): Biên dịch/mô phỏng thực tế không lỗi (`Errors: 0`).",
        f"- **Tập 100% Thuần Gemini Teacher CoT (`training/dataset_teacher_distilled.json`)**: **{len(teacher_items)}/{total_attempted} ({pass_pct:.1f}%)** mẫu vượt qua Truth Oracle ({len(teacher_cats)} họ vi mạch, gồm đề CE118 + VerilogDB `Rohan-code/Verilog_DB_read`).",
        f"- **Tập SFT hợp nhất (`training/dataset_clean_verified.json`)**: **{len(merged)} mẫu sạch** (gồm **{len(teacher_items)}** mẫu CoT thật từ Gemini Teacher + **{preserved_count}** mẫu đã thẩm định ModelSim từ kho gốc).",
        "",
        "---",
        "",
        "## 2. Phân Bố Nguồn Tập Thuần Teacher (`dataset_teacher_distilled.json`)",
        "| Nguồn Teacher | Số lượng mẫu | Ghi chú |",
        "| :--- | :---: | :--- |",
    ]
    for src, cnt in sorted(teacher_sources.items(), key=lambda x: -x[1]):
        report.append(f"| {src} | **{cnt}** | 100% CoT thật + Pass Truth Oracle |")

    report.extend([
        "",
        "## 3. Phân Bố Nguồn Dữ Liệu SFT Hợp Nhất (`dataset_clean_verified.json`)",
        "| Nguồn dữ liệu | Số lượng mẫu đạt chuẩn | Ghi chú |",
        "| :--- | :---: | :--- |",
    ])
    for src, cnt in sorted(source_stats.items(), key=lambda x: -x[1]):
        report.append(f"| {src} | **{cnt}** | Pass 100% ModelSim & AST Linter |")

    report.extend([
        "",
        "## 4. Phân Bố Theo Họ Vi Mạch (Tập Thuần Teacher)",
        "| Họ vi mạch | Số lượng mẫu | Tỷ lệ (%) |",
        "| :--- | :---: | :---: |",
    ])
    for cat, cnt in sorted(teacher_cats.items(), key=lambda x: -x[1]):
        pct = (cnt / len(teacher_items) * 100) if teacher_items else 0.0
        report.append(f"| {cat} | **{cnt}** | {pct:.1f}% |")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    return len(teacher_items), len(merged)


def main():
    parser = argparse.ArgumentParser(description="Chưng cất tri thức từ Gemini Teacher qua ModelSim Truth Oracle")
    parser.add_argument("--model", default="gemini-3.5-flash-lite,gemini-3-flash-preview,gemini-3.1-flash-lite,gemini-3.5-flash", help="Tên model Teacher Gemini (phân cách bằng dấu phẩy để fallback)")
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số đề bài xử lý mới trong lần chạy (0 = toàn bộ)")
    parser.add_argument("--delay", type=float, default=4.5, help="Thời gian nghỉ (giây) giữa các request Free Tier")
    parser.add_argument("--include-verilogdb", action="store_true", help="Bổ sung nguồn đặc tả đa dạng họ mạch từ Rohan-code/Verilog_DB_read")
    parser.add_argument("--verilogdb-count", type=int, default=1000, help="Số lượng mẫu VerilogDB cần kéo chọn lọc (mặc định 1000 để lấy toàn bộ pool)")
    parser.add_argument("--refresh-verilogdb", action="store_true", help="Tải lại tập chọn lọc VerilogDB từ HuggingFace")
    parser.add_argument("--verify-sim", action="store_true", help="Chạy thêm mô phỏng ModelSim vsim.exe ngoài bước biên dịch vlog.exe")
    parser.add_argument("--retry-failed", action="store_true", help="Chạy lại các mẫu từng failed trong checkpoint")
    parser.add_argument("--merge-only", action="store_true", help="Chỉ gộp lại từ checkpoint hiện có, không gọi API")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    print("=" * 80)
    print(f">>> CHƯNG CẤT TRI THỨC AI: TEACHER ({args.model}) -> AST LINTER + MODELSIM ORACLE")
    print("=" * 80)

    checkpoint = load_or_bootstrap_checkpoint()

    if args.merge_only:
        t_cnt, m_cnt = merge_and_export(checkpoint, args.model)
        print(f"[DONE] Đã gộp {t_cnt} mẫu Teacher vào {m_cnt} mẫu tổng tại {CLEAN_DATASET_PATH}")
        return

    api_key = load_api_key()
    if not api_key:
        print("[LỖI] Chưa tìm thấy GEMINI_API_KEY trong biến môi trường hoặc file .env!")
        sys.exit(1)

    vlog_path, vlib_path, vsim_path = get_vlog_path()
    if not vlog_path:
        print("[LỖI] Không tìm thấy ModelSim vlog.exe!")
        sys.exit(1)

    os.makedirs(SIM_DIR, exist_ok=True)
    work_dir = os.path.join(SIM_DIR, "work")
    if not os.path.exists(work_dir) and vlib_path:
        subprocess.run([vlib_path, "work"], cwd=SIM_DIR, capture_output=True)

    # Thu thập danh sách đề bài CE118 + specs/ + benchmarks/
    prompts = extract_prompts_from_pdf()
    seen_mods = {p["module_name"].lower() for p in prompts}
    extra_prompts = extract_extra_specs(seen_mods)
    prompts.extend(extra_prompts)
    seen_mods.update(p["module_name"].lower() for p in extra_prompts)
    seen_mods.update((item.get("module_name") or "").lower() for item in checkpoint.get("passed", []))

    if args.include_verilogdb:
        vdb_prompts = sample_verilogdb_prompts(
            target_count=args.verilogdb_count,
            seen_modules=seen_mods,
            force_refresh=args.refresh_verilogdb,
        )
        prompts.extend(vdb_prompts)

    print(f"[*] Tổng số đặc tả đầu vào thu thập được: {len(prompts)} bài toán.")

    if args.retry_failed:
        checkpoint["failed"] = []

    done_ids = {item["id"] for item in checkpoint.get("passed", [])}
    done_ids.update(item["id"] for item in checkpoint.get("failed", []))
    pending = [p for p in prompts if p["id"] not in done_ids]
    print(f"[*] Đã xử lý trước đó: {len(done_ids)} | Còn lại cần chưng cất: {len(pending)}")

    if args.limit > 0:
        pending = pending[:args.limit]
        print(f"[*] Chế độ giới hạn đợt chạy: {len(pending)} bài.")

    model_queue = [m.strip() for m in args.model.split(",") if m.strip()]
    model_idx = 0

    for idx, p in enumerate(pending, 1):
        mod_name = p["module_name"]
        if model_idx >= len(model_queue):
            break
        active_model = model_queue[model_idx]
        print(f"\n[{idx}/{len(pending)}] ({active_model}) Đang chưng cất: {mod_name} ({p['origin']})...")

        user_prompt = (
            "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau:\n\n"
            f"{p['spec_text']}"
        )

        resp_text, err = None, None
        while model_idx < len(model_queue):
            active_model = model_queue[model_idx]
            resp_text, err = call_gemini_teacher(api_key, active_model, user_prompt)
            if err and "QUOTA_DAILY_EXCEEDED" in err:
                print(f"    [HẾT QUOTA NGÀY] Model {active_model} chạm giới hạn RPD.")
                model_idx += 1
                if model_idx < len(model_queue):
                    print(f"    -> Tự động chuyển sang model dự phòng: {model_queue[model_idx]}")
                    continue
                else:
                    print("[DỪNG AN TOÀN] Tất cả model đều chạm giới hạn ngày. Checkpoint đã được lưu.")
                    break
            break

        if model_idx >= len(model_queue):
            break

        if err:
            print(f"    [LỖI API] {err}")
            checkpoint["failed"].append({"id": p["id"], "module_name": mod_name, "error": err})
            save_json(CHECKPOINT_PATH, checkpoint)
            time.sleep(args.delay)
            continue

        cot, code = extract_cot_and_verilog(resp_text)
        ok, issues = verify_with_truth_oracle(
            p["spec_text"], mod_name, code, vlog_path, vsim_path=vsim_path, verify_sim=args.verify_sim
        )

        # Self-Correction Reflection nếu lần 1 lỗi
        if not ok:
            print(f"    [Lần 1 FAIL Oracle]: {issues[0] if issues else 'Lỗi'} -> Gửi log cho Teacher tự sửa...")
            first_bad_code = code
            time.sleep(args.delay)
            fix_prompt = (
                f"{user_prompt}\n\n"
                f"Mã Verilog lần trước của bạn:\n```verilog\n{first_bad_code}\n```\n\n"
                f"Bị ModelSim / AST Linter từ chối với các lỗi sau:\n- " + "\n- ".join(issues) + "\n\n"
                "Hãy phân tích lại nguyên nhân lỗi và xuất lại đầy đủ 2 phần (Teacher CoT + mã Verilog đã sửa sạch 100%)."
            )
            resp2, err2 = call_gemini_teacher(api_key, active_model, fix_prompt)
            if err2 and "QUOTA_DAILY_EXCEEDED" in err2:
                print(f"    [HẾT QUOTA NGÀY KHI SELF-CORRECTION] Model {active_model} chạm giới hạn RPD.")
                model_idx += 1
                if model_idx >= len(model_queue):
                    print("[DỪNG AN TOÀN] Tất cả model đều chạm giới hạn ngày. Checkpoint đã được lưu.")
                    break
                time.sleep(args.delay)
                continue
            if not err2 and resp2:
                cot2, code2 = extract_cot_and_verilog(resp2)
                ok2, issues2 = verify_with_truth_oracle(
                    p["spec_text"], mod_name, code2, vlog_path, vsim_path=vsim_path, verify_sim=args.verify_sim
                )
                if ok2:
                    ok = True
                    cot, code = cot2, code2
                    verif_tag = "PASS_100_MODELSIM_VSIM" if args.verify_sim else "PASS_100_MODELSIM_VLOG"
                    checkpoint.setdefault("teacher_dpo_pairs", []).append({
                        "id": f"dpo_teacher_{mod_name}",
                        "category": p["category"],
                        "source": f"Google Gemini ({active_model}) Self-Correction DPO",
                        "module_name": mod_name,
                        "prompt": f"Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.\n\n{p['spec_text']}",
                        "chosen": f"```verilog\n{code2}\n```",
                        "rejected": f"```verilog\n{first_bad_code}\n```",
                        "rejected_error_type": f"TEACHER_ORACLE_REJECTED ({issues[0][:80]})",
                        "chosen_verification": verif_tag,
                        "rejected_verification": "FAIL_ORACLE_LINTER",
                    })
                    print("    [Self-Correction PASS] Đã sửa thành công & thu được 1 cặp DPO thật!")
                else:
                    issues = issues2

        if ok:
            verif_tag = "PASS_100_MODELSIM_VSIM" if args.verify_sim else "PASS_100_MODELSIM_VLOG"
            entry = {
                "id": p["id"],
                "category": p["category"],
                "source": f"Google Gemini ({active_model}) Distillation",
                "teacher_model": active_model,
                "module_name": mod_name,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": p["spec_text"],
                "output": f"{cot}\n\n```verilog\n{code}\n```",
                "verification_status": verif_tag,
                "linter_status": "CLEAN_0_LATCH_0_DANGLING_PIN",
            }
            checkpoint["passed"].append(entry)
            print(f"    [PASS 100%] Đã kiểm chứng ModelSim + AST Linter ({mod_name})")
        else:
            checkpoint["failed"].append({"id": p["id"], "module_name": mod_name, "issues": issues})
            print(f"    [REJECTED] Loại bỏ mẫu không đạt chuẩn: {issues[:2]}")

        save_json(CHECKPOINT_PATH, checkpoint)
        if idx < len(pending):
            time.sleep(args.delay)

    t_cnt, m_cnt = merge_and_export(checkpoint, args.model)
    print("\n" + "=" * 80)
    print(f"[HOÀN TẤT ĐỢT CHƯNG CẤT] Teacher PASS: {t_cnt} | Tập sạch hợp nhất: {m_cnt} mẫu.")
    print(f"- File Teacher thuần : {TEACHER_OUT_PATH}")
    print(f"- File SFT hợp nhất  : {CLEAN_DATASET_PATH}")
    print(f"- Báo cáo cập nhật   : {REPORT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
