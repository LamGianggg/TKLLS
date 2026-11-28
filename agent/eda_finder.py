"""
Module: eda_finder.py
Mô tả: Tự động dò tìm đường dẫn các công cụ EDA (ModelSim, Quartus II, Icarus Verilog) trên máy tính.
Giúp hệ thống chạy ổn định trên nhiều máy mà không cần người dùng cấu hình biến môi trường thủ công.
"""

import os
import glob
import shutil

def find_modelsim():
    """
    Tìm kiếm bộ công cụ mô phỏng ModelSim (gồm `vlog`, `vsim`, `vlib`).
    Thứ tự ưu tiên:
      1. Biến môi trường PATH của hệ thống.
      2. Các biến môi trường đặc thù của Altera/Intel (QUARTUS_ROOTDIR, MODELSIM_ROOT, ALTERA_ROOT).
      3. Quét trực tiếp các thư mục cài đặt phổ biến trên các ổ đĩa C..H.
    Trả về dict chứa đường dẫn thực thi nếu tìm thấy, ngược lại trả về None.
    """
    # Bước 1: Kiểm tra xem lệnh `vlog` đã có sẵn trong biến môi trường PATH chưa
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

    # Bước 2: Suy ra thư mục ModelSim từ các biến môi trường của Quartus / Altera
    DanhSachMoiTruong = [os.environ.get("QUARTUS_ROOTDIR", ""), os.environ.get("MODELSIM_ROOT", ""), os.environ.get("ALTERA_ROOT", "")]
    for GiaTriMoiTruong in DanhSachMoiTruong:
        if GiaTriMoiTruong:
            for ThuMucModelSim in ["modelsim_ase", "modelsim_ae", "modelsim"]:
                for SubDir in ["win32aloem", "win32", "win64"]:
                    DuongDanThu = os.path.join(GiaTriMoiTruong, "..", ThuMucModelSim, SubDir)
                    if os.path.exists(os.path.join(DuongDanThu, "vlog.exe")):
                        return {
                            "bin_dir": os.path.abspath(DuongDanThu),
                            "vlog": os.path.join(DuongDanThu, "vlog.exe"),
                            "vsim": os.path.join(DuongDanThu, "vsim.exe"),
                            "vlib": os.path.join(DuongDanThu, "vlib.exe"),
                            "type": "modelsim"
                        }

    # Bước 3: Quét tự động trên các ổ đĩa cục bộ (hỗ trợ cả Altera cũ và Intel FPGA mới)
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
    """
    Tìm kiếm trình mô phỏng mã nguồn mở Icarus Verilog (`iverilog` và `vvp`).
    Dùng làm phương án dự phòng khi máy người dùng chưa cài ModelSim.
    """
    # Bước 1: Kiểm tra trong PATH
    FileIVerilog = shutil.which("iverilog")
    FileVvp = shutil.which("vvp")
    if FileIVerilog and FileVvp:
        return {
            "iverilog": FileIVerilog,
            "vvp": FileVvp,
            "type": "iverilog"
        }

    # Bước 2: Kiểm tra thư mục cài đặt mặc định trên ổ C, D, E
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
    """
    Tìm kiếm bộ phân tích và tổng hợp logic Quartus II (`quartus_map.exe`).
    Dùng để kiểm tra khả năng tổng hợp phần cứng (Synthesis) và lấy báo cáo tài nguyên FPGA.
    """
    # Bước 1: Kiểm tra trong PATH
    FileQuartusMap = shutil.which("quartus_map")
    if FileQuartusMap:
        return os.path.abspath(FileQuartusMap)

    # Bước 2: Kiểm tra theo biến môi trường QUARTUS_ROOTDIR (ưu tiên bản 64-bit trước)
    GocQuartus = os.environ.get("QUARTUS_ROOTDIR")
    if GocQuartus:
        for ThuMucCon in ["bin64", "bin"]:
            FileTimThay = os.path.join(GocQuartus, ThuMucCon, "quartus_map.exe")
            if os.path.exists(FileTimThay):
                return os.path.abspath(FileTimThay)

    # Bước 3: Quét tự động trên các ổ đĩa C..H cho mọi phiên bản Altera / Intel FPGA
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
