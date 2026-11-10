"""
Module: run_spec2rtl.py
Description: Master CLI Orchestrator for Spec2RTL & Prompt2Silicon Framework.
Complete End-to-End Pipeline:
  1. Natural Language Spec Ingestion (specs/*.md)
  2. Synthesizable Verilog RTL Auto-Generation (src/*.v)
  3. Automated Self-Checking Testbench Generation (sim/*.v)
  4. Industrial EDA Simulation & Verification (ModelSim batch flow)
  5. Quartus Symbol (.bsf) & Schematic (.bdf) Auto-Generation
  6. Quartus II Project (.qpf/.qsf) Synthesis for RTL Viewer
"""

import os
import sys
import time
import argparse
import subprocess

# Force UTF-8 output on Windows consoles to prevent charmap crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from spec_analyzer import SpecAnalyzer
from rtl_generator import RTLGenerator
from tb_generator import TBGenerator
from bdf_generator import BDFGenerator
from simulator import EDASimulator
from reflection_loop import ReflectionAgent
from eda_finder import find_quartus_map

def setup_quartus_and_bdf(q_dir, project_name, top_entity, primary_rtl, all_rtl_files):
    """Auto-generates Quartus project, BSF symbol, and BDF schematic diagram."""
    os.makedirs(q_dir, exist_ok=True)
    qmap_exe = find_quartus_map()

    qpf_path = os.path.join(q_dir, f"{project_name}.qpf")
    qsf_path = os.path.join(q_dir, f"{project_name}.qsf")
    bsf_path = os.path.join(q_dir, f"{top_entity}.bsf")
    bdf_path = os.path.join(q_dir, f"{top_entity}.bdf")

    # 1. Write Initial QPF & QSF
    with open(qpf_path, "w", encoding="utf-8") as f:
        f.write(f'PROJECT_REVISION = "{project_name}"\n')

    qsf_lines = [
        'set_global_assignment -name FAMILY "Cyclone II"',
        'set_global_assignment -name DEVICE EP2C35F672C6',
        f'set_global_assignment -name TOP_LEVEL_ENTITY {top_entity}',
        'set_global_assignment -name ORIGINAL_QUARTUS_VERSION "13.0 SP1"',
        'set_global_assignment -name LAST_QUARTUS_VERSION "13.0 SP1"',
    ]
    for vf in all_rtl_files:
        if not os.path.basename(vf).startswith("tb_"):
            rel_vf = os.path.relpath(vf, q_dir).replace('\\', '/')
            qsf_lines.append(f'set_global_assignment -name VERILOG_FILE {rel_vf}')

    with open(qsf_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(qsf_lines) + '\n')

    # 2. Generate BSF Symbol using quartus_map --generate_symbol
    if qmap_exe and os.path.exists(qmap_exe) and os.path.exists(primary_rtl):
        subprocess.run([qmap_exe, project_name, f"--generate_symbol={primary_rtl}"], cwd=q_dir, capture_output=True)

    # 3. Generate BDF Diagram from BSF
    bdf_created = False
    if os.path.exists(bsf_path):
        bdf_gen = BDFGenerator()
        bdf_gen.generate_bdf_from_bsf(bsf_path, bdf_path)
        bdf_created = True

    # 4. Final Analysis & Synthesis
    if qmap_exe and os.path.exists(qmap_exe):
        subprocess.run([qmap_exe, project_name, "-c", project_name], cwd=q_dir, capture_output=True)
    elif not qmap_exe:
        print(f" -> [Lưu ý EDA]: Không tìm thấy quartus_map.exe trên máy. Project {project_name}.qpf đã được tạo để bạn mở trực tiếp trong Quartus II GUI.")

    return qpf_path, bsf_path, bdf_path if bdf_created else None

