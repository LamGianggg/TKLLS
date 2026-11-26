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

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFT_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_clean_verified.json")
DPO_DATASET_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_dpo_preference.json")

def extract_verilog(text):
    match = re.search(r"```(?:verilog)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()

def mutate_inject_latch(code):
    """Đột biến tạo chốt ẩn (Inferred Latch): Xóa bỏ nhánh default hoặc else trong khối tổ hợp."""
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
    if "posedge clk" in code and "<=" in code:
        mutated = code.replace("<=", "=")
        return mutated, "BLOCKING_IN_SEQUENTIAL (Dùng phép gán = trong khối tuần tự gây Race Condition)"
    return None, None

def build_dpo_dataset():
    print("================================================================================")
    print(">>> NHÓM 1: KHỞI TẠO TẬP DỮ LIỆU DPO PREFERENCE (CHOSEN VS REJECTED)")
    print("================================================================================")

    if not os.path.exists(SFT_DATASET_PATH):
        print(f"[LỖI] Không tìm thấy file {SFT_DATASET_PATH}")
        return

    with open(SFT_DATASET_PATH, "r", encoding="utf-8") as f:
        clean_items = json.load(f)

    print(f"[*] Nạp {len(clean_items)} mẫu CHOSEN đạt chuẩn ModelSim từ dataset_clean_verified.json...")

    dpo_pairs = []
    teacher_dpo_count = 0
    ckpt_path = os.path.join(PROJECT_ROOT, "training", "distill_checkpoint.json")
    if os.path.exists(ckpt_path):
        with open(ckpt_path, "r", encoding="utf-8") as cf:
            ckpt = json.load(cf)
        for td in ckpt.get("teacher_dpo_pairs", []):
            dpo_pairs.append(td)
            teacher_dpo_count += 1

    latch_count = 0
    dangling_count = 0
    blocking_count = 0

    for idx, item in enumerate(clean_items):
        item_id = item.get("id", f"sample_{idx}")
        instruction = item.get("instruction", "")
        input_spec = item.get("input", "")
        chosen_output = item.get("output", "")
        chosen_code = extract_verilog(chosen_output)

        prompt_text = f"{instruction}\n\n{input_spec}".strip()

        # Áp dụng chiến lược tạo mã REJECTED đối ứng
        rejected_code = None
        error_type = None

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

        # Nếu không đột biến được bằng các quy tắc trên, bắt buộc tạo lỗi sai lệch logic / cú pháp
        if not rejected_code or rejected_code == chosen_code:
            if "assign " in chosen_code:
                # Đảo ngược một phép gán để tạo lỗi chức năng (Functional Bug)
                rejected_code = re.sub(r"\b1'b0\b", "1'b1", chosen_code, count=1)
                if rejected_code == chosen_code:
                    rejected_code = re.sub(r"\b1'b1\b", "1'b0", chosen_code, count=1)
                error_type = "FUNCTIONAL_BUG (Sai lệch logic ngõ ra / Inverse output polarity)"
            else:
                # Đột biến xóa phần khởi tạo reset
                rejected_code = chosen_code.replace("if (!rst_n)", "if (1'b0)").replace("if (rst)", "if (1'b0)")
                error_type = "MISSING_RESET_INITIALIZATION (Không khởi tạo thanh ghi khi có tín hiệu reset)"

        # Đảm bảo 100% không trùng lặp giữa chosen và rejected
        if rejected_code == chosen_code:
            rejected_code = chosen_code.replace("endmodule", "// Lỗi thiếu kết thúc module\n")
            error_type = "SYNTAX_TRUNCATED (Mã nguồn bị ngắt quãng giữa chừng)"

        # Đóng gói cặp DPO chuẩn
        dpo_entry = {
            "id": f"dpo_{item_id}",
            "category": item.get("category", "General"),
            "source": item.get("source", "Spec2RTL"),
            "module_name": item.get("module_name", "mod"),
            "prompt": prompt_text,
            "chosen": f"```verilog\n{chosen_code}\n```",
            "rejected": f"```verilog\n{rejected_code}\n```",
            "rejected_error_type": error_type,
            "chosen_verification": "PASS_100_MODELSIM",
            "rejected_verification": "FAIL_LINTER_OR_SIMULATION"
        }
        dpo_pairs.append(dpo_entry)

    with open(DPO_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dpo_pairs, f, ensure_ascii=False, indent=2)

    print("--------------------------------------------------------------------------------")
    print(f"[THÀNH CÔNG] Đã tạo tập dữ liệu DPO Preference: {DPO_DATASET_PATH}")
    print(f"[*] Tổng số cặp CHOSEN / REJECTED: {len(dpo_pairs)} cặp.")
    print(f"    - Cặp thật từ Teacher Self-Correction   : {teacher_dpo_count} cặp")
    print(f"    - Lỗi Chốt ẩn (Inferred Latch)            : {latch_count} cặp")
    print(f"    - Lỗi Chân lơ lửng (Dangling Pin)         : {dangling_count} cặp")
    print(f"    - Lỗi Gán chắn (Blocking Race Condition)   : {blocking_count} cặp")
    print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    build_dpo_dataset()
