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

    def run_iverilog_flow(self, DanhSachFileVerilog, ModuleDau):
        """Biên dịch và chạy mô phỏng bằng Icarus Verilog."""
        FileVvpDauRa = os.path.join(self.sim_dir, f"{ModuleDau}.vvp")
        DuongDanTuyetDoi = [os.path.abspath(File) for File in DanhSachFileVerilog]

        # 1. Biên dịch
        LenhBienDich = [self.iverilog["iverilog"], "-o", FileVvpDauRa] + DuongDanTuyetDoi
        try:
            KetQuaBienDich = subprocess.run(LenhBienDich, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            XuatBienDich = KetQuaBienDich.stdout.decode('utf-8', errors='replace') if KetQuaBienDich.stdout else ""
        except subprocess.TimeoutExpired:
            return {
                "stage": "compile",
                "success": False,
                "errors": ["Quá trình biên dịch iverilog bị timeout sau 60 giây."],
                "log": "iverilog compile timeout (60s)"
            }
        except Exception as e:
            return {
                "stage": "compile",
                "success": False,
                "errors": [str(e)],
                "log": str(e)
            }

        if KetQuaBienDich.returncode != 0:
            return {
                "stage": "compile",
                "success": False,
                "errors": [XuatBienDich],
                "log": XuatBienDich
            }

        # 2. Chạy mô phỏng bằng vvp
        LenhMoPhong = [self.iverilog["vvp"], FileVvpDauRa]
        try:
            KetQuaMoPhong = subprocess.run(LenhMoPhong, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            KetQuaXuat = KetQuaMoPhong.stdout.decode('utf-8', errors='replace') if KetQuaMoPhong.stdout else ""
        except subprocess.TimeoutExpired:
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": ["Mô phỏng vvp bị treo (timeout 60 giây - có thể do vòng lặp vô hạn hoặc thiếu $finish)."],
                "log": "vvp simulation timeout (60s)"
            }
        except Exception as e:
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": [str(e)],
                "log": str(e)
            }

        TuKhoaLoi = [
            "** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]",
            "[HARNESS WATCHDOG TIMEOUT]", "[FAIL]", "FAIL:", "FAILED", "TEST FAILED", "MISMATCH"
        ]
        CoLoi = any(TuKhoa in KetQuaXuat for TuKhoa in TuKhoaLoi)
        KhopThatBai = re.search(r"Failed Assertions\s*:\s*([1-9]\d*)", KetQuaXuat)
        if KhopThatBai:
            CoLoi = True

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
        """Khởi tạo thư viện work cho ModelSim nếu chưa có."""
        ThuMucWork = os.path.join(self.sim_dir, "work")
        if not os.path.exists(ThuMucWork):
            LenhVlib = self.modelsim["vlib"]
            try:
                subprocess.run([LenhVlib, "work"], cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            except Exception as e:
                pass

    def run_modelsim_flow(self, DanhSachFileVerilog, ModuleDau):
        """Biên dịch và chạy mô phỏng bằng ModelSim."""
        self.init_work_library()
        DuongDanTuyetDoi = [os.path.abspath(File) for File in DanhSachFileVerilog]
        
        # 1. Biên dịch vlog
        LenhVlog = self.modelsim["vlog"]
        LenhBienDich = [LenhVlog, "-work", "work"] + DuongDanTuyetDoi
        try:
            KetQuaBienDich = subprocess.run(LenhBienDich, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            KetQuaXuatVlog = KetQuaBienDich.stdout.decode('utf-8', errors='replace') if KetQuaBienDich.stdout else ""
        except subprocess.TimeoutExpired:
            return {
                "stage": "compile",
                "success": False,
                "errors": ["Quá trình biên dịch vlog bị timeout sau 60 giây."],
                "log": "vlog compile timeout (60s)"
            }
        except Exception as e:
            return {
                "stage": "compile",
                "success": False,
                "errors": [str(e)],
                "log": str(e)
            }

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

        # 2. Chạy mô phỏng vsim
        LenhVsim = self.modelsim["vsim"]
        LenhMoPhong = [LenhVsim, "-c", "-do", "run -all; quit", f"work.{ModuleDau}"]
        try:
            KetQuaMoPhong = subprocess.run(LenhMoPhong, cwd=self.sim_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            KetQuaXuatVsim = KetQuaMoPhong.stdout.decode('utf-8', errors='replace') if KetQuaMoPhong.stdout else ""
        except subprocess.TimeoutExpired:
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": ["Mô phỏng vsim bị treo (timeout 60 giây - có thể do vòng lặp vô hạn hoặc thiếu $finish)."],
                "log": "vsim simulation timeout (60s)"
            }
        except Exception as e:
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": [str(e)],
                "log": str(e)
            }

        TuKhoaLoi = [
            "** Error:", "** Fatal:", "Error loading design", "[ERROR]", "[HARNESS FAIL]",
            "[HARNESS WATCHDOG TIMEOUT]", "[FAIL]", "FAIL:", "FAILED", "TEST FAILED", "MISMATCH"
        ]
        CoLoi = any(TuKhoa in KetQuaXuatVsim for TuKhoa in TuKhoaLoi)
        KhopThatBai = re.search(r"Failed Assertions\s*:\s*([1-9]\d*)", KetQuaXuatVsim)
        if KhopThatBai:
            CoLoi = True

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
        """Điều phối mô phỏng tự động chọn ModelSim, Icarus hoặc Python dự phòng."""
        ModuleDau = ModuleDau or top_module or "tb_top_soc"
        if self.modelsim:
            return self.run_modelsim_flow(DanhSachFileVerilog, ModuleDau)
        elif self.iverilog:
            return self.run_iverilog_flow(DanhSachFileVerilog, ModuleDau)
        else:
            ThongBaoLoi = "Không tìm thấy công cụ mô phỏng phần cứng (ModelSim hoặc Icarus Verilog)."
            return {
                "stage": "simulate",
                "success": False,
                "passed": False,
                "errors": [ThongBaoLoi],
                "log": f"[THÔNG BÁO EDA]: {ThongBaoLoi} Vui lòng cài đặt ModelSim hoặc Icarus Verilog để chạy mô phỏng."
            }
