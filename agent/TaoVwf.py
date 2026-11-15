"""
Module: TaoVwf.py (truoc day la vwf_generator.py)
Mô tả: Tự động tạo file dạng sóng Vector Waveform File (.vwf) chuẩn Quartus II.
Hỗ trợ mở trực tiếp trong Quartus II Waveform Editor để xem và chạy mô phỏng.
"""

import os
import re

class VWFGenerator:
    def __init__(self):
        pass

    def generate_vwf_from_rtl(self, DuongDanRtl, DuongDanVwf, ThoiGianNs=1000.0):
        """Trích xuất cổng tín hiệu từ Verilog RTL và tạo file Waveform .vwf cho Quartus."""
        if not os.path.exists(DuongDanRtl):
            return None

        with open(DuongDanRtl, "r", encoding="utf-8", errors="replace") as TepTin:
            MaNguon = TepTin.read()

        # Xóa chú thích
        ChuoiSach = re.sub(r"//.*", "", MaNguon)
        ChuoiSach = re.sub(r"/\*.*?\*/", "", ChuoiSach, flags=re.DOTALL)

        KhopModule = re.search(r"module\s+([A-Za-z0-9_]+)\s*(?:#\s*\(.*?\)\s*)?\((.*?)\);", ChuoiSach, re.DOTALL)
        if not KhopModule:
            return None

        TenModule = KhopModule.group(1)
        KhoiCong = KhopModule.group(2)

        DanhSachCong = []
        for Dong in KhoiCong.split(","):
            Dong = Dong.strip()
            KhopCong = re.search(r"(input|output|inout)\s+(?:wire|reg)?\s*(?:\[(\d+):(\d+)\])?\s*([A-Za-z0-9_]+)", Dong)
            if KhopCong:
                Huong, Msb, Lsb, TenCong = KhopCong.groups()
                DoRong = (int(Msb) - int(Lsb) + 1) if Msb and Lsb else 1
                DanhSachCong.append({
                    "name": TenCong,
                    "direction": Huong.upper(),
                    "width": DoRong,
                    "msb": int(Msb) if Msb else 0,
                    "lsb": int(Lsb) if Lsb else 0,
                    "is_bus": DoRong > 1
                })

        TieuDe = f"""/* Simulator = Quartus II Simulator */
/* Tu dong tao boi Spec2RTL & Prompt2Silicon */
HEADER
{{
\tVERSION = 1;
\tTIME_UNIT = ns;
\tDATA_OFFSET = 0.0;
\tDATA_DURATION = {ThoiGianNs:.1f};
\tSIMULATION_TIME = 0.0;
\tGRID_PHASE = 0.0;
\tGRID_PERIOD = 10.0;
\tGRID_DUTY_CYCLE = 50;
}}
"""

        KhoiTinHieu = []
        KhoiChuyenTrangThai = []
        DongHienThi = []

        TenXungNhip = ["clk", "clock", "sys_clk"]
        TenChanReset = ["rst_n", "rst", "reset", "clr", "clear"]

        for Cong in DanhSachCong:
            Ten = Cong["name"]
            Huong = Cong["direction"]
            DoRong = Cong["width"]

            if not Cong["is_bus"]:
                # Tín hiệu đơn 1-bit
                KhoiTinHieu.append(f"""SIGNAL("{Ten}")
{{
\tVALUE_TYPE = NINE_LEVEL_BIT;
\tSIGNAL_TYPE = SINGLE_BIT;
\tWIDTH = 1;
\tLSB_INDEX = -1;
\tDIRECTION = {Huong};
\tPARENT = "";
}}""")
                DongHienThi.append(f"""DISPLAY_LINE
{{
\tCHANNEL = "{Ten}";
\tEXPAND_STATUS = COLLAPSED;
\tRADIX = Binary;
\tTREE_INDEX = {len(DongHienThi)};
\tTREE_LEVEL = 0;
}}""")

                # Xung kích thích
                if Ten.lower() in TenXungNhip:
                    # Tạo xung clock tuần hoàn
                    ChuKy = int(ThoiGianNs // 10)
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tNODE
\t\t{{
\t\t\tREPEAT = {ChuKy};
\t\t\tLEVEL 0 FOR 5.0;
\t\t\tLEVEL 1 FOR 5.0;
\t\t}}
\t}}
}}""")
                elif Ten.lower() in TenChanReset:
                    # Tạo xung reset ban đầu
                    TichCucThap = "n" in Ten.lower()
                    MucBanDau = 0 if TichCucThap else 1
                    MucNghi = 1 if TichCucThap else 0
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL {MucBanDau} FOR 20.0;
\t\tLEVEL {MucNghi} FOR {ThoiGianNs - 20.0:.1f};
\t}}
}}""")
                elif Huong == "INPUT":
                    # Xung thử nghiệm đầu vào
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL 0 FOR 40.0;
\t\tLEVEL 1 FOR 20.0;
\t\tLEVEL 0 FOR 80.0;
\t\tLEVEL 1 FOR 20.0;
\t\tLEVEL 0 FOR {max(10.0, ThoiGianNs - 160.0):.1f};
\t}}
}}""")
                else:
                    # Tín hiệu đầu ra Output
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL X FOR {ThoiGianNs:.1f};
\t}}
}}""")

            else:
                # Tín hiệu dạng Bus (nhiều bit)
                TenBus = Ten
                KhoiTinHieu.append(f"""SIGNAL("{TenBus}")
{{
\tVALUE_TYPE = NINE_LEVEL_BIT;
\tSIGNAL_TYPE = BUS;
\tWIDTH = {DoRong};
\tLSB_INDEX = 0;
\tDIRECTION = {Huong};
\tPARENT = "";
}}""")
                DongHienThi.append(f"""DISPLAY_LINE
{{
\tCHANNEL = "{TenBus}";
\tEXPAND_STATUS = EXPANDED;
\tRADIX = Unsigned;
\tTREE_INDEX = {len(DongHienThi)};
\tTREE_LEVEL = 0;
\tCHILDREN = {", ".join([f'"{TenBus}[{i}]"' for i in reversed(range(DoRong))])};
}}""")
                for ChiSoBit in reversed(range(DoRong)):
                    TenBitCon = f"{TenBus}[{ChiSoBit}]"
                    KhoiTinHieu.append(f"""SIGNAL("{TenBitCon}")
{{
\tVALUE_TYPE = NINE_LEVEL_BIT;
\tSIGNAL_TYPE = SINGLE_BIT;
\tWIDTH = 1;
\tLSB_INDEX = -1;
\tDIRECTION = {Huong};
\tPARENT = "{TenBus}";
}}""")
                    DongHienThi.append(f"""DISPLAY_LINE
{{
\tCHANNEL = "{TenBitCon}";
\tEXPAND_STATUS = COLLAPSED;
\tRADIX = Unsigned;
\tTREE_INDEX = {len(DongHienThi)};
\tTREE_LEVEL = 1;
\tPARENT = "{TenBus}";
}}""")
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{TenBitCon}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL {'0' if Huong == 'INPUT' else 'X'} FOR {ThoiGianNs:.1f};
\t}}
}}""")

        NoiDungFile = TieuDe + "\n" + "\n".join(KhoiTinHieu) + "\n\n" + "\n".join(KhoiChuyenTrangThai) + "\n\n" + "\n".join(DongHienThi) + "\n"

        with open(DuongDanVwf, "w", encoding="utf-8") as TepTin:
            TepTin.write(NoiDungFile)
        return DuongDanVwf

if __name__ == "__main__":
    BoTaoVwf = VWFGenerator()
    ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    FileRtl = os.path.join(ThuMucGoc, "src", "vending_machine.v")
    FileVwf = os.path.join(ThuMucGoc, "quartus", "Waveform.vwf")
    if os.path.exists(FileRtl):
        BoTaoVwf.generate_vwf_from_rtl(FileRtl, FileVwf)
        print("Đã tạo file Waveform.vwf tại:", FileVwf)
