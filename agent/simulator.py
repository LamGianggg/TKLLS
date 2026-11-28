"""
Module: simulator.py
Mô tả: Tự động điều phối mô phỏng vi mạch EDA cho Spec2RTL.
Vai trò trong luồng Spec2RTL Fig. 3:
  Đóng vai trò "Verification Engine" tại Pha 3 (Simulation & Verification).
  Cung cấp kết quả chuẩn hóa (stage, success, passed, errors, log) để ReflectionAgent
  quyết định PASS ngay hay kích hoạt vòng lặp tự sửa lỗi (Self-Healing Reflection Loop).
Thứ tự ưu tiên công cụ:
  1. ModelSim-Altera batch mode (vlib -> vlog -> vsim -c) [Ưu tiên chính]
  2. Icarus Verilog (iverilog -> vvp) [FALLBACK khi máy không có ModelSim]
  3. Báo lỗi hướng dẫn nếu cả 2 công cụ EDA đều không khả dụng
"""

import os
import re
import subprocess
import shutil
from eda_finder import find_modelsim, find_iverilog

class EDASimulator:
    """Bộ điều phối biên dịch và mô phỏng Verilog tự động (ModelSim / Icarus)."""

    def __init__(self, ThuMucMoPhong=None):
        """Khởi tạo thư mục mô phỏng sim/ và dò tìm công cụ EDA theo thứ tự ưu tiên."""
        self.sim_dir = ThuMucMoPhong or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sim"))
        os.makedirs(self.sim_dir, exist_ok=True)
        
        # 1. Dò tìm phần mềm ModelSim (ưu tiên hàng đầu vì tương thích chuẩn Altera Quartus)
        self.modelsim = find_modelsim()
        self.iverilog = None
        if not self.modelsim:
            # 2. FALLBACK: Nếu không tìm thấy ModelSim, chuyển sang dò tìm Icarus Verilog
            self.iverilog = find_iverilog()

    def run_iverilog_flow(self, DanhSachFileVerilog, ModuleDau):
        """
        Biên dịch và chạy mô phỏng bằng Icarus Verilog (luồng 2 bước: `iverilog` -> `vvp`).
        Khác với ModelSim (`vlog`/`vsim` dùng thư viện `work`), Icarus biên dịch trực tiếp tất cả
        file `.v` thành một file bytecode `.vvp` rồi thực thi bằng `vvp`.
        """
        FileVvpDauRa = os.path.join(self.sim_dir, f"{ModuleDau}.vvp")
        DuongDanTuyetDoi = [os.path.abspath(File) for File in DanhSachFileVerilog]

        # 1. Biên dịch (`iverilog -o <top>.vvp <files...>`): phát hiện lỗi cú pháp / thiếu port / thiếu module
        LenhBienDich = [self.iverilog["iverilog"], "-o", FileVvpDauRa] + DuongDanTuyetDoi
        try:
            KetQuaBienDich = subprocess.run(LenhBienDich, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            XuatBienDich = KetQuaBienDich.stdout.decode('utf-8', errors='replace') if KetQuaBienDich.stdout else ""
        except subprocess.TimeoutExpired:
            # Nhánh FAIL (Compile Timeout)
            return {
                "stage": "compile",
                "success": False,
                "errors": ["Quá trình biên dịch iverilog bị timeout sau 60 giây."],
                "log": "iverilog compile timeout (60s)"
            }
        except Exception as e:
            # Nhánh FAIL (Compile Exception)
            return {
                "stage": "compile",
                "success": False,
                "errors": [str(e)],
                "log": str(e)
            }

        # Nếu returncode != 0 -> dừng ngay ở giai đoạn compile, trả FAIL để ReflectionAgent sửa lỗi cú pháp/nối cổng
        if KetQuaBienDich.returncode != 0:
            return {
                "stage": "compile",
                "success": False,
                "errors": [XuatBienDich],
                "log": XuatBienDich
            }

        # 2. Chạy mô phỏng bằng `vvp <top>.vvp` (thực thi testbench)
        LenhMoPhong = [self.iverilog["vvp"], FileVvpDauRa]
        try:
            KetQuaMoPhong = subprocess.run(LenhMoPhong, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            KetQuaXuat = KetQuaMoPhong.stdout.decode('utf-8', errors='replace') if KetQuaMoPhong.stdout else ""
        except subprocess.TimeoutExpired:
            # Nhánh FAIL (Simulation Timeout - thường do testbench thiếu $finish hoặc FSM kẹt)
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": ["Mô phỏng vvp bị treo (timeout 60 giây - có thể do vòng lặp vô hạn hoặc thiếu $finish)."],
                "log": "vvp simulation timeout (60s)"
            }
        except Exception as e:
            # Nhánh FAIL (Simulation Exception)
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": [str(e)],
                "log": str(e)
            }

        # Phân tích log đầu ra từ vvp để phân định PASS / FAIL
        TuKhoaLoi = [
            "** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]",
            "[HARNESS WATCHDOG TIMEOUT]", "[FAIL]", "FAIL:", "FAILED", "TEST FAILED", "MISMATCH"
        ]
        CoLoi = any(TuKhoa in KetQuaXuat for TuKhoa in TuKhoaLoi)
        KhopThatBai = re.search(r"Failed Assertions\s*:\s*([1-9]\d*)", KetQuaXuat)
        if KhopThatBai:
            CoLoi = True

        # Điều kiện PASS: có dấu hiệu thành công hoặc kết thúc sạch ($finish, exit 0) VÀ tuyệt đối không có bất kỳ lỗi nào
        ThanhCong = any(DauHieu in KetQuaXuat for DauHieu in ["[SUCCESS]", "PASSED", "Passed", "All tests passed", "TEST PASSED", "[HARNESS PASS]"])
        KetThucSach = KetQuaMoPhong.returncode == 0 and ("$finish" in KetQuaXuat or ThanhCong) and not CoLoi
        DatChuan = (ThanhCong or KetThucSach) and not CoLoi
        DanhSachLoi = [Dong.strip() for Dong in KetQuaXuat.splitlines() if any(TuKhoa in Dong for TuKhoa in TuKhoaLoi)]

        return {
            "stage": "simulate",
            "success": DatChuan,
            "passed": DatChuan,
            "errors": DanhSachLoi,
            "log": KetQuaXuat
        }

    def init_work_library(self):
        """Khởi tạo thư viện biên dịch `work` cho ModelSim (`vlib work`) nếu thư mục `sim/work` chưa tồn tại."""
        ThuMucWork = os.path.join(self.sim_dir, "work")
        if not os.path.exists(ThuMucWork):
            LenhVlib = self.modelsim["vlib"]
            try:
                subprocess.run([LenhVlib, "work"], cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            except Exception as e:
                pass

    def run_modelsim_flow(self, DanhSachFileVerilog, ModuleDau):
        """
        Biên dịch và chạy mô phỏng bằng ModelSim-Altera batch mode (luồng `vlib` -> `vlog` -> `vsim -c`).
        Điểm khác biệt so với Icarus (`iverilog`/`vvp`):
          - Phải khởi tạo thư viện `work` trước, rồi dùng `vlog -work work` biên dịch mã Verilog vào `work`.
          - Chạy `vsim -c -do "run -all; quit" work.<ModuleDau>` để mô phỏng không GUI và tự thoát.
          - Log của ModelSim có các định dạng riêng như `** Error:`, `** Fatal:`, `Simulation complete`.
        """
        self.init_work_library()
        DuongDanTuyetDoi = [os.path.abspath(File) for File in DanhSachFileVerilog]
        
        # 1. Biên dịch `vlog -work work <files...>`
        LenhVlog = self.modelsim["vlog"]
        LenhBienDich = [LenhVlog, "-work", "work"] + DuongDanTuyetDoi
        try:
            KetQuaBienDich = subprocess.run(LenhBienDich, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            KetQuaXuatVlog = KetQuaBienDich.stdout.decode('utf-8', errors='replace') if KetQuaBienDich.stdout else ""
        except subprocess.TimeoutExpired:
            # Nhánh FAIL (Compile Timeout)
            return {
                "stage": "compile",
                "success": False,
                "errors": ["Quá trình biên dịch vlog bị timeout sau 60 giây."],
                "log": "vlog compile timeout (60s)"
            }
        except Exception as e:
            # Nhánh FAIL (Compile Exception)
            return {
                "stage": "compile",
                "success": False,
                "errors": [str(e)],
                "log": str(e)
            }

        # Nếu vlog trả mã lỗi != 0 -> trích xuất các dòng ** Error: / ** Fatal: trả về FAIL ở stage compile
        if KetQuaBienDich.returncode != 0:
            DanhSachLoi = [Dong.strip() for Dong in KetQuaXuatVlog.splitlines() if "** Error:" in Dong or "** Fatal:" in Dong or "Error:" in Dong]
            if not DanhSachLoi and KetQuaXuatVlog.strip():
                DanhSachLoi = [KetQuaXuatVlog.strip()]
            return {
                "stage": "compile",
                "success": False,
                "errors": DanhSachLoi,
                "log": KetQuaXuatVlog
            }

        # 2. Chạy mô phỏng `vsim -c` (chế độ dòng lệnh headless, chạy tới $finish rồi quit)
        LenhVsim = self.modelsim["vsim"]
        LenhMoPhong = [LenhVsim, "-c", "-do", "run -all; quit", f"work.{ModuleDau}"]
        try:
            KetQuaMoPhong = subprocess.run(LenhMoPhong, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            KetQuaXuatVsim = KetQuaMoPhong.stdout.decode('utf-8', errors='replace') if KetQuaMoPhong.stdout else ""
        except subprocess.TimeoutExpired:
            # Nhánh FAIL (Simulation Timeout)
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": ["Mô phỏng vsim bị treo (timeout 60 giây - có thể do vòng lặp vô hạn hoặc thiếu $finish)."],
                "log": "vsim simulation timeout (60s)"
            }
        except Exception as e:
            # Nhánh FAIL (Simulation Exception)
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": [str(e)],
                "log": str(e)
            }

        # Phân tích log đầu ra của vsim để phân định PASS / FAIL
        TuKhoaLoi = [
            "** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]",
            "[HARNESS WATCHDOG TIMEOUT]", "[FAIL]", "FAIL:", "FAILED", "TEST FAILED", "MISMATCH"
        ]
        CoLoi = any(TuKhoa in KetQuaXuatVsim for TuKhoa in TuKhoaLoi)
        KhopThatBai = re.search(r"Failed Assertions\s*:\s*([1-9]\d*)", KetQuaXuatVsim)
        if KhopThatBai:
            CoLoi = True

        # Điều kiện PASS: có marker PASS hoặc kết thúc sạch (Simulation complete / $finish / returncode 0) và không có CoLoi
        ThanhCong = any(DauHieu in KetQuaXuatVsim for DauHieu in ["[SUCCESS]", "PASSED", "Passed", "passed", "TEST PASSED", "All tests passed", "[HARNESS PASS]"])
        KetThucSach = ("$finish" in KetQuaXuatVsim or "Simulation complete" in KetQuaXuatVsim or KetQuaMoPhong.returncode == 0) and not CoLoi and ("$finish" in KetQuaXuatVsim or ThanhCong)

        DatChuan = (ThanhCong or KetThucSach) and not CoLoi
        DanhSachLoi = [Dong.strip() for Dong in KetQuaXuatVsim.splitlines() if any(TuKhoa in Dong for TuKhoa in TuKhoaLoi)]

        return {
            "stage": "simulate",
            "success": DatChuan,
            "passed": DatChuan,
            "errors": DanhSachLoi,
            "log": KetQuaXuatVsim
        }

    def run_flow(self, DanhSachFileVerilog, ModuleDau=None, top_module=None):
        """
        Bộ điều phối chọn trình mô phỏng theo thứ tự ưu tiên:
          1) Có ModelSim -> chạy `run_modelsim_flow` (`vlog`/`vsim`).
          2) Không có ModelSim nhưng có Icarus -> FALLBACK sang `run_iverilog_flow` (`iverilog`/`vvp`).
          3) Không có cả hai -> trả FAIL kèm hướng dẫn cài đặt công cụ EDA.
        """
        ModuleDau = ModuleDau or top_module or "tb_top_soc"
        if self.modelsim:
            return self.run_modelsim_flow(DanhSachFileVerilog, ModuleDau)
        elif self.iverilog:
            return self.run_iverilog_flow(DanhSachFileVerilog, ModuleDau)
        else:
            # Nhánh FAIL (Missing EDA Tool)
            ThongBaoLoi = "Không tìm thấy công cụ mô phỏng phần cứng (ModelSim hoặc Icarus Verilog)."
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": [ThongBaoLoi],
                "log": f"[THÔNG BÁO EDA]: {ThongBaoLoi} Vui lòng cài đặt ModelSim hoặc Icarus Verilog để chạy mô phỏng."
            }
