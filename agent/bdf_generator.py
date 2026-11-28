"""
Module: bdf_generator.py
Mô tả: Tự động tạo sơ đồ nguyên lý BDF (Block Design File) và Symbol BSF.
Tạo sơ đồ mạch chuẩn Quartus II 13.0sp1 có thể mở, chỉnh sửa và tổng hợp trực tiếp.
"""

import os
import re

class BDFGenerator:
    """
    Bộ sinh biểu tượng khối (.bsf) và sơ đồ nguyên lý (.bdf) chuẩn Quartus II 13.0sp1.
    Cho phép chuyển trực tiếp mã Verilog RTL thành sơ đồ khối có chân INPUT/OUTPUT/BIDIR
    và dây nối (connector) để mở ngay trong Block Editor của Quartus.
    """

    def __init__(self):
        """Khởi tạo bộ sinh BDF/BSF."""
        pass

    def generate_bsf_from_rtl(self, DuongDanRtl, DuongDanBsf):
        """
        Bước 1 trong quy trình Quartus Schematic:
        Phân tích header module Verilog RTL để tách cổng vào/ra (đơn bit và bus),
        tính kích thước hình học theo lưới 8px/16px rồi xuất file Block Symbol (.bsf).
        """
        with open(DuongDanRtl, "r", encoding="utf-8", errors="replace") as TepTin:
            MaNguon = TepTin.read()

        # Dọn dẹp chú thích Verilog trước khi tách danh sách cổng
        MaSach = re.sub(r"//.*", "", MaNguon)
        MaSach = re.sub(r"/\*.*?\*/", "", MaSach, flags=re.DOTALL)

        # Trích xuất tên module và phần khai báo cổng nằm trong dấu ngoặc (...)
        KhopModule = re.search(r"module\s+([A-Za-z0-9_]+)\s*(?:#\s*\([\s\S]*?\)\s*)?\(([\s\S]*?)\);", MaSach)
        if not KhopModule:
            return None

        TenModule = KhopModule.group(1)
        KhoiCong = KhopModule.group(2)

        # Phân loại các cổng thành ngõ vào (bên trái symbol) và ngõ ra / hai chiều (bên phải symbol)
        DanhSachVao = []
        DanhSachRa = []
        HuongHienTai = "input"
        MsbHienTai, LsbHienTai = None, None
        TuKhoaVerilog = {"input", "output", "inout", "wire", "reg", "logic", "module", "endmodule"}

        for Dong in KhoiCong.split(","):
            Dong = Dong.strip()
            if not Dong:
                continue
            KhopHuong = re.search(r"\b(input|output|inout)\b", Dong)
            if KhopHuong:
                HuongHienTai = KhopHuong.group(1)
                KhopRong = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", Dong)
                if KhopRong:
                    MsbHienTai, LsbHienTai = KhopRong.group(1), KhopRong.group(2)
                else:
                    MsbHienTai, LsbHienTai = None, None

            KhopTen = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*$", Dong)
            if KhopTen:
                TenCong = KhopTen.group(1)
                if TenCong.lower() in TuKhoaVerilog:
                    continue
                DoRong = (int(MsbHienTai) - int(LsbHienTai) + 1) if (MsbHienTai and LsbHienTai) else 1
                ThongTinCong = {
                    "name": TenCong,
                    "direction": HuongHienTai,
                    "width": DoRong,
                    "msb": MsbHienTai,
                    "lsb": LsbHienTai,
                    "is_bus": DoRong > 1
                }
                if HuongHienTai == "input":
                    DanhSachVao.append(ThongTinCong)
                else:
                    DanhSachRa.append(ThongTinCong)

        # Tính chiều cao khung symbol theo số cổng tối đa (bội số của 16px chuẩn lưới Quartus)
        SoCongToiDa = max(len(DanhSachVao), len(DanhSachRa), 2)
        ChieuCaoSymbol = max(112, (SoCongToiDa + 2) * 24)
        ChieuCaoSymbol = (ChieuCaoSymbol // 16) * 16
        ChieuRongSymbol = 192

        DongCong = []
        # Vẽ các cổng vào (input) ở cạnh trái symbol (x = 0)
        BuocYVao = ChieuCaoSymbol // (len(DanhSachVao) + 1)
        for ChiSo, CongVao in enumerate(DanhSachVao):
            ToaDoY = ((ChiSo + 1) * BuocYVao // 8) * 8
            ChuoiRong = f"[{CongVao['msb']}..{CongVao['lsb']}]" if CongVao["is_bus"] else ""
            TenDayDu = f"{CongVao['name']}{ChuoiRong}"
            DoDayNet = 3 if CongVao["is_bus"] else 1
            DongCong.append(f"""\t(port
\t\t(pt 0 {ToaDoY})
\t\t(input)
\t\t(text "{TenDayDu}" (rect 0 0 {len(TenDayDu)*7} 12)(font "Arial" ))
\t\t(text "{TenDayDu}" (rect 21 {ToaDoY-5} {21 + len(TenDayDu)*7} {ToaDoY+7})(font "Arial" ))
\t\t(line (pt 0 {ToaDoY})(pt 16 {ToaDoY})(line_width {DoDayNet}))
\t)""")

        # Cổng ra bên phải (x = ChieuRongSymbol)
        BuocYRa = ChieuCaoSymbol // (len(DanhSachRa) + 1)
        for ChiSo, CongRa in enumerate(DanhSachRa):
            ToaDoY = ((ChiSo + 1) * BuocYRa // 8) * 8
            ChuoiRong = f"[{CongRa['msb']}..{CongRa['lsb']}]" if CongRa["is_bus"] else ""
            TenDayDu = f"{CongRa['name']}{ChuoiRong}"
            DoDayNet = 3 if CongRa["is_bus"] else 1
            ToaDoXChu = ChieuRongSymbol - 21 - len(TenDayDu)*7
            LoaiCongBsf = "bidir" if CongRa.get("direction") == "inout" else "output"
            DongCong.append(f"""\t(port
\t\t(pt {ChieuRongSymbol} {ToaDoY})
\t\t({LoaiCongBsf})
\t\t(text "{TenDayDu}" (rect 0 0 {len(TenDayDu)*7} 12)(font "Arial" ))
\t\t(text "{TenDayDu}" (rect {ToaDoXChu} {ToaDoY-5} {ToaDoXChu + len(TenDayDu)*7} {ToaDoY+7})(font "Arial" ))
\t\t(line (pt {ChieuRongSymbol} {ToaDoY})(pt {ChieuRongSymbol - 16} {ToaDoY})(line_width {DoDayNet}))
\t)""")

        MaBsf = f"""/*
WARNING: Do NOT edit the input and output ports in this file in a text
editor if you plan to continue editing the block that represents it in
the Block Editor! File corruption is VERY likely to occur.
*/
(header "symbol" (version "1.1"))
(symbol
\t(rect 16 16 {16 + ChieuRongSymbol} {16 + ChieuCaoSymbol})
\t(text "{TenModule}" (rect 5 0 {5 + len(TenModule)*7} 12)(font "Arial" ))
\t(text "inst" (rect 8 {ChieuCaoSymbol - 16} 20 {ChieuCaoSymbol - 4})(font "Arial" ))
""" + "\n".join(DongCong) + f"""
\t(drawing
\t\t(rectangle (rect 16 16 {ChieuRongSymbol - 16} {ChieuCaoSymbol - 16})(line_width 1))
\t)
)
"""
        with open(DuongDanBsf, "w", encoding="utf-8") as TepTin:
            TepTin.write(MaBsf)
        return DuongDanBsf

    def generate_bdf_from_bsf(self, DuongDanBsf, DuongDanBdf, ToaDoX=368, ToaDoY=176):
        """
        Bước 2 trong quy trình Quartus Schematic:
        Đọc file Symbol .bsf vừa tạo, đặt khối vào tọa độ (ToaDoX, ToaDoY) trên bản vẽ,
        sinh các chân INPUT/OUTPUT/BIDIR tương ứng và nối dây (single wire hoặc bus) thành file .bdf.
        """
        with open(DuongDanBsf, "r", encoding="utf-8", errors="replace") as TepTin:
            NoiDungBsf = TepTin.read()

        # Đọc kích thước khung bao symbol từ file .bsf
        KhopKichThuoc = re.search(r'\(symbol\s+\(rect\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\)', NoiDungBsf)
        if not KhopKichThuoc:
            KhopKichThuoc = re.search(r'\(symbol\s*\(rect\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\)', NoiDungBsf)
        if not KhopKichThuoc:
            raise ValueError(f"File BSF không hợp lệ: {DuongDanBsf}")

        RongGoc = int(KhopKichThuoc.group(3)) - int(KhopKichThuoc.group(1))
        CaoGoc = int(KhopKichThuoc.group(4)) - int(KhopKichThuoc.group(2))

        # Căn chỉnh tọa độ theo lưới 8px
        ToaDoX = (ToaDoX // 8) * 8
        ToaDoY = (ToaDoY // 8) * 8
        ToaDoX2 = ToaDoX + RongGoc
        ToaDoY2 = ToaDoY + CaoGoc

        # Trích xuất các cổng (input, output, bidir) hỗ trợ cả thụt lề tabs/spaces và mọi định dạng xuống dòng
        DanhSachKhoiCong = re.findall(
            r'\(port\s+\(pt\s+(\d+)\s+(\d+)\)\s+\((input|output|bidir)\)\s+\(text\s+"([^"]+)"',
            NoiDungBsf
        )

        SymbolBenTrong = NoiDungBsf[NoiDungBsf.find('(symbol'):]
        SymbolBenTrong = re.sub(r'\(rect\s+\d+\s+\d+\s+\d+\s+\d+\)', f'(rect {ToaDoX} {ToaDoY} {ToaDoX2} {ToaDoY2})', SymbolBenTrong, count=1)

        MaChanPin = []
        MaDayNoi = []

        ChanVaoX = ToaDoX - 208
        ChanRaX = ToaDoX2 + 80

        for DiemX, DiemY, Huong, TenCong in DanhSachKhoiCong:
            ToaDoCongY = ToaDoY + int(DiemY)

            LaBus = ('[' in TenCong and '..' in TenCong) or ('[' in TenCong and ':' in TenCong)
            TenCongBdf = re.sub(r'\[(\d+):(\d+)\]', r'[\1..\2]', TenCong)

            if Huong == "input":
                ChanY = ToaDoCongY - 8
                NetBus = "\t\t(line (pt 113 8)(pt 168 8)(line_width 3))\n" if LaBus else "\t\t(line (pt 113 8)(pt 168 8))\n"
                HopChan = f"""(pin
\t(input)
\t(rect {ChanVaoX} {ChanY} {ChanVaoX + 168} {ChanY + 16})
\t(text "INPUT" (rect 125 0 153 10)(font "Arial" (font_size 6)))
\t(text "{TenCongBdf}" (rect 5 0 {5 + len(TenCongBdf)*7} 12)(font "Arial" ))
\t(pt 168 8)
\t(drawing
\t\t(line (pt 84 12)(pt 109 12))
\t\t(line (pt 84 4)(pt 109 4))
{NetBus}\t\t(line (pt 84 12)(pt 84 4))
\t\t(line (pt 109 4)(pt 113 8))
\t\t(line (pt 109 12)(pt 113 8))
\t)
\t(text "VCC" (rect 128 7 148 17)(font "Arial" (font_size 6)))
)"""
                MaChanPin.append(HopChan)
                TheBus = " (bus)" if LaBus else ""
                MaDayNoi.append(f"(connector (pt {ChanVaoX + 168} {ToaDoCongY}) (pt {ToaDoX} {ToaDoCongY}){TheBus})")

            else:
                ChanY = ToaDoCongY - 8
                LoaiPin = "bidir" if Huong == "bidir" else "output"
                NhanPin = "BIDIR" if Huong == "bidir" else "OUTPUT"
                NetBus = "\t\t(line (pt 0 8)(pt 52 8)(line_width 3))\n" if LaBus else "\t\t(line (pt 0 8)(pt 52 8))\n"
                HopChan = f"""(pin
\t({LoaiPin})
\t(rect {ChanRaX} {ChanY} {ChanRaX + 176} {ChanY + 16})
\t(text "{NhanPin}" (rect 1 0 39 10)(font "Arial" (font_size 6)))
\t(text "{TenCongBdf}" (rect 90 0 {90 + len(TenCongBdf)*7} 12)(font "Arial" ))
\t(pt 0 8)
\t(drawing
{NetBus}\t\t(line (pt 52 4)(pt 78 4))
\t\t(line (pt 52 12)(pt 78 12))
\t\t(line (pt 52 12)(pt 52 4))
\t\t(line (pt 78 4)(pt 82 8))
\t\t(line (pt 82 8)(pt 78 12))
\t\t(line (pt 78 12)(pt 82 8))
\t)
)"""
                MaChanPin.append(HopChan)
                TheBus = " (bus)" if LaBus else ""
                MaDayNoi.append(f"(connector (pt {ToaDoX2} {ToaDoCongY}) (pt {ChanRaX} {ToaDoCongY}){TheBus})")

        # Ghép nối file BDF: Header -> Chân Pin -> Symbol -> Dây nối Connectors
        DanhSachDongBdf = [
            '/* Tu dong tao boi Spec2RTL & Prompt2Silicon */',
            '(header "graphic" (version "1.4"))'
        ]
        DanhSachDongBdf.extend(MaChanPin)
        DanhSachDongBdf.append(SymbolBenTrong.strip())
        DanhSachDongBdf.extend(MaDayNoi)

        with open(DuongDanBdf, "w", encoding="utf-8") as TepTin:
            TepTin.write("\n".join(DanhSachDongBdf) + "\n")
        return DuongDanBdf

if __name__ == "__main__":
    BoTaoBdf = BDFGenerator()
    ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    FileBsf = os.path.join(ThuMucGoc, "quartus", "vending_machine.bsf")
    FileBdf = os.path.join(ThuMucGoc, "quartus", "top_vending_machine.bdf")
    if os.path.exists(FileBsf):
        BoTaoBdf.generate_bdf_from_bsf(FileBsf, FileBdf)
        print("Đã tạo file BDF tại:", FileBdf)