def run_single_spec(spec_path, base_dir):
    """Executes the full Spec2RTL pipeline for a single specification file."""
    src_dir = os.path.join(base_dir, "src")
    sim_dir = os.path.join(base_dir, "sim")
    q_dir   = os.path.join(base_dir, "quartus")

    print("\n" + "=" * 80)
    print(f"   [PROCESSING SPEC]: {os.path.basename(spec_path)}")
    print("=" * 80)

    # Step 1: Read Spec
    print(f"[Step 1] Ingesting and Parsing Specification...")
    with open(spec_path, "r", encoding="utf-8", errors="replace") as f:
        spec_text = f.read()
    print("-" * 80)
    print(spec_text.strip()[:350] + ("..." if len(spec_text) > 350 else ""))
    print("-" * 80)

    # Step 2: Auto-generate RTL and TB if missing
    print(f"[Step 2] Resolving and Generating Synthesizable Verilog & Testbench...")
    rtl_gen = RTLGenerator(src_dir)
    tb_gen  = TBGenerator(sim_dir)

    analyzer = SpecAnalyzer(spec_path)
    cat = analyzer.classify_system()
    mod_name = analyzer.extract_module_name()

    if cat == "SOC_AI":
        top_name = "tb_top_soc"
        top_entity = "top_soc"
        project_name = "Top_SoC"
        primary_rtl = os.path.join(src_dir, "top_soc.v")
        verilog_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith(".v") and not any(k in f for k in ["traffic", "vending", "elevator"]) and f != "top_soc.v"]
        verilog_files.insert(0, primary_rtl)
        rtl_files = [f for f in verilog_files]
        verilog_files.append(os.path.join(sim_dir, "tb_top_soc.v"))

    elif cat == "VENDING":
        top_name = "tb_vending_machine"
        top_entity = "vending_machine"
        project_name = "Vending_Machine"
        v_file = os.path.join(src_dir, "vending_machine.v")
        tb_file = os.path.join(sim_dir, "tb_vending_machine.v")
        if not os.path.exists(v_file):
            rtl_gen.generate_vending_machine(spec_text)
            print(" -> [Auto-Gen] Synthesized: src/vending_machine.v")
        if not os.path.exists(tb_file):
            tb_gen.generate_vending_tb()
            print(" -> [Auto-Gen] Synthesized: sim/tb_vending_machine.v")
        verilog_files = [v_file, tb_file]
        rtl_files = [v_file]
        primary_rtl = v_file

    elif cat == "ELEVATOR":
        top_name = "tb_elevator_controller"
        top_entity = "elevator_controller"
        project_name = "Elevator_Controller"
        v_file = os.path.join(src_dir, "elevator_controller.v")
        tb_file = os.path.join(sim_dir, "tb_elevator_controller.v")
        if not os.path.exists(v_file):
            rtl_gen.generate_elevator_controller(spec_text)
            print(" -> [Auto-Gen] Synthesized: src/elevator_controller.v")
        if not os.path.exists(tb_file):
            tb_gen.generate_elevator_tb()
            print(" -> [Auto-Gen] Synthesized: sim/tb_elevator_controller.v")
        verilog_files = [v_file, tb_file]
        rtl_files = [v_file]
        primary_rtl = v_file

    elif cat == "TRAFFIC":
        top_name = "tb_traffic_light"
        top_entity = "traffic_light"
        project_name = "Traffic_Light"
        v_file = os.path.join(src_dir, "traffic_light.v")
        tb_file = os.path.join(sim_dir, "tb_traffic_light.v")
        if not os.path.exists(v_file):
            rtl_gen.generate_traffic_light(spec_text)
            print(" -> [Auto-Gen] Synthesized: src/traffic_light.v")
        if not os.path.exists(tb_file):
            tb_gen.generate_traffic_tb()
            print(" -> [Auto-Gen] Synthesized: sim/tb_traffic_light.v")
        verilog_files = [v_file, tb_file]
        rtl_files = [v_file]
        primary_rtl = v_file

    else:
        # AUTONOMOUS GENERAL SPEC2RTL SYNTHESIS FOR ANY CUSTOM / RANDOM SPEC
        top_entity = mod_name
        top_name = f"tb_{top_entity}"
        project_name = "".join(part.capitalize() for part in top_entity.split("_"))
        v_file = os.path.join(src_dir, f"{top_entity}.v")
        tb_file = os.path.join(sim_dir, f"{top_name}.v")

        # Synthesize RTL
        if not os.path.exists(v_file):
            _, v_file = rtl_gen.generate_from_spec(spec_text, spec_path)
            print(f" -> [Auto-Gen Dynamic RTL] Synthesized: src/{os.path.basename(v_file)}")

        # Synthesize Testbench
        if not os.path.exists(tb_file):
            _, tb_file = tb_gen.generate_tb_from_spec(spec_text, v_file, spec_path)
            print(f" -> [Auto-Gen Dynamic TB] Synthesized: sim/{os.path.basename(tb_file)}")

        verilog_files = [v_file, tb_file]
        rtl_files = [v_file]
        primary_rtl = v_file

    print(f" -> Active design files ({len(verilog_files)}):")
    for f in verilog_files:
        print(f"    * {os.path.basename(f)}")

    # Step 3: Simulation & Verification
    print(f"\n[Step 3] Invoking EDA Simulation Engine for Top: {top_name}...")
    sim = EDASimulator(sim_dir)
    reflector = ReflectionAgent(sim)

    start_t = time.time()
    result = sim.run_flow(verilog_files, top_module=top_name)
    elapsed = time.time() - start_t

    print("\n" + "-" * 80)
    print("   SIMULATION TRANSCRIPT OUTPUT")
    print("-" * 80)
    print(result.get("log", "").strip())
    print("-" * 80)

    # Step 4: Auto-generate BSF, BDF, and Quartus Project
    print(f"\n[Step 4] Auto-generating Schematic BSF, BDF & Quartus Project...")
    qpf_path, bsf_path, bdf_path = setup_quartus_and_bdf(q_dir, project_name, top_entity, primary_rtl, rtl_files)
    print(f" -> Quartus Project created: {qpf_path}")
    print(f" -> Symbol File (.bsf):      {bsf_path}")
    if bdf_path:
        print(f" -> Schematic Diagram (.bdf): {bdf_path}")

    # Step 5: Verification Judgment
    if result["success"]:
        print(f"\n>>> [SPEC2RTL STATUS: SUCCESS (100% PASS)] <<<")
        print(f"Execution Time: {elapsed:.2f} seconds")
        print(f"Simulation waveform dumped in: {sim_dir}")
        print("\n[Available Visual Inspection Formats]:")
        if bdf_path:
            print(f" 1. BDF Schematic: Open Quartus II -> {bdf_path}")
        print(f" 2. RTL Viewer:    Open Quartus II -> {qpf_path} -> Tools -> Netlist Viewers -> RTL Viewer")
        print(f" 3. Waveform:      Open ModelSim   -> {os.path.join(sim_dir, top_entity + '.vcd')}")
        return True, elapsed, top_entity, bdf_path
    else:
        print(f"\n>>> [SPEC2RTL STATUS: FAILED] <<<")
        diagnosis = reflector.diagnose_error(result)
        print(f"Failure Stage: {diagnosis['stage']}")
        print(f"Category: {diagnosis['category']}")
        print(f"Root Cause: {diagnosis['root_cause']}")
        print(f"Suggested Fix: {diagnosis['suggested_fix']}")
        return False, elapsed, top_entity, None

