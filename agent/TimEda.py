"""
Module: TimEda.py (truoc day la eda_finder.py)
Mô tả: Tự động tìm kiếm công cụ ModelSim, Quartus II, Icarus Verilog trên máy.
Hỗ trợ chạy mượt mà trên nhiều máy tính mà không cần cấu hình thủ công.
"""

import os
import glob
import shutil

def find_modelsim():
    """Tìm kiếm phần mềm mô phỏng ModelSim (vlog, vsim, vlib)."""
    # 1. Kiểm tra trong biến môi trường PATH
    DuongDanVlog = shutil.which("vlog")
    if DuongDanVlog:
        ThuMucChay = os.path.dirname(DuongDanVlog)
        if os.path.exists(os.path.join(ThuMucChay, "vsim.exe")) or shutil.which("vsim"):
            return {
                "bin_dir": ThuMucChay,
                "vlog": DuongDanVlog,
                "vsim": shutil.which("vsim") or os.path.join(ThuMucChay, "vsim.exe"),
                "vlib": shutil.which("vlib") or os.path.join(ThuMucChay, "vlib.exe"),
                "type": "modelsim"
            }

    # 2. Kiểm tra biến môi trường của hệ điều hành
    DanhSachMoiTruong = [os.environ.get("QUARTUS_ROOTDIR", ""), os.environ.get("MODELSIM_ROOT", ""), os.environ.get("ALTERA_ROOT", "")]
    for GiaTriMoiTruong in DanhSachMoiTruong:
        if GiaTriMoiTruong:
            DuongDanThu = os.path.join(GiaTriMoiTruong, "..", "modelsim_ase", "win32aloem")
            if os.path.exists(os.path.join(DuongDanThu, "vlog.exe")):
                return {
                    "bin_dir": os.path.abspath(DuongDanThu),
                    "vlog": os.path.join(DuongDanThu, "vlog.exe"),
                    "vsim": os.path.join(DuongDanThu, "vsim.exe"),
                    "vlib": os.path.join(DuongDanThu, "vlib.exe"),
                    "type": "modelsim"
                }

    # 3. Quét tự động trên các ổ đĩa của máy tính
    for TenODia in ["C", "D", "E", "F", "G", "H"]:
        MauTimKiem = [
            f"{TenODia}:/altera/*/modelsim_ase/win32aloem",
            f"{TenODia}:/altera/*/modelsim_ae/win32aloem",
            f"{TenODia}:/intelFPGA/*/modelsim_ase/win32aloem",
            f"{TenODia}:/intelFPGA_lite/*/modelsim_ase/win32aloem",
            f"{TenODia}:/intelFPGA/*/modelsim_ae/win32aloem",
            f"{TenODia}:/intelFPGA_lite/*/modelsim_ae/win32aloem",
            f"{TenODia}:/intelFPGA_pro/*/modelsim_ase/win32aloem",
            f"{TenODia}:/intelFPGA_pro/*/modelsim_ae/win32aloem",
            f"{TenODia}:/modeltech*/win32",
            f"{TenODia}:/modeltech*/win64",
            f"{TenODia}:/Program Files/altera/*/modelsim_ase/win32aloem",
            f"{TenODia}:/Program Files (x86)/altera/*/modelsim_ase/win32aloem",
        ]
        for Mau in MauTimKiem:
            for ThuMuc in glob.glob(Mau):
                FileVlog = os.path.join(ThuMuc, "vlog.exe")
                if os.path.exists(FileVlog):
                    return {
                        "bin_dir": os.path.abspath(ThuMuc),
                        "vlog": os.path.abspath(FileVlog),
                        "vsim": os.path.abspath(os.path.join(ThuMuc, "vsim.exe")),
                        "vlib": os.path.abspath(os.path.join(ThuMuc, "vlib.exe")),
                        "type": "modelsim"
                    }

    return None

def find_iverilog():
    """Tìm phần mềm mô phỏng Icarus Verilog dự phòng."""
    FileIVerilog = shutil.which("iverilog")
    FileVvp = shutil.which("vvp")
    if FileIVerilog and FileVvp:
        return {
            "iverilog": FileIVerilog,
            "vvp": FileVvp,
            "type": "iverilog"
        }

    for TenODia in ["C", "D", "E"]:
        ThuMucChay = f"{TenODia}:/iverilog/bin"
        if os.path.exists(os.path.join(ThuMucChay, "iverilog.exe")):
            return {
                "iverilog": os.path.join(ThuMucChay, "iverilog.exe"),
                "vvp": os.path.join(ThuMucChay, "vvp.exe"),
                "type": "iverilog"
            }
    return None

def find_quartus_map():
    """Tìm bộ biên dịch Quartus II (quartus_map.exe)."""
    # 1. Kiểm tra trong PATH
    FileQuartusMap = shutil.which("quartus_map")
    if FileQuartusMap:
        return os.path.abspath(FileQuartusMap)

    # 2. Kiểm tra biến môi trường
    GocQuartus = os.environ.get("QUARTUS_ROOTDIR")
    if GocQuartus:
        for ThuMucCon in ["bin64", "bin"]:
            FileTimThay = os.path.join(GocQuartus, ThuMucCon, "quartus_map.exe")
            if os.path.exists(FileTimThay):
                return os.path.abspath(FileTimThay)

    # 3. Quét tự động trên tất cả các ổ đĩa
    for TenODia in ["C", "D", "E", "F", "G", "H"]:
        MauTimKiem = [
            f"{TenODia}:/altera/*/quartus/bin64/quartus_map.exe",
            f"{TenODia}:/altera/*/quartus/bin/quartus_map.exe",
            f"{TenODia}:/Program Files/altera/*/quartus/bin64/quartus_map.exe",
            f"{TenODia}:/Program Files/altera/*/quartus/bin/quartus_map.exe",
            f"{TenODia}:/Program Files (x86)/altera/*/quartus/bin64/quartus_map.exe",
            f"{TenODia}:/Program Files (x86)/altera/*/quartus/bin/quartus_map.exe",
            f"{TenODia}:/intelFPGA/*/quartus/bin64/quartus_map.exe",
            f"{TenODia}:/intelFPGA_lite/*/quartus/bin64/quartus_map.exe",
            f"{TenODia}:/intelFPGA/*/quartus/bin/quartus_map.exe",
            f"{TenODia}:/intelFPGA_lite/*/quartus/bin/quartus_map.exe",
            f"{TenODia}:/intelFPGA_pro/*/quartus/bin64/quartus_map.exe",
            f"{TenODia}:/intelFPGA_pro/*/quartus/bin/quartus_map.exe",
        ]
        for Mau in MauTimKiem:
            for ThuMuc in glob.glob(Mau):
                if os.path.exists(ThuMuc):
                    return os.path.abspath(ThuMuc)

    return None
