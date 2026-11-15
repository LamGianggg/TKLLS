"""
Module: simulator.py
Mô tả: Tự động điều phối mô phỏng vi mạch EDA cho Spec2RTL.
Hỗ trợ:
  1. ModelSim-Altera batch mode (vlog, vsim -c)
  2. Icarus Verilog (iverilog, vvp)
  3. Bộ kiểm thử Python dự phòng độc lập
"""

import os
import re
import subprocess
import shutil
from eda_finder import find_modelsim, find_iverilog

class EDASimulator:
    def __init__(self, ThuMucMoPhong=None):
        self.sim_dir = ThuMucMoPhong or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sim"))
        os.makedirs(self.sim_dir, exist_ok=True)
        
        # 1. Dò tìm phần mềm ModelSim
        self.modelsim = find_modelsim()
        self.iverilog = None
        if not self.modelsim:
            # 2. Dò tìm Icarus Verilog dự phòng
            self.iverilog = find_iverilog()

    def run_builtin_python_verifier(self, ModuleDau):
        """Mô phỏng dự phòng: thông báo người dùng cài đặt ModelSim hoặc Icarus."""
        ThongBaoLoi = "Cần cài đặt ModelSim hoặc Icarus Verilog để chạy mô phỏng phần cứng thực tế."
        return {
            "stage": "simulate",
            "success": False,
            "passed": False,
            "errors": [ThongBaoLoi],
            "log": f"[THÔNG BÁO EDA]: Không tìm thấy ModelSim hoặc Icarus Verilog. {ThongBaoLoi}"
        }

    def run_iverilog_flow(self, DanhSachFileVerilog, ModuleDau):
        """Biên dịch và chạy mô phỏng bằng Icarus Verilog."""
        FileVvpDauRa = os.path.join(self.sim_dir, f"{ModuleDau}.vvp")
        DuongDanTuyetDoi = [os.path.abspath(File) for File in DanhSachFileVerilog]

        # 1. Biên dịch
        LenhBienDich = [self.iverilog["iverilog"], "-o", FileVvpDauRa] + DuongDanTuyetDoi
        KetQuaBienDich = subprocess.run(LenhBienDich, cwd=self.sim_dir, capture_output=True)
        if KetQuaBienDich.returncode != 0:
            return {
                "stage": "compile",
                "success": False,
                "errors": [KetQuaBienDich.stderr.decode('utf-8', errors='replace')],
                "log": KetQuaBienDich.stderr.decode('utf-8', errors='replace')
            }

        # 2. Chạy mô phỏng bằng vvp
        LenhMoPhong = [self.iverilog["vvp"], FileVvpDauRa]
        KetQuaMoPhong = subprocess.run(LenhMoPhong, cwd=self.sim_dir, capture_output=True)
        KetQuaXuat = KetQuaMoPhong.stdout.decode('utf-8', errors='replace') if KetQuaMoPhong.stdout else ""
        CoLoi = any(TuKhoa in KetQuaXuat for TuKhoa in ["ERROR", "Error", "FAIL", "Fatal", "assert failed", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])
        ThanhCong = any(DauHieu in KetQuaXuat for DauHieu in ["[SUCCESS]", "PASSED", "Passed", "All tests passed", "TEST PASSED", "[HARNESS PASS]"])
        KetThucSach = KetQuaMoPhong.returncode == 0 and ("$finish" in KetQuaXuat or ThanhCong) and not CoLoi
        DatChuan = (ThanhCong or KetThucSach) and not CoLoi
        DanhSachLoi = [Dong.strip() for Dong in KetQuaXuat.splitlines() if any(TuKhoa in Dong for TuKhoa in ["ERROR", "Error", "FAIL", "Fatal", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])]

        return {
            "stage": "simulate",
            "success": DatChuan,
            "passed": DatChuan,
            "errors": DanhSachLoi,
            "log": KetQuaXuat
        }

    def init_work_library(self):
        """Khởi tạo thư viện work cho ModelSim nếu chưa có."""
        ThuMucWork = os.path.join(self.sim_dir, "work")
        if not os.path.exists(ThuMucWork):
            LenhVlib = self.modelsim["vlib"]
            subprocess.run([LenhVlib, "work"], cwd=self.sim_dir, capture_output=True, check=True)

    def run_modelsim_flow(self, DanhSachFileVerilog, ModuleDau):
        """Biên dịch và chạy mô phỏng bằng ModelSim."""
        self.init_work_library()
        DuongDanTuyetDoi = [os.path.abspath(File) for File in DanhSachFileVerilog]
        
        # 1. Biên dịch vlog
        LenhVlog = self.modelsim["vlog"]
        LenhBienDich = [LenhVlog, "-work", "work"] + DuongDanTuyetDoi
        KetQuaBienDich = subprocess.run(LenhBienDich, cwd=self.sim_dir, capture_output=True)
        KetQuaXuatVlog = KetQuaBienDich.stdout.decode('utf-8', errors='replace') if KetQuaBienDich.stdout else ""
        if KetQuaBienDich.returncode != 0:
            DanhSachLoi = [Dong.strip() for Dong in KetQuaXuatVlog.splitlines() if "** Error:" in Dong or "** Fatal:" in Dong]
            return {
                "stage": "compile",
                "success": False,
                "errors": DanhSachLoi,
                "log": KetQuaXuatVlog
            }

        # 2. Chạy mô phỏng vsim
        LenhVsim = self.modelsim["vsim"]
        LenhMoPhong = [LenhVsim, "-c", "-do", "log -r /*; run -all; quit", f"work.{ModuleDau}"]
        KetQuaMoPhong = subprocess.run(LenhMoPhong, cwd=self.sim_dir, capture_output=True)
        KetQuaXuatVsim = KetQuaMoPhong.stdout.decode('utf-8', errors='replace') if KetQuaMoPhong.stdout else ""

        CoLoi = any(TuKhoa in KetQuaXuatVsim for TuKhoa in ["** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])
        KhopThatBai = re.search(r"Failed Assertions\s*:\s*([1-9]\d*)", KetQuaXuatVsim)
        if KhopThatBai:
            CoLoi = True

        ThanhCong = any(DauHieu in KetQuaXuatVsim for DauHieu in ["[SUCCESS]", "PASSED", "Passed", "passed", "TEST PASSED", "All tests passed", "[HARNESS PASS]"])
        KetThucSach = ("$finish" in KetQuaXuatVsim or "Simulation complete" in KetQuaXuatVsim or KetQuaMoPhong.returncode == 0) and not CoLoi and ("$finish" in KetQuaXuatVsim or ThanhCong)

        DatChuan = (ThanhCong or KetThucSach) and not CoLoi
        DanhSachLoi = [Dong.strip() for Dong in KetQuaXuatVsim.splitlines() if any(TuKhoa in Dong for TuKhoa in ["** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]", "[HARNESS WATCHDOG TIMEOUT]"])]

        return {
            "stage": "simulate",
            "success": DatChuan,
            "passed": DatChuan,
            "errors": DanhSachLoi,
            "log": KetQuaXuatVsim
        }

    def run_flow(self, DanhSachFileVerilog, ModuleDau=None, top_module=None):
        """Điều phối mô phỏng tự động chọn ModelSim, Icarus hoặc Python dự phòng."""
        ModuleDau = ModuleDau or top_module or "tb_top_soc"
        if self.modelsim:
            return self.run_modelsim_flow(DanhSachFileVerilog, ModuleDau)
        elif self.iverilog:
            return self.run_iverilog_flow(DanhSachFileVerilog, ModuleDau)
        else:
            return self.run_builtin_python_verifier(ModuleDau)
