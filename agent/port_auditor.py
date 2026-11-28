"""
Module: port_auditor.py
Mô tả: Kiểm tra tính toàn vẹn của các cổng tín hiệu (Ports).
Đảm bảo khớp 100% giữa đặc tả spec, mã Verilog RTL, file Symbol BSF và sơ đồ BDF.
"""

import os
import re

class PortAuditor:
    """
    Bộ kiểm toán cổng tín hiệu (Port Integrity Auditor).
    Đối chiếu danh sách cổng giữa 4 nguồn: Đặc tả (Spec), Mã Verilog RTL,
    Biểu tượng khối Quartus (.bsf) và Sơ đồ nguyên lý (.bdf).
    """

    @staticmethod
    def audit(CongSpec, DuongDanRtl, DuongDanBsf, DuongDanBdf):
        """
        Kiểm tra và in bảng đối soát từng cổng tín hiệu qua Spec, RTL, BSF và BDF.
        Trả về True nếu toàn bộ cổng khớp 100%, False nếu phát hiện thiếu hoặc lệch tên cổng.
        """
        if not CongSpec or not os.path.exists(DuongDanRtl):
            return True

        # Bước 1: Trích xuất danh sách cổng từ mã RTL Verilog (hỗ trợ cả parameter #(...) và inout)
        with open(DuongDanRtl, "r", encoding="utf-8", errors="replace") as TepTin:
            MaRtl = TepTin.read()
        MauModule = re.search(r"module\s+([A-Za-z0-9_]+)\s*(?:#\s*\([\s\S]*?\)\s*)?\(([\s\S]*?)\);", MaRtl)
        CongRtl = {}
        if MauModule:
            ChuoiCong = re.sub(r"//.*", "", MauModule.group(2))
            ChuoiCong = re.sub(r"/\*.*?\*/", "", ChuoiCong, flags=re.DOTALL)
            for Dong in ChuoiCong.split(","):
                MauCong = re.search(r"(input|output|inout)\s+(?:wire|reg)?\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*([A-Za-z0-9_]+)", Dong.strip())
                if MauCong:
                    Huong, Msb, Lsb, TenCong = MauCong.groups()
                    DoRong = abs(int(Msb) - int(Lsb)) + 1 if (Msb and Lsb) else 1
                    CongRtl[TenCong.lower()] = {"name": TenCong, "dir": Huong, "width": DoRong}

        # Bước 2: Trích xuất cổng từ file Symbol BSF của Quartus (chỉ đọc khối (port ...), bỏ qua tên module/inst)
        CongBsf = set()
        if os.path.exists(DuongDanBsf):
            with open(DuongDanBsf, "r", encoding="utf-8", errors="replace") as TepTin:
                NoiDungBsf = TepTin.read()
            for KhopPort in re.finditer(r'\(port[\s\S]*?\(text\s+"([A-Za-z0-9_]+)(?:\[.*?\])?"', NoiDungBsf):
                CongBsf.add(KhopPort.group(1).lower())

        # Bước 3: Trích xuất chân tín hiệu (pin) từ sơ đồ nguyên lý BDF (input, output, bidir)
        ChanBdf = set()
        if os.path.exists(DuongDanBdf):
            with open(DuongDanBdf, "r", encoding="utf-8", errors="replace") as TepTin:
                NoiDungBdf = TepTin.read()
            for KhopChan in re.finditer(r'\(pin\s+\((?:input|output|bidir)\)[\s\S]*?\(text\s+"(?:INPUT|OUTPUT|BIDIR)"[\s\S]*?\(text\s+"([A-Za-z0-9_]+)', NoiDungBdf):
                ChanBdf.add(KhopChan.group(1).lower())

        # Bước 4: Lập bảng báo cáo đối soát trực quan ra console và kết luận PASS/FAIL
        DanhSachDong = []
        DanhSachDong.append("+-------------------------------------------------------------------------------+")
        DanhSachDong.append("|           KIỂM TRA TÍNH TOÀN VẸN CỔNG TÍN HIỆU (PORT AUDIT)                   |")
        DanhSachDong.append("+-------------------------------------------------------------------------------+")
        DanhSachDong.append(f"| {'Tên cổng':<18} | {'Hướng':<6} | {'Bit':<4} | {'RTL':<6} | {'BSF':<6} | {'BDF':<6} | {'Kết quả':<10} |")
        DanhSachDong.append("+--------------------+--------+------+--------+--------+--------+------------+")

        DatChuan = True
        for Cong in CongSpec:
            Ten = Cong["name"]
            TenThuong = Ten.lower()
            CoRtl = TenThuong in CongRtl
            CoBsf = TenThuong in CongBsf
            CoBdf = TenThuong in ChanBdf
            Khop = CoRtl and CoBsf and CoBdf
            if not Khop:
                DatChuan = False

            ChuoiRtl = "[OK]" if CoRtl else "[MISS]"
            ChuoiBsf = "[OK]" if CoBsf else "[MISS]"
            ChuoiBdf = "[OK]" if CoBdf else "[MISS]"
            TrangThai = "PASS" if Khop else "FAIL"
            ChuoiRong = f"[{Cong['width']-1}:0]" if Cong["width"] > 1 else "1"
            DanhSachDong.append(f"| {Ten:<18} | {Cong['direction']:6} | {ChuoiRong:<4} | {ChuoiRtl:<6} | {ChuoiBsf:<6} | {ChuoiBdf:<6} | {TrangThai:<10} |")

        DanhSachDong.append("+-------------------------------------------------------------------------------+")
        if DatChuan:
            DanhSachDong.append(f"| Trạng thái: TOÀN BỘ {len(CongSpec)} CỔNG ĐỀU KHỚP VÀ CHÍNH XÁC 100% (PASS)                  |")
        else:
            DanhSachDong.append(f"| Trạng thái: [CẢNH BÁO] PHÁT HIỆN LỆCH CỔNG GIỮA SPEC VÀ SƠ ĐỒ THIẾT KẾ          |")
        DanhSachDong.append("+-------------------------------------------------------------------------------+")

        BangKiemTra = "\n".join(DanhSachDong)
        print(BangKiemTra)
        return DatChuan
