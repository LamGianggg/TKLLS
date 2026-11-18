"""
Module: run_spec2rtl.py
Mô tả: Chương trình điều phối tự động quy trình Spec2RTL & Prompt2Silicon.
Quy trình thực thi hoàn chỉnh:
  1. Đọc và phân tích yêu cầu đặc tả (specs/*.txt, specs/*.md)
  2. Tự động sinh mã nguồn Verilog RTL (src/*.v)
  3. Tự động sinh Testbench tự kiểm tra lỗi (sim/*.v)
  4. Mô phỏng và phản hồi tự sửa lỗi qua ModelSim / Icarus
  5. Tự động tạo file Symbol (.bsf) và sơ đồ nguyên lý (.bdf) cho Quartus II
  6. Tạo dự án Quartus II (.qpf/.qsf) và trích xuất tài nguyên (LE, Flip-Flop, Pin)
"""

import os
import re
import sys
import time
import argparse
import subprocess
import shutil

# Cấu hình UTF-8 cho console Windows để tránh lỗi hiển thị tiếng Việt
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from spec_analyzer import SpecAnalyzer
from rtl_generator import RTLGenerator
from tb_generator import TBGenerator
from bdf_generator import BDFGenerator
from port_auditor import PortAuditor
from simulator import EDASimulator
from reflection_loop import ReflectionAgent
from eda_finder import find_quartus_map, find_modelsim
from verilog_linter import VerilogLinter
from synthesis_profiler import SynthesisProfiler
from vwf_generator import VWFGenerator

