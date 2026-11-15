"""
Module: waveform_visualizer.py
Chuc nang: Tao dang song truc quan tu ket qua mo phong EDA:
1. File khoi dong ModelSim GUI truc quan.
2. Trinh xem dang song HTML5/SVG tuong tac doc lap.
3. Xu ly du lieu tu tep tin VCD (Value Change Dump).
"""

import os
import re

class WaveformVisualizer:
    """Bo truc quan hoa dang song tin hieu mo phong."""

    def __init__(self):
        pass

    @staticmethod
    def parse_vcd(DuongDanVcd=None, vcd_path=None):
        """Phan tich file VCD thanh du lieu xung nhip theo thoi gian."""
        TepVcd = vcd_path if vcd_path is not None else DuongDanVcd
        if not TepVcd or not os.path.exists(TepVcd):
            return None

        with open(TepVcd, "r", encoding="utf-8", errors="replace") as TepTin:
            DanhSachDong = TepTin.readlines()

        BangBien = {} # KyHieu -> {name, width, is_bus}
        HeSoThoiGian = 1.0 # Quy ve nanosecond (ns)

        ChiSo = 0
        while ChiSo < len(DanhSachDong):
            Dong = DanhSachDong[ChiSo].strip()
            if "$timescale" in Dong:
                ChuoiThoiGian = DanhSachDong[ChiSo + 1].strip() if ChiSo + 1 < len(DanhSachDong) else "1ns"
                if "ps" in ChuoiThoiGian:
                    HeSoThoiGian = 0.001
                elif "ns" in ChuoiThoiGian:
                    HeSoThoiGian = 1.0
                elif "us" in ChuoiThoiGian:
                    HeSoThoiGian = 1000.0

            if "$var" in Dong:
                ThanhPhan = Dong.split()
                if len(ThanhPhan) >= 5:
                    DoRong = int(ThanhPhan[2]) if ThanhPhan[2].isdigit() else 1
                    KyHieu = ThanhPhan[3]
                    TenTinHieu = ThanhPhan[4]
                    if len(ThanhPhan) > 5 and ThanhPhan[5].startswith("["):
                        TenTinHieu = f"{TenTinHieu}{ThanhPhan[5]}"
                    # Bo qua bien dem noi bo testbench
                    if not any(TuKhoa in TenTinHieu for TuKhoa in ["total_tests", "passed_tests", "failed_tests"]):
                        BangBien[KyHieu] = {
                            "name": TenTinHieu,
                            "width": DoRong,
                            "symbol": KyHieu
                        }

            if "$enddefinitions" in Dong:
                ChiSo += 1
                break
            ChiSo += 1

        # Doc su bien doi gia tri theo thoi gian
        ThoiGianNs = 0.0
        XungTinHieu = {KyHieu: [] for KyHieu in BangBien}

        while ChiSo < len(DanhSachDong):
            Dong = DanhSachDong[ChiSo].strip()
            if Dong.startswith("#"):
                ThoiGianNs = round(float(Dong[1:]) * HeSoThoiGian, 2)
            elif Dong.startswith(("b", "B")):
                ThanhPhan = Dong.split()
                if len(ThanhPhan) >= 2 and ThanhPhan[1] in XungTinHieu:
                    XungTinHieu[ThanhPhan[1]].append((ThoiGianNs, ThanhPhan[0][1:]))
            elif len(Dong) >= 2 and not Dong.startswith(("r", "R", "$")):
                KyHieu = Dong[1:].strip()
                if KyHieu in XungTinHieu:
                    XungTinHieu[KyHieu].append((ThoiGianNs, Dong[0]))
            ChiSo += 1

        return {
            "var_map": BangBien,
            "signal_traces": XungTinHieu,
            "max_time": ThoiGianNs if ThoiGianNs > 0 else 500.0
        }

    @staticmethod
    def generate_html_viewer(DuongDanVcd=None, DuongDanHtml=None, TieuDe="Dang Song Mo Phong Phan Cung", vcd_path=None, html_path=None, title=None):
        """Tao file HTML5 hien thi dang song truc quan tu du lieu VCD."""
        TepVcd = vcd_path if vcd_path is not None else DuongDanVcd
        TepHtml = html_path if html_path is not None else DuongDanHtml
        TieuDeTrang = title if title is not None else TieuDe

        DuLieuPhanTich = WaveformVisualizer.parse_vcd(TepVcd)
        if not DuLieuPhanTich:
            with open(TepHtml, "w", encoding="utf-8") as TepTin:
                TepTin.write("<html><body><h3>Khong co du lieu dang song VCD</h3></body></html>")
            return TepHtml

        BangBien = DuLieuPhanTich["var_map"]
        XungTinHieu = DuLieuPhanTich["signal_traces"]
        ThoiGianToiDa = max(DuLieuPhanTich["max_time"], 100.0)

        # Chon cac tin hieu can ve
        TinHieuVe = []
        TenDaVe = set()
        for KyHieu, ThongTin in BangBien.items():
            TenGoc = re.sub(r"\[\d+\]", "", ThongTin["name"])
            if TenGoc not in TenDaVe:
                TenDaVe.add(TenGoc)
                ChuyenTrangThai = XungTinHieu.get(KyHieu, [])
                TinHieuVe.append({
                    "name": ThongTin["name"],
                    "symbol": KyHieu,
                    "transitions": ChuyenTrangThai,
                    "is_bus": ThongTin["width"] > 1 or "[" in ThongTin["name"]
                })

        TyLeX = 1.8
        ChieuRongTong = max(900, int(ThoiGianToiDa * TyLeX) + 100)
        ChieuCaoHang = 42

        DanhSachHangSvg = []
        for ChiMuc, TinHieu in enumerate(TinHieuVe):
            ToaDoY = ChiMuc * ChieuCaoHang + 30
            YMucCao, YMucThap = ToaDoY + 6, ToaDoY + 30

            ToaDoDiem = []
            DanhSachChuyen = TinHieu["transitions"] or [(0.0, "0"), (ThoiGianToiDa, "0")]
            YCuoi = YMucThap

            for ThoiGian, GiaTri in DanhSachChuyen:
                ToaDoX = ThoiGian * TyLeX
                YDich = YMucCao if GiaTri in ["1", "h", "H"] else YMucThap
                ToaDoDiem.append(f"{ToaDoX:.1f},{YCuoi:.1f}")
                ToaDoDiem.append(f"{ToaDoX:.1f},{YDich:.1f}")
                YCuoi = YDich
            ToaDoDiem.append(f"{ThoiGianToiDa * TyLeX:.1f},{YCuoi:.1f}")

            TenInThuong = TinHieu["name"].lower()
            MauDuong = "#00e676" if "clk" in TenInThuong else ("#ffab00" if ("coin" in TenInThuong or "in" in TenInThuong) else "#00b0ff")
            ChuoiToaDo = " ".join(ToaDoDiem)

            DanhSachHangSvg.append(f"""
            <!-- Tin hieu: {TinHieu['name']} -->
            <g class="signal-row" data-name="{TinHieu['name']}">
                <rect x="0" y="{ToaDoY}" width="{ChieuRongTong}" height="{ChieuCaoHang}" fill="{'#1a1e24' if ChiMuc % 2 == 0 else '#15181c'}" />
                <line x1="0" y1="{YMucThap}" x2="{ChieuRongTong}" y2="{YMucThap}" stroke="#2a303c" stroke-dasharray="2,4" />
                <polyline points="{ChuoiToaDo}" fill="none" stroke="{MauDuong}" stroke-width="2" />
            </g>
            """)

        # Vach thoi gian
        DanhSachLuoiSvg = []
        MocThoiGian = 0.0
        while MocThoiGian <= ThoiGianToiDa:
            ToaDoX = MocThoiGian * TyLeX
            DanhSachLuoiSvg.append(f"""
                <line x1="{ToaDoX:.1f}" y1="0" x2="{ToaDoX:.1f}" y2="{len(TinHieuVe) * ChieuCaoHang + 30}" stroke="#2c3440" stroke-width="1" />
                <text x="{ToaDoX + 2:.1f}" y="18" fill="#788b9c" font-size="11" font-family="monospace">{int(MocThoiGian)}ns</text>
            """)
            MocThoiGian += 20.0

        NoiDungHtml = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>{TieuDeTrang}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #0f1216;
            color: #eceff1;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Consolas", monospace;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #263238;
            padding-bottom: 12px;
            margin-bottom: 15px;
        }}
        .title {{
            font-size: 20px;
            font-weight: bold;
            color: #00e5ff;
        }}
        .badges {{
            display: flex;
            gap: 10px;
        }}
        .badge {{
            background: #1e293b;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            border: 1px solid #334155;
        }}
        .badge-success {{
            color: #00e676;
            border-color: #00e676;
        }}
        .container {{
            display: flex;
            border: 1px solid #334155;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            background: #15181c;
        }}
        .signal-labels {{
            width: 220px;
            background: #111417;
            border-right: 2px solid #263238;
            flex-shrink: 0;
            padding-top: 30px;
        }}
        .label-row {{
            height: {ChieuCaoHang}px;
            display: flex;
            align-items: center;
            padding: 0 15px;
            font-weight: 600;
            font-size: 13px;
            border-bottom: 1px solid #1f2730;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .waveform-scroll {{
            overflow-x: auto;
            flex-grow: 1;
            background: #15181c;
            position: relative;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">⚡ {TieuDeTrang}</div>
        <div class="badges">
            <div class="badge badge-success">● ModelSim Da Kiem Tra</div>
            <div class="badge">Thoi gian: {ThoiGianToiDa:.1f} ns</div>
            <div class="badge">Dang: Binary / Hex</div>
        </div>
    </div>

    <div class="container">
        <div class="signal-labels">
            {"".join([f'<div class="label-row" title="{T["name"]}">{T["name"]}</div>' for T in TinHieuVe])}
        </div>
        <div class="waveform-scroll">
            <svg width="{ChieuRongTong}" height="{len(TinHieuVe) * ChieuCaoHang + 35}" xmlns="http://www.w3.org/2000/svg">
                {"".join(DanhSachLuoiSvg)}
                {"".join(DanhSachHangSvg)}
            </svg>
        </div>
    </div>
    <p style="color: #64748b; font-size: 12px; margin-top: 15px;">
        * Truc ngang the hien thoi gian mo phong (nanoseconds). Co the cuon ngang de xem toan bo qua trinh hoat dong cua mach.
    </p>
</body>
</html>
"""
        with open(TepHtml, "w", encoding="utf-8") as TepTin:
            TepTin.write(NoiDungHtml)
        return TepHtml

    @staticmethod
    def generate_view_launcher(ThuMucBinModelSim=None, ThuMucSim=None, TenModuleDau=None, DuongDanBat=None, modelsim_bin=None, sim_dir=None, top_module=None, bat_path=None):
        """Tao file .bat khoi dong nhanh ModelSim GUI."""
        ThuMucBin = modelsim_bin if modelsim_bin is not None else ThuMucBinModelSim
        ThuMucMoPhong = sim_dir if sim_dir is not None else ThuMucSim
        TenMod = top_module if top_module is not None else TenModuleDau
        TepBat = bat_path if bat_path is not None else DuongDanBat

        ThucThiVsim = os.path.join(ThuMucBin, "vsim.exe") if ThuMucBin else "vsim.exe"
        
        NoiDungBat = f"""@echo off
chcp 65001 > nul
echo ===============================================================================
echo     Khoi Dong Trinh Xem Dang Song ModelSim Cho: {TenMod}
echo ===============================================================================
echo.
cd /d "{ThuMucMoPhong}"

if exist "{ThucThiVsim}" (
    start "" "{ThucThiVsim}" -novopt work.{TenMod} -do "add wave -r /*; run -all; wave zoom full;"
    echo -> [OK] Da mo cua so song truc quan trong ModelSim GUI!
) else (
    echo -> [Luu y] Khong tim thay ModelSim GUI!
    echo -> Co the mo truc tiep file Waveform.vwf trong Quartus II Waveform Editor.
)
"""
        with open(TepBat, "w", encoding="utf-8") as TepTin:
            TepTin.write(NoiDungBat)
        return TepBat

if __name__ == "__main__":
    from eda_finder import find_modelsim
    ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    TepVcd = os.path.join(ThuMucGoc, "sim", "vending_machine.vcd")
    TepHtml = os.path.join(ThuMucGoc, "sim", "waveform.html")

    BoTrucQuan = WaveformVisualizer()
    if os.path.exists(TepVcd):
        BoTrucQuan.generate_html_viewer(TepVcd, TepHtml, "May Ban Nuoc Tu Dong")
        print("Da tao file HTML bieu dien dang song tai:", TepHtml)
    else:
        print("Chua co file VCD de thu nghiem.")
