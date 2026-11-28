"""
Module: run_inference.py
Mô tả: Chương trình nạp mô hình Spec2RTL (ưu tiên GGUF nhẹ RAM cho máy 4GB RAM,
hoặc Qwen2.5-Coder LoRA DPO Adapter) để sinh mã nguồn Verilog synthesizable từ
đặc tả ngôn ngữ tự nhiên. Chạy hoàn toàn cục bộ (Local Offline Inference).

Vai trò trong luồng Spec2RTL (Fig. 3):
  - Đứng ở giai đoạn RTL Generation (Sinh mã phần cứng) sau Analysis & Knowledge Retrieval.
  - Kết nối Domain Guard (`SpecAnalyzer`) + RAG Context (`KnowledgeMatcher`) vào chuỗi suy luận
    theo thứ tự ưu tiên 3 tầng: GGUF cục bộ -> PyTorch LoRA DPO -> Fallback RTLGenerator.
"""

import os
import sys
import argparse
import tempfile


def _fallback_rtl_generator(spec_text):
    """
    Tầng dự phòng (Ưu tiên 3): Gọi bộ sinh RTL phần cứng tích hợp khi không có model GGUF/PyTorch.

    Input:
        spec_text (str): Văn bản đặc tả phần cứng (ngôn ngữ tự nhiên hoặc đường dẫn file spec).
    Output:
        str | None: Mã nguồn Verilog synthesizable được sinh từ `agent/rtl_generator.py`,
                    hoặc None nếu quá trình fallback gặp lỗi.
    """
    print("    Tự động chuyển tiếp (Fallback) sang bộ sinh RTL phần cứng tích hợp: agent/rtl_generator.py...")
    try:
        from rtl_generator import RTLGenerator
        # Dùng thư mục tạm để không làm rác thư mục làm việc chính trong chế độ inference đơn lẻ
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = RTLGenerator(src_dir=tmpdir)
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


