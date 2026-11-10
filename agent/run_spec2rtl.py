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

def setup_quartus_and_bdf(q_dir, project_name, top_entity, primary_rtl, all_rtl_files):
    """Auto-generates Quartus project, BSF symbol, and BDF schematic diagram."""
    os.makedirs(q_dir, exist_ok=True)
    qmap_exe = r"D:\altera\13.0sp1\quartus\bin64\quartus_map.exe"

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
    if os.path.exists(qmap_exe) and os.path.exists(primary_rtl):
        subprocess.run([qmap_exe, project_name, f"--generate_symbol={primary_rtl}"], cwd=q_dir, capture_output=True)

    # 3. Generate BDF Diagram from BSF
    bdf_created = False
    if os.path.exists(bsf_path):
        bdf_gen = BDFGenerator()
        bdf_gen.generate_bdf_from_bsf(bsf_path, bdf_path)
        bdf_created = True

    # 4. Final Analysis & Synthesis
    if os.path.exists(qmap_exe):
        subprocess.run([qmap_exe, project_name, "-c", project_name], cwd=q_dir, capture_output=True)

    return qpf_path, bsf_path, bdf_path if bdf_created else None

def main():
    parser = argparse.ArgumentParser(description="Spec2RTL & Prompt2Silicon Autonomous Pipeline")
    parser.add_argument("--spec", type=str, default=None, help="Name or index of the spec file in specs/")
    args = parser.parse_args()

    base_dir  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    specs_dir = os.path.join(base_dir, "specs")
    src_dir   = os.path.join(base_dir, "src")
    sim_dir   = os.path.join(base_dir, "sim")
    q_dir     = os.path.join(base_dir, "quartus")

    print("=" * 80)
    print("   Spec2RTL & Prompt2Silicon Autonomous Hardware Generation Pipeline")
    print("   Based on NVIDIA Research (arXiv:2506.13905) & ISCAS 2026 (arXiv:2601.13815)")
    print("=" * 80)

    available_specs = sorted([f for f in os.listdir(specs_dir) if f.endswith(".md") or f.endswith(".txt")])

    spec_target = args.spec
    if spec_target and spec_target.isdigit():
        idx = int(spec_target) - 1
        if 0 <= idx < len(available_specs):
            spec_target = available_specs[idx]

    if not spec_target:
        print("\n[Available Specifications in specs/]:")
        for idx, s in enumerate(available_specs):
            print(f"  [{idx+1}] {s}")
        if "vendding_machine.md" in available_specs:
            spec_target = "vendding_machine.md"
        else:
            spec_target = available_specs[0]
        print(f"\n -> Default Selection: {spec_target} (Use --spec <name|number> to choose)")

    if not os.path.isabs(spec_target):
        # find matching spec
        matched = None
        for s in available_specs:
            if s.lower() == spec_target.lower() or spec_target.lower() in s.lower():
                matched = s
                break
        if matched:
            spec_path = os.path.join(specs_dir, matched)
        else:
            spec_path = os.path.join(specs_dir, spec_target)
    else:
        spec_path = spec_target

    if not os.path.exists(spec_path):
        print(f"[ERROR] Specification file not found: {spec_path}")
        sys.exit(1)

    # Step 1: Read Spec
    print(f"\n[Step 1] Ingesting and Parsing Specification: {os.path.basename(spec_path)}...")
    with open(spec_path, "r", encoding="utf-8", errors="replace") as f:
        spec_text = f.read()
    print("-" * 80)
    print(spec_text.strip()[:400] + ("..." if len(spec_text) > 400 else ""))
    print("-" * 80)

    # Step 2: Auto-generate RTL and TB if missing
    print(f"\n[Step 2] Resolving and Generating Synthesizable Verilog & Testbench...")
    rtl_gen = RTLGenerator(src_dir)
    tb_gen  = TBGenerator(sim_dir)

    spec_lower = (os.path.basename(spec_path) + " " + spec_text).lower()

    if "vend" in spec_lower or "bán nước" in spec_lower:
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

    elif "thang" in spec_lower or "elevator" in spec_lower:
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

    elif "traffic" in spec_lower or "giao thông" in spec_lower:
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
        top_name = "tb_top_soc"
        top_entity = "top_soc"
        project_name = "Top_SoC"
        primary_rtl = os.path.join(src_dir, "top_soc.v")
        verilog_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith(".v") and not any(k in f for k in ["traffic", "vending", "elevator"])]
        rtl_files = [f for f in verilog_files]
        verilog_files.append(os.path.join(sim_dir, "tb_top_soc.v"))

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

    # Step 5: Verification Judgment & Reflection
    if result["success"]:
        print(f"\n>>> [SPEC2RTL STATUS: SUCCESS (100% PASS)] <<<")
        print(f"Execution Time: {elapsed:.2f} seconds")
        print(f"Simulation waveform dumped in: {sim_dir}")
        print("\n[Available Visual Inspection Formats]:")
        if bdf_path:
            print(f" 1. BDF Schematic: Open Quartus II -> {bdf_path}")
        print(f" 2. RTL Viewer:    Open Quartus II -> {qpf_path} -> Tools -> Netlist Viewers -> RTL Viewer")
        print(f" 3. Waveform:      Open ModelSim   -> {os.path.join(sim_dir, top_entity + '.vcd')}")
        sys.exit(0)
    else:
        print(f"\n>>> [SPEC2RTL STATUS: FAILED] <<<")
        diagnosis = reflector.diagnose_error(result)
        print(f"Failure Stage: {diagnosis['stage']}")
        print(f"Category: {diagnosis['category']}")
        print(f"Root Cause: {diagnosis['root_cause']}")
        print(f"Suggested Fix: {diagnosis['suggested_fix']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