def get_base_dir():
    """Tự động xác định thư mục gốc của dự án trên mọi máy tính và hệ điều hành."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def get_circuit_quartus_dir(ThuMucGoc, TenMach):
    """Tự động tạo và trả về thư mục riêng cho từng mạch trong quartus/."""
    if not ThuMucGoc:
        ThuMucGoc = get_base_dir()
    TenSach = re.sub(r'[^A-Za-z0-9_]', '_', str(TenMach)).strip('_') or "circuit"
    GocQuartus = os.path.join(os.path.abspath(ThuMucGoc), "quartus")
    os.makedirs(GocQuartus, exist_ok=True)
    ThuMucQuartus = os.path.join(GocQuartus, TenSach)
    os.makedirs(ThuMucQuartus, exist_ok=True)
    return ThuMucQuartus

def setup_quartus_and_bdf(ThuMucQuartus, TenDuAn, TenMach, FileRtlChinh, DanhSachRtl, DuongDanVcd=None):
    """Tự động tạo dự án Quartus, biểu tượng BSF và sơ đồ nguyên lý BDF."""
    os.makedirs(ThuMucQuartus, exist_ok=True)
    FileQuartusMap = find_quartus_map()

    TenSoDoTop = f"sch_{TenMach}"

    # Xóa file BDF cũ nếu trùng tên để tránh lỗi Quartus 12049
    FileBdfCu = os.path.join(ThuMucQuartus, f"{TenMach}.bdf")
    if os.path.exists(FileBdfCu):
        try: os.remove(FileBdfCu)
        except Exception: pass

    FileQpf = os.path.join(ThuMucQuartus, f"{TenDuAn}.qpf")
    FileQsf = os.path.join(ThuMucQuartus, f"{TenDuAn}.qsf")
    FileBsf = os.path.join(ThuMucQuartus, f"{TenMach}.bsf")
    FileBdf = os.path.join(ThuMucQuartus, f"{TenSoDoTop}.bdf")

    # 1. Tạo file cấu hình QPF & QSF với đường dẫn tương đối
    with open(FileQpf, "w", encoding="utf-8") as TepTin:
        TepTin.write(f'PROJECT_REVISION = "{TenDuAn}"\n')

    DongCauHinhQsf = [
        'set_global_assignment -name FAMILY "Cyclone II"',
        'set_global_assignment -name DEVICE EP2C35F672C6',
        f'set_global_assignment -name TOP_LEVEL_ENTITY "{TenSoDoTop}"',
        'set_global_assignment -name ORIGINAL_QUARTUS_VERSION "13.0 SP1"',
        'set_global_assignment -name LAST_QUARTUS_VERSION "13.0 SP1"',
        'set_global_assignment -name SEARCH_PATH "../../src"',
        'set_global_assignment -name SEARCH_PATH "../src"',
        'set_global_assignment -name SEARCH_PATH "."',
        f'set_global_assignment -name BDF_FILE "{TenSoDoTop}.bdf"',
    ]
    for FileRtl in DanhSachRtl:
        if not os.path.basename(FileRtl).startswith("tb_"):
            FileRtlDich = os.path.join(ThuMucQuartus, os.path.basename(FileRtl))
            if os.path.abspath(FileRtl) != os.path.abspath(FileRtlDich) and os.path.exists(FileRtl):
                try: shutil.copy2(FileRtl, FileRtlDich)
                except Exception: pass
            TenRtlTuongDoi = os.path.basename(FileRtl)
            DongCauHinhQsf.append(f'set_global_assignment -name VERILOG_FILE "{TenRtlTuongDoi}"')

    with open(FileQsf, "w", encoding="utf-8") as TepTin:
        TepTin.write('\n'.join(DongCauHinhQsf) + '\n')

    # 2. Sinh Symbol BSF từ cổng RTL
    BoTaoBdf = BDFGenerator()
    if os.path.exists(FileRtlChinh):
        BoTaoBdf.generate_bsf_from_rtl(FileRtlChinh, FileBsf)

    # 3. Sinh sơ đồ nguyên lý BDF từ BSF
    DaTaoBdf = False
    if os.path.exists(FileBsf):
        BoTaoBdf.generate_bdf_from_bsf(FileBsf, FileBdf)
        DaTaoBdf = True

    # 3.5. Sinh duy nhất 1 file dạng sóng Quartus VWF (Waveform.vwf)
    FileVwf = os.path.join(ThuMucQuartus, "Waveform.vwf")
    FileVwfMachCu = os.path.join(ThuMucQuartus, f"Waveform_{TenMach}.vwf")
    if os.path.exists(FileVwfMachCu):
        try: os.remove(FileVwfMachCu)
        except Exception: pass

    BoTaoVwf = VWFGenerator()
    if os.path.exists(FileRtlChinh):
        BoTaoVwf.generate_vwf_from_rtl(FileRtlChinh, FileVwf, DuongDanVcd=DuongDanVcd)
        TenVwfTuongDoi = "Waveform.vwf"
        DongCauHinhQsf = [dong for dong in DongCauHinhQsf if "VECTOR_WAVEFORM_FILE" not in dong]
        DongCauHinhQsf.append(f'set_global_assignment -name VECTOR_WAVEFORM_FILE "{TenVwfTuongDoi}"')
        with open(FileQsf, "w", encoding="utf-8") as TepTin:
            TepTin.write('\n'.join(DongCauHinhQsf) + '\n')

    # 4. Tổng hợp Quartus Map
    if FileQuartusMap and os.path.exists(FileQuartusMap):
        for ThuMucTam in ["db", "incremental_db"]:
            DuongDanTam = os.path.join(ThuMucQuartus, ThuMucTam)
            if os.path.exists(DuongDanTam):
                try: shutil.rmtree(DuongDanTam, ignore_errors=True)
                except Exception: pass
        try:
            subprocess.run([FileQuartusMap, TenDuAn, "-c", TenDuAn], cwd=ThuMucQuartus, capture_output=True, timeout=60)
        except Exception as e:
            print(f" -> [Lưu ý EDA]: Quá trình chạy quartus_map gặp cảnh báo: {e}")
    elif not FileQuartusMap:
        print(f" -> [Lưu ý EDA]: Không tìm thấy quartus_map.exe trên máy. Project {TenDuAn}.qpf, sơ đồ {TenSoDoTop}.bdf và sóng Waveform.vwf đã sẵn sàng để mở trực tiếp trong Quartus II GUI.")

    return FileQpf, FileBsf, FileBdf if DaTaoBdf else None, FileVwf

def run_single_spec(DuongDanSpec, ThuMucGoc=None, MoGiaoDien=False, DungHarness=False, MoTrangWeb=False):
    """Thực thi toàn bộ quy trình Spec2RTL cho một bài toán đặc tả."""
    if not ThuMucGoc:
        ThuMucGoc = get_base_dir()
    ThuMucGoc = os.path.abspath(ThuMucGoc)
    ThuMucSrc = os.path.join(ThuMucGoc, "src")
    ThuMucSim = os.path.join(ThuMucGoc, "sim")
    ThuMucQuartusGoc = os.path.join(ThuMucGoc, "quartus")
    os.makedirs(ThuMucSrc, exist_ok=True)
    os.makedirs(ThuMucSim, exist_ok=True)
    os.makedirs(ThuMucQuartusGoc, exist_ok=True)
    ThuMucQuartus = ThuMucQuartusGoc

    print("\n" + "=" * 80)
    print(f"   [XỬ LÝ BÀI TOÁN]: {os.path.basename(DuongDanSpec)}")
    print("=" * 80)

    # Bước 1: Đọc và phân tích đặc tả
    print(f"[Bước 1] Đang đọc và phân tích văn bản đặc tả...")
    with open(DuongDanSpec, "r", encoding="utf-8", errors="replace") as TepTin:
        NoiDungSpec = TepTin.read()
    print("-" * 80)
    print(NoiDungSpec.strip()[:350] + ("..." if len(NoiDungSpec) > 350 else ""))
    print("-" * 80)

    # Bước 2: Tự động sinh mã RTL và Testbench
    print(f"\n[Bước 2] Tự động sinh mã nguồn Verilog RTL & Testbench...")
    BoSinhRtl = RTLGenerator(ThuMucSrc)
    BoSinhTb  = TBGenerator(ThuMucSim)

    BoPhanTich = SpecAnalyzer(DuongDanSpec)
    PhanLoai = BoPhanTich.classify_system()
    TenModule = BoPhanTich.extract_module_name()

    BangMachMau = {
        "VENDING":  ("vending_machine", "Vending_Machine", BoSinhRtl.generate_vending_machine, BoSinhTb.generate_vending_tb),
        "ELEVATOR": ("elevator_controller", "Elevator_Controller", BoSinhRtl.generate_elevator_controller, BoSinhTb.generate_elevator_tb),
        "TRAFFIC":  ("traffic_light", "Traffic_Light", BoSinhRtl.generate_traffic_light, BoSinhTb.generate_traffic_tb),
    }

    if PhanLoai == "SOC_AI" or BoPhanTich.is_30_percent_architecture():
        print("\n" + "=" * 80)
        print("   [CHIẾN LƯỢC PHÂN TÁCH KIẾN TRÚC]: BÁO HIỆU GIỚI HẠN KIẾN TRÚC PHẦN CỨNG")
        print("=" * 80)
        print(" -> [TRẠNG THÁI: TỪ CHỐI TỔNG HỢP NGUYÊN KHỐI / ARCHITECTURAL BOUNDARY]")
        print(f" -> Phân loại vi mạch: NHÓM VI KIẾN TRÚC CỐT LÕI ({TenModule.upper()} / SOC COMPLEX)")
        print("\n[LÝ DO BÁO THẤT BẠI TỰ ĐỘNG]:")
        print("  1. Các hệ thống phức tạp (SoC đa phân hệ, AI Accelerator Core, Systolic Array NPU, DMA)")
        print("     tuyệt đối KHÔNG ĐƯỢC sinh nguyên khối (monolithic) chỉ bằng 1 câu prompt.")
        print("  2. Cần phân tách thành các khối linh kiện phổ thông độc lập (MAC, ReLU, FSM, RAM).")
        print("=" * 80)
        print(">>> [SPEC2RTL STATUS: FAILED (REJECTED BY ARCHITECTURAL BOUNDARY GUARD)] <<<\n")
        return False, 0.0, TenModule, None, {}

    elif PhanLoai in BangMachMau:
        TenMach, TenDuAn, HamSinhRtl, HamSinhTb = BangMachMau[PhanLoai]
        ThuMucQuartus = get_circuit_quartus_dir(ThuMucGoc, TenMach)
        TenModuleTb = f"tb_{TenMach}"
        FileRtl = os.path.join(ThuMucSrc, f"{TenMach}.v")
        FileTb = os.path.join(ThuMucSim, f"{TenModuleTb}.v")
        if not os.path.exists(FileRtl):
            HamSinhRtl(NoiDungSpec)
            print(f" -> [Auto-Gen] Đã sinh RTL: src/{TenMach}.v")
        if not os.path.exists(FileTb):
            HamSinhTb()
            print(f" -> [Auto-Gen] Đã sinh TB : sim/{TenModuleTb}.v")
        DanhSachVerilog, DanhSachFileRtl, FileRtlChinh = [FileRtl, FileTb], [FileRtl], FileRtl

    else:
        # Tự động sinh mã cho bài toán tùy ý
        TenMach = TenModule
        TenModuleTb = f"tb_{TenMach}"
        TenDuAn = "".join(Tu.capitalize() for Tu in TenMach.split("_"))
        ThuMucQuartus = get_circuit_quartus_dir(ThuMucGoc, TenMach)
        FileRtl = os.path.join(ThuMucSrc, f"{TenMach}.v")
        FileTb = os.path.join(ThuMucSim, f"{TenModuleTb}.v")

        # Xóa các file cũ nếu có
        for FileCu in [os.path.join(ThuMucQuartus, f"{TenMach}.bsf"), os.path.join(ThuMucQuartus, f"{TenMach}.bdf"), os.path.join(ThuMucQuartus, f"top_{TenMach}.bdf"), os.path.join(ThuMucQuartus, f"sch_{TenMach}.bdf")]:
            if os.path.exists(FileCu):
                try: os.remove(FileCu)
                except Exception: pass

        _, FileRtl = BoSinhRtl.generate_from_spec(NoiDungSpec, DuongDanSpec)
        print(f" -> [Auto-Gen Dynamic RTL] Đã sinh: src/{os.path.basename(FileRtl)}")

        _, FileTb = BoSinhTb.generate_tb_from_spec(NoiDungSpec, FileRtl, DuongDanSpec)
        print(f" -> [Auto-Gen Dynamic TB] Đã sinh: sim/{os.path.basename(FileTb)}")

        DanhSachVerilog = [FileRtl, FileTb]
        DanhSachFileRtl = [FileRtl]
        FileRtlChinh = FileRtl

    # Đảm bảo TenMach và TenModuleTb khớp chính xác với khai báo module Verilog
    if FileRtlChinh and os.path.exists(FileRtlChinh):
        with open(FileRtlChinh, "r", encoding="utf-8", errors="replace") as TepTin:
            NoiDungRtl = re.sub(r"//.*", "", TepTin.read())
            NoiDungRtl = re.sub(r"/\*.*?\*/", "", NoiDungRtl, flags=re.DOTALL)
            KhopModule = re.search(r"\bmodule\s+([A-Za-z0-9_]+)", NoiDungRtl)
            if KhopModule and not KhopModule.group(1).startswith("tb_") and not KhopModule.group(1).startswith("harness_"):
                TenMach = KhopModule.group(1)
                TenDuAn = "".join(Tu.capitalize() for Tu in TenMach.split("_"))
                ThuMucQuartus = get_circuit_quartus_dir(ThuMucGoc, TenMach)

    for FileV in DanhSachVerilog:
        if os.path.basename(FileV).startswith("tb_") and os.path.exists(FileV):
            with open(FileV, "r", encoding="utf-8", errors="replace") as TepTin:
                NoiDungTb = re.sub(r"//.*", "", TepTin.read())
                NoiDungTb = re.sub(r"/\*.*?\*/", "", NoiDungTb, flags=re.DOTALL)
                KhopTb = re.search(r"\bmodule\s+([A-Za-z0-9_]+)", NoiDungTb)
                if KhopTb:
                    TenModuleTb = KhopTb.group(1)

    print(f" -> Danh sách file thiết kế ({len(DanhSachVerilog)}):")
    for FileV in DanhSachVerilog:
        print(f"    * {os.path.basename(FileV)}")

    # Bước 2.5: Kiểm tra tĩnh AST và dọn dẹp cú pháp Verilog
    print(f"\n[Bước 2.5] Phân tích tĩnh AST & dọn dẹp cú pháp Verilog (VerilogLinter)...")
    for FileV in DanhSachVerilog:
        VerilogLinter.sanitize_file(FileV)
    if FileRtlChinh and os.path.exists(FileRtlChinh):
        VerilogLinter.lint_file(FileRtlChinh)
    print(f" -> [VerilogLinter]: Toàn bộ {len(DanhSachVerilog)} file đã được kiểm tra và chuẩn hóa.")

    # Bước 3: Mô phỏng và phản hồi tự sửa lỗi (Reflection Loop)
    print(f"\n[Bước 3] Chạy mô phỏng EDA với vòng lặp tự phản hồi (Reflection Loop)...")
    BoMoPhong = EDASimulator(ThuMucSim)
    BoPhanHoi = ReflectionAgent(BoMoPhong)

    ThoiGianBatDau = time.time()
    KetQuaMoPhong = BoPhanHoi.execute_closed_loop_flow(DanhSachVerilog, top_module=TenModuleTb, max_retries=3)
    ThoiGianChay = time.time() - ThoiGianBatDau

    print("\n" + "-" * 80)
    print("   KẾT QUẢ MÔ PHỎNG (SIMULATION LOG)")
    print("-" * 80)
    print(KetQuaMoPhong.get("log", "").strip())
    print("-" * 80)

    # Bước 4: Tự động sinh Symbol BSF, sơ đồ BDF, sóng VWF và Dự án Quartus
    print(f"\n[Bước 4] Tự động tạo Symbol BSF, Sơ đồ BDF, Sóng VWF & Dự án Quartus...")
    FileVcd = os.path.join(ThuMucSim, f"{TenMach}.vcd")
    FileQpf, FileBsf, FileBdf, FileVwf = setup_quartus_and_bdf(ThuMucQuartus, TenDuAn, TenMach, FileRtlChinh, DanhSachFileRtl, DuongDanVcd=FileVcd)
    print(f" -> Dự án Quartus (.qpf) : {FileQpf}")
    print(f" -> Ký hiệu Symbol (.bsf): {FileBsf}")
    if FileBdf:
        print(f" -> Sơ đồ mạch (.bdf)    : {FileBdf}")
    if FileVwf and os.path.exists(FileVwf):
        print(f" -> Dạng sóng (.vwf)     : {FileVwf}")

    # Bước 4.2: Đối soát cổng tín hiệu
    print(f"\n[Bước 4.2] Đối soát tính toàn vẹn cổng tín hiệu...")
    DanhSachCongSpec = BoPhanTich.extract_ports()
    PortAuditor.audit(DanhSachCongSpec, FileRtlChinh, FileBsf, FileBdf)

    FileVcd = os.path.join(ThuMucSim, f"{TenMach}.vcd")

    ThongTinModelSim = find_modelsim()
    ThuMucBinModelSim = ThongTinModelSim.get("bin_dir") if ThongTinModelSim else ""

    if MoGiaoDien and ThuMucBinModelSim:
        print(f"\n[ModelSim GUI]: Đang khởi động giao diện sóng ModelSim...")
        FileVsimExe = os.path.join(ThuMucBinModelSim, "vsim.exe")
        subprocess.Popen([FileVsimExe, "-novopt", f"work.{TenModuleTb}", "-do", "add wave -r /*; run -all; wave zoom full;"], cwd=ThuMucSim)

    # Bước 4.5: Đo đạc tài nguyên phần cứng
    print(f"\n[Bước 4.5] Đo đạc mức độ tiêu thụ tài nguyên phần cứng...")
    ThongSoTaiNguyen = SynthesisProfiler.profile_module(ThuMucQuartus, TenDuAn, FileRtlChinh)
    print(SynthesisProfiler.format_profiler_card(ThongSoTaiNguyen, TenMach))

    # Bước 5: Đánh giá kết quả
    if KetQuaMoPhong["success"]:
        print(f"\n>>> [SPEC2RTL STATUS: THÀNH CÔNG (100% PASS)] <<<")
        print(f"Thời gian thực thi: {ThoiGianChay:.2f} giây")
        print(f"Thư mục dạng sóng mô phỏng: {ThuMucSim}")
        print("\n[Các định dạng trực quan sẵn có]:")
        if FileBdf:
            print(f" 1. Sơ đồ BDF   : Mở Quartus II -> {FileBdf}")
        if FileVwf and os.path.exists(FileVwf):
            print(f" 2. Dạng sóng VWF: Mở Quartus II -> {FileVwf}")
        print(f" 3. RTL Viewer  : Mở Quartus II -> {FileQpf} -> Tools -> Netlist Viewers -> RTL Viewer")
        print(f" 4. Dữ liệu VCD : {FileVcd}")
        return True, ThoiGianChay, TenMach, FileBdf, ThongSoTaiNguyen
    else:
        print(f"\n>>> [SPEC2RTL STATUS: THẤT BẠI] <<<")
        ChanDoan = BoPhanHoi.diagnose_error(KetQuaMoPhong)
        print(f"Giai đoạn lỗi: {ChanDoan['stage']}")
        print(f"Phân loại lỗi: {ChanDoan['category']}")
        print(f"Nguyên nhân  : {ChanDoan['root_cause']}")
        print(f"Hướng xử lý  : {ChanDoan['suggested_fix']}")
        return False, ThoiGianChay, TenMach, None, ThongSoTaiNguyen

def get_spec_description(TenFile, ThuMucSpecs=None):
    """Lấy mô tả ngắn gọn dễ hiểu cho bài toán."""
    DuongDanDayDu = os.path.join(ThuMucSpecs, TenFile) if ThuMucSpecs else TenFile
    try:
        return SpecAnalyzer(DuongDanDayDu).get_friendly_description()
    except Exception:
        return "Bài toán thiết kế vi mạch tùy chỉnh"

def get_benchmark_suites(ThuMucGoc):
    """Tìm kiếm các bộ kiểm thử benchmark trong thư mục benchmarks/."""
    ThuMucBenchmark = os.path.join(ThuMucGoc, "benchmarks")
    BoKiemThu = {
        "verilog_eval": {"name": "VerilogEval (NVIDIA Research)", "specs": []},
        "rtllm":        {"name": "RTLLM (HKUST Benchmark)", "specs": []},
        "veriprefer":   {"name": "VeriPrefer (CityU HK)", "specs": []}
    }
    if os.path.exists(ThuMucBenchmark):
        for Khoa in BoKiemThu.keys():
            ThuMucBo = os.path.join(ThuMucBenchmark, Khoa)
            if os.path.exists(ThuMucBo):
                DanhSachFile = sorted([os.path.join(ThuMucBo, f) for f in os.listdir(ThuMucBo) if f.endswith(".md") or f.endswith(".txt")])
                BoKiemThu[Khoa]["specs"] = DanhSachFile
    return BoKiemThu

def run_benchmark_suite(TenBoKiemThu, ThuMucGoc):
    """Chạy toàn bộ bài toán kiểm thử trong bộ benchmark."""
    BoKiemThu = get_benchmark_suites(ThuMucGoc)
    DanhSachChay = []
    if TenBoKiemThu in ["all", "benchmark", "b"]:
        for Khoa, GiaTri in BoKiemThu.items():
            for DuongDan in GiaTri["specs"]:
                DanhSachChay.append((Khoa, GiaTri["name"], DuongDan))
    elif TenBoKiemThu in BoKiemThu:
        for DuongDan in BoKiemThu[TenBoKiemThu]["specs"]:
            DanhSachChay.append((TenBoKiemThu, BoKiemThu[TenBoKiemThu]["name"], DuongDan))
    else:
        print(f"[ERROR] Không tìm thấy bộ benchmark: '{TenBoKiemThu}'.")
        return False

    print("\n" + "=" * 110)
    print(f"   BẮT ĐẦU CHẠY KIỂM THỬ BENCHMARK ({len(DanhSachChay)} THIẾT KẾ)")
    print("=" * 110 + "\n")

    BangKetQua = []
    TongSoPass = 0
    for Khoa, TenBo, DuongDan in DanhSachChay:
        ThanhCong, ThoiGian, ThucThe, SodoBdf, ChiSo = run_single_spec(DuongDan, ThuMucGoc)
        BangKetQua.append((Khoa, os.path.basename(DuongDan), ThucThe, ThanhCong, ThoiGian, ChiSo))
        if ThanhCong:
            TongSoPass += 1

    print("\n" + "=" * 115)
    print("                  BẢNG TỔNG KẾT KẾT QUẢ ĐO ĐẠC BENCHMARK")
    print("=" * 115)
    print(f"{'Bộ Benchmark':<18} | {'File bài toán':<26} | {'Tên Entity':<22} | {'Logic (LEs)':<12} | {'Regs (FF)':<11} | {'Trạng thái':<10}")
    print("-" * 115)

    BoHienTai = None
    for Khoa, TenFile, ThucThe, ThanhCong, ThoiGian, ChiSo in BangKetQua:
        if Khoa != BoHienTai:
            BoHienTai = Khoa
            print(f"--- [BỘ: {BoKiemThu[Khoa]['name']}] ---")
        ChuoiTrangThai = "100% PASS" if ThanhCong else "FAILED"
        ChuoiLe = f"{ChiSo.get('logic_elements', '-')} LEs"
        ChuoiFf  = f"{ChiSo.get('total_registers', '-')} FFs"
        print(f"{Khoa:<18} | {TenFile:<26} | {ThucThe:<22} | {ChuoiLe:<12} | {ChuoiFf:<11} | {ChuoiTrangThai:<10}")

    print("=" * 115)
    TiLePass = (TongSoPass * 100.0) / len(DanhSachChay) if DanhSachChay else 0.0
    print(f"KẾT QUẢ: {TongSoPass}/{len(DanhSachChay)} BÀI ĐẠT CHUẨN ({TiLePass:.1f}% THÀNH CÔNG)")
    print("=" * 115)
    return TongSoPass == len(DanhSachChay)

def main():
    ThuMucGoc = get_base_dir()
    ThuMucSpecs = os.path.join(ThuMucGoc, "specs")

    print("=" * 80)
    print("   HỆ THỐNG TỰ ĐỘNG THIẾT KẾ VI MẠCH SPEC2RTL & PROMPT2SILICON")
    print("   Quy trình: YÊU CẦU -> SINH MÃ -> MÔ PHỎNG -> XUẤT SƠ ĐỒ QUARTUS")
    print("=" * 80)

    DanhSachSpecs = sorted([f for f in os.listdir(ThuMucSpecs) if f.endswith(".txt") or f.endswith(".md")])
    BoTienIch = get_benchmark_suites(ThuMucGoc)

    BoPhanTichThamSo = argparse.ArgumentParser(description="Hệ thống tự động Spec2RTL")
    BoPhanTichThamSo.add_argument("spec_pos", nargs="?", default=None, help="Tên spec, số thứ tự hoặc 'all'")
    BoPhanTichThamSo.add_argument("--spec", dest="spec_flag", default=None, help="Tên spec hoặc số")
    BoPhanTichThamSo.add_argument("--all", action="store_true", help="Chạy tất cả bài toán trong specs/")
    BoPhanTichThamSo.add_argument("--gui", action="store_true", help="Mở giao diện sóng đồ họa ModelSim")
    BoPhanTichThamSo.add_argument("--web", action="store_true", help="Mở dạng sóng trên trình duyệt")
    BoPhanTichThamSo.add_argument("--harness", action="store_true", help="Sử dụng Test Harness")
    BoPhanTichThamSo.add_argument("--benchmark", dest="benchmark_suite", default=None, help="Chạy bộ benchmark")
    ThamSo = BoPhanTichThamSo.parse_args()

    LuaChonDauVao = ThamSo.spec_flag or ThamSo.spec_pos

    BangChon = {
        "benchmark": "all", "benchmarks": "all", "bm": "all",
        "b1": "verilog_eval", "verilog_eval": "verilog_eval",
        "b2": "rtllm", "rtllm": "rtllm",
        "b3": "veriprefer", "veriprefer": "veriprefer",
    }

    CoSpecA = any(s.lower() in ["a", "a.txt", "a.md"] for s in DanhSachSpecs)

    BoBenchmarkChon = ThamSo.benchmark_suite
    if not BoBenchmarkChon and LuaChonDauVao:
        ChuThuong = LuaChonDauVao.lower()
        if ChuThuong in BangChon:
            BoBenchmarkChon = LuaChonDauVao

    if BoBenchmarkChon:
        MaBo = BangChon.get(BoBenchmarkChon.lower(), BoBenchmarkChon.lower())
        sys.exit(0 if run_benchmark_suite(MaBo, ThuMucGoc) else 1)
    if LuaChonDauVao and LuaChonDauVao.lower() == "all":
        CheDoChayTatCa = True
    elif LuaChonDauVao and LuaChonDauVao.lower() == "a" and not CoSpecA:
        CheDoChayTatCa = True
    elif ThamSo.all:
        CheDoChayTatCa = True
    else:
        CheDoChayTatCa = False

    if not LuaChonDauVao and not ThamSo.all:
        print("\n[DANH SÁCH CÁC BÀI TOÁN CÓ SẴN TRONG specs/]:")
        for ChiSo, TenTep in enumerate(DanhSachSpecs):
            MoTa = get_spec_description(TenTep, ThuMucSpecs)
            print(f"  [{ChiSo+1}] {TenTep:<22} -> {MoTa}")
        print(f"  [ALL] Chạy TẤT CẢ ({len(DanhSachSpecs)} bài toán lần lượt)")

        try:
            LuaChon = input(f"\n👉 Vui lòng chọn bài toán muốn chạy [1-{len(DanhSachSpecs)}, ALL, mặc định: ALL]: ").strip()
        except (EOFError, KeyboardInterrupt):
            LuaChon = "ALL"

        if LuaChon == "" or LuaChon.lower() == "all" or (LuaChon.lower() == "a" and not CoSpecA):
            CheDoChayTatCa = True
        elif LuaChon.lower() in BangChon:
            sys.exit(0 if run_benchmark_suite(BangChon[LuaChon.lower()], ThuMucGoc) else 1)
        else:
            LuaChonDauVao = LuaChon

    # Trường hợp 1: Chạy TẤT CẢ các bài toán
    if CheDoChayTatCa:
        print(f"\n>>> [CHẾ ĐỘ TỰ ĐỘNG]: TIẾN HÀNH CHẠY TẤT CẢ {len(DanhSachSpecs)} BÀI TOÁN <<<\n")
        DanhSachKetQuaTongHop = []
        for TenTep in DanhSachSpecs:
            DuongDanTep = os.path.join(ThuMucSpecs, TenTep)
            ThanhCong, ThoiGian, ThucThe, SodoBdf, ChiSo = run_single_spec(DuongDanTep, ThuMucGoc, MoGiaoDien=ThamSo.gui, DungHarness=ThamSo.harness, MoTrangWeb=ThamSo.web)
            DanhSachKetQuaTongHop.append((TenTep, ThucThe, ThanhCong, ThoiGian, SodoBdf, ChiSo))

        print("\n" + "=" * 96)
        print("    BẢNG TỔNG KẾT ĐO ĐẠC TÀI NGUYÊN & ĐỘ CHÍNH XÁC CHỨC NĂNG")
        print("=" * 96)
        print(f"{'STT':<4} | {'Tên Spec':<22} | {'Entity':<20} | {'Logic (LEs)':<12} | {'Registers (FF)':<15} | {'Trạng Thái':<10}")
        print("-" * 96)
        for i, (TenSpec, ThucThe, ThanhCong, ThoiGian, SodoBdf, ChiSo) in enumerate(DanhSachKetQuaTongHop):
            ChuoiTrangThai = "100% PASS" if ThanhCong else "FAILED"
            ChuoiLe = f"{ChiSo.get('logic_elements', '-')} LEs"
            ChuoiFf  = f"{ChiSo.get('total_registers', '-')} FFs"
            print(f"[{i+1}]  | {TenSpec:<22} | {ThucThe:<20} | {ChuoiLe:<12} | {ChuoiFf:<15} | {ChuoiTrangThai:<10}")
        print("=" * 96)
        print("\n[Tất cả các sơ đồ BDF và Project Quartus đều đã sẵn sàng trong thư mục quartus/!]")
        sys.exit(0)

    # Trường hợp 2: Chạy MỘT bài toán cụ thể
    MucTieuSpec = LuaChonDauVao
    if MucTieuSpec.isdigit():
        ChiSo = int(MucTieuSpec) - 1
        if 0 <= ChiSo < len(DanhSachSpecs):
            MucTieuSpec = DanhSachSpecs[ChiSo]
        else:
            print(f"[ERROR] Chỉ số không hợp lệ. Vui lòng chọn từ 1 đến {len(DanhSachSpecs)}.")
            sys.exit(1)

    if os.path.isabs(MucTieuSpec) and os.path.exists(MucTieuSpec):
        DuongDanMucTieu = MucTieuSpec
    elif os.path.exists(os.path.join(ThuMucGoc, MucTieuSpec)):
        DuongDanMucTieu = os.path.abspath(os.path.join(ThuMucGoc, MucTieuSpec))
    elif os.path.exists(MucTieuSpec):
        DuongDanMucTieu = os.path.abspath(MucTieuSpec)
    else:
        KhopTen = None
        for TenTep in DanhSachSpecs:
            if TenTep.lower() == MucTieuSpec.lower() or TenTep.lower() == f"{MucTieuSpec.lower()}.txt" or TenTep.lower() == f"{MucTieuSpec.lower()}.md":
                KhopTen = TenTep
                break
        if not KhopTen:
            for TenTep in DanhSachSpecs:
                if MucTieuSpec.lower() in TenTep.lower():
                    KhopTen = TenTep
                    break

        if KhopTen:
            DuongDanMucTieu = os.path.join(ThuMucSpecs, KhopTen)
        elif os.path.exists(os.path.join(ThuMucSpecs, f"{MucTieuSpec}.txt")):
            DuongDanMucTieu = os.path.join(ThuMucSpecs, f"{MucTieuSpec}.txt")
        elif os.path.exists(os.path.join(ThuMucSpecs, f"{MucTieuSpec}.md")):
            DuongDanMucTieu = os.path.join(ThuMucSpecs, f"{MucTieuSpec}.md")
        else:
            DuongDanMucTieu = os.path.join(ThuMucSpecs, MucTieuSpec)

    if not os.path.exists(DuongDanMucTieu):
        print(f"[ERROR] Không tìm thấy file đặc tả: {DuongDanMucTieu}")
        sys.exit(1)

    ThanhCong, ThoiGian, ThucThe, SodoBdf, ChiSo = run_single_spec(DuongDanMucTieu, ThuMucGoc, MoGiaoDien=ThamSo.gui, DungHarness=ThamSo.harness, MoTrangWeb=ThamSo.web)
    sys.exit(0 if ThanhCong else 1)

if __name__ == "__main__":
    main()
