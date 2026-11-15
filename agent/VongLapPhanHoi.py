"""
Module: VongLapPhanHoi.py (truoc day la reflection_loop.py)
Mô tả: Vòng lặp phản hồi tự sửa lỗi (Self-Healing Reflection Loop).
Bắt lỗi từ trình biên dịch / mô phỏng ModelSim và tự động vá mã Verilog để đạt 100% PASS.
"""

import os
import re
from DonDepVerilog import VerilogLinter

class ReflectionAgent:
    def __init__(self, BoMoPhong):
        self.simulator = BoMoPhong

    def diagnose_error(self, KetQuaChay):
        """Chẩn đoán nguyên nhân lỗi từ log của ModelSim / Icarus."""
        GiaiDoan = KetQuaChay.get("stage", "unknown")
        DanhSachLoi = KetQuaChay.get("errors", [])
        NhatKy = KetQuaChay.get("log", "")

        ChanDoan = {
            "stage": GiaiDoan,
            "category": "Không rõ",
            "root_cause": "",
            "suggested_fix": "",
            "file_target": None,
            "line_target": None
        }

        # Trích xuất vị trí file và số dòng lỗi nếu có
        KhopViTri = re.search(r"([A-Za-z0-9_\-\.\/\\]+\.v)\((\d+)\):\s*(.*)", NhatKy)
        if KhopViTri:
            ChanDoan["file_target"] = KhopViTri.group(1).replace("/", os.sep)
            ChanDoan["line_target"] = int(KhopViTri.group(2))
            ChanDoan["root_cause"] = KhopViTri.group(3).strip()

        if GiaiDoan == "compile":
            ChanDoan["category"] = "Lỗi cú pháp biên dịch"
            if not ChanDoan["root_cause"]:
                ChanDoan["root_cause"] = "Trình biên dịch không tìm thấy symbol, lệch độ rộng bit hoặc sai cú pháp."
            ChanDoan["suggested_fix"] = "Kiểm tra khai báo module, dấu chấm phẩy, kiểu wire/reg."

        elif GiaiDoan == "simulate":
            if "TIMEOUT" in NhatKy:
                ChanDoan["category"] = "Tắc nghẽn FSM / Hết thời gian chờ"
                ChanDoan["root_cause"] = "Máy trạng thái FSM bị treo hoặc điều kiện kích hoạt không xảy ra."
                ChanDoan["suggested_fix"] = "Kiểm tra điều kiện chuyển trạng thái và tín hiệu bắt tay."
            elif "MISMATCH" in NhatKy or "FAIL" in NhatKy:
                ChanDoan["category"] = "Sai lệch kết quả logic / Testbench báo lỗi"
                ChanDoan["root_cause"] = "Đầu ra thực tế khác với đầu ra mong đợi trong Testbench."
                ChanDoan["suggested_fix"] = "Kiểm tra phương trình logic hoặc xung nhịp enable."

        return ChanDoan

    def apply_auto_repair(self, DuongDanFile, ChanDoan, NhatKy):
        """Tự động vá lỗi vào file Verilog dựa trên chẩn đoán."""
        if not DuongDanFile or not os.path.exists(DuongDanFile):
            return False, "Không tìm thấy file cần sửa"

        with open(DuongDanFile, "r", encoding="utf-8", errors="replace") as TepTin:
            DanhSachDong = TepTin.readlines()

        DaSua = False
        NhatKySua = []

        # Sửa 0: Lỗi lệch tên module khi gọi instance
        KhopGoi = re.search(r"Instantiation of '([A-Za-z0-9_]+)' failed", NhatKy)
        if KhopGoi:
            ModuleThieu = KhopGoi.group(1)
            ThuMucHienTai = os.path.dirname(DuongDanFile)
            ThuMucSrc = os.path.join(os.path.dirname(ThuMucHienTai), "src") if "sim" in ThuMucHienTai else ThuMucHienTai
            ModuleThucTe = None
            if os.path.exists(ThuMucSrc):
                for TenTep in os.listdir(ThuMucSrc):
                    if TenTep.endswith(".v") and not TenTep.startswith("tb_"):
                        with open(os.path.join(ThuMucSrc, TenTep), "r", encoding="utf-8", errors="replace") as TepRtl:
                            KhopKhaiBao = re.search(r"module\s+([A-Za-z0-9_]+)", TepRtl.read())
                            if KhopKhaiBao and not KhopKhaiBao.group(1).startswith("tb_"):
                                ModuleThucTe = KhopKhaiBao.group(1)
                                break
            if ModuleThucTe and ModuleThucTe != ModuleThieu:
                for ChiSo, Dong in enumerate(DanhSachDong):
                    if re.search(r"\b" + re.escape(ModuleThieu) + r"\b", Dong):
                        DanhSachDong[ChiSo] = re.sub(r"\b" + re.escape(ModuleThieu) + r"\b", ModuleThucTe, DanhSachDong[ChiSo])
                        DaSua = True
                NhatKySua.append(f"Cập nhật tên module gọi '{ModuleThieu}' thành '{ModuleThucTe}'")

        # Sửa 1: Lỗi format '%!' trong lệnh $display
        if "Invalid format specifier" in NhatKy or "%!" in NhatKy:
            for ChiSo, Dong in enumerate(DanhSachDong):
                if "%!" in Dong or ("%" in Dong and "$display" in Dong):
                    DanhSachDong[ChiSo] = re.sub(r'100%!', r'100 PERCENT!', DanhSachDong[ChiSo])
                    DanhSachDong[ChiSo] = re.sub(r'100%', r'100 PERCENT', DanhSachDong[ChiSo])
                    DanhSachDong[ChiSo] = re.sub(r'%!', r' PERCENT!', DanhSachDong[ChiSo])
                    DaSua = True
            NhatKySua.append("Sửa ký tự format '%!' trong $display thành '100 PERCENT!'")

        # Sửa 2: Thiếu dấu phẩy ngăn cách các cổng
        if "syntax error, unexpected '.'" in NhatKy or "unexpected IDENTIFIER" in NhatKy:
            for ChiSo, Dong in enumerate(DanhSachDong):
                if re.search(r'\.[A-Za-z0-9_]+\s*\([^\)]*\)\s*$', Dong.strip()) and ChiSo < len(DanhSachDong) - 2:
                    DongTiepTheo = DanhSachDong[ChiSo+1].strip()
                    if DongTiepTheo.startswith("."):
                        DanhSachDong[ChiSo] = DanhSachDong[ChiSo].rstrip() + ",\n"
                        DaSua = True
            NhatKySua.append("Bổ sung dấu phẩy ngăn cách danh sách cổng")

        # Sửa 3: Chuẩn hóa tổng quát qua linter
        ToanBoMa = "".join(DanhSachDong)
        MaSach = VerilogLinter.sanitize_verilog_code(ToanBoMa)
        if MaSach != ToanBoMa:
            DanhSachDong = MaSach.splitlines(keepends=True)
            DaSua = True
            NhatKySua.append("Chuẩn hóa cú pháp và format qua VerilogLinter")

        if DaSua:
            with open(DuongDanFile, "w", encoding="utf-8") as TepTin:
                TepTin.writelines(DanhSachDong)
            return True, "; ".join(NhatKySua)

        return False, "Không có mẫu vá tự động khớp với lỗi này"

    def execute_closed_loop_flow(self, DanhSachFileVerilog, ModuleDau=None, SoLanThuToiDa=3, top_module=None, max_retries=None):
        """
        Vòng lặp tự phản hồi và sửa lỗi khép kín.
        Chạy mô phỏng -> phát hiện lỗi -> tự động vá -> kiểm thử lại.
        """
        ModuleDau = ModuleDau or top_module or "tb_top_soc"
        if max_retries is not None:
            SoLanThuToiDa = max_retries
        LanThu = 0
        KetQuaHienTai = self.simulator.run_flow(DanhSachFileVerilog, top_module=ModuleDau)

        while not KetQuaHienTai.get("success", False) and LanThu < SoLanThuToiDa:
            LanThu += 1
            print(f"\n>>> [VÒNG LẶP TỰ PHẢN HỒI REFLECTION - LẦN {LanThu}/{SoLanThuToiDa}] <<<")
            ChanDoan = self.diagnose_error(KetQuaHienTai)
            print(f" -> Phát hiện lỗi ở giai đoạn: [{ChanDoan['stage'].upper()}]")
            print(f" -> Loại lỗi: {ChanDoan['category']}")
            print(f" -> Nguyên nhân: {ChanDoan['root_cause']}")

            FileCanSua = ChanDoan.get("file_target")
            if not FileCanSua or not os.path.exists(FileCanSua):
                for FileRtl in DanhSachFileVerilog:
                    if os.path.exists(FileRtl):
                        FileCanSua = FileRtl
                        break

            if FileCanSua and os.path.exists(FileCanSua):
                print(f" -> Đang tự động vá lỗi trên: {os.path.basename(FileCanSua)}...")
                DaSua, ThongDiepSua = self.apply_auto_repair(FileCanSua, ChanDoan, KetQuaHienTai.get("log", ""))
                if DaSua:
                    print(f"    * [Hành động vá lỗi]: {ThongDiepSua}")
                    print(f"    * Đang chạy lại mô phỏng EDA...")
                    KetQuaHienTai = self.simulator.run_flow(DanhSachFileVerilog, top_module=ModuleDau)
                    if KetQuaHienTai.get("success", False):
                        print(f"\n>>> [TỰ VÁ LỖI THÀNH CÔNG]: Mạch '{ModuleDau}' đã đạt 100% PASS ở lần {LanThu}! <<<\n")
                        return KetQuaHienTai
                else:
                    print(f"    * [Thông báo]: {ThongDiepSua}")
                    break
            else:
                break

        return KetQuaHienTai
