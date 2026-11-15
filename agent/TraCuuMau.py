"""
Module: TraCuuMau.py (truoc day la knowledge_matcher.py)
Chuc nang: Tra cuu va tim kiem thiet ke mau tu co so du lieu phan cung.
Ho tro he thong nhan dien mach, trich xuat cong, ma RTL chuan va testbench.
"""

import os
import re
import json
import unicodedata

ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DuongDanDb = os.path.join(ThuMucGoc, "knowledge_base", "hardware_db.json")
DuongDanQuyTac = os.path.join(ThuMucGoc, "knowledge_base", "reflection_db.json")

# Ho tro tuong thich bien cu
BASE_DIR = ThuMucGoc
DB_PATH = DuongDanDb
REFL_PATH = DuongDanQuyTac

def xoa_dau_tieng_viet(VanBan):
    """Loai bo dau tieng Viet de tim kiem khong dau."""
    VanBanKhongDau = VanBan.replace('đ', 'd').replace('Đ', 'D')
    VanBanKhongDau = unicodedata.normalize('NFKD', VanBanKhongDau).encode('ascii', 'ignore').decode('ascii')
    return VanBanKhongDau.lower()

remove_vietnamese_accents = xoa_dau_tieng_viet

def tach_tu(VanBan):
    """Tach van ban thanh danh sach cac tu khoa co nghia."""
    VanBanSach = xoa_dau_tieng_viet(VanBan)
    DanhSachTu = re.findall(r"[a-z0-9_]+", VanBanSach)
    TuDung = {
        "va", "thi", "la", "cac", "cho", "co", "the", "duoc", "mot", "trong",
        "the", "a", "an", "and", "or", "to", "of", "in", "with", "is", "for",
        "module", "thiet", "ke", "mach", "he", "thong", "dong", "bo"
    }
    return [Tu for Tu in DanhSachTu if len(Tu) > 1 and Tu not in TuDung]

tokenize = tach_tu

# Tap khai niem phan cung de nhan dien kieu mach
KHAI_NIEM_PHAN_CUNG = {
    "vending_machine": {
        "triggers": ["ban nuoc", "vending", "lon nuoc", "15000", "5000", "10000", "thoi tien", "nhan tien"],
        "target_names": ["vending_machine"],
        "target_category": "Control / FSM"
    },
    "traffic_light": {
        "triggers": ["den giao thong", "traffic light", "den do", "den xanh", "nga tu", "di bo"],
        "target_names": ["traffic_light"],
        "target_category": "Control / FSM"
    },
    "elevator": {
        "triggers": ["thang may", "elevator", "tang", "cua thang may", "elevator controller"],
        "target_names": ["fsm", "sequence_detector"],
        "target_category": "Control / FSM"
    },
    "up_down_counter": {
        "triggers": ["dem len xuong", "up down counter", "up down", "len xuong"],
        "target_names": ["up_down_counter"],
        "target_category": "Counter"
    },
    "counter": {
        "triggers": ["bo dem", "mach dem", "counter", "dem 4 bit", "dem 8 bit", "dem 1 bit", "johnson", "ring counter"],
        "target_names": ["counter_12", "JC_counter", "ring_counter", "up_down_counter"],
        "target_category": "Counter"
    },
    "asyn_fifo": {
        "triggers": ["asyn fifo", "bat dong bo fifo", "fifo bat dong bo", "asynchronous fifo"],
        "target_names": ["asyn_fifo"],
        "target_category": "Memory / Storage"
    },
    "fifo": {
        "triggers": ["fifo", "hang doi", "first in first out", "bo dem fifo"],
        "target_names": ["asyn_fifo"],
        "target_category": "Memory / Storage"
    },
    "multi_booth_8bit": {
        "triggers": ["booth multiplier", "nhan booth", "booth", "nhan 8 bit"],
        "target_names": ["multi_booth_8bit", "multi_8bit", "multi_16bit"],
        "target_category": "Arithmetic"
    },
    "multiplier": {
        "triggers": ["bo nhan", "mach nhan", "multiplier", "phep nhan"],
        "target_names": ["multi_8bit", "multi_16bit", "multi_booth_8bit", "multi_pipe_4bit", "multi_pipe_8bit", "float_multi"],
        "target_category": "Arithmetic"
    },
    "adder_bcd": {
        "triggers": ["adder bcd", "cong bcd", "bcd adder"],
        "target_names": ["adder_bcd"],
        "target_category": "Arithmetic"
    },
    "adder": {
        "triggers": ["bo cong", "mach cong", "adder", "full adder", "half adder", "cong 8 bit", "cong 16 bit", "cong 32 bit"],
        "target_names": ["adder_8bit", "adder_16bit", "adder_32bit", "adder_bcd", "adder_pipe_64bit"],
        "target_category": "Arithmetic"
    },
    "divider": {
        "triggers": ["bo chia", "mach chia", "divider", "radix2 div", "chia 16 bit"],
        "target_names": ["div_16bit", "radix2_div"],
        "target_category": "Arithmetic"
    },
    "comparator": {
        "triggers": ["bo so sanh", "mach so sanh", "comparator"],
        "target_names": ["comparator_3bit", "comparator_4bit"],
        "target_category": "Arithmetic"
    },
    "alu": {
        "triggers": ["alu", "arithmetic logic unit", "khoi alu"],
        "target_names": ["alu"],
        "target_category": "Arithmetic"
    },
    "top_soc": {
        "triggers": ["soc", "ai accelerator", "cpu controller", "dma 8237", "ai core"],
        "target_names": ["top_soc"],
        "target_category": "SoC / Processor"
    },
    "barrel_shifter": {
        "triggers": ["barrel shifter", "dich bit", "shifter", "dich trai", "dich phai"],
        "target_names": ["barrel_shifter", "right_shifter", "LFSR"],
        "target_category": "Memory / Storage"
    },
    "frequency_divider": {
        "triggers": ["chia tan", "chia tan so", "freq div", "frequency divider"],
        "target_names": ["freq_div", "freq_divbyeven", "freq_divbyodd", "freq_divbyfrac"],
        "target_category": "Clock & Timing"
    }
}

