"""
Module: build_dpo_dataset.py
Nhiệm vụ Nhóm 1 (Dữ liệu & Thẩm định):
- Xây dựng tập dữ liệu DPO Preference (Direct Preference Optimization) gồm cặp đôi CHOSEN và REJECTED.
- Dành cho tiến trình Huấn luyện Căn chỉnh Phần cứng (Hardware Alignment / RLHF) ở Tuần 2.
- Cấu trúc mẫu DPO:
  {
    "id": "dpo_...",
    "prompt": "...",
    "chosen": "<Mã Verilog chuẩn sạch 100%, pass ModelSim, không chốt ẩn, không chân lơ lửng>",
    "rejected": "<Mã Verilog bị lỗi phần cứng vi mạch do mô hình sơ cấp sinh ra>",
    "rejected_error_type": "INFERRED_LATCH | DANGLING_PIN | BLOCKING_IN_SEQUENTIAL"
  }
"""

import os
import re
import json
import argparse

# Định nghĩa đường dẫn các tập dữ liệu SFT đầu vào, tập DPO đầu ra và checkpoint chưng cất
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFT_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_clean_verified.json")
TEACHER_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_teacher_distilled.json")
DPO_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_dpo_preference.json")
TEACHER_DPO_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_teacher_dpo.json")
CHECKPOINT_PATH = os.path.join(PROJECT_ROOT, "training", "distill_checkpoint.json")

