"""
Module: run_inference.py
Mô tả: Chương trình nạp mô hình Qwen2.5-Coder-3B cùng với LoRA DPO Adapter
để sinh mã nguồn Verilog synthesizable từ đặc tả ngôn ngữ tự nhiên.
Chạy hoàn toàn cục bộ (Local Offline Inference).
"""

import os
import sys
import argparse

def generate_verilog(spec_text, model_dir="models/qwen2.5_3b_verilog_dpo", device="auto"):
    """
    Nạp mô hình nền Qwen2.5-Coder-3B kết hợp LoRA Adapter đã huấn luyện DPO.
    """
    print("=" * 80)
    print("   KHỞI ĐỘNG SUY LUẬN MÔ HÌNH SPEC2RTL QWEN2.5-3B DPO")
    print("=" * 80)
    print(f"[*] Thư mục LoRA Adapter: {model_dir}")

    # 1. Kiểm tra Domain Guard (Chặn các câu hỏi không liên quan, văn bản rác, hoặc mạch Analog)
    ThuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ThuMucAgent = os.path.join(ThuMucGoc, "agent")
    if ThuMucAgent not in sys.path:
        sys.path.insert(0, ThuMucAgent)
    try:
        from spec_analyzer import SpecAnalyzer
        bo_phan_tich = SpecAnalyzer(spec_text)
        is_unsup, cat_code, reason = bo_phan_tich.check_unsupported_domain()
        if is_unsup:
            print("\n" + "=" * 80)
            print(f"   [DOMAIN GUARD]: TỪ CHỐI XỬ LÝ ({cat_code})")
            print("=" * 80)
            print(f"[*] Lý do kỹ thuật: {reason}")
            print("=" * 80)
            return None
    except Exception as e:
        pass

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except (ImportError, OSError, Exception) as e:
        print(f"[!] Không thể nạp PyTorch / Transformers ({e}).")
        print("    Tự động chuyển tiếp (Fallback) sang bộ sinh RTL phần cứng tích hợp: agent/rtl_generator.py...")
        try:
            ThuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ThuMucAgent = os.path.join(ThuMucGoc, "agent")
            if ThuMucAgent not in sys.path:
                sys.path.insert(0, ThuMucAgent)
            from rtl_generator import RTLGenerator
            
            generator = RTLGenerator()
            _, file_path = generator.generate_from_spec(spec_text)
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                response = f.read()
            print("\n" + "=" * 80)
            print("MÃ NGUỒN VERILOG ĐƯỢC SINH BỞI FALLBACK EXPERT RTL GENERATOR:")
            print("=" * 80)
            print(response)
            print("=" * 80)
            return response
        except Exception as fallback_err:
            print(f"[!] Fallback thất bại: {fallback_err}")
            return None

    base_model_name = "Qwen/Qwen2.5-Coder-3B-Instruct"
    print(f"[*] Đang nạp Tokenizer & Mô hình nền: {base_model_name}...")

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    
    # Xác định device
    if device == "auto":
        actual_device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        actual_device = device

    print(f"[*] Thiết bị suy luận (Compute Device): {actual_device}")

    # Nạp mô hình nền
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16 if actual_device == "cuda" else torch.float32,
        device_map=actual_device if actual_device == "cuda" else None,
        low_cpu_mem_usage=True
    )

    # Nạp chồng trọng số LoRA DPO đã huấn luyện
    print(f"[*] Đang nạp chồng trọng số LoRA Adapter từ {model_dir}...")
    model = PeftModel.from_pretrained(base_model, model_dir)
    model.eval()

    system_prompt = (
        "Bạn là chuyên gia thiết kế vi mạch kỹ thuật số (Hardware Digital IC Architect). "
        "Hãy chuyển đổi đặc tả yêu cầu thành mã Verilog synthesizable chuẩn IEEE 1364-2001. "
        "Tuyệt đối không để chốt ẩn (inferred latches), không để chân lơ lửng (dangling pins) "
        "và luôn sử dụng phép gán non-blocking (<=) cho logic tuần tự."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": spec_text}
    ]

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt").to(actual_device)

    print("[*] Đang sinh mã nguồn Verilog...")
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.2,
            top_p=0.9,
            do_sample=True
        )

    response = tokenizer.decode(generated_ids[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    print("\n" + "=" * 80)
    print("MÃ NGUỒN VERILOG ĐƯỢC SINH BỞI QWEN2.5-3B DPO:")
    print("=" * 80)
    print(response)
    print("=" * 80)
    return response

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy suy luận mô hình Spec2RTL Qwen2.5-3B LoRA DPO")
    parser.add_argument("--spec", type=str, default="Thiết kế bộ đếm BCD 0-59 có tín hiệu enable và reset tích cực cao.", help="Văn bản đặc tả vi mạch")
    parser.add_argument("--model_dir", type=str, default="models/qwen2.5_3b_verilog_dpo", help="Đường dẫn thư mục LoRA adapter")
    args = parser.parse_args()

    generate_verilog(args.spec, args.model_dir)