def generate_verilog(spec_text, model_dir="models/qwen2.5_3b_verilog_dpo", device="auto", use_rag=True):
    """
    Sinh mã Verilog synthesizable từ đặc tả sau khi qua lớp bảo vệ Domain Guard và Hybrid RAG.

    Chuỗi ưu tiên suy luận (Fallback Chain):
        1. Model lượng tử hóa GGUF cục bộ qua `llama_cpp` (nhẹ RAM <700MB, phù hợp máy 4GB RAM).
        2. PyTorch + PEFT LoRA DPO Adapter trên nền `Qwen/Qwen2.5-Coder-3B-Instruct`.
        3. Bộ sinh RTL phần cứng tích hợp `_fallback_rtl_generator` (`agent/rtl_generator.py`).

    Input:
        spec_text (str): Đặc tả yêu cầu thiết kế vi mạch.
        model_dir (str): Đường dẫn tới thư mục chứa trọng số LoRA Adapter.
        device (str): Thiết bị tính toán ('auto', 'cuda', hoặc 'cpu').
        use_rag (bool): Bật/tắt bước chèn Top-2 thiết kế tham khảo từ Hybrid RAG vào prompt.
    Output:
        str | None: Chuỗi mã Verilog sinh ra, hoặc None nếu bị Domain Guard từ chối / lỗi hoàn toàn.
    """
    print("=" * 80)
    print("   KHỞI ĐỘNG SUY LUẬN MÔ HÌNH SPEC2RTL OFFLINE")
    print("=" * 80)
    print(f"[*] Thư mục LoRA Adapter: {model_dir}")

    # Bổ sung thư mục agent/ vào sys.path để import SpecAnalyzer, KnowledgeMatcher và RTLGenerator
    ThuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ThuMucAgent = os.path.join(ThuMucGoc, "agent")
    if ThuMucAgent not in sys.path:
        sys.path.insert(0, ThuMucAgent)

    # Bước 1: Kiểm tra Domain Guard (Chặn các câu hỏi không liên quan, văn bản rác, hoặc mạch Analog/PHY)
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
    except Exception:
        pass

    # Bước 1.5: Truy xuất ngữ cảnh Hybrid RAG từ kho tri thức (nếu bật use_rag) để giảm lỗi cú pháp/cổng
    rag_context = ""
    if use_rag:
        try:
            from knowledge_matcher import KnowledgeMatcher
            rag_context = KnowledgeMatcher().format_rag_context(spec_text, top_k=2) or ""
            if rag_context.strip():
                print(f"[*] Đã nạp ngữ cảnh RAG từ kho tri thức ({len(rag_context)} ký tự).")
        except Exception as rag_err:
            print(f"[!] Không thể truy xuất RAG ({rag_err}) -> tiếp tục không có RAG.")
            rag_context = ""

    # Ghép đặc tả gốc với mẫu tham khảo RAG (nếu có) thành thông điệp người dùng cho LLM
    user_message = spec_text
    if rag_context and rag_context.strip():
        user_message = (
            f"{spec_text}\n\n"
            f"### Thiết kế tham khảo từ kho tri thức (RAG):\n"
            f"{rag_context.strip()}"
        )

    system_prompt = (
        "Bạn là chuyên gia thiết kế vi mạch kỹ thuật số (Hardware Digital IC Architect). "
        "Hãy chuyển đổi đặc tả yêu cầu thành mã Verilog synthesizable chuẩn IEEE 1364-2001. "
        "Tuyệt đối không để chốt ẩn (inferred latches), không để chân lơ lửng (dangling pins) "
        "và luôn sử dụng phép gán non-blocking (<=) cho logic tuần tự."
    )

    # Bước 2 (Ưu tiên 1): Chạy bản lượng tử GGUF nhẹ RAM (<700MB cho máy 4GB RAM) nếu tìm thấy file .gguf
    gguf_candidates = []
    models_root = os.path.join(ThuMucGoc, "models")
    if os.path.isdir(models_root):
        for dp, _, fns in os.walk(models_root):
            for fn in sorted(fns):
                if fn.lower().endswith(".gguf"):
                    gguf_candidates.append(os.path.join(dp, fn))

    if gguf_candidates:
        try:
            from llama_cpp import Llama
            gguf_path = gguf_candidates[0]
            print(f"[*] Phát hiện model GGUF nhẹ RAM: {gguf_path}")
            # Giới hạn ngữ cảnh 2048 token và dùng nửa số nhân CPU để giữ máy chạy mượt
            llm = Llama(
                model_path=gguf_path,
                n_ctx=2048,
                n_threads=max(2, (os.cpu_count() or 4) // 2),
                verbose=False,
            )
            # Định dạng prompt theo chuẩn ChatML của Qwen2.5
            chat_prompt = (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n{user_message}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            out = llm(chat_prompt, max_tokens=1024, temperature=0.2, top_p=0.9, stop=["<|im_end|>"])
            response = out["choices"][0]["text"].strip()
            print("\n" + "=" * 80)
            print("MÃ NGUỒN VERILOG ĐƯỢC SINH BỞI MODEL GGUF OFFLINE:")
            print("=" * 80)
            print(response)
            print("=" * 80)
            return response
        except ImportError:
            print("[!] Tìm thấy file .gguf nhưng chưa cài `llama-cpp-python` -> thử PyTorch/Fallback...")
        except Exception as gguf_err:
            print(f"[!] Lỗi nạp GGUF ({gguf_err}) -> thử PyTorch/Fallback...")

    # Bước 3 (Ưu tiên 2): Thử PyTorch + PEFT LoRA; fallback sang RTLGenerator nếu thiếu thư viện/adapter
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except (ImportError, OSError, Exception) as e:
        print(f"[!] Không thể nạp PyTorch / Transformers ({e}).")
        return _fallback_rtl_generator(spec_text)

    if not os.path.isdir(model_dir):
        resolved_model_dir = os.path.join(ThuMucGoc, model_dir)
        if os.path.isdir(resolved_model_dir):
            model_dir = resolved_model_dir
        else:
            print(f"[!] Không tìm thấy thư mục LoRA Adapter '{model_dir}'.")
            return _fallback_rtl_generator(spec_text)

    base_model_name = "Qwen/Qwen2.5-Coder-3B-Instruct"
    print(f"[*] Đang nạp Tokenizer & Mô hình nền: {base_model_name}...")

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        actual_device = ("cuda" if torch.cuda.is_available() else "cpu") if device == "auto" else device
        print(f"[*] Thiết bị suy luận (Compute Device): {actual_device}")

        # Nạp mô hình nền theo độ chính xác phù hợp GPU (fp16) hoặc CPU (fp32)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16 if actual_device == "cuda" else torch.float32,
            device_map=actual_device if actual_device == "cuda" else None,
            low_cpu_mem_usage=True,
        )

        # Gắn trọng số LoRA DPO đã huấn luyện chồng lên mô hình nền
        print(f"[*] Đang nạp chồng trọng số LoRA Adapter từ {model_dir}...")
        model = PeftModel.from_pretrained(base_model, model_dir)
        model.eval()
    except Exception as model_err:
        print(f"[!] Lỗi nạp mô hình PyTorch/LoRA ({model_err}).")
        return _fallback_rtl_generator(spec_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Tạo prompt chat và sinh chuỗi token Verilog mới với nhiệt độ thấp (0.2) để ổn định cú pháp
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt").to(actual_device)

    print("[*] Đang sinh mã nguồn Verilog...")
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.2,
            top_p=0.9,
            do_sample=True,
        )

    # Cắt bỏ phần prompt đầu vào để chỉ giữ lại mã Verilog do mô hình sinh ra
    response = tokenizer.decode(generated_ids[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    print("\n" + "=" * 80)
    print("MÃ NGUỒN VERILOG ĐƯỢC SINH BỞI QWEN2.5 DPO:")
    print("=" * 80)
    print(response)
    print("=" * 80)
    return response


if __name__ == "__main__":
    # Giao diện dòng lệnh cho phép thử nhanh suy luận offline với tùy chọn tắt/bật RAG
    parser = argparse.ArgumentParser(description="Chạy suy luận mô hình Spec2RTL LoRA/GGUF")
    parser.add_argument("--spec", type=str, default="Thiết kế bộ đếm BCD 0-59 có tín hiệu enable và reset tích cực cao.", help="Văn bản đặc tả vi mạch")
    parser.add_argument("--model_dir", type=str, default="models/qwen2.5_3b_verilog_dpo", help="Đường dẫn thư mục LoRA adapter")
    parser.add_argument("--no-rag", action="store_true", help="Tắt truy xuất ngữ cảnh RAG từ kho tri thức")
    args = parser.parse_args()

    generate_verilog(args.spec, args.model_dir, use_rag=not args.no_rag)
