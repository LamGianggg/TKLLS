"""
Module: reflection_loop.py
Mô tả: Vòng lặp phản hồi tự sửa lỗi (Self-Healing Reflection Loop).
Vai trò trong luồng Spec2RTL Fig. 3:
  Đóng vai trò khối "Error Diagnosis & Iterative Self-Repair" ở Pha 3.
  Khi EDASimulator trả về FAIL (compile hoặc simulate), ReflectionAgent phân tích log,
  áp dụng tuần tự các chiến lược tự vá mã Verilog (Sửa 0 -> Sửa 4), rồi kích hoạt
  chạy lại mô phỏng khép kín (tối đa max_retries lần) cho tới khi đạt 100% PASS
  hoặc không còn mẫu vá phù hợp.
"""

import os
import re
from verilog_linter import VerilogLinter

class ReflectionAgent:
    """Agent chẩn đoán log lỗi EDA và thực hiện tự vá mã Verilog trong vòng lặp kín."""

    def __init__(self, BoMoPhong):
        """Gắn instance EDASimulator để chủ động gọi chạy lại mô phỏng sau mỗi lần vá."""
        self.simulator = BoMoPhong

    def diagnose_error(self, KetQuaChay):
        """
        Chẩn đoán nguyên nhân gốc rễ (root cause) từ kết quả trả về của ModelSim / Icarus:
        - Trích xuất vị trí file & số dòng lỗi theo định dạng EDA `<file.v>(<line>): <msg>`.
        - Rẽ nhánh theo giai đoạn lỗi (`compile` vs `simulate` -> `TIMEOUT` / `MISMATCH`/`FAIL`)
          để trả về từ điển chẩn đoán phục vụ tự vá hoặc báo cáo lỗi ở Bước 5.
        """
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

        # Trích xuất vị trí file và số dòng lỗi từ log EDA (vd: sim/tb_foo.v(42): syntax error...)
        KhopViTri = re.search(r"([A-Za-z0-9_\-\.\/\\]+\.v)\((\d+)\):\s*(.*)", NhatKy)
        if KhopViTri:
            ChanDoan["file_target"] = KhopViTri.group(1).replace("/", os.sep)
            ChanDoan["line_target"] = int(KhopViTri.group(2))
            ChanDoan["root_cause"] = KhopViTri.group(3).strip()

        # Rẽ nhánh 1: Lỗi ở giai đoạn biên dịch (vlog / iverilog)
        if GiaiDoan == "compile":
            ChanDoan["category"] = "Lỗi cú pháp biên dịch"
            if not ChanDoan["root_cause"]:
                ChanDoan["root_cause"] = "Trình biên dịch không tìm thấy symbol, lệch độ rộng bit hoặc sai cú pháp."
            ChanDoan["suggested_fix"] = "Kiểm tra khai báo module, dấu chấm phẩy, kiểu wire/reg."

        # Rẽ nhánh 2: Lỗi xảy ra khi đang chạy mô phỏng (vsim / vvp)
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
        """
        Tự động vá lỗi vào file Verilog dựa trên log lỗi thực tế từ simulator.
        Áp dụng kết hợp các chiến lược tự vá theo tầng (từ đặc hiệu đến tổng quát):
          - Sửa 0 (Đồng bộ tên Module): Sửa lỗi Testbench gọi sai tên module RTL (`Instantiation failed`).
          - Sửa 1 (Format `$display`): Chuyển `%!`, `100%` không hợp lệ trong `$display` sang `PERCENT`.
          - Sửa 2 (Thiếu dấu phẩy nối cổng): Chèn `,` giữa hai dòng `.port_a(...)` và `.port_b(...)` liền nhau.
          - Sửa 3 (Chuẩn hóa Linter AST): Gọi `VerilogLinter.sanitize_verilog_code` dọn cú pháp tổng quát.
          - Sửa 4 (Tái tạo Testbench đồng bộ cổng): Khi lỗi `Port '...' not found`, gọi `TBGenerator`
            sinh lại Testbench khớp 100% danh sách cổng thực tế của RTL.
        Trả về `(True, mô_tả_vá)` nếu file có thay đổi, hoặc `(False, ...)` để dừng vòng lặp.
        """
        if not DuongDanFile or not os.path.exists(DuongDanFile):
            return False, "Không tìm thấy file cần sửa"

        with open(DuongDanFile, "r", encoding="utf-8", errors="replace") as TepTin:
            DanhSachDong = TepTin.readlines()

        DaSua = False
        NhatKySua = []

        # Chiến lược 0 (Sửa 0): Lỗi lệch tên module khi gọi instance trong Testbench
        KhopGoi = re.search(r"Instantiation of '([A-Za-z0-9_]+)' failed", NhatKy)
        if KhopGoi:
            ModuleThieu = KhopGoi.group(1)
            ThuMucHienTai = os.path.dirname(DuongDanFile)
            # Suy ra thư mục src/ chứa file RTL gốc từ vị trí file đang sửa (thường là sim/tb_*.v)
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

        # Chiến lược 1 (Sửa 1): Lỗi format '%!' hoặc '%' đứng lẻ trong lệnh $display
        if "Invalid format specifier" in NhatKy or "%!" in NhatKy:
            for ChiSo, Dong in enumerate(DanhSachDong):
                if "%!" in Dong or ("%" in Dong and "$display" in Dong):
                    DanhSachDong[ChiSo] = re.sub(r'100%!', r'100 PERCENT!', DanhSachDong[ChiSo])
                    DanhSachDong[ChiSo] = re.sub(r'100%', r'100 PERCENT', DanhSachDong[ChiSo])
                    DanhSachDong[ChiSo] = re.sub(r'%!', r' PERCENT!', DanhSachDong[ChiSo])
                    DaSua = True
            NhatKySua.append("Sửa ký tự format '%!' trong $display thành '100 PERCENT!'")

        # Chiến lược 2 (Sửa 2): Thiếu dấu phẩy ngăn cách các cổng khi nối instance (.port1(a) <thiếu ,> .port2(b))
        if "syntax error, unexpected '.'" in NhatKy or "unexpected IDENTIFIER" in NhatKy:
            for ChiSo, Dong in enumerate(DanhSachDong):
                if re.search(r'\.[A-Za-z0-9_]+\s*\([^\)]*\)\s*$', Dong.strip()) and ChiSo < len(DanhSachDong) - 2:
                    DongTiepTheo = DanhSachDong[ChiSo+1].strip()
                    if DongTiepTheo.startswith("."):
                        DanhSachDong[ChiSo] = DanhSachDong[ChiSo].rstrip() + ",\n"
                        DaSua = True
            NhatKySua.append("Bổ sung dấu phẩy ngăn cách danh sách cổng")

        # Chiến lược 3 (Sửa 3): Chuẩn hóa tổng quát qua VerilogLinter (vd: bỏ dấu ',)' thừa ở cuối danh sách cổng)
        ToanBoMa = "".join(DanhSachDong)
        MaSach = VerilogLinter.sanitize_verilog_code(ToanBoMa)
        if MaSach != ToanBoMa:
            DanhSachDong = MaSach.splitlines(keepends=True)
            DaSua = True
            NhatKySua.append("Chuẩn hóa cú pháp và format qua VerilogLinter")

        # Chiến lược 4 (Sửa 4): Lỗi lệch tên cổng khi gọi module (Port '...' not found) -> tái tạo Testbench đồng bộ cổng
        KhopCongLoi = re.search(r"Port '([A-Za-z0-9_]+)' not found in the connected module", NhatKy)
        if KhopCongLoi:
            ThuMucHienTai = os.path.dirname(DuongDanFile)
            ThuMucSrc = os.path.join(os.path.dirname(ThuMucHienTai), "src") if "sim" in ThuMucHienTai else ThuMucHienTai
            TenTb = os.path.basename(DuongDanFile)
            TenModule = TenTb.replace("tb_", "").replace(".v", "")
            TepRtl = os.path.join(ThuMucSrc, f"{TenModule}.v")
            if os.path.exists(TepRtl):
                from tb_generator import TBGenerator
                bo_tb = TBGenerator(ThuMucHienTai)
                bo_tb.generate_generic_tb(TepRtl, TenModule)
                DaSua = True
                NhatKySua.append(f"Tự động tái tạo Testbench đồng bộ 100% theo các cổng thực tế của {TenModule}.v")

        # Nếu có ít nhất 1 chiến lược vá thành công -> ghi đè lại file đích để chuẩn bị mô phỏng lại
        if DaSua:
            with open(DuongDanFile, "w", encoding="utf-8") as TepTin:
                TepTin.writelines(DanhSachDong)
            return True, "; ".join(NhatKySua)

        # Không có mẫu vá nào khớp -> báo False để execute_closed_loop_flow dừng sớm
        return False, "Không có mẫu vá tự động khớp với lỗi này"

    def execute_closed_loop_flow(self, DanhSachFileVerilog, ModuleDau=None, SoLanThuToiDa=3, top_module=None, max_retries=None):
        """
        [Spec2RTL Fig. 3 - Vòng lặp Tự Phản Hồi Khép Kín]
        Luồng thực thi:
          1) Chạy mô phỏng lần đầu qua EDASimulator. Nếu PASS ngay -> thoát vòng lặp, trả kết quả.
          2) Nếu FAIL và còn lượt thử (`LanThu < SoLanThuToiDa`):
             - Gọi `diagnose_error()` để xác định loại lỗi và `file_target`.
             - FALLBACK chọn file tồn tại đầu tiên nếu log không chỉ rõ `file_target`.
             - Gọi `apply_auto_repair()`:
               + Nếu vá được (`DaSua == True`): chạy lại mô phỏng; nếu PASS -> trả về ngay!
               + Nếu không vá được (`DaSua == False`): `break` thoát sớm, trả về FAIL để Bước 5 báo cáo.
        """
        ModuleDau = ModuleDau or top_module or "tb_top_soc"
        if max_retries is not None:
            SoLanThuToiDa = max_retries
        LanThu = 0
        # Lượt chạy mô phỏng đầu tiên (trước khi vá lỗi)
        KetQuaHienTai = self.simulator.run_flow(DanhSachFileVerilog, top_module=ModuleDau)

        # Chỉ bước vào vòng lặp tự vá khi mô phỏng FAIL và chưa vượt quá số lần thử tối đa
        while not KetQuaHienTai.get("success", False) and LanThu < SoLanThuToiDa:
            LanThu += 1
            print(f"\n>>> [VÒNG LẶP TỰ PHẢN HỒI REFLECTION - LẦN {LanThu}/{SoLanThuToiDa}] <<<")
            ChanDoan = self.diagnose_error(KetQuaHienTai)
            print(f" -> Phát hiện lỗi ở giai đoạn: [{ChanDoan['stage'].upper()}]")
            print(f" -> Loại lỗi: {ChanDoan['category']}")
            print(f" -> Nguyên nhân: {ChanDoan['root_cause']}")

            # Xác định file cần vá: ưu tiên file_target từ log EDA; FALLBACK lấy file đầu tiên tồn tại trong danh sách
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
                        # Nhánh PASS sau khi tự vá thành công
                        print(f"\n>>> [TỰ VÁ LỖI THÀNH CÔNG]: Mạch '{ModuleDau}' đã đạt 100% PASS ở lần {LanThu}! <<<\n")
                        return KetQuaHienTai
                else:
                    # Nhánh FAIL sớm: không có mẫu vá phù hợp -> tránh lặp lại vô ích
                    print(f"    * [Thông báo]: {ThongDiepSua}")
                    break
            else:
                break

        return KetQuaHienTai
