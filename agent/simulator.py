"""
Module: simulator.py
Description: Automated EDA Simulation Driver for Spec2RTL / Prompt2Silicon.
Supports:
  1. ModelSim-Altera batch mode (vlog, vsim -c)
  2. Icarus Verilog (iverilog, vvp)
  3. Portable Built-in Python Logic Verifier (Zero-dependency fallback for new machines)
"""

import os
import re
import subprocess
import shutil
from eda_finder import find_modelsim, find_iverilog

class EDASimulator:
    def __init__(self, sim_dir=None):
        self.sim_dir = sim_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sim"))
        os.makedirs(self.sim_dir, exist_ok=True)
        
        # 1. Probe for ModelSim
        self.modelsim = find_modelsim()
        self.iverilog = None
        if not self.modelsim:
            # 2. Probe for Icarus Verilog
            self.iverilog = find_iverilog()

    def run_builtin_python_verifier(self, top_module):
        """Zero-dependency simulation fallback: informs user that real EDA simulation requires ModelSim or Icarus."""
        err_msg = "ModelSim or Icarus Verilog is required for genuine hardware simulation."
        return {
            "stage": "simulate",
            "success": False,
            "passed": False,
            "errors": [err_msg],
            "log": f"[SIMULATOR NOTICE]: Neither ModelSim nor Icarus Verilog found. {err_msg}"
        }

    def run_iverilog_flow(self, verilog_files, top_module):
        """Compiles and executes using Icarus Verilog."""
        out_vvp = os.path.join(self.sim_dir, f"{top_module}.vvp")
        abs_files = [os.path.abspath(f) for f in verilog_files]
        # Compile
        c_cmd = [self.iverilog["iverilog"], "-o", out_vvp] + abs_files
        c_res = subprocess.run(c_cmd, cwd=self.sim_dir, capture_output=True)
        if c_res.returncode != 0:
            return {
                "stage": "compile",
                "success": False,
                "errors": [c_res.stderr.decode('utf-8', errors='replace')],
                "log": c_res.stderr.decode('utf-8', errors='replace')
            }

        # Simulate with vvp
        s_cmd = [self.iverilog["vvp"], out_vvp]
        s_res = subprocess.run(s_cmd, cwd=self.sim_dir, capture_output=True)
        stdout = s_res.stdout.decode('utf-8', errors='replace') if s_res.stdout else ""
        has_errors = any(kw in stdout for kw in ["ERROR", "Error", "FAIL", "Fatal", "assert failed", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])
        has_success = any(marker in stdout for marker in ["[SUCCESS]", "PASSED", "Passed", "All tests passed", "TEST PASSED", "[HARNESS PASS]"])
        has_clean_finish = s_res.returncode == 0 and ("$finish" in stdout or has_success) and not has_errors
        passed = (has_success or has_clean_finish) and not has_errors
        errors = [l.strip() for l in stdout.splitlines() if any(kw in l for kw in ["ERROR", "Error", "FAIL", "Fatal", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])]

        return {
            "stage": "simulate",
            "success": passed,
            "passed": passed,
            "errors": errors,
            "log": stdout
        }

    def init_work_library(self):
        work_path = os.path.join(self.sim_dir, "work")
        if not os.path.exists(work_path):
            vlib = self.modelsim["vlib"]
            subprocess.run([vlib, "work"], cwd=self.sim_dir, capture_output=True, check=True)

    def run_modelsim_flow(self, verilog_files, top_module):
        """Compiles and executes using ModelSim."""
        self.init_work_library()
        abs_files = [os.path.abspath(f) for f in verilog_files]
        
        # 1. Compile
        vlog = self.modelsim["vlog"]
        cmd = [vlog, "-work", "work"] + abs_files
        res = subprocess.run(cmd, cwd=self.sim_dir, capture_output=True)
        stdout = res.stdout.decode('utf-8', errors='replace') if res.stdout else ""
        if res.returncode != 0:
            errors = [l.strip() for l in stdout.splitlines() if "** Error:" in l or "** Fatal:" in l]
            return {
                "stage": "compile",
                "success": False,
                "errors": errors,
                "log": stdout
            }

        # 2. Simulate
        vsim = self.modelsim["vsim"]
        s_cmd = [vsim, "-c", "-do", "run -all; quit", f"work.{top_module}"]
        s_res = subprocess.run(s_cmd, cwd=self.sim_dir, capture_output=True)
        s_out = s_res.stdout.decode('utf-8', errors='replace') if s_res.stdout else ""

        has_errors = any(kw in s_out for kw in ["** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])
        m_failed = re.search(r"Failed Assertions\s*:\s*([1-9]\d*)", s_out)
        if m_failed:
            has_errors = True

        has_success = any(tok in s_out for tok in ["[SUCCESS]", "PASSED", "Passed", "passed", "TEST PASSED", "All tests passed", "[HARNESS PASS]"])
        has_clean_finish = ("$finish" in s_out or "Simulation complete" in s_out or s_res.returncode == 0) and not has_errors and ("$finish" in s_out or has_success)

        passed = (has_success or has_clean_finish) and not has_errors
        errors = [l.strip() for l in s_out.splitlines() if any(kw in l for kw in ["** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])]

        return {
            "stage": "simulate",
            "success": passed,
            "passed": passed,
            "errors": errors,
            "log": s_out
        }

    def run_flow(self, verilog_files, top_module="tb_top_soc"):
        """Dispatches simulation to ModelSim, Icarus Verilog, or Built-in Python fallback."""
        if self.modelsim:
            return self.run_modelsim_flow(verilog_files, top_module)
        elif self.iverilog:
            return self.run_iverilog_flow(verilog_files, top_module)
        else:
            return self.run_builtin_python_verifier(top_module)
