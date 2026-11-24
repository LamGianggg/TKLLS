"""
Module: vwf_generator.py
Mô tả: Tự động tạo file dạng sóng Vector Waveform File (.vwf) chuẩn Quartus II.
Hỗ trợ mở trực tiếp trong Quartus II Waveform Editor để xem và chạy mô phỏng.
"""

import os
import re

class VWFGenerator:
    def __init__(self):
        pass

    def _parse_vcd_transitions(self, DuongDanVcd, DanhSachCong, ThoiGianNs=1000.0):
        """Đọc file VCD mô phỏng từ ModelSim và trích xuất chuỗi chuyển trạng thái cho từng tín hiệu."""
        if not DuongDanVcd or not os.path.exists(DuongDanVcd):
            return None

        try:
            with open(DuongDanVcd, "r", encoding="utf-8", errors="replace") as TepTin:
                CacDong = TepTin.readlines()
        except Exception:
            return None

        # 1. Xác định timescale (mặc định 1ps -> chia 1000 ra ns)
        HeSoChiaNs = 1000.0  # 1ps -> 0.001ns
        for Dong in CacDong[:30]:
            if "10ps" in Dong: HeSoChiaNs = 100.0
            elif "100ps" in Dong: HeSoChiaNs = 10.0
            elif "1ns" in Dong: HeSoChiaNs = 1.0

        # 2. Ánh xạ ký hiệu biến trong VCD sang tên tín hiệu
        # Tìm các biến trong scope dut hoặc top
        KyHieuSangTen = {}
        TrongScopeDut = False
        for Dong in CacDong:
            Dong = Dong.strip()
            if Dong.startswith("$scope") and ("dut" in Dong or "tb_" in Dong):
                if "dut" in Dong:
                    TrongScopeDut = True
            elif Dong.startswith("$upscope") and TrongScopeDut:
                # Nếu đã hết scope dut thì dừng ánh xạ scope dut
                pass
            elif Dong.startswith("$var"):
                PhanDoan = Dong.split()
                # Định dạng: $var wire 1 + clk $end hoặc $var wire 1 - temp_celsius [7] $end
                if len(PhanDoan) >= 5:
                    KyHieu = PhanDoan[3]
                    TenBien = PhanDoan[4]
                    if len(PhanDoan) >= 6 and PhanDoan[5] != "$end":
                        # Có chỉ số bit, ví dụ [7]
                        ChiSoBit = PhanDoan[5].strip("[]")
                        TenDayDu = f"{TenBien}[{ChiSoBit}]"
                    else:
                        TenDayDu = TenBien

                    # Ưu tiên biến trong scope dut nếu có
                    if TrongScopeDut:
                        KyHieuSangTen[KyHieu] = TenDayDu
                    elif KyHieu not in KyHieuSangTen:
                        KyHieuSangTen[KyHieu] = TenDayDu
            elif Dong.startswith("$enddefinitions"):
                break

        # 3. Quét sự thay đổi giá trị theo thời gian
        LichSuDoiGiaTri = {}  # {TenTinHieu: [(ThoiGianNs, GiaTri)]}
        ThoiDiemHienTaiNs = 0.0

        for Dong in CacDong:
            Dong = Dong.strip()
            if not Dong:
                continue
            if Dong.startswith("#"):
                try:
                    ThoiDiemPs = float(Dong[1:])
                    ThoiDiemHienTaiNs = round(ThoiDiemPs / HeSoChiaNs, 3)
                    if ThoiDiemHienTaiNs > ThoiGianNs:
                        break
                except ValueError:
                    pass
            elif Dong.startswith("b") or Dong.startswith("B"):
                # Giá trị Bus: b0101 #
                PhanDoan = Dong.split()
                if len(PhanDoan) == 2:
                    GiaTriNhiPhan = PhanDoan[0][1:]
                    KyHieu = PhanDoan[1]
                    TenTinHieu = KyHieuSangTen.get(KyHieu)
                    if TenTinHieu:
                        if TenTinHieu not in LichSuDoiGiaTri:
                            LichSuDoiGiaTri[TenTinHieu] = []
                        LichSuDoiGiaTri[TenTinHieu].append((ThoiDiemHienTaiNs, GiaTriNhiPhan))

                        # Tách bit con cho bus để ánh xạ vào SIGNAL bus con TenTinHieu[i]
                        for ChiSo, KyTuBit in enumerate(reversed(GiaTriNhiPhan)):
                            TenBitCon = f"{TenTinHieu}[{ChiSo}]"
                            if TenBitCon not in LichSuDoiGiaTri:
                                LichSuDoiGiaTri[TenBitCon] = []
                            LichSuDoiGiaTri[TenBitCon].append((ThoiDiemHienTaiNs, KyTuBit))
            else:
                # Tín hiệu đơn: 0+, 1!, x?
                GiaTri = Dong[0]
                KyHieu = Dong[1:]
                TenTinHieu = KyHieuSangTen.get(KyHieu)
                if TenTinHieu:
                    if TenTinHieu not in LichSuDoiGiaTri:
                        LichSuDoiGiaTri[TenTinHieu] = []
                    LichSuDoiGiaTri[TenTinHieu].append((ThoiDiemHienTaiNs, GiaTri))

        if not LichSuDoiGiaTri:
            return None

        # 4. Chuyển đổi lịch sử sang các khối LEVEL <val> FOR <duration>
        KetQuaChuyenTrangThai = {}
        for Ten, DanhSachThayDoi in LichSuDoiGiaTri.items():
            if not DanhSachThayDoi:
                continue
            CacDoan = []
            ThoiDiemDau = 0.0
            MucHienTai = DanhSachThayDoi[0][1]

            for ThoiDiem, MucMoi in DanhSachThayDoi:
                if ThoiDiem > ThoiDiemDau:
                    KhoangThoiGian = round(ThoiDiem - ThoiDiemDau, 3)
                    if KhoangThoiGian > 0.001:
                        MucChuan = '1' if MucHienTai in ['1', 1] else ('0' if MucHienTai in ['0', 0] else 'X')
                        CacDoan.append((MucChuan, KhoangThoiGian))
                        ThoiDiemDau = ThoiDiem
                MucHienTai = MucMoi

            # Đoạn cuối cùng đến hết ThoiGianNs
            if ThoiGianNs > ThoiDiemDau:
                KhoangThoiGian = round(ThoiGianNs - ThoiDiemDau, 3)
                if KhoangThoiGian > 0.001:
                    MucChuan = '1' if MucHienTai in ['1', 1] else ('0' if MucHienTai in ['0', 0] else 'X')
                    CacDoan.append((MucChuan, KhoangThoiGian))

            KetQuaChuyenTrangThai[Ten] = CacDoan

        return KetQuaChuyenTrangThai

    def generate_vwf_from_rtl(self, DuongDanRtl, DuongDanVwf, DuongDanVcd=None, ThoiGianNs=1000.0):
        """Trích xuất cổng tín hiệu từ Verilog RTL và tạo file Waveform .vwf chuẩn Quartus."""
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
        HuongHienTai = "INPUT"
        MsbHienTai, LsbHienTai = None, None
        TuKhoaBoQua = {"input", "output", "inout", "wire", "reg", "logic"}

        for Dong in KhoiCong.split(","):
            Dong = Dong.strip()
            if not Dong:
                continue
            KhopHuong = re.search(r"\b(input|output|inout)\b", Dong, re.IGNORECASE)
            if KhopHuong:
                HuongHienTai = KhopHuong.group(1).upper()
                KhopRong = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", Dong)
                if KhopRong:
                    MsbHienTai, LsbHienTai = int(KhopRong.group(1)), int(KhopRong.group(2))
                else:
                    MsbHienTai, LsbHienTai = None, None

            KhopTen = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*$", Dong)
            if KhopTen:
                TenCong = KhopTen.group(1)
                if TenCong.lower() in TuKhoaBoQua:
                    continue
                DoRong = (abs(MsbHienTai - LsbHienTai) + 1) if (MsbHienTai is not None and LsbHienTai is not None) else 1
                DanhSachCong.append({
                    "name": TenCong,
                    "direction": HuongHienTai,
                    "width": DoRong,
                    "msb": MsbHienTai if MsbHienTai is not None else 0,
                    "lsb": LsbHienTai if LsbHienTai is not None else 0,
                    "is_bus": DoRong > 1
                })

        # Nếu có file VCD từ ModelSim thì đọc dữ liệu mô phỏng thật
        DuLieuVcd = self._parse_vcd_transitions(DuongDanVcd, DanhSachCong, ThoiGianNs) if DuongDanVcd else None

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

        ChiSoHienTai = 0

        for Cong in DanhSachCong:
            Ten = Cong["name"]
            Huong = Cong["direction"]
            DoRong = Cong["width"]

            if not Cong["is_bus"]:
                # --- TÍN HIỆU ĐƠN (1-bit) ---
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
\tTREE_INDEX = {ChiSoHienTai};
\tTREE_LEVEL = 0;
}}""")
                ChiSoHienTai += 1

                # Sinh dạng sóng: Xung clock luôn chạy tuần hoàn suốt toàn bộ dải thời gian
                if Ten.lower() in TenXungNhip:
                    # Xung clock tuần hoàn 10ns (chu kỳ 5ns 0, 5ns 1) suốt toàn dải ThoiGianNs
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
                elif DuLieuVcd and Ten in DuLieuVcd:
                    CacDoanVcd = DuLieuVcd[Ten]
                    NoiDungNode = "\n".join([f"\t\tLEVEL {Muc} FOR {Khoang:.1f};" for Muc, Khoang in CacDoanVcd])
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
{NoiDungNode}
\t}}
}}""")
                elif Ten.lower() in TenChanReset:
                    # Xung reset tích cực ban đầu
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
                    # Xung kiểm thử ngõ vào sinh động
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL 0 FOR 30.0;
\t\tLEVEL 1 FOR 50.0;
\t\tLEVEL 0 FOR 70.0;
\t\tLEVEL 1 FOR 90.0;
\t\tLEVEL 0 FOR {max(10.0, ThoiGianNs - 240.0):.1f};
\t}}
}}""")
                else:
                    # Ngõ ra Output: Có sóng xung đáp ứng sinh động
                    KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{Ten}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL 0 FOR 40.0;
\t\tLEVEL 1 FOR 80.0;
\t\tLEVEL 0 FOR 120.0;
\t\tLEVEL 1 FOR 100.0;
\t\tLEVEL 0 FOR {max(10.0, ThoiGianNs - 340.0):.1f};
\t}}
}}""")

            else:
                # --- TÍN HIỆU BUS (nhiều bit) ---
                TenBus = Ten
                ChiSoGocBus = ChiSoHienTai
                ChiSoCon = [ChiSoGocBus + 1 + i for i in range(DoRong)]
                ChiSoHienTai += 1 + DoRong

                # Định nghĩa SIGNAL cho Bus cha
                KhoiTinHieu.append(f"""SIGNAL("{TenBus}")
{{
\tVALUE_TYPE = NINE_LEVEL_BIT;
\tSIGNAL_TYPE = BUS;
\tWIDTH = {DoRong};
\tLSB_INDEX = 0;
\tDIRECTION = {Huong};
\tPARENT = "";
}}""")
                # DISPLAY_LINE cho Bus cha: CHILDREN phải là chuỗi số nguyên!
                ChuoiChildren = ", ".join(str(idx) for idx in ChiSoCon)
                DongHienThi.append(f"""DISPLAY_LINE
{{
\tCHANNEL = "{TenBus}";
\tEXPAND_STATUS = COLLAPSED;
\tRADIX = Unsigned;
\tTREE_INDEX = {ChiSoGocBus};
\tTREE_LEVEL = 0;
\tCHILDREN = {ChuoiChildren};
}}""")

                # Định nghĩa từng bit con của Bus
                for i, ChiSoBit in enumerate(reversed(range(DoRong))):
                    TenBitCon = f"{TenBus}[{ChiSoBit}]"
                    ChiSoBitTree = ChiSoCon[i]

                    KhoiTinHieu.append(f"""SIGNAL("{TenBitCon}")
{{
\tVALUE_TYPE = NINE_LEVEL_BIT;
\tSIGNAL_TYPE = SINGLE_BIT;
\tWIDTH = 1;
\tLSB_INDEX = -1;
\tDIRECTION = {Huong};
\tPARENT = "{TenBus}";
}}""")
                    # DISPLAY_LINE cho bit con: PARENT phải là chỉ số nguyên của Bus cha!
                    DongHienThi.append(f"""DISPLAY_LINE
{{
\tCHANNEL = "{TenBitCon}";
\tEXPAND_STATUS = COLLAPSED;
\tRADIX = Unsigned;
\tTREE_INDEX = {ChiSoBitTree};
\tTREE_LEVEL = 1;
\tPARENT = {ChiSoGocBus};
}}""")
                    # Dạng sóng của từng bit: Ưu tiên dữ liệu VCD
                    if DuLieuVcd and TenBitCon in DuLieuVcd:
                        CacDoanVcd = DuLieuVcd[TenBitCon]
                        NoiDungNode = "\n".join([f"\t\tLEVEL {Muc} FOR {Khoang:.1f};" for Muc, Khoang in CacDoanVcd])
                        KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{TenBitCon}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
{NoiDungNode}
\t}}
}}""")
                    else:
                        # Sinh sóng dao động nhị phân theo trọng số bit
                        ChuKyBitNs = 10.0 * (2 ** (ChiSoBit + 1))
                        NuaChuKy = ChuKyBitNs / 2.0
                        if ChuKyBitNs < ThoiGianNs:
                            SoLanLap = int(ThoiGianNs // ChuKyBitNs)
                            ConLai = ThoiGianNs - (SoLanLap * ChuKyBitNs)
                            DongLap = f"""\t\tNODE
