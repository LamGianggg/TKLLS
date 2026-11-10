"""
Module: simulator.py
Description: Automated EDA Simulation Driver for Spec2RTL / Prompt2Silicon.
Supports ModelSim-Altera batch mode (vlog, vsim -c) and Icarus Verilog.
Captures compile/runtime logs and formats structured feedback for the Reflection Agent.
"""

import os
import subprocess
import shutil

class EDASimulator:
    def __init__(self, sim_dir=None):
        self.sim_dir = sim_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sim"))
        os.makedirs(self.sim_dir, exist_ok=True)
        
        # Locate ModelSim binaries
        modelsim_bin = r"D:\altera\13.0sp1\modelsim_ase\win32aloem"
        self.vlog_exe = os.path.join(modelsim_bin, "vlog.exe")
        self.vsim_exe = os.path.join(modelsim_bin, "vsim.exe")
        self.vlib_exe = os.path.join(modelsim_bin, "vlib.exe")
        
        # Fallback check
        if not os.path.exists(self.vlog_exe):
            self.vlog_exe = shutil.which("vlog")
        if not os.path.exists(self.vsim_exe):
            self.vsim_exe = shutil.which("vsim")

    def init_work_library(self):
        work_path = os.path.join(self.sim_dir, "work")
        if not os.path.exists(work_path):
            subprocess.run([self.vlib_exe, "work"], cwd=self.sim_dir, capture_output=True, check=True)

    def compile(self, verilog_files):
        """Compiles Verilog source files."""
        self.init_work_library()
        cmd = [self.vlog_exe, "-work", "work"] + verilog_files
        res = subprocess.run(cmd, cwd=self.sim_dir, capture_output=True)
        
        stdout = res.stdout.decode('utf-8', errors='replace') if res.stdout else ""
        stderr = res.stderr.decode('utf-8', errors='replace') if res.stderr else ""
        
        success = (res.returncode == 0)
        errors = []
        for line in stdout.splitlines():
            if "** Error:" in line or "** Fatal:" in line:
                errors.append(line.strip())
                
        return {
            "success": success,
            "returncode": res.returncode,
            "errors": errors,
            "stdout": stdout,
            "stderr": stderr
        }

    def simulate(self, top_module="tb_top_soc", run_time="run -all; quit"):
        """Runs batch simulation."""
        cmd = [self.vsim_exe, "-c", "-do", run_time, f"work.{top_module}"]
        res = subprocess.run(cmd, cwd=self.sim_dir, capture_output=True)
        
        stdout = res.stdout.decode('utf-8', errors='replace') if res.stdout else ""
        stderr = res.stderr.decode('utf-8', errors='replace') if res.stderr else ""
        
        passed = "[SUCCESS]" in stdout
        mismatch = "[ERROR] MISMATCH" in stdout or "[ERROR] SIMULATION TIMEOUT" in stdout
        
        runtime_errors = []
        for line in stdout.splitlines():
            if "[ERROR]" in line or "** Error:" in line or "[FAIL]" in line:
                runtime_errors.append(line.strip())

        return {
            "success": passed and not mismatch,
            "passed": passed,
            "errors": runtime_errors,
            "stdout": stdout,
            "stderr": stderr
        }

    def run_flow(self, verilog_files, top_module="tb_top_soc"):
        """Executes full compile + simulate flow."""
        c_res = self.compile(verilog_files)
        if not c_res["success"]:
            return {
                "stage": "compile",
                "success": False,
                "errors": c_res["errors"],
                "log": c_res["stdout"]
            }
        
        s_res = self.simulate(top_module)
        return {
            "stage": "simulate",
            "success": s_res["success"],
            "passed": s_res["passed"],
            "errors": s_res["errors"],
            "log": s_res["stdout"]
        }

if __name__ == "__main__":
    sim = EDASimulator()
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    sim_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sim"))
    files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith(".v")]
    files.append(os.path.join(sim_dir, "tb_top_soc.v"))
    result = sim.run_flow(files)
    print(f"Flow Success: {result['success']}")
    if result['errors']:
        print("Errors:", result['errors'])
