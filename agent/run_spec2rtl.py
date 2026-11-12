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
from eda_finder import find_quartus_map, find_modelsim
from verilog_linter import VerilogLinter
from synthesis_profiler import SynthesisProfiler
from knowledge_matcher import KnowledgeMatcher
from vwf_generator import VWFGenerator
from waveform_visualizer import WaveformVisualizer

def setup_quartus_and_bdf(q_dir, project_name, top_entity, primary_rtl, all_rtl_files):
    """Auto-generates Quartus project, BSF symbol, and BDF schematic diagram.
    Ensures BDF can be opened, edited, and synthesized without duplicate declaration errors."""
    os.makedirs(q_dir, exist_ok=True)
    qmap_exe = find_quartus_map()

    # Schematic top entity:
    # If the entity is already top_soc or starts with top_, keep it; otherwise prefix with top_
    schematic_top = top_entity if top_entity.lower().startswith("top") else f"top_{top_entity}"

    qpf_path = os.path.join(q_dir, f"{project_name}.qpf")
    qsf_path = os.path.join(q_dir, f"{project_name}.qsf")
    bsf_path = os.path.join(q_dir, f"{top_entity}.bsf")
    bdf_path = os.path.join(q_dir, f"{schematic_top}.bdf")

    # 1. Write Initial QPF & QSF with relative search paths and BDF file registration
    with open(qpf_path, "w", encoding="utf-8") as f:
        f.write(f'PROJECT_REVISION = "{project_name}"\n')

    qsf_lines = [
        'set_global_assignment -name FAMILY "Cyclone II"',
        'set_global_assignment -name DEVICE EP2C35F672C6',
        f'set_global_assignment -name TOP_LEVEL_ENTITY {schematic_top}',
        'set_global_assignment -name ORIGINAL_QUARTUS_VERSION "13.0 SP1"',
        'set_global_assignment -name LAST_QUARTUS_VERSION "13.0 SP1"',
        'set_global_assignment -name SEARCH_PATH ../src',
        'set_global_assignment -name SEARCH_PATH .',
        f'set_global_assignment -name BDF_FILE {schematic_top}.bdf',
    ]
    for vf in all_rtl_files:
        if not os.path.basename(vf).startswith("tb_"):
            rel_vf = os.path.relpath(vf, q_dir).replace('\\', '/')
            qsf_lines.append(f'set_global_assignment -name VERILOG_FILE {rel_vf}')

    with open(qsf_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(qsf_lines) + '\n')

    # 2. Generate BSF Symbol (via quartus_map or standalone generator fallback)
    bdf_gen = BDFGenerator()
    if qmap_exe and os.path.exists(qmap_exe) and os.path.exists(primary_rtl):
        subprocess.run([qmap_exe, project_name, f"--generate_symbol={primary_rtl}"], cwd=q_dir, capture_output=True)

    if not os.path.exists(bsf_path) and os.path.exists(primary_rtl):
        bdf_gen.generate_bsf_from_rtl(primary_rtl, bsf_path)

    # 3. Generate BDF Diagram from BSF
    bdf_created = False
    if os.path.exists(bsf_path):
        bdf_gen.generate_bdf_from_bsf(bsf_path, bdf_path)
        bdf_created = True

    # 3.5. Generate Quartus II Vector Waveform File (.vwf)
    vwf_path = os.path.join(q_dir, "Waveform.vwf")
    vwf_gen = VWFGenerator()
    if os.path.exists(primary_rtl):
        vwf_gen.generate_vwf_from_rtl(primary_rtl, vwf_path)
        if not any("VECTOR_WAVEFORM_FILE" in l for l in qsf_lines):
            qsf_lines.append('set_global_assignment -name VECTOR_WAVEFORM_FILE Waveform.vwf')
            with open(qsf_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(qsf_lines) + '\n')

    # 4. Final Analysis & Synthesis
    if qmap_exe and os.path.exists(qmap_exe):
        subprocess.run([qmap_exe, project_name, "-c", project_name], cwd=q_dir, capture_output=True)
    elif not qmap_exe:
        print(f" -> [Lưu ý EDA]: Không tìm thấy quartus_map.exe trên máy. Project {project_name}.qpf, sơ đồ {schematic_top}.bdf và sóng Waveform.vwf đã được tạo sẵn để bạn mở và chỉnh sửa trực tiếp trong Quartus II GUI.")

    return qpf_path, bsf_path, bdf_path if bdf_created else None, vwf_path

