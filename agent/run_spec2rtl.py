"""
Module: run_spec2rtl.py
Mô tả: Chương trình điều phối tự động quy trình Spec2RTL & Prompt2Silicon (theo kiến trúc vòng lặp kín Spec2RTL Fig. 3).
Vai trò trong luồng Spec2RTL Fig. 3:
  Đóng vai trò Orchestrator trung tâm kết nối toàn bộ các pha:
  1. Spec Ingestion & Guard (Bước 1-2): Đọc đặc tả, kiểm tra Domain Guard & Architectural Boundary.
  2. RTL & Testbench Generation (Bước 2): Sinh mã bằng Template / AI Distilled + Hybrid RAG / Dynamic RTLGenerator.
  3. Static AST Hardware Linter (Bước 2.5): Kiểm tra tĩnh latch, dangling pin, race condition qua VerilogLinter.
  4. EDA Verification & Self-Healing Reflection Loop (Bước 3): Mô phỏng ModelSim/Icarus và tự vá lỗi tối đa 3 vòng.
  5. Hardware Packaging & Port Audit (Bước 4 - 4.5): Xuất dự án Quartus II (.qpf/.qsf), Symbol (.bsf), Sơ đồ (.bdf), Dạng sóng (.vwf), đối soát cổng và đo tài nguyên (LE, FF, Pin).
  6. Knowledge Feedback Loop: Nạp ngược các thiết kế đạt chuẩn (PASS mô phỏng + PASS Linter) vào RAG Knowledge DB.
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
from rtl_generator import RTLGenerator, RTLPortEnforcer
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
    """
    Tự động xác định thư mục gốc của dự án trên mọi máy tính và hệ điều hành.
    (Đi lên 1 cấp từ thư mục agent/ chứa file hiện tại).
    """
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def get_circuit_quartus_dir(ThuMucGoc, TenMach):
    """
    Tự động tạo và trả về thư mục riêng cho từng mạch trong quartus/<TenMach>/.
    Chuẩn hóa tên mạch (chỉ giữ chữ, số, dấu gạch dưới) để tránh lỗi đường dẫn Quartus.
    """
    if not ThuMucGoc:
        ThuMucGoc = get_base_dir()
    TenSach = re.sub(r'[^A-Za-z0-9_]', '_', str(TenMach)).strip('_') or "circuit"
    GocQuartus = os.path.join(os.path.abspath(ThuMucGoc), "quartus")
    os.makedirs(GocQuartus, exist_ok=True)
    ThuMucQuartus = os.path.join(GocQuartus, TenSach)
    os.makedirs(ThuMucQuartus, exist_ok=True)
    return ThuMucQuartus

def setup_quartus_and_bdf(ThuMucQuartus, TenDuAn, TenMach, FileRtlChinh, DanhSachRtl, DuongDanVcd=None):
    """
    [Spec2RTL Fig. 3 - Pha Đóng gói Phần cứng & Tổng hợp Backend EDA]
    Tự động tạo dự án Quartus II (.qpf/.qsf), biểu tượng khối (.bsf), sơ đồ nguyên lý (.bdf),
    file dạng sóng (.vwf) và chạy tổng hợp tĩnh quartus_map (nếu có sẵn trên máy).
    """
    os.makedirs(ThuMucQuartus, exist_ok=True)
    FileQuartusMap = find_quartus_map()

    # Đặt tên sơ đồ top là sch_<TenMach> để không trùng tên entity RTL gốc
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

    # 1. Tạo file cấu hình QPF & QSF với đường dẫn tương đối (nhắm đích FPGA Cyclone II EP2C35F672C6)
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
    # Lọc bỏ file testbench (tb_*), chỉ copy và đăng ký các file RTL tổng hợp được vào QSF
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

    # 2. Sinh Symbol BSF từ cổng RTL để có thể nhúng vào sơ đồ khối Quartus
    BoTaoBdf = BDFGenerator()
    if os.path.exists(FileRtlChinh):
        BoTaoBdf.generate_bsf_from_rtl(FileRtlChinh, FileBsf)

    # 3. Sinh sơ đồ nguyên lý BDF từ BSF (chỉ tạo khi BSF tồn tại)
    DaTaoBdf = False
    if os.path.exists(FileBsf):
        BoTaoBdf.generate_bdf_from_bsf(FileBsf, FileBdf)
        DaTaoBdf = True

    # 3.5. Sinh duy nhất 1 file dạng sóng Quartus VWF (Waveform.vwf) từ VCD mô phỏng hoặc cấu trúc cổng RTL
    FileVwf = os.path.join(ThuMucQuartus, "Waveform.vwf")
    FileVwfMachCu = os.path.join(ThuMucQuartus, f"Waveform_{TenMach}.vwf")
    if os.path.exists(FileVwfMachCu):
        try: os.remove(FileVwfMachCu)
        except Exception: pass

    BoTaoVwf = VWFGenerator()
    if os.path.exists(FileRtlChinh):
        BoTaoVwf.generate_vwf_from_rtl(FileRtlChinh, FileVwf, DuongDanVcd=DuongDanVcd)
        TenVwfTuongDoi = "Waveform.vwf"
        # Cập nhật lại QSF để tránh trùng lặp VECTOR_WAVEFORM_FILE
        DongCauHinhQsf = [dong for dong in DongCauHinhQsf if "VECTOR_WAVEFORM_FILE" not in dong]
        DongCauHinhQsf.append(f'set_global_assignment -name VECTOR_WAVEFORM_FILE "{TenVwfTuongDoi}"')
        with open(FileQsf, "w", encoding="utf-8") as TepTin:
            TepTin.write('\n'.join(DongCauHinhQsf) + '\n')

    # 4. Tổng hợp Quartus Map (nhánh có quartus_map.exe vs nhánh FALLBACK chỉ xuất file dự án)
    if FileQuartusMap and os.path.exists(FileQuartusMap):
        for ThuMucTam in ["db", "incremental_db"]:
            DuongDanTam = os.path.join(ThuMucQuartus, ThuMucTam)
            if os.path.exists(DuongDanTam):
                try: shutil.rmtree(DuongDanTam, ignore_errors=True)
                except Exception: pass
        # Xóa các file báo cáo tổng hợp cũ để tránh đọc kết quả cũ nếu quartus_map lỗi
        for FileBaoCaoCu in [f"{TenDuAn}.map.summary", f"{TenDuAn}.map.rpt"]:
            DuongDanBaoCaoCu = os.path.join(ThuMucQuartus, FileBaoCaoCu)
            if os.path.exists(DuongDanBaoCaoCu):
                try: os.remove(DuongDanBaoCaoCu)
                except Exception: pass
        try:
            subprocess.run([FileQuartusMap, TenDuAn, "-c", TenDuAn], cwd=ThuMucQuartus, capture_output=True, timeout=60)
        except Exception as e:
            print(f" -> [Lưu ý EDA]: Quá trình chạy quartus_map gặp cảnh báo: {e}")
    elif not FileQuartusMap:
        # FALLBACK: Máy không cài Quartus CLI -> vẫn giữ đủ .qpf, .bdf, .vwf để mở thủ công trong GUI
        print(f" -> [Lưu ý EDA]: Không tìm thấy quartus_map.exe trên máy. Project {TenDuAn}.qpf, sơ đồ {TenSoDoTop}.bdf và sóng Waveform.vwf đã sẵn sàng để mở trực tiếp trong Quartus II GUI.")

    return FileQpf, FileBsf, FileBdf if DaTaoBdf else None, FileVwf

def _extract_verilog_code(raw_text):
    """
    Trích xuất mã Verilog hợp lệ (có đủ cặp module/endmodule) từ output thô của mô hình AI.
    - Ưu tiên bóc từ block code markdown ```verilog ... ```.
    - Fallback: dùng regex tìm trực tiếp đoạn `module ... endmodule`.
    - Trả về None nếu không hợp lệ (kích hoạt nhánh fallback sang RTLGenerator).
    """
    if not raw_text or not isinstance(raw_text, str):
        return None
    blocks = re.findall(r"```(?:verilog|systemverilog|v)?\s*([\s\S]*?)```", raw_text, flags=re.IGNORECASE)
    for blk in blocks:
        if re.search(r"\bmodule\b", blk) and re.search(r"\bendmodule\b", blk):
            return blk.strip()
    m = re.search(r"((?:`timescale[^\n]*\n\s*)?\bmodule\b[\s\S]*?\bendmodule\b)", raw_text)
    if m:
        return m.group(1).strip()
    return None


def run_single_spec(DuongDanSpec, ThuMucGoc=None, MoGiaoDien=False, DungHarness=False, MoTrangWeb=False, DungAiChinh=False):
    """
    [Spec2RTL Fig. 3 - Pipeline Chính Cho 1 Đặc Tả]
    Thực thi toàn bộ quy trình khép kín cho một bài toán đặc tả:
      - Pha 1 (Spec Ingestion): Đọc nội dung văn bản đặc tả.
      - Pha 2 (Guards & Code Gen): Kiểm tra Domain Guard / Architectural Boundary; sinh RTL + TB
        theo Template, hoặc AI Distilled + Hybrid RAG (fallback sang RTLGenerator nếu lỗi).
      - Pha 2.5 (Static AST Linter): Dọn cú pháp và kiểm tra Latch / Dangling Pin / Race Condition.
      - Pha 3 (Simulation & Reflection Loop): Chạy ModelSim/Icarus và tự sửa lỗi vòng lặp kín.
      - Pha 4 - 4.5 (Packaging, Audit, Profiling & Knowledge Feedback): Xuất Quartus QPF/BSF/BDF/VWF,
        đối soát cổng, đo tài nguyên LE/FF và nạp ngược vào RAG DB nếu PASS cả mô phỏng lẫn Linter.
      - Pha 5 (Final Verdict): Kết luận PASS hoặc chẩn đoán lỗi FAIL.
    """
    # Pha 0: Khởi tạo các thư mục đầu ra chuẩn (src/, sim/, quartus/)
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

    # Pha 1 (Bước 1): Đọc và xem trước văn bản đặc tả đầu vào
    print(f"[Bước 1] Đang đọc và phân tích văn bản đặc tả...")
    with open(DuongDanSpec, "r", encoding="utf-8", errors="replace") as TepTin:
        NoiDungSpec = TepTin.read()
    print("-" * 80)
    print(NoiDungSpec.strip()[:350] + ("..." if len(NoiDungSpec) > 350 else ""))
    print("-" * 80)

    # Pha 2 (Bước 2): Phân tích đặc tả, kiểm tra rào chắn an toàn (Guards) và sinh mã RTL & Testbench
    print(f"\n[Bước 2] Tự động sinh mã nguồn Verilog RTL & Testbench...")
    BoSinhRtl = RTLGenerator(ThuMucSrc)
    BoSinhTb  = TBGenerator(ThuMucSim)

    BoPhanTich = SpecAnalyzer(DuongDanSpec)
    PhanLoai = BoPhanTich.classify_system()
    TenModule = BoPhanTich.extract_module_name()

    # Bảng ánh xạ các hệ thống mẫu kinh điển có sẵn bộ sinh chuyên biệt
    BangMachMau = {
        "VENDING":  ("vending_machine", "Vending_Machine", BoSinhRtl.generate_vending_machine, BoSinhTb.generate_vending_tb),
        "ELEVATOR": ("elevator_controller", "Elevator_Controller", BoSinhRtl.generate_elevator_controller, BoSinhTb.generate_elevator_tb),
        "TRAFFIC":  ("traffic_light", "Traffic_Light", BoSinhRtl.generate_traffic_light, BoSinhTb.generate_traffic_tb),
    }

    # Rẽ nhánh FAIL #1 (Domain Guard): Từ chối sớm các yêu cầu ngoài phạm vi RTL số (analog, RF, phần mềm thuần...)
    is_unsup, domain_cat, reject_reason = BoPhanTich.check_unsupported_domain()
    if is_unsup:
        print("\n" + "=" * 80)
        print("   [DOMAIN GUARD]: PHÁT HIỆN YÊU CẦU NGOÀI PHẠM VI HỆ THỐNG")
        print("=" * 80)
        print(f" -> [TRẠNG THÁI: TỪ CHỐI TỔNG HỢP / OUT-OF-DOMAIN REJECTED]")
        print(f" -> Nhóm vi mạch không hỗ trợ: {domain_cat}")
        print(f" -> Lý do kỹ thuật: {reject_reason}")
        print("=" * 80)
        print(">>> [SPEC2RTL STATUS: REJECTED (OUT OF SCOPE)] <<<\n")
        return False, 0.0, TenModule, None, {"rejected_reason": reject_reason, "category": domain_cat}

    # Rẽ nhánh FAIL #2 (Architectural Boundary Guard): Chặn sinh nguyên khối các SoC/AI NPU phức tạp
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

    # Nhánh 2A: Bài toán thuộc nhóm mạch mẫu (VENDING / ELEVATOR / TRAFFIC) -> sinh từ bộ sinh chuyên biệt nếu chưa có
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

    # Nhánh 2B: Bài toán tùy ý -> ưu tiên AI Distilled + Hybrid RAG (nếu bật cờ), FALLBACK về RTLGenerator
    else:
        # Tự động sinh mã cho bài toán tùy ý
        TenMach = TenModule
        TenModuleTb = f"tb_{TenMach}"
        TenDuAn = "".join(Tu.capitalize() for Tu in TenMach.split("_"))
        ThuMucQuartus = get_circuit_quartus_dir(ThuMucGoc, TenMach)
        FileRtl = os.path.join(ThuMucSrc, f"{TenMach}.v")
        FileTb = os.path.join(ThuMucSim, f"{TenModuleTb}.v")

        # Xóa các file sơ đồ cũ trong quartus/ để tránh dùng nhầm bản cũ khi tái sinh RTL
        for FileCu in [os.path.join(ThuMucQuartus, f"{TenMach}.bsf"), os.path.join(ThuMucQuartus, f"{TenMach}.bdf"), os.path.join(ThuMucQuartus, f"top_{TenMach}.bdf"), os.path.join(ThuMucQuartus, f"sch_{TenMach}.bdf")]:
            if os.path.exists(FileCu):
                try: os.remove(FileCu)
                except Exception: pass

        ma_rtl_ai = None
        if DungAiChinh:
            try:
                if ThuMucGoc not in sys.path:
                    sys.path.insert(0, ThuMucGoc)
                from models.run_inference import generate_verilog
                print(" -> [AI Distilled + RAG] Đang thử sinh RTL bằng mô hình AI (use_rag=True)...")
                ket_qua_ai = generate_verilog(NoiDungSpec, use_rag=True)
                ma_rtl_ai = _extract_verilog_code(ket_qua_ai)
                if ma_rtl_ai:
                    # Ép chuẩn lại danh sách cổng theo spec và lọc lỗi cú pháp cơ bản trước khi lưu
                    DanhSachCongSpec = BoPhanTich.extract_ports()
                    if DanhSachCongSpec:
                        ma_rtl_ai = RTLPortEnforcer.enforce(ma_rtl_ai, DanhSachCongSpec)
                    ma_rtl_ai = VerilogLinter.sanitize_verilog_code(ma_rtl_ai)
                    with open(FileRtl, "w", encoding="utf-8") as TepRtl:
                        TepRtl.write(ma_rtl_ai)
                    print(f" -> [AI Distilled + RAG] Đã sinh & chuẩn hóa RTL: src/{os.path.basename(FileRtl)}")
                else:
                    # FALLBACK: Output AI không có module/endmodule hợp lệ -> chuyển sang bộ sinh động
                    print(" -> [AI Distilled + RAG] Output AI chưa có module/endmodule hợp lệ -> fallback RTLGenerator...")
            except Exception as ai_err:
                # FALLBACK: Lỗi khi gọi model AI (thiếu trọng số, lỗi runtime...) -> chuyển sang bộ sinh động
                print(f" -> [AI Distilled + RAG] Không khả dụng ({ai_err}) -> fallback RTLGenerator...")
                ma_rtl_ai = None

        # Thực thi FALLBACK hoặc luồng mặc định (khi không dùng AI chính): sinh RTL từ RTLGenerator
        if not ma_rtl_ai:
            _, FileRtl = BoSinhRtl.generate_from_spec(NoiDungSpec, DuongDanSpec)
            print(f" -> [Auto-Gen Dynamic RTL] Đã sinh: src/{os.path.basename(FileRtl)}")

        # Luôn sinh Testbench tương ứng theo spec và file RTL vừa có
        _, FileTb = BoSinhTb.generate_tb_from_spec(NoiDungSpec, FileRtl, DuongDanSpec)
        print(f" -> [Auto-Gen Dynamic TB] Đã sinh: sim/{os.path.basename(FileTb)}")

        DanhSachVerilog = [FileRtl, FileTb]
        DanhSachFileRtl = [FileRtl]
        FileRtlChinh = FileRtl

    # Đồng bộ lại TenMach và TenModuleTb theo khai báo `module <name>` thực tế trong file .v (tránh lệch tên khi tạo QPF/BDF/vsim)
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

    # Pha 2.5 (Bước 2.5): Kiểm tra tĩnh AST và dọn dẹp cú pháp Verilog trước khi mô phỏng EDA
    print(f"\n[Bước 2.5] Phân tích tĩnh AST & dọn dẹp cú pháp Verilog (VerilogLinter)...")
    for FileV in DanhSachVerilog:
        VerilogLinter.sanitize_file(FileV)
    if FileRtlChinh and os.path.exists(FileRtlChinh):
        VerilogLinter.lint_file(FileRtlChinh)
    print(f" -> [VerilogLinter]: Toàn bộ {len(DanhSachVerilog)} file đã được kiểm tra và chuẩn hóa.")

    # Pha 3 (Bước 3): Mô phỏng EDA & Vòng lặp phản hồi tự sửa lỗi (Reflection Loop - Fig. 3)
    print(f"\n[Bước 3] Chạy mô phỏng EDA với vòng lặp tự phản hồi (Reflection Loop)...")
    BoMoPhong = EDASimulator(ThuMucSim)
    BoPhanHoi = ReflectionAgent(BoMoPhong)

    ThoiGianBatDau = time.time()
    # Chạy vòng lặp khép kín tối đa 3 lần tự vá lỗi (PASS trả kết quả ngay, FAIL chuyển xuống Bước 5 chẩn đoán)
    KetQuaMoPhong = BoPhanHoi.execute_closed_loop_flow(DanhSachVerilog, top_module=TenModuleTb, max_retries=3)
    ThoiGianChay = time.time() - ThoiGianBatDau

    print("\n" + "-" * 80)
    print("   KẾT QUẢ MÔ PHỎNG (SIMULATION LOG)")
    print("-" * 80)
    print(KetQuaMoPhong.get("log", "").strip())
    print("-" * 80)

    # Pha 4 (Bước 4): Đóng gói dự án Quartus II (QPF/QSF), Symbol BSF, Sơ đồ BDF và Sóng VWF
    print(f"\n[Bước 4] Tự động tạo Symbol BSF, Sơ đồ BDF, Sóng VWF & Dự án Quartus...")
    FileVcd = os.path.join(ThuMucSim, f"{TenMach}.vcd")
    FileQpf, FileBsf, FileBdf, FileVwf = setup_quartus_and_bdf(ThuMucQuartus, TenDuAn, TenMach, FileRtlChinh, DanhSachFileRtl, DuongDanVcd=FileVcd)
    print(f" -> Dự án Quartus (.qpf) : {FileQpf}")
    print(f" -> Ký hiệu Symbol (.bsf): {FileBsf}")
    if FileBdf:
        print(f" -> Sơ đồ mạch (.bdf)    : {FileBdf}")
    if FileVwf and os.path.exists(FileVwf):
        print(f" -> Dạng sóng (.vwf)     : {FileVwf}")

    # Pha 4.2 (Bước 4.2): Đối soát tính toàn vẹn cổng tín hiệu giữa Spec <-> RTL <-> BSF <-> BDF
    print(f"\n[Bước 4.2] Đối soát tính toàn vẹn cổng tín hiệu...")
    DanhSachCongSpec = BoPhanTich.extract_ports()
    PortAuditor.audit(DanhSachCongSpec, FileRtlChinh, FileBsf, FileBdf)

    FileVcd = os.path.join(ThuMucSim, f"{TenMach}.vcd")

    ThongTinModelSim = find_modelsim()
    ThuMucBinModelSim = ThongTinModelSim.get("bin_dir") if ThongTinModelSim else ""

    # Nếu người dùng truyền cờ --gui và có ModelSim, bật cửa sổ xem dạng sóng trực quan
    if MoGiaoDien and ThuMucBinModelSim:
        print(f"\n[ModelSim GUI]: Đang khởi động giao diện sóng ModelSim...")
        FileVsimExe = os.path.join(ThuMucBinModelSim, "vsim.exe")
        subprocess.Popen([FileVsimExe, "-novopt", f"work.{TenModuleTb}", "-do", "add wave -r /*; run -all; wave zoom full;"], cwd=ThuMucSim)

    # Pha 4.5 (Bước 4.5): Đo đạc mức tiêu thụ tài nguyên phần cứng (LEs, Flip-Flops, I/O Pins)
    print(f"\n[Bước 4.5] Đo đạc mức độ tiêu thụ tài nguyên phần cứng...")
    ThongSoTaiNguyen = SynthesisProfiler.profile_module(ThuMucQuartus, TenDuAn, FileRtlChinh)
    print(SynthesisProfiler.format_profiler_card(ThongSoTaiNguyen, TenMach))

    # Pha phản hồi tri thức (Knowledge Feedback Loop): Chỉ nạp ngược vào RAG DB khi ĐẠT CẢ 2 điều kiện:
    # 1) Mô phỏng passed == True  VÀ  2) Kiểm tra Linter AST không có bất kỳ lỗi nào (lint_hop_le == True)
    if KetQuaMoPhong.get("passed") is True and FileRtlChinh and os.path.exists(FileRtlChinh):
        try:
            ket_qua_lint = VerilogLinter.lint_file(FileRtlChinh)
            lint_hop_le = ket_qua_lint[0] if isinstance(ket_qua_lint, tuple) else bool(ket_qua_lint.get("valid"))
            if lint_hop_le:
                from knowledge_matcher import KnowledgeMatcher
                with open(FileRtlChinh, "r", encoding="utf-8", errors="replace") as TepRtl:
                    ma_rtl_da_kiem_chung = TepRtl.read()
                da_luu_db = KnowledgeMatcher().save_verified_design(
                    TenMach, NoiDungSpec, ma_rtl_da_kiem_chung, category=PhanLoai
                )
                if da_luu_db:
                    print(f" -> [Knowledge DB]: Đã nạp ngược thiết kế '{TenMach}' đạt chuẩn vào knowledge_base/hardware_db.json.")
        except Exception as db_err:
            print(f" -> [Knowledge DB]: Bỏ qua nạp ngược DB ({db_err}).")

    # Pha 5 (Bước 5): Rẽ nhánh đánh giá kết quả cuối cùng (PASS / FAIL)
    if KetQuaMoPhong["success"]:
        # Nhánh PASS: Trả về True cùng thời gian chạy, tên module, file BDF và thống kê tài nguyên
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
        # Nhánh FAIL: Chẩn đoán nguyên nhân lỗi chi tiết qua ReflectionAgent và trả về False
        print(f"\n>>> [SPEC2RTL STATUS: THẤT BẠI] <<<")
        ChanDoan = BoPhanHoi.diagnose_error(KetQuaMoPhong)
        print(f"Giai đoạn lỗi: {ChanDoan['stage']}")
        print(f"Phân loại lỗi: {ChanDoan['category']}")
        print(f"Nguyên nhân  : {ChanDoan['root_cause']}")
        print(f"Hướng xử lý  : {ChanDoan['suggested_fix']}")
        return False, ThoiGianChay, TenMach, None, ThongSoTaiNguyen

def get_spec_description(TenFile, ThuMucSpecs=None):
    """Lấy mô tả ngắn gọn dễ hiểu cho bài toán (dùng để hiển thị trong menu chọn tương tác)."""
    DuongDanDayDu = os.path.join(ThuMucSpecs, TenFile) if ThuMucSpecs else TenFile
    try:
        return SpecAnalyzer(DuongDanDayDu).get_friendly_description()
    except Exception:
        # FALLBACK: trả về nhãn mặc định nếu đọc/phân tích file spec lỗi
        return "Bài toán thiết kế vi mạch tùy chỉnh"

def get_benchmark_suites(ThuMucGoc):
    """Tìm kiếm và gom nhóm các bộ kiểm thử chuẩn quốc tế trong thư mục benchmarks/."""
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
    """
    Điều phối chạy hàng loạt các bài toán kiểm thử trong một bộ benchmark (hoặc tất cả 'all').
    Trả về True (PASS toàn bộ) chỉ khi 100% bài trong bộ đều đạt chuẩn.
    """
    BoKiemThu = get_benchmark_suites(ThuMucGoc)
    DanhSachChay = []
    # Điều kiện chọn bộ: 'all'/'benchmark'/'b' -> chạy cả 3 bộ; ngược lại chạy đúng 1 bộ được chỉ định
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
    """
    Hàm điều phối giao diện dòng lệnh (CLI) & menu tương tác của hệ thống Spec2RTL.
    Xử lý các nhánh chạy: Benchmark Suite / Chạy tất cả specs (--all) / Chạy 1 spec theo tên hoặc số thứ tự.
    """
    ThuMucGoc = get_base_dir()
    ThuMucSpecs = os.path.join(ThuMucGoc, "specs")

    print("=" * 80)
    print("   HỆ THỐNG TỰ ĐỘNG THIẾT KẾ VI MẠCH SPEC2RTL & PROMPT2SILICON")
    print("   Quy trình: YÊU CẦU -> SINH MÃ -> MÔ PHỎNG -> XUẤT SƠ ĐỒ QUARTUS")
    print("=" * 80)

    DanhSachSpecs = sorted([f for f in os.listdir(ThuMucSpecs) if f.endswith(".txt") or f.endswith(".md")])
    BoTienIch = get_benchmark_suites(ThuMucGoc)

    # Phân tích tham số dòng lệnh CLI
    BoPhanTichThamSo = argparse.ArgumentParser(description="Hệ thống tự động Spec2RTL")
    BoPhanTichThamSo.add_argument("spec_pos", nargs="?", default=None, help="Tên spec, số thứ tự hoặc 'all'")
    BoPhanTichThamSo.add_argument("--spec", dest="spec_flag", default=None, help="Tên spec hoặc số")
    BoPhanTichThamSo.add_argument("--all", action="store_true", help="Chạy tất cả bài toán trong specs/")
    BoPhanTichThamSo.add_argument("--gui", action="store_true", help="Mở giao diện sóng đồ họa ModelSim")
    BoPhanTichThamSo.add_argument("--web", action="store_true", help="Mở dạng sóng trên trình duyệt")
    BoPhanTichThamSo.add_argument("--harness", action="store_true", help="Sử dụng Test Harness")
    BoPhanTichThamSo.add_argument("--use-distilled", action="store_true", help="Sử dụng mô hình AI đã chưng cất kết hợp Hybrid RAG ở Bước 2")
    BoPhanTichThamSo.add_argument("--benchmark", dest="benchmark_suite", default=None, help="Chạy bộ benchmark")
    ThamSo = BoPhanTichThamSo.parse_args()

    LuaChonDauVao = ThamSo.spec_flag or ThamSo.spec_pos

    # Bảng ánh xạ từ khóa tắt cho các bộ benchmark
    BangChon = {
        "benchmark": "all", "benchmarks": "all", "bm": "all",
        "b1": "verilog_eval", "verilog_eval": "verilog_eval",
        "b2": "rtllm", "rtllm": "rtllm",
        "b3": "veriprefer", "veriprefer": "veriprefer",
    }

    # Tránh nhầm chữ 'a' (viết tắt của 'all') nếu trong specs/ có file tên a.txt / a.md
    CoSpecA = any(s.lower() in ["a", "a.txt", "a.md"] for s in DanhSachSpecs)

    # Nhánh điều phối 0: Kiểm tra xem người dùng có chọn chạy Benchmark không -> chạy và thoát theo exit code 0/1
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

    # Nếu không truyền spec hoặc --all trên CLI, hiển thị menu để người dùng chọn tương tác
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

    # Trường hợp 1: Chạy TẤT CẢ các bài toán trong specs/ rồi in bảng tổng kết LE/FF/PASS-FAIL
    if CheDoChayTatCa:
        print(f"\n>>> [CHẾ ĐỘ TỰ ĐỘNG]: TIẾN HÀNH CHẠY TẤT CẢ {len(DanhSachSpecs)} BÀI TOÁN <<<\n")
        DanhSachKetQuaTongHop = []
        for TenTep in DanhSachSpecs:
            DuongDanTep = os.path.join(ThuMucSpecs, TenTep)
            ThanhCong, ThoiGian, ThucThe, SodoBdf, ChiSo = run_single_spec(DuongDanTep, ThuMucGoc, MoGiaoDien=ThamSo.gui, DungHarness=ThamSo.harness, MoTrangWeb=ThamSo.web, DungAiChinh=ThamSo.use_distilled)
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

    # Trường hợp 2: Chạy MỘT bài toán cụ thể (phân giải theo số thứ tự, đường dẫn hoặc khớp tên gần đúng)
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
        # Thử khớp chính xác tên file (có/không đuôi .txt/.md), fallback sang tìm chuỗi con
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

    ThanhCong, ThoiGian, ThucThe, SodoBdf, ChiSo = run_single_spec(DuongDanMucTieu, ThuMucGoc, MoGiaoDien=ThamSo.gui, DungHarness=ThamSo.harness, MoTrangWeb=ThamSo.web, DungAiChinh=ThamSo.use_distilled)
    # Exit code 0 nếu PASS, 1 nếu FAIL để tích hợp CI/script tự động
    sys.exit(0 if ThanhCong else 1)

if __name__ == "__main__":
    main()