HARDWARE_CONCEPTS = KHAI_NIEM_PHAN_CUNG

class KnowledgeMatcher:
    """Bo tra cuu tri thuc phan cung tu co so du lieu mau."""

    def __init__(self, DuongDanCoSo=DuongDanDb, DuongDanPhanChieu=DuongDanQuyTac, db_path=None, refl_path=None):
        self.DuongDanDb = db_path if db_path is not None else DuongDanCoSo
        self.DuongDanQuyTac = refl_path if refl_path is not None else DuongDanPhanChieu
        self.db_path = self.DuongDanDb
        self.refl_path = self.DuongDanQuyTac
        self.DanhSachMau = []
        self.QuyTacPhanChieu = []
        self._tai_du_lieu()

    def _tai_du_lieu(self):
        """Doc du lieu tu file JSON."""
        if os.path.exists(self.DuongDanDb):
            with open(self.DuongDanDb, "r", encoding="utf-8", errors="replace") as TepTin:
                self.DanhSachMau = json.load(TepTin)
        if os.path.exists(self.DuongDanQuyTac):
            with open(self.DuongDanQuyTac, "r", encoding="utf-8", errors="replace") as TepTin:
                self.QuyTacPhanChieu = json.load(TepTin)
        self.entries = self.DanhSachMau
        self.reflection_rules = self.QuyTacPhanChieu

    def search(self, VanBanSpec, TopK=3, spec_text=None, top_k=None):
        """Tim kiem mach phu hop nhat trong CSDL tri thuc."""
        VanBanCanTim = spec_text if spec_text is not None else VanBanSpec
        SoLuongCanLay = top_k if top_k is not None else TopK

        if not self.DanhSachMau:
            return None, "CUSTOM", 0.0, []

        VanBanChuanHoa = xoa_dau_tieng_viet(VanBanCanTim)
        TuKhoaTruyVan = tach_tu(VanBanCanTim)
        TapTuKhoa = set(TuKhoaTruyVan)

        # Nhan dien khai niem phan cung
        KhaiNiemKhop = []
        for TenKhaiNiem, DuLieuKhaiNiem in KHAI_NIEM_PHAN_CUNG.items():
            for TuKichHoat in DuLieuKhaiNiem["triggers"]:
                if TuKichHoat in VanBanChuanHoa:
                    KhaiNiemKhop.append(DuLieuKhaiNiem)
                    break

        DanhSachChamDiem = []
        TenDaGap = set()

        for Muc in self.DanhSachMau:
            DiemSo = 0.0
            TenMuc = Muc.get("name", "").lower()
            TenModule = Muc.get("module_name", "").lower()
            DanhMuc = Muc.get("category", "")
            TuKhoaMuc = [Tu.lower() for Tu in Muc.get("keywords", [])]

            # 1. Khop khai niem truc tiep
            for DuLieu in KhaiNiemKhop:
                if TenMuc in DuLieu["target_names"] or TenModule in DuLieu["target_names"]:
                    DiemSo += 1.5
                elif DanhMuc == DuLieu.get("target_category"):
                    DiemSo += 0.4

            # 2. Khop tu khoa voi ten va danh sach keywords
            for Tu in TuKhoaTruyVan:
                if Tu == TenMuc or Tu == TenModule:
                    DiemSo += 0.8
                elif Tu in TenMuc or TenMuc in Tu:
                    DiemSo += 0.35
                if any(Tu in Kw for Kw in TuKhoaMuc):
                    DiemSo += 0.2

            # 3. Khop tu giua spec va keywords cua muc
            TapTuDich = set(tach_tu(TenMuc + " " + " ".join(TuKhoaMuc)))
            GiaoDiem = TapTuKhoa.intersection(TapTuDich)
            if TapTuDich:
                DiemSo += (len(GiaoDiem) / float(len(TapTuDich))) * 0.5

            if DiemSo > 0.25:
                DoTinCay = min(1.0, DiemSo / 3.0)
                DanhSachChamDiem.append((DiemSo, DoTinCay, Muc))

        # Sap xep theo diem cao nhat truoc
        DanhSachChamDiem.sort(key=lambda x: x[0], reverse=True)

        if not DanhSachChamDiem:
            return None, "CUSTOM", 0.0, []

        # Loc cac ban ghi duy nhat theo ten module
        MauDuyNhat = []
        for DiemGoc, DoTinCay, Muc in DanhSachChamDiem:
            TenMod = Muc.get("module_name", Muc.get("name"))
            if TenMod not in TenDaGap:
                TenDaGap.add(TenMod)
                MauDuyNhat.append(Muc)
            if len(MauDuyNhat) >= SoLuongCanLay:
                break

        DiemCaoNhat, DoTinCayCaoNhat, MauTotNhat = DanhSachChamDiem[0]

        if DoTinCayCaoNhat >= 0.70:
            LoaiKhop = "EXACT"
        elif DoTinCayCaoNhat >= 0.35:
            LoaiKhop = "SIMILAR"
        else:
            LoaiKhop = "CUSTOM"

        return MauTotNhat, LoaiKhop, round(DoTinCayCaoNhat, 3), MauDuyNhat

    def get_reflection_guidance(self, ThongBaoLoi=None, error_message=None):
        """Tra cuu huong dan sua loi EDA dua tren quy tac phan chieu."""
        NoiDungLoi = error_message if error_message is not None else (ThongBaoLoi or "")
        DanhSachGoiY = []
        for QuyTac in self.QuyTacPhanChieu:
            MauLoi = QuyTac.get("pattern", "")
            if re.search(MauLoi, NoiDungLoi, re.IGNORECASE):
                DanhSachGoiY.append({
                    "error_type": QuyTac.get("error_type"),
                    "diagnosis": QuyTac.get("diagnosis"),
                    "remedy": QuyTac.get("remedy")
                })
        return DanhSachGoiY

