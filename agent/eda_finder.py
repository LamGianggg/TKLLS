"""
Module: eda_finder.py
Description: Cross-platform Auto-Discovery Engine for EDA Toolchains (ModelSim, Quartus II, Icarus Verilog).
Enables seamless execution across different machines without hardcoded paths.
"""

import os
import glob
import shutil

def find_modelsim():
    """Locates ModelSim binaries (vlog, vsim, vlib)."""
    # 1. Check if vlog is on PATH
    vlog_path = shutil.which("vlog")
    if vlog_path:
        bin_dir = os.path.dirname(vlog_path)
        if os.path.exists(os.path.join(bin_dir, "vsim.exe")) or shutil.which("vsim"):
            return {
                "bin_dir": bin_dir,
                "vlog": vlog_path,
                "vsim": shutil.which("vsim") or os.path.join(bin_dir, "vsim.exe"),
                "vlib": shutil.which("vlib") or os.path.join(bin_dir, "vlib.exe"),
                "type": "modelsim"
            }

    # 2. Check environment variables
    env_roots = [os.environ.get("QUARTUS_ROOTDIR", ""), os.environ.get("MODELSIM_ROOT", ""), os.environ.get("ALTERA_ROOT", "")]
    for env_r in env_roots:
        if env_r:
            candidate = os.path.join(env_r, "..", "modelsim_ase", "win32aloem")
            if os.path.exists(os.path.join(candidate, "vlog.exe")):
                return {
                    "bin_dir": os.path.abspath(candidate),
                    "vlog": os.path.join(candidate, "vlog.exe"),
                    "vsim": os.path.join(candidate, "vsim.exe"),
                    "vlib": os.path.join(candidate, "vlib.exe"),
                    "type": "modelsim"
                }

    # 3. Scan common Altera / Intel FPGA installation locations across drives
    for drive in ["C", "D", "E", "F"]:
        patterns = [
            f"{drive}:/altera/*/modelsim_ase/win32aloem",
            f"{drive}:/altera/*/modelsim_ae/win32aloem",
            f"{drive}:/intelFPGA/*/modelsim_ase/win32aloem",
            f"{drive}:/intelFPGA_lite/*/modelsim_ase/win32aloem",
            f"{drive}:/intelFPGA/*/modelsim_ae/win32aloem",
            f"{drive}:/intelFPGA_lite/*/modelsim_ae/win32aloem",
            f"{drive}:/modeltech*/win32",
            f"{drive}:/modeltech*/win64",
        ]
        for p in patterns:
            for m in glob.glob(p):
                vlog_f = os.path.join(m, "vlog.exe")
                if os.path.exists(vlog_f):
                    return {
                        "bin_dir": os.path.abspath(m),
                        "vlog": os.path.abspath(vlog_f),
                        "vsim": os.path.abspath(os.path.join(m, "vsim.exe")),
                        "vlib": os.path.abspath(os.path.join(m, "vlib.exe")),
                        "type": "modelsim"
                    }

    return None

def find_iverilog():
    """Locates Icarus Verilog binaries as an alternative EDA simulator."""
    iverilog_exe = shutil.which("iverilog")
    vvp_exe = shutil.which("vvp")
    if iverilog_exe and vvp_exe:
        return {
            "iverilog": iverilog_exe,
            "vvp": vvp_exe,
            "type": "iverilog"
        }

    for drive in ["C", "D", "E"]:
        cand_bin = f"{drive}:/iverilog/bin"
        if os.path.exists(os.path.join(cand_bin, "iverilog.exe")):
            return {
                "iverilog": os.path.join(cand_bin, "iverilog.exe"),
                "vvp": os.path.join(cand_bin, "vvp.exe"),
                "type": "iverilog"
            }
    return None

def find_quartus_map():
    """Locates quartus_map.exe binary for Quartus II analysis & synthesis."""
    # 1. Check PATH
    qmap = shutil.which("quartus_map")
    if qmap:
        return os.path.abspath(qmap)

    # 2. Check environment variable
    q_root = os.environ.get("QUARTUS_ROOTDIR")
    if q_root:
        for sub in ["bin64", "bin"]:
            cand = os.path.join(q_root, sub, "quartus_map.exe")
            if os.path.exists(cand):
                return os.path.abspath(cand)

    # 3. Scan across drives
    for drive in ["C", "D", "E", "F"]:
        patterns = [
            f"{drive}:/altera/*/quartus/bin64/quartus_map.exe",
            f"{drive}:/altera/*/quartus/bin/quartus_map.exe",
            f"{drive}:/intelFPGA/*/quartus/bin64/quartus_map.exe",
            f"{drive}:/intelFPGA_lite/*/quartus/bin64/quartus_map.exe",
            f"{drive}:/intelFPGA/*/quartus/bin/quartus_map.exe",
            f"{drive}:/intelFPGA_lite/*/quartus/bin/quartus_map.exe",
        ]
        for p in patterns:
            for m in glob.glob(p):
                if os.path.exists(m):
                    return os.path.abspath(m)

    return None