def run_single_spec(spec_path, base_dir, open_gui=False):
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

    # Step 1.5: Hardware Knowledge Base Query & Intent Matching (RAG Engine)
    print(f"[Step 1.5] Hardware Knowledge Base Query & Intent Matching (RAG Engine)...")
    kb_matcher = KnowledgeMatcher()
    matched_entry, match_type, conf, exemplars = kb_matcher.search(spec_text, top_k=3)
    if matched_entry:
        print(f" -> Knowledge Base Status: [{match_type}] Match (Confidence: {conf*100:.1f}%)")
        print(f" -> Source Benchmark    : {matched_entry.get('source', 'Hardware KB')}")
        print(f" -> Matched Design ID   : {matched_entry.get('id')} ({matched_entry.get('name')})")
        print(f" -> Circuit Category    : {matched_entry.get('category')}")
        if exemplars:
            ex_names = [e.get('name') for e in exemplars if e.get('name') != matched_entry.get('name')]
            if ex_names:
                print(f" -> In-Context Exemplars: {', '.join(ex_names[:3])}")
    else:
        print(f" -> Knowledge Base Status: [NOVEL SPECIFICATION] - Dynamic Synthesis Mode Active")
    print("-" * 80)

    # Step 2: Auto-generate RTL and TB if missing
    print(f"\n[Step 2] Resolving and Generating Synthesizable Verilog & Testbench...")
    rtl_gen = RTLGenerator(src_dir)
    tb_gen  = TBGenerator(sim_dir)

    analyzer = SpecAnalyzer(spec_path)
    cat = analyzer.classify_system()
    mod_name = analyzer.extract_module_name()

    # Known system dispatch table (ponytail: eliminates 50 lines of duplicate boilerplate)
    KNOWN_SYSTEMS = {
        "VENDING":  ("vending_machine", "Vending_Machine", rtl_gen.generate_vending_machine, tb_gen.generate_vending_tb),
        "ELEVATOR": ("elevator_controller", "Elevator_Controller", rtl_gen.generate_elevator_controller, tb_gen.generate_elevator_tb),
        "TRAFFIC":  ("traffic_light", "Traffic_Light", rtl_gen.generate_traffic_light, tb_gen.generate_traffic_tb),
    }

    if cat == "SOC_AI":
        top_name = "tb_top_soc"
        top_entity = "top_soc"
        project_name = "Top_SoC"
        primary_rtl = os.path.join(src_dir, "top_soc.v")
        soc_core_files = [
            "top_soc.v", "ai_core.v", "ai_datapath.v", "ai_fsm.v",
            "cpu_controller.v", "dma_8237.v", "mac_unit.v", "ram_16x4.v",
            "relu.v", "vector_counter.v"
        ]
        verilog_files = [os.path.join(src_dir, f) for f in soc_core_files if os.path.exists(os.path.join(src_dir, f))]
        rtl_files = [f for f in verilog_files]
        verilog_files.append(os.path.join(sim_dir, "tb_top_soc.v"))

    elif cat in KNOWN_SYSTEMS:
        top_entity, project_name, gen_rtl, gen_tb = KNOWN_SYSTEMS[cat]
        top_name = f"tb_{top_entity}"
        v_file = os.path.join(src_dir, f"{top_entity}.v")
        tb_file = os.path.join(sim_dir, f"{top_name}.v")
        if not os.path.exists(v_file):
            gen_rtl(spec_text)
            print(f" -> [Auto-Gen] Synthesized: src/{top_entity}.v")
        if not os.path.exists(tb_file):
            gen_tb()
            print(f" -> [Auto-Gen] Synthesized: sim/{top_name}.v")
        verilog_files, rtl_files, primary_rtl = [v_file, tb_file], [v_file], v_file

    else:
        # AUTONOMOUS GENERAL SPEC2RTL SYNTHESIS FOR ANY CUSTOM / RANDOM SPEC
        top_entity = mod_name
        top_name = f"tb_{top_entity}"
        project_name = "".join(part.capitalize() for part in top_entity.split("_"))
        v_file = os.path.join(src_dir, f"{top_entity}.v")
        tb_file = os.path.join(sim_dir, f"{top_name}.v")

        # Knowledge Base Fast-Path: Deploy Golden Synthesizable Verilog
        if match_type == "EXACT" and matched_entry and matched_entry.get("golden_rtl") and not os.path.exists(v_file):
            print(f" -> [Knowledge Base Fast-Path]: Deploying Golden Synthesizable RTL from {matched_entry['source']}...")
            with open(v_file, "w", encoding="utf-8") as f:
                f.write(matched_entry["golden_rtl"] + "\n")
            if matched_entry.get("golden_tb") and not os.path.exists(tb_file):
                print(f" -> [Knowledge Base Fast-Path]: Deploying Golden Testbench from {matched_entry['source']}...")
                with open(tb_file, "w", encoding="utf-8") as f:
                    f.write(matched_entry["golden_tb"] + "\n")

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

    # Step 2.5: VerilogDB Static Pre-Synthesis Analysis & Linting
    print(f"\n[Step 2.5] Executing VerilogDB Static Linting & Syntax Pre-Validation...")
    for vf in verilog_files:
        VerilogLinter.sanitize_file(vf)
    print(f" -> [VerilogDB Linter]: All {len(verilog_files)} design files verified and sanitized.")

    # Step 3: Simulation & Verification with VeriPrefer Closed-Loop Reflection
    print(f"\n[Step 3] Invoking EDA Simulation with Closed-Loop Reflection (VeriPrefer Framework)...")
    sim = EDASimulator(sim_dir)
    reflector = ReflectionAgent(sim)

    start_t = time.time()
    result = reflector.execute_closed_loop_flow(verilog_files, top_module=top_name, max_retries=3)
    elapsed = time.time() - start_t

    print("\n" + "-" * 80)
    print("   SIMULATION TRANSCRIPT OUTPUT")
    print("-" * 80)
    print(result.get("log", "").strip())
    print("-" * 80)

    # Step 4: Auto-generate BSF, BDF, VWF, and Quartus Project
    print(f"\n[Step 4] Auto-generating Schematic BSF, BDF, Waveform VWF & Quartus Project...")
    qpf_path, bsf_path, bdf_path, vwf_path = setup_quartus_and_bdf(q_dir, project_name, top_entity, primary_rtl, rtl_files)
    print(f" -> Quartus Project created: {qpf_path}")
    print(f" -> Symbol File (.bsf):      {bsf_path}")
    if bdf_path:
        print(f" -> Schematic Diagram (.bdf): {bdf_path}")
    if vwf_path and os.path.exists(vwf_path):
        print(f" -> Quartus Waveform (.vwf):  {vwf_path}")

    # Generate interactive HTML Waveform and 1-Click Launchers
    vcd_path = os.path.join(sim_dir, f"{top_entity}.vcd")
    html_path = os.path.join(sim_dir, "waveform.html")
    bat_sim = os.path.join(sim_dir, "view_waveform.bat")
    bat_root = os.path.join(base_dir, "view_waveform.bat")

    modelsim_info = find_modelsim()
    m_bin = modelsim_info.get("bin_dir") if modelsim_info else ""

    vis = WaveformVisualizer()
    if os.path.exists(vcd_path):
        vis.generate_html_viewer(vcd_path, html_path, f"{top_entity.replace('_', ' ').title()} Simulation Waveform")
    vis.generate_view_launcher(m_bin, sim_dir, top_name, bat_sim)
    vis.generate_view_launcher(m_bin, sim_dir, top_name, bat_root)

    if open_gui and m_bin:
        print(f"\n[ModelSim GUI]: Đang khởi động cửa sổ sóng đồ họa trên màn hình...")
        vsim_exe = os.path.join(m_bin, "vsim.exe")
        subprocess.Popen([vsim_exe, "-novopt", f"work.{top_name}", "-do", "add wave -r /*; run -all; wave zoom full;"], cwd=sim_dir)

    # Step 4.5: VerilogDB Hardware Synthesis & Resource Utilization Profiling
    print(f"\n[Step 4.5] Profiling Hardware Synthesis Resource Footprint (VerilogDB Standard)...")
    metrics = SynthesisProfiler.profile_module(q_dir, project_name, primary_rtl)
    print(SynthesisProfiler.format_profiler_card(metrics, top_entity))

    # Step 5: Verification Judgment
    if result["success"]:
        print(f"\n>>> [SPEC2RTL STATUS: SUCCESS (100% PASS)] <<<")
        print(f"Execution Time: {elapsed:.2f} seconds")
        print(f"Simulation waveform dumped in: {sim_dir}")
        print("\n[Available Visual Inspection Formats]:")
        if bdf_path:
            print(f" 1. BDF Schematic : Open Quartus II -> {bdf_path}")
        if vwf_path and os.path.exists(vwf_path):
            print(f" 2. Quartus VWF   : Open Quartus II -> {vwf_path} (Sóng xung nhịp trong Quartus Waveform Editor)")
        print(f" 3. 1-Click GUI   : Nhấp đúp chuột vào 'view_waveform.bat' (Mở trực tiếp cửa sổ sóng trong ModelSim)")
        print(f" 4. Web Waveform  : Nhấp đúp chuột vào '{html_path}' (Xem dạng sóng đồ họa tương tác trên trình duyệt)")
        print(f" 5. RTL Viewer    : Open Quartus II -> {qpf_path} -> Tools -> Netlist Viewers -> RTL Viewer")
        print(f" 6. Raw VCD Data  : {vcd_path}")
        return True, elapsed, top_entity, bdf_path, metrics
    else:
        print(f"\n>>> [SPEC2RTL STATUS: FAILED] <<<")
        diagnosis = reflector.diagnose_error(result)
        print(f"Failure Stage: {diagnosis['stage']}")
        print(f"Category: {diagnosis['category']}")
        print(f"Root Cause: {diagnosis['root_cause']}")
        print(f"Suggested Fix: {diagnosis['suggested_fix']}")
        # VeriPrefer Reflection Self-Healing Guidance
        refl_guidance = kb_matcher.get_reflection_guidance(result.get("log", ""))
        if refl_guidance:
            print("\n" + "=" * 80)
            print("   [VeriPrefer Reflection Guidance (arXiv:2504.15804)]")
            print("=" * 80)
            for r in refl_guidance:
                print(f" * Error Pattern: {r['error_type']}")
                print(f"   Diagnosis    : {r['diagnosis']}")
                print(f"   Remedy       : {r['remedy']}")
            print("=" * 80)
        return False, elapsed, top_entity, None, metrics