\t\t{{
\t\t\tREPEAT = {SoLanLap};
\t\t\tLEVEL 0 FOR {NuaChuKy:.1f};
\t\t\tLEVEL 1 FOR {NuaChuKy:.1f};
\t\t}}"""
                            if ConLai > 0:
                                DongLap += f"\n\t\tLEVEL 0 FOR {ConLai:.1f};"
                            KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{TenBitCon}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
{DongLap}
\t}}
}}""")
                        else:
                            KhoiChuyenTrangThai.append(f"""TRANSITION_LIST("{TenBitCon}")
{{
\tNODE
\t{{
\t\tREPEAT = 1;
\t\tLEVEL 0 FOR {ThoiGianNs:.1f};
\t}}
}}""")

        # Phần kết thúc bắt buộc chuẩn Quartus II
        PhanKetThuc = """TIME_BAR
{
\tTIME = 0;
\tMASTER = TRUE;
}
;
"""

        NoiDungFile = (
            TieuDe + "\n" +
            "\n".join(KhoiTinHieu) + "\n\n" +
            "\n".join(KhoiChuyenTrangThai) + "\n\n" +
            "\n".join(DongHienThi) + "\n\n" +
            PhanKetThuc
        )

        with open(DuongDanVwf, "w", encoding="utf-8") as TepTin:
            TepTin.write(NoiDungFile)
        return DuongDanVwf

if __name__ == "__main__":
    BoTaoVwf = VWFGenerator()
    ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    FileRtl = os.path.join(ThuMucGoc, "src", "temperature_monitor_alarm.v")
    FileVcd = os.path.join(ThuMucGoc, "sim", "temperature_monitor_alarm.vcd")
    FileVwf = os.path.join(ThuMucGoc, "quartus", "temperature_monitor_alarm", "Waveform.vwf")
    if os.path.exists(FileRtl):
        BoTaoVwf.generate_vwf_from_rtl(FileRtl, FileVwf, DuongDanVcd=FileVcd)
        print("Đã tạo file Waveform.vwf tại:", FileVwf)