def get_spec_description(filename, specs_dir=None):
    """Returns friendly description for available specs."""
    full_path = os.path.join(specs_dir, filename) if specs_dir else filename
    if os.path.exists(full_path):
        try:
            return SpecAnalyzer(full_path).get_friendly_description()
        except Exception:
            pass
    fn = filename.lower()
    if "soc" in fn:
        return "Autonomous SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core)"
    elif "thang" in fn or "elevator" in fn:
        return "Bộ điều khiển Thang máy 5 tầng (5-Floor Intelligent Elevator FSM)"
    elif "traffic" in fn or "giao thong" in fn:
        return "Bộ điều khiển Đèn giao thông ngã tư (Intersection Traffic Light FSM)"
    elif "vend" in fn or "ban nuoc" in fn:
        return "Máy bán nước tự động 15.000đ (Vending Machine FSM)"
    return "Custom Hardware Specification"

def main():
    base_dir  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    specs_dir = os.path.join(base_dir, "specs")

    print("=" * 80)
    print("   Spec2RTL & Prompt2Silicon Autonomous Hardware Generation Pipeline")
    print("   Based on NVIDIA Research (arXiv:2506.13905) & ISCAS 2026 (arXiv:2601.13815)")
    print("=" * 80)

    available_specs = sorted([f for f in os.listdir(specs_dir) if f.endswith(".md") or f.endswith(".txt")])

    # Parse arguments: support both positional ('python run_spec2rtl.py 2') and flag ('--spec 2', '--all')
    parser = argparse.ArgumentParser(description="Spec2RTL & Prompt2Silicon Autonomous Pipeline")
    parser.add_argument("spec_pos", nargs="?", default=None, help="Name, number (1-4), or 'all' to run specs")
    parser.add_argument("--spec", dest="spec_flag", default=None, help="Name, number, or 'all'")
    parser.add_argument("--all", action="store_true", help="Run all available specifications sequentially")
    args = parser.parse_args()

    user_input = args.spec_flag or args.spec_pos

    run_all_mode = args.all or (user_input and user_input.lower() in ["all", "a"])

    if not user_input and not args.all:
        print("\n[DANH SÁCH CÁC BÀI TOÁN CÓ SẴN TRONG specs/]:")
        for idx, s in enumerate(available_specs):
            desc = get_spec_description(s, specs_dir)
            print(f"  [{idx+1}] {s:<22} -> {desc}")
        print(f"  [A] Chạy TẤT CẢ ({len(available_specs)} bài toán lần lượt)")

        # Interactive selection
        try:
            choice = input(f"\n👉 Vui lòng chọn bài toán muốn chạy [1-{len(available_specs)} hoặc A, mặc định: A]: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "A"

        if choice == "" or choice.lower() in ["a", "all"]:
            run_all_mode = True
        elif choice.isdigit():
            user_input = choice
        else:
            user_input = choice

    # Case 1: Run ALL specs
    if run_all_mode:
        print(f"\n>>> [CHẾ ĐỘ TỰ ĐỘNG]: TIẾN HÀNH CHẠY TẤT CẢ {len(available_specs)} BÀI TOÁN <<<\n")
        summary_results = []
        for s in available_specs:
            spec_file_path = os.path.join(specs_dir, s)
            success, elapsed, entity, bdf = run_single_spec(spec_file_path, base_dir)
            summary_results.append((s, entity, success, elapsed, bdf))

        print("\n" + "=" * 80)
        print("          BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ TỰ ĐỘNG TOÀN BỘ CÁC BÀI TOÁN")
        print("=" * 80)
        print(f"{'STT':<4} | {'Tên Spec':<24} | {'Module Entity':<22} | {'Trạng Thái':<12} | {'Thời Gian':<10}")
        print("-" * 80)
        for i, (spec_n, ent, succ, elap, bdf) in enumerate(summary_results):
            status_str = "100% PASS" if succ else "FAILED"
            print(f"[{i+1}]  | {spec_n:<24} | {ent:<22} | {status_str:<12} | {elap:.2f}s")
        print("=" * 80)
        print("\n[Tất cả các sơ đồ BDF và Project Quartus đều đã sẵn sàng trong thư mục quartus/!]")
        sys.exit(0)

    # Case 2: Run a SPECIFIC spec
    spec_target = user_input
    if spec_target.isdigit():
        idx = int(spec_target) - 1
        if 0 <= idx < len(available_specs):
            spec_target = available_specs[idx]
        else:
            print(f"[ERROR] Chỉ số không hợp lệ. Vui lòng chọn từ 1 đến {len(available_specs)}.")
            sys.exit(1)

    matched = None
    for s in available_specs:
        if s.lower() == spec_target.lower() or spec_target.lower() in s.lower():
            matched = s
            break

    if matched:
        target_path = os.path.join(specs_dir, matched)
    elif os.path.exists(spec_target):
        target_path = os.path.abspath(spec_target)
    else:
        target_path = os.path.join(specs_dir, spec_target)

    if not os.path.exists(target_path):
        print(f"[ERROR] Specification file not found: {target_path}")
        sys.exit(1)

    success, elapsed, entity, bdf = run_single_spec(target_path, base_dir)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