if __name__ == "__main__":
    BoTraCuu = KnowledgeMatcher()
    print("=" * 75)
    print("   KIEM TRA BO TRA CUU TRI THUC PHAN CUNG")
    print("=" * 75)
    DanhSachCauHoi = [
        "Thiết kế máy bán nước tự động nhận 5k và 10k, lon nước giá 15k",
        "Thiết kế hệ thống đèn giao thông ngã tư với đèn đỏ, xanh, vàng và nút cho người đi bộ",
        "Mạch đếm lên xuống (up down counter) 4 bit đồng bộ",
        "Thiết kế bộ nhớ đệm bất đồng bộ FIFO (Asynchronous FIFO)",
        "Thiết kế mạch nhân 8 bit Booth multiplier",
        "Thiết kế bộ cộng BCD (BCD Adder)",
        "Hệ thống SoC AI Accelerator tích hợp CPU, DMA, AI Core và RAM"
    ]
    for CauHoi in DanhSachCauHoi:
        Mau, Loai, DoTinCay, DanhSachMauGoiY = BoTraCuu.search(CauHoi)
        print(f"\n[Truy van]: {CauHoi}")
        print(f" -> Ket qua: [{Loai}] Do tin cay: {DoTinCay*100:.1f}%")
        if Mau:
            print(f" -> Khop: {Mau['id']} ({Mau['name']}) | Nguon: {Mau['source']} | Nhom: {Mau['category']}")
        print(f" -> Top {len(DanhSachMauGoiY)} mau: {', '.join([M['name'] for M in DanhSachMauGoiY])}")