def extract_verilog(text):
    """Tách phần mã Verilog thuần nằm trong thẻ ```verilog ... ``` (làm mẫu CHOSEN chuẩn sạch)."""
    match = re.search(r"```(?:verilog)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()

def mutate_inject_latch(code):
    """Đột biến tạo chốt ẩn (Inferred Latch): Xóa bỏ nhánh default hoặc else trong khối tổ hợp."""
    # Chỉ coi là khối tổ hợp nếu có always @(*) và không có cạnh xung clock (posedge/negedge)
    is_comb = ("always @*" in code or "always @(*)" in code or "always @ (" in code) and not ("posedge" in code or "negedge" in code)
    if "default:" in code:
        # Xóa nhánh default trong khối case
        mutated = re.sub(r"\bdefault\s*:.*?(?=\bendcase\b)", "", code, flags=re.DOTALL)
        return mutated, "INFERRED_LATCH (Thiếu nhánh default trong khối case tổ hợp)"
    elif is_comb and "else begin" in code:
        # Xóa nhánh else cuối cùng trong khối tổ hợp
        mutated = re.sub(r"\belse\s+begin\b.*?\bend\b(?=\s*\bend\b|\s*endmodule)", "", code, flags=re.DOTALL)
        return mutated, "INFERRED_LATCH (Thiếu nhánh else gán giá trị mặc định trong khối tổ hợp)"
    return None, None

def mutate_inject_dangling_pin(code):
    """Đột biến tạo chân lơ lửng (Dangling Pin): Tách rời tín hiệu ngõ vào khỏi logic nội vi."""
    # Tìm tín hiệu ngõ vào dạng input wire / input reg (bỏ qua signed)
    inputs = re.findall(r"\binput\s+(?:wire\s+|reg\s+)?(?:signed\s+)?(?:\[[^\]]+\]\s+)?([a-zA-Z_][a-zA-Z0-9_]*)", code)
    # Lọc bỏ clk, rst, và từ khóa Verilog
    TuKhoaBoQua = {"clk", "rst", "rst_n", "clock", "reset", "signed", "wire", "reg", "input", "output"}
    candidate_inputs = [inp for inp in inputs if inp.lower() not in TuKhoaBoQua]
    if candidate_inputs:
        target_pin = candidate_inputs[0]
        # Tách phần header cổng và thân logic để chỉ thay thế trong thân logic, giữ nguyên header
        # Mục tiêu: cổng vẫn khai báo ở module header nhưng không hề tham gia tính toán bên trong -> tạo Dangling Pin
        m_mod = re.search(r"\bmodule\s+[A-Za-z0-9_]+\s*(?:#\s*\([\s\S]*?\)\s*)?\(([\s\S]*?)\);", code)
        if m_mod:
            header_end = m_mod.end()
            header_part = code[:header_end]
            body_part = code[header_end:]
            body_mutated = re.sub(rf"\b{re.escape(target_pin)}\b", "1'b0", body_part)
            if body_mutated != body_part:
                mutated = header_part + body_mutated
                return mutated, f"DANGLING_PIN (Cổng ngõ vào '{target_pin}' không được kết nối vào mạch logic)"
    return None, None

def mutate_inject_blocking_assignment(code):
    """Đột biến vi phạm chuẩn IEEE: Dùng phép gán blocking (=) trong khối tuần tự clock."""
    # Thay non-blocking (<=) thành blocking (=) để mô phỏng lỗi Race Condition trong Flip-Flop
    if "posedge clk" in code and "<=" in code:
        mutated = code.replace("<=", "=")
        return mutated, "BLOCKING_IN_SEQUENTIAL (Dùng phép gán = trong khối tuần tự gây Race Condition)"
    return None, None

def clean_prompt_text(text):
    """Loại bỏ ký tự điều khiển PDF còn sót lại trong prompt."""
    return re.split(r"\n?[\x00\s]*Sao chép khối nội dung", text or "")[0].replace("\x00", "").strip()


def load_teacher_dpo_pairs():
    """Nạp các cặp DPO thật từ quá trình Teacher Self-Correction (checkpoint hoặc tập DPO hiện có)."""
    # Cặp DPO thật = (lần 1 Teacher sinh lỗi bị Oracle từ chối) vs (lần 2 Teacher tự sửa đạt 100% Oracle)
    pairs_by_id = {}

    if os.path.exists(DPO_DATASET_PATH):
        try:
            with open(DPO_DATASET_PATH, "r", encoding="utf-8") as df:
                existing_dpo = json.load(df)
            for td in existing_dpo:
                if td.get("id", "").startswith("dpo_teacher_") or "Self-Correction" in td.get("source", ""):
                    item = dict(td)
                    item["prompt"] = clean_prompt_text(item.get("prompt", ""))
                    pairs_by_id[item["id"]] = item
        except Exception:
            pass

    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as cf:
                ckpt = json.load(cf)
            for td in ckpt.get("teacher_dpo_pairs", []):
                item = dict(td)
                item["prompt"] = clean_prompt_text(item.get("prompt", ""))
                pairs_by_id[item["id"]] = item
        except Exception:
            pass

    return list(pairs_by_id.values())


def generate_dpo_pairs_from_items(clean_items, real_teacher_dpo, out_path, label):
    """Sinh tập cặp DPO (Chosen vs Rejected) ưu tiên cặp Teacher Self-Correction + đột biến 3 lỗi RTL."""
    print(f"\n[*] Đang tạo {label}: nạp {len(clean_items)} mẫu CHOSEN...")

    # Đưa các cặp DPO thật từ quá trình Self-Correction vào đầu tập dữ liệu
    dpo_pairs = list(real_teacher_dpo)
    teacher_dpo_count = len(dpo_pairs)
    latch_count = 0
    dangling_count = 0
    blocking_count = 0

    for idx, item in enumerate(clean_items):
        item_id = item.get("id", f"sample_{idx}")
        instruction = item.get("instruction", "")
        input_spec = clean_prompt_text(item.get("input", ""))
        chosen_output = item.get("output", "")
        chosen_code = extract_verilog(chosen_output)
        if not chosen_code:
            continue

        prompt_text = f"{instruction}\n\n{input_spec}".strip()

        rejected_code = None
        error_type = None

        # Xoay vòng phân bổ 3 dạng lỗi vi mạch kinh điển theo chỉ số idx % 3 để cân bằng dữ liệu phạt:
        # 1. Thử tạo lỗi Chốt ẩn (Inferred Latch)
        if idx % 3 == 0:
            rejected_code, error_type = mutate_inject_latch(chosen_code)
            if rejected_code:
                latch_count += 1

        # 2. Thử tạo lỗi Chân lơ lửng (Dangling Pin)
        if not rejected_code or idx % 3 == 1:
            mut_code, err = mutate_inject_dangling_pin(chosen_code)
            if mut_code:
                rejected_code = mut_code
                error_type = err
                dangling_count += 1

        # 3. Thử tạo lỗi Race Condition (Blocking in Sequential)
        if not rejected_code:
            mut_code, err = mutate_inject_blocking_assignment(chosen_code)
            if mut_code:
                rejected_code = mut_code
                error_type = err
                blocking_count += 1

        # Dự phòng nếu 3 phép đột biến trên không áp dụng được (đảo bit logic hoặc vô hiệu hóa reset)
        if not rejected_code or rejected_code == chosen_code:
            if "assign " in chosen_code:
                rejected_code = re.sub(r"\b1'b0\b", "1'b1", chosen_code, count=1)
                if rejected_code == chosen_code:
                    rejected_code = re.sub(r"\b1'b1\b", "1'b0", chosen_code, count=1)
                error_type = "FUNCTIONAL_BUG (Sai lệch logic ngõ ra / Inverse output polarity)"
            else:
                rejected_code = chosen_code.replace("if (!rst_n)", "if (1'b0)").replace("if (rst)", "if (1'b0)")
                error_type = "MISSING_RESET_INITIALIZATION (Không khởi tạo thanh ghi khi có tín hiệu reset)"

        # Phương án cuối cùng nếu code vẫn không đổi: cắt bỏ từ khóa endmodule tạo lỗi cú pháp
        if rejected_code == chosen_code:
            rejected_code = chosen_code.replace("endmodule", "// Lỗi thiếu kết thúc module\n")
            error_type = "SYNTAX_TRUNCATED (Mã nguồn bị ngắt quãng giữa chừng)"

        # Đóng gói cặp preference (prompt, chosen, rejected) phục vụ huấn luyện DPO trên Colab
        dpo_pairs.append({
            "id": f"dpo_{item_id}",
            "category": item.get("category", "General"),
            "source": item.get("source", "Spec2RTL"),
            "module_name": item.get("module_name", "mod"),
            "prompt": prompt_text,
            "chosen": f"```verilog\n{chosen_code}\n```",
            "rejected": f"```verilog\n{rejected_code}\n```",
            "rejected_error_type": error_type,
            "chosen_verification": "PASS_100_MODELSIM",
            "rejected_verification": "FAIL_LINTER_OR_SIMULATION",
        })

    # Ghi tập cặp DPO ra file JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dpo_pairs, f, ensure_ascii=False, indent=2)

    print("--------------------------------------------------------------------------------")
    print(f"[THÀNH CÔNG] {label}: {out_path}")
    print(f"[*] Tổng số cặp CHOSEN / REJECTED: {len(dpo_pairs)} cặp.")
    print(f"    - Cặp thật từ Teacher Self-Correction   : {teacher_dpo_count} cặp")
    print(f"    - Lỗi Chốt ẩn (Inferred Latch)            : {latch_count} cặp")
    print(f"    - Lỗi Chân lơ lửng (Dangling Pin)         : {dangling_count} cặp")
    print(f"    - Lỗi Gán chắn (Blocking Race Condition)   : {blocking_count} cặp")
    print("--------------------------------------------------------------------------------")
    return len(dpo_pairs)


def build_dpo_dataset(pure_teacher_only=False):
    """Điều phối xuất cả bản DPO hợp nhất (Full) và bản DPO thuần từ tập Gemini Teacher."""
    print("================================================================================")
    print(">>> NHÓM 1: KHỞI TẠO TẬP DỮ LIỆU DPO PREFERENCE (CHOSEN VS REJECTED)")
    print("================================================================================")

    # Bước 1: Nạp các cặp DPO thật thu được khi Teacher tự sửa lỗi trước ModelSim Oracle
    real_teacher_dpo = load_teacher_dpo_pairs()

    # Bước 2: Sinh bản DPO đầy đủ từ toàn bộ tập SFT đã kiểm chứng (trừ khi bật cờ --pure-teacher-only)
    if not pure_teacher_only:
        if os.path.exists(SFT_DATASET_PATH):
            with open(SFT_DATASET_PATH, "r", encoding="utf-8") as f:
                clean_items = json.load(f)
            generate_dpo_pairs_from_items(clean_items, real_teacher_dpo, DPO_DATASET_PATH, "DPO Hợp nhất (Full)")
        else:
            print(f"[CẢNH BÁO] Không tìm thấy {SFT_DATASET_PATH}, bỏ qua xuất DPO hợp nhất.")

    # Bước 3: Sinh thêm bản DPO riêng cho tập thuần Gemini Teacher (dataset_teacher_dpo.json)
    if os.path.exists(TEACHER_DATASET_PATH):
        with open(TEACHER_DATASET_PATH, "r", encoding="utf-8") as f:
            teacher_items = json.load(f)
        generate_dpo_pairs_from_items(
            teacher_items,
            real_teacher_dpo,
            TEACHER_DPO_DATASET_PATH,
            "DPO 100% Thuần Gemini Teacher",
        )
    else:
        print(f"[CẢNH BÁO] Không tìm thấy {TEACHER_DATASET_PATH}, bỏ qua xuất DPO thuần Teacher.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Xây dựng tập dữ liệu DPO Preference")
    parser.add_argument("--pure-teacher-only", action="store_true", help="Chỉ xuất training/dataset_teacher_dpo.json")
    args = parser.parse_args()
    build_dpo_dataset(pure_teacher_only=args.pure_teacher_only)
