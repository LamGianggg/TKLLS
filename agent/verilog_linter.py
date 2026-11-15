"""
Module: verilog_linter.py
Mô tả: Bộ tiền kiểm tra và dọn dẹp cú pháp Verilog trước khi biên dịch EDA.
Tự động sửa lỗi dấu phẩy thừa, format chuỗi % và kiểm tra cân bằng begin/end.
"""

import re
import os

class VerilogLinter:
    """Bộ kiểm tra tĩnh và chuẩn hóa cú pháp Verilog RTL và Testbench."""

    @staticmethod
    def sanitize_verilog_code(MaNguon):
        """Dọn dẹp các lỗi cú pháp phổ biến trong mã Verilog."""
        # 1. Sửa ký tự '%' chưa escape trong chuỗi $display
        def SuaKyTuPhanTram(Khop):
            NoiDung = Khop.group(0)
            NoiDung = re.sub(r'%!', r' PERCENT!', NoiDung)
            NoiDung = re.sub(r'100%(?!%|[0-9a-zA-Z])', r'100 PERCENT', NoiDung)
            return NoiDung

        MaNguon = re.sub(r'\$display\s*\([^;]+;', SuaKyTuPhanTram, MaNguon)

        # 2. Xóa dấu phẩy thừa ở cuối danh sách cổng module
        MaNguon = re.sub(r',\s*\)', r'\n)', MaNguon)

        return MaNguon

    @staticmethod
    def sanitize_file(DuongDanFile):
        """Đọc, chuẩn hóa cú pháp và lưu lại file Verilog nếu có lỗi."""
        if not os.path.exists(DuongDanFile):
            return False, "File không tồn tại"

        with open(DuongDanFile, "r", encoding="utf-8", errors="replace") as TepTin:
            NoiDungGoc = TepTin.read()

        NoiDungSach = VerilogLinter.sanitize_verilog_code(NoiDungGoc)

        if NoiDungSach != NoiDungGoc:
            with open(DuongDanFile, "w", encoding="utf-8") as TepTin:
                TepTin.write(NoiDungSach)
            return True, "Đã chuẩn hóa cú pháp (dấu phẩy thừa, ký tự format)"
        return False, "Chuẩn cú pháp"

    @staticmethod
    def lint_check(MaNguon):
        """Kiểm tra tĩnh cấu trúc khối lệnh begin/end, case/endcase, module/endmodule."""
        DanhSachLoi = []

        # 1. Kiểm tra cặp begin/end
        SoLuongBegin = len(re.findall(r'\bbegin\b', MaNguon))
        SoLuongEnd = len(re.findall(r'\bend\b', MaNguon))
        if SoLuongBegin != SoLuongEnd:
            DanhSachLoi.append(f"Lệch số lượng khối: {SoLuongBegin} 'begin' so với {SoLuongEnd} 'end'")

        # 2. Kiểm tra cặp case/endcase
        SoLuongCase = len(re.findall(r'\bcase\b|\bcasex\b|\bcasez\b', MaNguon))
        SoLuongEndcase = len(re.findall(r'\bendcase\b', MaNguon))
        if SoLuongCase != SoLuongEndcase:
            DanhSachLoi.append(f"Lệch số lượng case: {SoLuongCase} 'case' so với {SoLuongEndcase} 'endcase'")

        # 3. Kiểm tra cặp module/endmodule
        SoLuongModule = len(re.findall(r'\bmodule\b', MaNguon))
        SoLuongEndmodule = len(re.findall(r'\bendmodule\b', MaNguon))
        if SoLuongModule != SoLuongEndmodule:
            DanhSachLoi.append(f"Lệch module: {SoLuongModule} 'module' so với {SoLuongEndmodule} 'endmodule'")

        # 4. Kiểm tra format không hợp lệ trong $display
        if re.search(r'\$display\s*\([^"]*"[^"]*%![^"]*"', MaNguon):
            DanhSachLoi.append("Phát hiện format '%!' không hợp lệ trong lệnh $display")

        return {
            "valid": len(DanhSachLoi) == 0,
            "issues": DanhSachLoi
        }

if __name__ == "__main__":
    MauThu = '''module test; initial begin $display("100%!"); end endmodule'''
    KetQuaSach = VerilogLinter.sanitize_verilog_code(MauThu)
    print("Mã sau dọn dẹp:", KetQuaSach)
    print("Kết quả kiểm tra:", VerilogLinter.lint_check(KetQuaSach))