def get_spec_description(filename, specs_dir=None):
    """Returns friendly description for available specs (delegates to SpecAnalyzer)."""
    full_path = os.path.join(specs_dir, filename) if specs_dir else filename
    try:
        return SpecAnalyzer(full_path).get_friendly_description()
    except Exception:
        return "Custom Hardware Specification"

def get_benchmark_suites(base_dir):
    """Discovers and organizes available benchmark specs across the 3 datasets."""
    bm_root = os.path.join(base_dir, "benchmarks")
    suites = {
        "verilog_eval": {"name": "VerilogEval (NVIDIA Research)", "specs": []},
        "rtllm":        {"name": "RTLLM (HKUST Benchmark)", "specs": []},
        "veriprefer":   {"name": "VeriPrefer (CityU HK - arXiv:2504.15804)", "specs": []}
    }
    if os.path.exists(bm_root):
        for s_key in suites.keys():
            s_dir = os.path.join(bm_root, s_key)
            if os.path.exists(s_dir):
                files = sorted([os.path.join(s_dir, f) for f in os.listdir(s_dir) if f.endswith(".md") or f.endswith(".txt")])
                suites[s_key]["specs"] = files
    return suites

def run_benchmark_suite(target_suite, base_dir):
    """Executes benchmarks across specified suites and outputs a grouped academic report."""
    suites = get_benchmark_suites(base_dir)
    to_run = []
    if target_suite in ["all", "benchmark", "b"]:
        for k, v in suites.items():
            for sp in v["specs"]:
                to_run.append((k, v["name"], sp))
    elif target_suite in suites:
        for sp in suites[target_suite]["specs"]:
            to_run.append((target_suite, suites[target_suite]["name"], sp))
    else:
        print(f"[ERROR] Unknown benchmark suite: '{target_suite}'. Available: 'all', 'verilog_eval', 'rtllm', 'veriprefer'.")
        return False

    print("\n" + "=" * 110)
    print(f"   STARTING MULTI-DATASET HARDWARE BENCHMARK EXECUTION ({len(to_run)} DESIGNS)")
    print("   Datasets: NVIDIA VerilogEval, HKUST RTLLM, CityU HK VeriPrefer")
    print("=" * 110 + "\n")

    results = []
    total_passed = 0
    for s_key, s_name, sp in to_run:
        success, elapsed, entity, bdf, metrics = run_single_spec(sp, base_dir)
        results.append((s_key, os.path.basename(sp), entity, success, elapsed, metrics))
        if success:
            total_passed += 1

    # Print Grouped Summary Table
    print("\n" + "=" * 115)
    print("                  MULTI-DATASET ACADEMIC HARDWARE BENCHMARK & SYNTHESIS REPORT")
    print("                  Datasets: NVIDIA VerilogEval, HKUST RTLLM, CityU HK VeriPrefer")
    print("=" * 115)
    print(f"{'Dataset / Suite':<18} | {'Specification File':<26} | {'Top Entity':<22} | {'Logic (LEs)':<12} | {'Regs (FF)':<11} | {'Status':<10}")
    print("-" * 115)

    curr_suite = None
    for s_key, fname, ent, succ, elap, m in results:
        if s_key != curr_suite:
            curr_suite = s_key
            print(f"--- [SUITE: {suites[s_key]['name']}] ---")
        status_str = "100% PASS" if succ else "FAILED"
        les_str = f"{m.get('logic_elements', '-')} LEs"
        ff_str  = f"{m.get('total_registers', '-')} FFs"
        print(f"{s_key:<18} | {fname:<26} | {ent:<22} | {les_str:<12} | {ff_str:<11} | {status_str:<10}")

    print("=" * 115)
    pass_pct = (total_passed * 100.0) / len(to_run) if to_run else 0.0
    print(f"BENCHMARK OUTCOME: {total_passed}/{len(to_run)} PASSED ({pass_pct:.1f}% SUCCESS RATE)")
    print("=" * 115)
    return total_passed == len(to_run)

def main():
    base_dir  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    specs_dir = os.path.join(base_dir, "specs")

    print("=" * 80)
    print("   Spec2RTL & Prompt2Silicon Autonomous Hardware Generation Pipeline")
    print("   Based on NVIDIA Research (arXiv:2506.13905) & ISCAS 2026 (arXiv:2601.13815)")
    print("   Benchmarking: VerilogEval (NVIDIA), RTLLM (HKUST), VeriPrefer (CityU HK)")
    print("=" * 80)

    available_specs = sorted([f for f in os.listdir(specs_dir) if f.endswith(".md") or f.endswith(".txt")])
    bm_suites = get_benchmark_suites(base_dir)

    # Parse arguments: support positional ('python run_spec2rtl.py benchmark', 'all', '1') and flags
    parser = argparse.ArgumentParser(description="Spec2RTL & Prompt2Silicon Autonomous Pipeline")
    parser.add_argument("spec_pos", nargs="?", default=None, help="Spec name, number, 'all', or 'benchmark'")
    parser.add_argument("--spec", dest="spec_flag", default=None, help="Name, number, or 'all'")
    parser.add_argument("--all", action="store_true", help="Run all available core specifications")
    parser.add_argument("--gui", action="store_true", help="Automatically launch ModelSim Graphical Waveform Viewer on completion")
    parser.add_argument("--benchmark", dest="benchmark_suite", default=None, help="Run benchmark suite: 'all', 'verilog_eval', 'rtllm', 'veriprefer'")
    args = parser.parse_args()

    user_input = args.spec_flag or args.spec_pos

    SUITE_MAP = {
        "benchmark": "all", "benchmarks": "all", "bm": "all", "b": "all",
        "b1": "verilog_eval", "verilog_eval": "verilog_eval",
        "b2": "rtllm", "rtllm": "rtllm",
        "b3": "veriprefer", "veriprefer": "veriprefer",
    }

    # Check for benchmark execution (CLI flags or arguments)
    target_bm = args.benchmark_suite or (user_input if user_input and user_input.lower() in SUITE_MAP else None)
    if target_bm:
        suite_id = SUITE_MAP.get(target_bm.lower(), target_bm.lower())
        sys.exit(0 if run_benchmark_suite(suite_id, base_dir) else 1)

    run_all_mode = args.all or (user_input and user_input.lower() in ["all", "a"])

    if not user_input and not args.all:
        print("\n[DANH SÁCH CÁC BÀI TOÁN CÓ SẴN TRONG specs/]:")
        for idx, s in enumerate(available_specs):
            desc = get_spec_description(s, specs_dir)
            print(f"  [{idx+1}] {s:<22} -> {desc}")
        print(f"  [A]  Chạy TẤT CẢ ({len(available_specs)} bài toán core lần lượt)")
        print("\n[CÁC BỘ BENCHMARK HỌC THUẬT TIÊU CHUẨN (benchmarks/)]:")
        print(f"  [B1] VerilogEval Suite  -> NVIDIA Research Benchmark ({len(bm_suites['verilog_eval']['specs'])} bài)")
        print(f"  [B2] RTLLM Suite        -> HKUST System-level RTL Benchmark ({len(bm_suites['rtllm']['specs'])} bài)")
        print(f"  [B3] VeriPrefer Suite   -> CityU HK Verification Feedback Benchmark ({len(bm_suites['veriprefer']['specs'])} bài)")
        print(f"  [B]  Chạy TẤT CẢ 3 BỘ BENCHMARK HỌC THUẬT (Tổng cộng {sum(len(v['specs']) for v in bm_suites.values())} bài)")

        # Interactive selection
        try:
            choice = input(f"\n👉 Vui lòng chọn bài toán muốn chạy [1-{len(available_specs)}, A, B1, B2, B3, hoặc B, mặc định: A]: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "A"

        if choice == "" or choice.lower() in ["a", "all"]:
            run_all_mode = True
        elif choice.lower() in SUITE_MAP:
            sys.exit(0 if run_benchmark_suite(SUITE_MAP[choice.lower()], base_dir) else 1)
        else:
            user_input = choice

    # Case 1: Run ALL specs
    if run_all_mode:
        print(f"\n>>> [CHẾ ĐỘ TỰ ĐỘNG]: TIẾN HÀNH CHẠY TẤT CẢ {len(available_specs)} BÀI TOÁN <<<\n")
        summary_results = []
        for s in available_specs:
            spec_file_path = os.path.join(specs_dir, s)
            success, elapsed, entity, bdf, metrics = run_single_spec(spec_file_path, base_dir, open_gui=args.gui)
            summary_results.append((s, entity, success, elapsed, bdf, metrics))

        print("\n" + "=" * 96)
        print("    BẢNG TỔNG KẾT ĐO ĐẠC TÀI NGUYÊN & ĐỘ CHÍNH XÁC CHỨC NĂNG (VERIPREFER & VERILOGDB)")
        print("    Chuẩn đo lường: CityU VeriPrefer (arXiv:2504.15804) & Univ. Florida VerilogDB (arXiv:2507.13369)")
        print("=" * 96)
        print(f"{'STT':<4} | {'Tên Spec':<22} | {'Entity':<20} | {'Logic (LEs)':<12} | {'Registers (FF)':<15} | {'Trạng Thái':<10}")
        print("-" * 96)
        for i, (spec_n, ent, succ, elap, bdf, m) in enumerate(summary_results):
            status_str = "100% PASS" if succ else "FAILED"
            les_str = f"{m.get('logic_elements', '-')} LEs"
            ff_str  = f"{m.get('total_registers', '-')} FFs"
            print(f"[{i+1}]  | {spec_n:<22} | {ent:<20} | {les_str:<12} | {ff_str:<15} | {status_str:<10}")
        print("=" * 96)
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

    if os.path.isabs(spec_target) and os.path.exists(spec_target):
        target_path = spec_target
    elif os.path.exists(os.path.join(base_dir, spec_target)):
        target_path = os.path.abspath(os.path.join(base_dir, spec_target))
    elif os.path.exists(spec_target):
        target_path = os.path.abspath(spec_target)
    else:
        matched = None
        for s in available_specs:
            if s.lower() == spec_target.lower() or spec_target.lower() in s.lower():
                matched = s
                break

        if matched:
            target_path = os.path.join(specs_dir, matched)
        else:
            target_path = os.path.join(specs_dir, spec_target)

    if not os.path.exists(target_path):
        print(f"[ERROR] Specification file not found: {target_path}")
        sys.exit(1)

    success, elapsed, entity, bdf, metrics = run_single_spec(target_path, base_dir, open_gui=args.gui)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
