"""
Module: knowledge_matcher.py
Chuc nang: Tra cuu va tim kiem thiet ke mau tu co so du lieu phan cung.
Kien truc Hybrid Retrieval bang Reciprocal Rank Fusion (RRF):
  Hybrid = Semantic Vector + BM25 + Character 3-gram + KHAI_NIEM_PHAN_CUNG
Ho tro 3 backend tao Semantic Vector theo thu tu uu tien (khong dung torch):
  1. Offline `fastembed` (ONNX CPU) neu may co cai san.
  2. Pre-computed cache `knowledge_base/hardware_embeddings.npz` (numpy) + `gemini-embedding-001`
     khi runtime co `GEMINI_API_KEY` & ket noi mang.
  3. Pure-offline `TfidfVectorizer + TruncatedSVD` (LSA dense vector bang sklearn/numpy)
     lam semantic branch mac dinh khi chua co `.npz`/`fastembed`.
"""

from collections import Counter
import hashlib
import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.request

try:
    import numpy as np
except ImportError:
    np = None

ThuMucGoc = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DuongDanDb = os.path.join(ThuMucGoc, "knowledge_base", "hardware_db.json")
DuongDanQuyTac = os.path.join(ThuMucGoc, "knowledge_base", "reflection_db.json")
DuongDanTeacher = os.path.join(ThuMucGoc, "training", "dataset_teacher_distilled.json")
DuongDanEmbeddings = os.path.join(ThuMucGoc, "knowledge_base", "hardware_embeddings.npz")

# Ho tro tuong thich bien cu
BASE_DIR = ThuMucGoc
DB_PATH = DuongDanDb
REFL_PATH = DuongDanQuyTac
TEACHER_DB_PATH = DuongDanTeacher
EMBEDDINGS_PATH = DuongDanEmbeddings

_PREFIX_BO_QUA_LUU = ("test_", "tc", "web_spec_", "custom_hw_module")
_NGUONG_RAG_TOI_THIEU = 0.28
_SO_DONG_RTL_TOI_DA = 45
_RRF_K = 30.0
_RRF_WEIGHTS = {
    "vector": 1.25,
    "bm25": 1.15,
    "3gram": 0.70,
    "concept": 1.00,
}

# Cache nhe trong RAM cho LSA index theo chu ky corpus (tranh fit lai nhieu lan trong cung process)
_LSA_MEMORY_CACHE = {}


def xoa_dau_tieng_viet(VanBan):
    """Loai bo dau tieng Viet de tim kiem khong dau."""
    if not VanBan:
        return ""
    VanBanStr = str(VanBan)
    VanBanKhongDau = VanBanStr.replace("đ", "d").replace("Đ", "D")
    VanBanKhongDau = unicodedata.normalize("NFKD", VanBanKhongDau).encode("ascii", "ignore").decode("ascii")
    return VanBanKhongDau.lower()


remove_vietnamese_accents = xoa_dau_tieng_viet

_TU_DUNG = {
    "va", "thi", "la", "cac", "cho", "co", "the", "duoc", "mot", "trong",
    "a", "an", "and", "or", "to", "of", "in", "with", "is", "for", "on", "by",
    "module", "thiet", "ke", "mach", "he", "thong", "dong", "bo", "tu", "nay",
    "sau", "theo", "chuan", "hay", "tuong", "ung", "tai", "moi", "khi", "neu",
    "voi", "bang", "nhu", "hoac", "nhung", "se", "da", "dang", "den", "ve",
}


def tach_tu(VanBan):
    """Tach van ban thanh danh sach cac tu khoa co nghia."""
    VanBanSach = xoa_dau_tieng_viet(VanBan)
    DanhSachTu = re.findall(r"[a-z0-9_]+", VanBanSach)
    return [Tu for Tu in DanhSachTu if len(Tu) > 1 and Tu not in _TU_DUNG]


tokenize = tach_tu


def _tach_tu_mo_rong(VanBan):
    """Tach tu cho BM25: giu ca dinh danh ghep va cac thanh phan snake_case/camelCase."""
    VanBanStr = str(VanBan or "")
    VanBanTachCamel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", VanBanStr)
    VanBanSach = xoa_dau_tieng_viet(VanBanTachCamel)
    TokensGoc = re.findall(r"[a-z0-9_]+", VanBanSach)
    KetQua = []
    for Tok in TokensGoc:
        if len(Tok) <= 1 or Tok in _TU_DUNG:
            continue
        KetQua.append(Tok)
        if "_" in Tok:
            for Phan in Tok.split("_"):
                if len(Phan) > 1 and Phan not in _TU_DUNG:
                    KetQua.append(Phan)
    return KetQua


def _tao_3gram(VanBan):
    """Tao tap character 3-gram tu van ban da chuan hoa khong dau."""
    Sach = re.sub(r"[^a-z0-9]+", " ", xoa_dau_tieng_viet(VanBan)).strip()
    if not Sach:
        return frozenset()
    if len(Sach) < 3:
        return frozenset((Sach,))
    return frozenset(Sach[i:i + 3] for i in range(len(Sach) - 2))


def _jaccard_3gram(TapA, TapB):
    """Tinh do tuong dong Jaccard giua hai tap 3-gram."""
    if not TapA or not TapB:
        return 0.0
    Giao = len(TapA & TapB)
    if Giao == 0:
        return 0.0
    Hop = len(TapA | TapB)
    return Giao / float(Hop)


def _chuan_hoa_code_md5(VerilogCode):
    """Tinh MD5 cua ma Verilog sau khi loai bo comment va toan bo khoang trang."""
    if not VerilogCode:
        return ""
    Sach = re.sub(r"/\*.*?\*/", "", str(VerilogCode), flags=re.DOTALL)
    Sach = re.sub(r"//[^\r\n]*", "", Sach)
    Sach = re.sub(r"\s+", "", Sach)
    if not Sach:
        return ""
    return hashlib.md5(Sach.encode("utf-8")).hexdigest()


def _trich_rtl_tu_output(OutputText):
    """Trich xuat code Verilog va phan CoT tu truong output cua Gemini Teacher."""
    if not OutputText:
        return "", ""
    Text = str(OutputText)
    FenceMatches = list(
        re.finditer(r"```(?:verilog|systemverilog|sv)?\s*(.*?)```", Text, flags=re.IGNORECASE | re.DOTALL)
    )
    if FenceMatches:
        Chosen = FenceMatches[-1]
        for M in FenceMatches:
            if "module " in M.group(1):
                Chosen = M
                break
        Rtl = Chosen.group(1).strip()
        Cot = Text[:Chosen.start()].strip()
        return Rtl, Cot

    ModMatch = re.search(r"(\bmodule\b.*?\bendmodule\b)", Text, flags=re.DOTALL)
    if ModMatch:
        return ModMatch.group(1).strip(), Text[:ModMatch.start()].strip()

    return Text.strip(), ""


# Cau noi ngu nghia song ngu Anh-Viet dung rieng cho nhanh Semantic Vector
# (giup hieu y mo ta gian tiep/song ngu ma khong lam nhieu baseline BM25/keyword)
_CAU_NOI_NGU_NGHIA = (
    (
        ("uart", "start bit", "stop bit", "baud", "baudrate", "khung truyen", "truyen noi tiep bat dong bo", "nhan noi tiep bat dong bo", "asynchronous serial", "tx_serial", "rx_serial"),
        "uart serial asynchronous transmitter receiver start stop bit baud",
    ),
    (
        ("spi", "mosi", "miso", "sclk", "chip select", "slave select", "4 day", "truyen noi tiep dong bo", "synchronous serial"),
        "spi serial peripheral interface master slave mosi miso sclk cs",
    ),
    (
        ("i2c", "sda", "scl", "open drain", "two wire", "2 day"),
        "i2c inter integrated circuit sda scl two wire serial bus",
    ),
    (
        ("fifo", "vao truoc ra truoc", "first in first out", "hang doi", "full", "empty", "bo dem du lieu", "circular queue"),
        "fifo first in first out queue buffer full empty read write pointer",
    ),
    (
        ("gray", "1 bit lien tiep", "khac nhau 1 bit", "khac nhau dung 1 bit", "mot bit lien tiep", "single bit transition", "adjacent states differ by one bit"),
        "gray code counter binary to gray converter single bit change",
    ),
    (
        ("bcd", "7 doan", "7 thanh", "seven segment", "7seg", "anode", "cathode", "hien thi so", "led bay doan"),
        "bcd to 7seg seven segment display anode cathode digit decoder",
    ),
    (
        ("bcd", "0 den 9", "00 den 59", "hang don vi", "hang chuc", "thap phan ma hoa nhi phan", "double dabble"),
        "bcd decimal counter converter tens ones double dabble",
    ),
    (
        ("dem len xuong", "up down", "len xuong", "tang giam", "dao chieu dem", "bidirectional"),
        "up down bidirectional counter increment decrement",
    ),
    (
        ("pwm", "dieu rong xung", "do rong xung", "chu ky nhiem vu", "duty cycle", "pulse width", "do sang led", "toc do dong co", "servo"),
        "pwm pulse width modulation duty cycle motor servo led brightness",
    ),
    (
        ("chong rung", "khu rung", "chong doi", "nay tiep diem", "tiep diem co khi", "nut bam", "nut nhan", "switch bounce", "debounc", "mechanical switch"),
        "button debouncer switch bounce filter stable key press",
    ),
    (
        ("watchdog", "wdt", "giam sat", "treo he thong", "tu dong reset", "dat lai he thong", "het thoi gian cho", "timeout reset", "system hang"),
        "watchdog timer wdt monitor timeout automatic system reset",
    ),
    (
        ("khoa so", "mat khau", "mo khoa", "passcode", "password", "safe lock", "digital lock", "pin code"),
        "digital safe lock password sequence fsm unlock alarm",
    ),
    (
        ("den giao thong", "traffic light", "nga tu", "den do", "den xanh", "den vang", "di bo"),
        "traffic light controller intersection red yellow green pedestrian fsm",
    ),
    (
        ("ban nuoc", "ban ve", "vending", "thoi tien", "tra tien thua", "dong xu", "coin", "dispense"),
        "vending machine coin acceptor dispense change fsm",
    ),
    (
        ("uu tien", "priority", "8 sang 3", "8to3", "cao nhat", "highest priority", "encode"),
        "priority encoder 8to3 highest priority request binary index",
    ),
    (
        ("giai ma", "decoder", "3 sang 8", "2 sang 4", "3to8", "2to4", "one hot", "chon 1 trong", "dia chi bo nho"),
        "decoder demux 2to4 3to8 address line one hot select",
    ),
    (
        ("thanh ghi dich", "shift register", "dich bit", "sipo", "piso", "noi tiep sang song song", "song song sang noi tiep", "barrel shifter", "dich vong"),
        "shift register sipo piso universal barrel shifter serial parallel",
    ),
    (
        ("chia tan", "chia xung", "freq div", "frequency divider", "1hz", "prescaler", "giam tan so"),
        "frequency clock divider prescaler 1hz even odd fractional",
    ),
    (
        ("alu", "so hoc va logic", "arithmetic logic", "phep toan", "cong tru", "opcode", "co tran"),
        "alu arithmetic logic unit add sub and or xor overflow zero flag",
    ),
    (
        ("bo nhan", "phep nhan", "multiplier", "booth", "tich hai so", "product"),
        "multiplier booth multiplication product arithmetic",
    ),
    (
        ("bo chia", "phep chia", "divider", "thuong so", "so du", "quotient", "remainder", "radix2"),
        "divider radix2 division quotient remainder arithmetic",
    ),
    (
        ("bo so sanh", "so sanh", "comparator", "lon hon", "nho hon", "bang nhau", "magnitude"),
        "comparator magnitude greater equal less comparison",
    ),
    (
        ("bo cong", "mach cong", "adder", "cong nhi phan", "half adder", "full adder", "carry"),
        "adder binary addition sum carry half full pipeline",
    ),
)


def _mo_rong_ngu_nghia_vector(VanBan):
    """Chuan hoa khong dau, tach camelCase/snake_case va bo sung the ngu nghia song ngu cho nhanh Vector."""
    if not VanBan:
        return ""
    VanBanStr = str(VanBan)
    VanBanTachCamel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", VanBanStr)
    Sach = xoa_dau_tieng_viet(VanBanTachCamel)
    Sach = Sach.replace("_", " ")
    TheBoSung = []
    for Triggers, Tags in _CAU_NOI_NGU_NGHIA:
        for Trig in Triggers:
            if Trig in Sach:
                TheBoSung.append(Tags)
                break
    if TheBoSung:
        return f"{Sach} {' '.join(TheBoSung)}"
    return Sach


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
    """Bo tra cuu tri thuc phan cung voi Hybrid RRF (Semantic Vector + BM25 + 3-gram + Concept)."""

    def __init__(self, DuongDanCoSo=DuongDanDb, DuongDanPhanChieu=DuongDanQuyTac,
                 db_path=None, refl_path=None, teacher_path=None,
                 embeddings_path=None, vector_backend="auto"):
        self.DuongDanDb = db_path if db_path is not None else DuongDanCoSo
        self.DuongDanQuyTac = refl_path if refl_path is not None else DuongDanPhanChieu
        self.DuongDanTeacher = teacher_path if teacher_path is not None else DuongDanTeacher
        self.DuongDanEmbeddings = embeddings_path if embeddings_path is not None else DuongDanEmbeddings
        self.db_path = self.DuongDanDb
        self.refl_path = self.DuongDanQuyTac
        self.teacher_path = self.DuongDanTeacher
        self.embeddings_path = self.DuongDanEmbeddings
        self._requested_vector_backend = str(vector_backend or "auto").strip().lower()

        self.DanhSachMau = []
        self.TeacherMau = []
        self.QuyTacPhanChieu = []
        self._corpus = []
        self._db_code_hashes = set()
        self._inverted = {}
        self._idf = {}
        self._doc_tfs = []
        self._doc_lens = []
        self._avgdl = 1.0
        self._doc_label_3grams = []
        self._doc_name_3grams = []
        self._doc_kw_tokens = []
        self._doc_meta = []

        # Trang thai nhanh Semantic Vector
        self.vector_backend = "none"
        self._doc_vectors = None
        self._doc_vector_mask = None
        self._fastembed_model = None
        self._lsa_vectorizer = None
        self._lsa_svd = None
        self._corpus_signature = ""

        self._tai_du_lieu()

    def _tai_du_lieu(self):
        """Doc du lieu tu file JSON chinh, quy tac phan chieu va index Gemini Teacher (trong RAM)."""
        self.DanhSachMau = []
        self.TeacherMau = []
        self.QuyTacPhanChieu = []

        if self.DuongDanDb and os.path.exists(self.DuongDanDb):
            with open(self.DuongDanDb, "r", encoding="utf-8", errors="replace") as TepTin:
                DuLieuDb = json.load(TepTin)
                if isinstance(DuLieuDb, list):
                    self.DanhSachMau = DuLieuDb

        if self.DuongDanQuyTac and os.path.exists(self.DuongDanQuyTac):
            with open(self.DuongDanQuyTac, "r", encoding="utf-8", errors="replace") as TepTin:
                DuLieuQuyTac = json.load(TepTin)
                if isinstance(DuLieuQuyTac, list):
                    self.QuyTacPhanChieu = DuLieuQuyTac

        if self.DuongDanTeacher and os.path.exists(self.DuongDanTeacher):
            try:
                with open(self.DuongDanTeacher, "r", encoding="utf-8", errors="replace") as TepTin:
                    DuLieuTeacher = json.load(TepTin)
                if isinstance(DuLieuTeacher, list):
                    for Idx, Item in enumerate(DuLieuTeacher):
                        if not isinstance(Item, dict):
                            continue
                        ModName = str(Item.get("module_name") or Item.get("name") or f"teacher_mod_{Idx}").strip()
                        SpecInput = str(Item.get("input") or Item.get("spec") or "").strip()
                        RtlCode, CotText = _trich_rtl_tu_output(Item.get("output", ""))
                        if not RtlCode:
                            continue
                        Cat = str(Item.get("category") or "Teacher Distilled")
                        Src = str(Item.get("source") or "Gemini Teacher Distilled")
                        Keywords = list(dict.fromkeys(_tach_tu_mo_rong(f"{ModName} {Cat} {SpecInput.splitlines()[0] if SpecInput else ''}")))
                        self.TeacherMau.append({
                            "id": Item.get("id", f"teacher_{Idx}"),
                            "name": ModName,
                            "module_name": ModName,
                            "source": Src,
                            "category": Cat,
                            "spec": SpecInput,
                            "golden_rtl": RtlCode,
                            "cot": CotText,
                            "keywords": Keywords[:24],
                            "_in_ram_teacher": True,
                        })
            except (OSError, ValueError):
                self.TeacherMau = []

        self.entries = self.DanhSachMau
        self.reflection_rules = self.QuyTacPhanChieu
        self._xay_dung_chi_muc()

    def _xay_dung_chi_muc(self):
        """Xay dung chi muc BM25, IDF, 3-gram, Keyword va Semantic Vector cho kho tri thuc."""
        self._corpus = list(self.DanhSachMau) + list(self.TeacherMau)
        self._db_code_hashes = set()
        for Muc in self.DanhSachMau:
            CodeHash = _chuan_hoa_code_md5(Muc.get("golden_rtl", ""))
            if CodeHash:
                self._db_code_hashes.add(CodeHash)

        N = len(self._corpus)
        self._inverted = {}
        self._idf = {}
        self._doc_tfs = []
        self._doc_lens = []
        self._doc_label_3grams = []
        self._doc_name_3grams = []
        self._doc_kw_tokens = []
        self._doc_meta = []

        if N == 0:
            self._avgdl = 1.0
            self.vector_backend = "none"
            self._doc_vectors = None
            self._doc_vector_mask = None
            return

        DocFreq = Counter()
        SigHasher = hashlib.md5()
        for Idx, Muc in enumerate(self._corpus):
            TenMuc = str(Muc.get("name") or "")
            TenModule = str(Muc.get("module_name") or "")
            DanhMuc = str(Muc.get("category") or "")
            Spec = str(Muc.get("spec") or "")
            TuKhoa = Muc.get("keywords") or []
            if not isinstance(TuKhoa, list):
                TuKhoa = [str(TuKhoa)]
            TuKhoaStr = " ".join(str(Kw) for Kw in TuKhoa)

            SigHasher.update(f"{Muc.get('id','')}|{TenModule}|{len(Spec)}|".encode("utf-8", errors="ignore"))

            Tf = Counter()
            for Tok in _tach_tu_mo_rong(f"{TenMuc} {TenModule}"):
                Tf[Tok] += 3
            for Tok in _tach_tu_mo_rong(TuKhoaStr):
                Tf[Tok] += 2
            for Tok in _tach_tu_mo_rong(DanhMuc):
                Tf[Tok] += 1
            for Tok in _tach_tu_mo_rong(Spec):
                Tf[Tok] += 1

            self._doc_tfs.append(Tf)
            DocLen = sum(Tf.values())
            self._doc_lens.append(DocLen)

            KwSet = set(tach_tu(f"{TenMuc} {TenModule} {TuKhoaStr} {DanhMuc} {Spec[:500]}"))
            self._doc_kw_tokens.append(KwSet)

            for Term, Count in Tf.items():
                DocFreq[Term] += 1
                self._inverted.setdefault(Term, []).append((Idx, Count))

            DongDauSpec = ""
            for Line in Spec.splitlines():
                LineSach = Line.lstrip("#").strip()
                if LineSach:
                    DongDauSpec = LineSach
                    break

            NhanDayDu = f"{TenMuc} {TenModule} {TuKhoaStr} {DongDauSpec}"
            NhanNgan = f"{TenMuc} {TenModule} {TuKhoaStr}"
            self._doc_label_3grams.append(_tao_3gram(NhanDayDu))
            self._doc_name_3grams.append(_tao_3gram(NhanNgan))

            TenModGoc = TenModule.lower()
            TenModChuan = TenModGoc[9:] if TenModGoc.startswith("verified_") else TenModGoc
            self._doc_meta.append({
                "name_lower": TenMuc.lower(),
                "mod_lower": TenModGoc,
                "mod_norm": TenModChuan,
                "cat": DanhMuc,
                "cat_lower": DanhMuc.lower(),
                "cat_tokens": set(_tach_tu_mo_rong(DanhMuc)),
            })

        self._corpus_signature = f"{N}_{SigHasher.hexdigest()}"
        self._avgdl = max(1.0, sum(self._doc_lens) / float(N))
        for Term, Df in DocFreq.items():
            self._idf[Term] = math.log(1.0 + (N - Df + 0.5) / (Df + 0.5))

        self._khoi_tao_vector_backend()

    @staticmethod
    def _chuan_hoa_vector_ma_tran(MaTran):
        """Chuan hoa L2 tung hang vector thanh float32."""
        Arr = np.asarray(MaTran, dtype=np.float32)
        if Arr.ndim == 1:
            Norm = float(np.linalg.norm(Arr))
            return (Arr / Norm) if Norm > 1e-12 else Arr
        Norms = np.linalg.norm(Arr, axis=1, keepdims=True)
        Mask = (Norms[:, 0] > 1e-12)
        SafeNorms = np.where(Norms > 1e-12, Norms, 1.0)
        return Arr / SafeNorms, Mask

    def _tao_van_ban_vector(self, Muc):
        """Tao van ban dai dien ngu nghia cho 1 mau trong kho tri thuc."""
        TenMuc = str(Muc.get("name") or "")
        TenModule = str(Muc.get("module_name") or "")
        DanhMuc = str(Muc.get("category") or "")
        Spec = str(Muc.get("spec") or "")[:700]
        TuKhoa = Muc.get("keywords") or []
        if not isinstance(TuKhoa, list):
            TuKhoa = [str(TuKhoa)]
        TuKhoaStr = " ".join(str(Kw) for Kw in TuKhoa)
        VanBanGop = f"{TenMuc} {TenModule} {TenModule} {DanhMuc} {TuKhoaStr} {Spec}"
        return _mo_rong_ngu_nghia_vector(VanBanGop)

    def _khoi_tao_vector_backend(self):
        """Chon tu dong 1 trong 3 backend vector theo thu tu uu tien (khong dung torch)."""
        self.vector_backend = "none"
        self._doc_vectors = None
        self._doc_vector_mask = None
        self._fastembed_model = None
        self._lsa_vectorizer = None
        self._lsa_svd = None

        Req = self._requested_vector_backend
        if Req == "none" or np is None or not self._corpus:
            return

        # 1. Uu tien 1: Offline fastembed (ONNX CPU, tuyet doi khong import torch)
        if Req in ("auto", "fastembed"):
            if self._thu_khoi_tao_fastembed():
                return

        # 2. Uu tien 2: Pre-computed cache hardware_embeddings.npz + gemini-embedding-001
        if Req in ("auto", "npz_gemini", "npz", "gemini"):
            if self._thu_khoi_tao_npz_gemini(allow_without_key=(Req != "auto")):
                return

        # 3. Uu tien 3 (Mac dinh pure-offline): TfidfVectorizer + TruncatedSVD (LSA)
        if Req in ("auto", "lsa", "lsa_tfidf_svd", "tfidf_svd"):
            self._khoi_tao_lsa_tfidf_svd()

    def _thu_khoi_tao_fastembed(self):
        """Thu nap backend ONNX CPU `fastembed` neu da cai san va dung duoc offline."""
        try:
            from fastembed import TextEmbedding
        except Exception:
            return False

        try:
            # Chi thu nap neu model da co san hoac TextEmbedding khoi tao nhanh thanh cong
            try:
                Model = TextEmbedding(local_files_only=True)
            except TypeError:
                Model = TextEmbedding()
            Docs = [self._tao_van_ban_vector(M) for M in self._corpus]
            EmbList = list(Model.embed(Docs))
            if not EmbList or len(EmbList) != len(self._corpus):
                return False
            Normed, Mask = self._chuan_hoa_vector_ma_tran(np.vstack(EmbList))
            self._fastembed_model = Model
            self._doc_vectors = Normed
            self._doc_vector_mask = Mask
            self.vector_backend = "fastembed"
            return True
        except Exception:
            self._fastembed_model = None
            return False

    def _thu_khoi_tao_npz_gemini(self, allow_without_key=False):
        """Thu nap pre-computed cache `hardware_embeddings.npz` va kiem tra GEMINI_API_KEY."""
        if not self.DuongDanEmbeddings or not os.path.isfile(self.DuongDanEmbeddings):
            return False

        ApiKey = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not ApiKey and not allow_without_key:
            return False

        try:
            with np.load(self.DuongDanEmbeddings, allow_pickle=False) as Cache:
                Mat = None
                for Key in ("embeddings", "vectors", "corpus_embeddings", "matrix"):
                    if Key in Cache:
                        Mat = Cache[Key]
                        break
                if Mat is None:
                    for Key in Cache.files:
                        Arr = Cache[Key]
                        if getattr(Arr, "ndim", 0) == 2:
                            Mat = Arr
                            break
                if Mat is None or getattr(Mat, "ndim", 0) != 2 or Mat.shape[0] == 0:
                    return False

                Dim = int(Mat.shape[1])
                Aligned = np.zeros((len(self._corpus), Dim), dtype=np.float32)
                IdsArr = None
                for IdKey in ("ids", "doc_ids", "module_names"):
                    if IdKey in Cache:
                        IdsArr = [str(X) for X in Cache[IdKey].tolist()]
                        break

                if IdsArr and len(IdsArr) == Mat.shape[0]:
                    IdToRow = {DocId: RowIdx for RowIdx, DocId in enumerate(IdsArr)}
                    MatchedRows = 0
                    for DocIdx, Muc in enumerate(self._corpus):
                        CandKeys = (
                            str(Muc.get("id") or ""),
                            str(Muc.get("module_name") or ""),
                            str(Muc.get("name") or ""),
                        )
                        for Ck in CandKeys:
                            if Ck and Ck in IdToRow:
                                Aligned[DocIdx] = Mat[IdToRow[Ck]]
                                MatchedRows += 1
                                break
                    if MatchedRows == 0:
                        return False
                elif Mat.shape[0] == len(self._corpus):
                    Aligned[:] = Mat
                elif Mat.shape[0] == len(self.DanhSachMau):
                    Aligned[:len(self.DanhSachMau)] = Mat
                else:
                    Limit = min(len(self._corpus), int(Mat.shape[0]))
                    Aligned[:Limit] = Mat[:Limit]

            Normed, Mask = self._chuan_hoa_vector_ma_tran(Aligned)
            self._doc_vectors = Normed
            self._doc_vector_mask = Mask
            self.vector_backend = "npz_gemini"
            return True
        except Exception:
            return False

    def _khoi_tao_lsa_tfidf_svd(self):
        """Khoi tao pure-offline TfidfVectorizer + TruncatedSVD (LSA dense vector)."""
        if np is None or not self._corpus:
            return False

        CacheKey = (self._corpus_signature, "lsa_tfidf_svd")
        Cached = _LSA_MEMORY_CACHE.get(CacheKey)
        if Cached is not None:
            Vec, Svd, DocVecs, DocMask = Cached
            self._lsa_vectorizer = Vec
            self._lsa_svd = Svd
            self._doc_vectors = DocVecs
            self._doc_vector_mask = DocMask
            self.vector_backend = "lsa_tfidf_svd"
            return True

        try:
            from sklearn.decomposition import TruncatedSVD
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.pipeline import FeatureUnion
        except Exception:
            return False

        Docs = [self._tao_van_ban_vector(M) for M in self._corpus]
        try:
            WordVec = TfidfVectorizer(
                ngram_range=(1, 2),
                token_pattern=r"(?u)\b[a-z0-9_]+\b",
                min_df=1,
                max_df=0.92,
                max_features=4500,
                sublinear_tf=True,
            )
            CharVec = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 4),
                min_df=1 if len(Docs) < 10 else 2,
                max_df=0.92,
                max_features=4500,
                sublinear_tf=True,
            )
            UnionVec = FeatureUnion([("word", WordVec), ("char", CharVec)])
            X = UnionVec.fit_transform(Docs)

            NDocs, NFeats = X.shape
            MaxComp = min(96, NDocs - 1, NFeats - 1)
            if MaxComp >= 2:
                Svd = TruncatedSVD(n_components=MaxComp, n_iter=3, random_state=42)
                Z = Svd.fit_transform(X)
            else:
                Svd = None
                Z = X.toarray()

            Normed, Mask = self._chuan_hoa_vector_ma_tran(Z)
            self._lsa_vectorizer = UnionVec
            self._lsa_svd = Svd
            self._doc_vectors = Normed
            self._doc_vector_mask = Mask
            self.vector_backend = "lsa_tfidf_svd"

            if len(_LSA_MEMORY_CACHE) > 4:
                _LSA_MEMORY_CACHE.clear()
            _LSA_MEMORY_CACHE[CacheKey] = (UnionVec, Svd, Normed, Mask)
            return True
        except Exception:
            self._lsa_vectorizer = None
            self._lsa_svd = None
            self._doc_vectors = None
            self._doc_vector_mask = None
            self.vector_backend = "none"
            return False

    def _embed_query_gemini(self, QueryText):
        """Goi gemini-embedding-001 qua google.genai hoac REST API voi timeout ngan."""
        ApiKey = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not ApiKey:
            return None

        try:
            from google import genai
            Client = genai.Client(api_key=ApiKey)
            Resp = Client.models.embed_content(model="gemini-embedding-001", contents=QueryText)
            Vals = Resp.embeddings[0].values
            return self._chuan_hoa_vector_ma_tran(np.asarray(Vals, dtype=np.float32))
        except Exception:
            pass

        Url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-embedding-001:embedContent?key={ApiKey}"
        )
        Payload = json.dumps({
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": QueryText}]},
        }).encode("utf-8")
        Req = urllib.request.Request(
            Url,
            data=Payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(Req, timeout=5.0) as Resp:
                Data = json.loads(Resp.read().decode("utf-8"))
            Vals = (Data.get("embedding") or {}).get("values")
            if not Vals:
                return None
            return self._chuan_hoa_vector_ma_tran(np.asarray(Vals, dtype=np.float32))
        except (OSError, urllib.error.URLError, ValueError, KeyError):
            return None

    def _embed_query(self, VanBanCanTim):
        """Tao vector truy van tuong ung voi backend dang hoat dong."""
        if np is None or self.vector_backend == "none":
            return None

        QueryVecText = _mo_rong_ngu_nghia_vector(VanBanCanTim)

        if self.vector_backend == "fastembed" and self._fastembed_model is not None:
            try:
                Emb = next(iter(self._fastembed_model.embed([QueryVecText])))
                return self._chuan_hoa_vector_ma_tran(np.asarray(Emb, dtype=np.float32))
            except Exception:
                return None

        if self.vector_backend == "npz_gemini":
            Vec = self._embed_query_gemini(str(VanBanCanTim))
            if Vec is not None and self._doc_vectors is not None and Vec.shape[0] == self._doc_vectors.shape[1]:
                return Vec
            # Fallback runtime ve LSA neu mat mang / loi API khi o che do auto
            if self._requested_vector_backend == "auto" and self._khoi_tao_lsa_tfidf_svd():
                QueryVecText = _mo_rong_ngu_nghia_vector(VanBanCanTim)
            else:
                return None

        if self.vector_backend == "lsa_tfidf_svd" and self._lsa_vectorizer is not None:
            try:
                X = self._lsa_vectorizer.transform([QueryVecText])
                Z = self._lsa_svd.transform(X) if self._lsa_svd is not None else X.toarray()
                QVec = self._chuan_hoa_vector_ma_tran(Z[0])
                if float(np.linalg.norm(QVec)) <= 1e-12:
                    return None
                return QVec
            except Exception:
                return None

        return None

    def get_vector_backend_info(self):
        """Tra ve thong tin trang thai backend vector dang hoat dong."""
        Shape = tuple(self._doc_vectors.shape) if self._doc_vectors is not None else (0, 0)
        return {
            "backend": self.vector_backend,
            "corpus_size": len(self._corpus),
            "vector_shape": Shape,
            "has_npz_cache": bool(self.DuongDanEmbeddings and os.path.isfile(self.DuongDanEmbeddings)),
            "has_gemini_key": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        }

    @staticmethod
    def _khoa_khop_khai_niem(VanBanChuanHoa):
        """Nhan dien cac khai niem phan cung trong van ban da bo dau."""
        KhaiNiemKhop = []
        for TenKhaiNiem, DuLieuKhaiNiem in KHAI_NIEM_PHAN_CUNG.items():
            for TuKichHoat in DuLieuKhaiNiem["triggers"]:
                if re.search(r"(?<![a-z0-9])" + re.escape(TuKichHoat) + r"(?![a-z0-9])", VanBanChuanHoa):
                    KhaiNiemKhop.append((TenKhaiNiem.lower(), DuLieuKhaiNiem))
                    break
        return KhaiNiemKhop

    @staticmethod
    def _khoa_loai_trung(Muc):
        """Tao khoa dinh danh duy nhat de loc Top-K khong bi trung lap."""
        TenMod = str(Muc.get("module_name") or "").strip()
        TenMuc = str(Muc.get("name") or "").strip()
        if TenMod.lower() in ("", "refmodule", "topmodule"):
            return ("name", TenMuc.lower())
        ModNorm = TenMod.lower()
        if ModNorm.startswith("verified_"):
            ModNorm = ModNorm[9:]
        return ("mod", ModNorm)

    def _tinh_diem_bm25_va_khai_niem(self, VanBanCanTim):
        """Tinh diem cho tung nhanh thanh phan: BM25, 3-gram, Concept va Semantic Vector."""
        VanBanChuanHoa = xoa_dau_tieng_viet(VanBanCanTim)
        TuKhoaTruyVan = _tach_tu_mo_rong(VanBanCanTim)
        TruyVanDuyNhat = list(dict.fromkeys(TuKhoaTruyVan))
        GramTruyVan = _tao_3gram(VanBanCanTim)
        KhaiNiemKhop = self._khoa_khop_khai_niem(VanBanChuanHoa)

        # 1. BM25 qua inverted index
        K1 = 1.5
        B = 0.75
        Bm25Raw = {}
        MatchedIdf = {}
        OovIdf = math.log(1.0 + (len(self._corpus) + 0.5) / 0.5)
        TotalQueryIdf = sum(self._idf.get(Term, OovIdf) for Term in TruyVanDuyNhat)

        for Term in TruyVanDuyNhat:
            Idf = self._idf.get(Term)
            if Idf is None:
                continue
            for DocIdx, Tf in self._inverted.get(Term, ()):
                Dl = self._doc_lens[DocIdx]
                TuSo = Tf * (K1 + 1.0)
                MauSo = Tf + K1 * (1.0 - B + B * (Dl / self._avgdl))
                Bm25Raw[DocIdx] = Bm25Raw.get(DocIdx, 0.0) + Idf * (TuSo / MauSo)
                MatchedIdf[DocIdx] = MatchedIdf.get(DocIdx, 0.0) + Idf

        Bm25NormMap = {}
        for Idx, Raw in Bm25Raw.items():
            IdfRecall = (MatchedIdf.get(Idx, 0.0) / TotalQueryIdf) if TotalQueryIdf > 0 else 0.0
            Bm25Sat = Raw / (Raw + 6.0)
            Bm25NormMap[Idx] = 0.55 * IdfRecall + 0.45 * Bm25Sat

        # 2. Concept + Exact Name
        ConceptMap = {}
        ExactBonusMap = {}
        TargetNamesAll = {T.lower() for _, D in KhaiNiemKhop for T in D["target_names"]}
        TargetCatsAll = {D.get("target_category", "") for _, D in KhaiNiemKhop}

        for Idx, Meta in enumerate(self._doc_meta):
            ConceptScore = 0.0
            if KhaiNiemKhop and (
                Meta["name_lower"] in TargetNamesAll
                or Meta["mod_lower"] in TargetNamesAll
                or Meta["mod_norm"] in TargetNamesAll
                or Meta["cat"] in TargetCatsAll
                or any(
                    set(_tach_tu_mo_rong(D.get("target_category", ""))) & Meta["cat_tokens"]
                    for _, D in KhaiNiemKhop
                )
            ):
                for TenKhaiNiem, DuLieu in KhaiNiemKhop:
                    Targets = {T.lower() for T in DuLieu["target_names"]}
                    TargetCatTokens = set(_tach_tu_mo_rong(DuLieu.get("target_category", "")))
                    if (
                        Meta["name_lower"] == TenKhaiNiem
                        or Meta["mod_lower"] == TenKhaiNiem
                        or Meta["mod_norm"] == TenKhaiNiem
                    ):
                        ConceptScore = max(ConceptScore, 1.0)
                    elif (
                        Meta["name_lower"] in Targets
                        or Meta["mod_lower"] in Targets
                        or Meta["mod_norm"] in Targets
                    ):
                        ConceptScore = max(ConceptScore, 0.55)
                    elif Meta["cat"] == DuLieu.get("target_category") or (
                        TargetCatTokens and (TargetCatTokens & Meta["cat_tokens"])
                    ):
                        ConceptScore = max(ConceptScore, 0.35)

            ExactNameBonus = 0.0
            for CandName in (Meta["name_lower"], Meta["mod_norm"]):
                if len(CandName) >= 3 and CandName not in ("refmodule", "topmodule"):
                    if re.search(r"(?<![a-z0-9_])" + re.escape(CandName) + r"(?![a-z0-9_])", VanBanChuanHoa):
                        ExactNameBonus = 0.25
                        break

            if ConceptScore > 0.0:
                ConceptMap[Idx] = ConceptScore
            if ExactNameBonus > 0.0:
                ExactBonusMap[Idx] = ExactNameBonus

        return {
            "van_ban_chuan": VanBanChuanHoa,
            "gram_truy_van": GramTruyVan,
            "bm25_raw": Bm25Raw,
            "bm25_norm": Bm25NormMap,
            "concept": ConceptMap,
            "exact_bonus": ExactBonusMap,
        }

    def _tinh_diem_vector(self, VanBanCanTim):
        """Tinh cosine similarity giua truy van va toan bo kho tri thuc (co loc nhieu OOV)."""
        if self._doc_vectors is None or np is None:
            return {}

        # Chan truy van vo nghia / ngoai tu dien (vd: 'xyzzy_khong_ton_tai_99999')
        TruyVanTokens = list(dict.fromkeys(_tach_tu_mo_rong(VanBanCanTim)))
        if TruyVanTokens and self.vector_backend == "lsa_tfidf_svd":
            SoTuBiet = sum(1 for T in TruyVanTokens if T in self._idf)
            if SoTuBiet == 0 or (len(TruyVanTokens) >= 3 and SoTuBiet <= 1 and (SoTuBiet / float(len(TruyVanTokens))) <= 0.35):
                return {}

        QVec = self._embed_query(VanBanCanTim)
        if QVec is None:
            return {}
        Sims = (self._doc_vectors @ QVec).ravel()
        if self._doc_vector_mask is not None:
            Sims = np.where(self._doc_vector_mask, Sims, 0.0)
        return {int(Idx): float(Score) for Idx, Score in enumerate(Sims) if Score > 0.0}

    def _cham_diem_keyword(self, VanBanCanTim):
        """Che do co dien (Keyword overlap + KHAI_NIEM_PHAN_CUNG), dung lam baseline benchmark."""
        if not self._corpus or not VanBanCanTim or not str(VanBanCanTim).strip():
            return []

        VanBanChuanHoa = xoa_dau_tieng_viet(VanBanCanTim)
        QueryTokens = set(tach_tu(VanBanCanTim))
        KhaiNiemKhop = self._khoa_khop_khai_niem(VanBanChuanHoa)
        if not QueryTokens and not KhaiNiemKhop:
            return []

        DanhSach = []
        for Idx, Meta in enumerate(self._doc_meta):
            DocTokens = self._doc_kw_tokens[Idx]
            Overlap = len(QueryTokens & DocTokens)
            Recall = (Overlap / float(len(QueryTokens))) if QueryTokens else 0.0
            Jaccard = (Overlap / float(len(QueryTokens | DocTokens))) if (QueryTokens or DocTokens) else 0.0

            ConceptScore = 0.0
            for TenKhaiNiem, DuLieu in KhaiNiemKhop:
                Targets = {T.lower() for T in DuLieu["target_names"]}
                if Meta["name_lower"] == TenKhaiNiem or Meta["mod_norm"] == TenKhaiNiem:
                    ConceptScore = max(ConceptScore, 1.0)
                elif Meta["name_lower"] in Targets or Meta["mod_norm"] in Targets:
                    ConceptScore = max(ConceptScore, 0.55)
                elif Meta["cat"] == DuLieu.get("target_category"):
                    ConceptScore = max(ConceptScore, 0.30)

            ExactBonus = 0.0
            for CandName in (Meta["name_lower"], Meta["mod_norm"]):
                if len(CandName) >= 3 and CandName not in ("refmodule", "topmodule"):
                    if re.search(r"(?<![a-z0-9_])" + re.escape(CandName) + r"(?![a-z0-9_])", VanBanChuanHoa):
                        ExactBonus = 0.25
                        break

            if Overlap == 0 and ConceptScore == 0.0 and ExactBonus == 0.0:
                continue

            Score = min(1.0, 0.55 * Recall + 0.25 * Jaccard + 0.25 * ConceptScore + ExactBonus)
            if Score >= 0.15:
                DanhSach.append((Score + Overlap * 0.01, Score, self._corpus[Idx]))

        DanhSach.sort(key=lambda X: (X[1], X[0]), reverse=True)
        return DanhSach

    def _cham_diem_bm25(self, VanBanCanTim):
        """Che do thuan BM25 (khong semantic vector, khong 3-gram, khong RRF)."""
        if not self._corpus or not VanBanCanTim or not str(VanBanCanTim).strip():
            return []
        TinHieu = self._tinh_diem_bm25_va_khai_niem(VanBanCanTim)
        Bm25Raw = TinHieu["bm25_raw"]
        Bm25Norm = TinHieu["bm25_norm"]
        if not Bm25Raw:
            return []
        DanhSach = []
        for Idx, Raw in Bm25Raw.items():
            DoTinCay = min(1.0, Bm25Norm[Idx])
            if DoTinCay >= 0.15:
                DanhSach.append((Raw, DoTinCay, self._corpus[Idx]))
        DanhSach.sort(key=lambda X: (X[1], X[0]), reverse=True)
        return DanhSach

    def _cham_diem_vector(self, VanBanCanTim):
        """Che do thuan Semantic Vector (cosine similarity)."""
        if not self._corpus or not VanBanCanTim or not str(VanBanCanTim).strip():
            return []
        VecMap = self._tinh_diem_vector(VanBanCanTim)
        if not VecMap:
            return []
        DanhSach = []
        for Idx, Sim in VecMap.items():
            if Sim >= 0.14:
                DoTinCay = min(1.0, max(0.0, Sim))
                DanhSach.append((Sim, DoTinCay, self._corpus[Idx]))
        DanhSach.sort(key=lambda X: (X[1], X[0]), reverse=True)
        return DanhSach

    def _cham_diem_hybrid(self, VanBanCanTim):
        """Cham diem Hybrid = Semantic Vector + BM25 + 3-gram + KHAI_NIEM_PHAN_CUNG bang RRF."""
        if not self._corpus or not VanBanCanTim or not str(VanBanCanTim).strip():
            return []

        TinHieu = self._tinh_diem_bm25_va_khai_niem(VanBanCanTim)
        GramTruyVan = TinHieu["gram_truy_van"]
        Bm25Raw = TinHieu["bm25_raw"]
        Bm25Norm = TinHieu["bm25_norm"]
        ConceptMap = TinHieu["concept"]
        ExactBonusMap = TinHieu["exact_bonus"]

        VecMap = self._tinh_diem_vector(VanBanCanTim)

        # Tap ung vien tu ca 4 nhanh
        UngVien = set(Bm25Raw.keys()) | set(ConceptMap.keys()) | set(ExactBonusMap.keys())
        for Idx, Sim in VecMap.items():
            if Sim >= 0.14:
                UngVien.add(Idx)
        if not UngVien and not GramTruyVan:
            return []

        # Tinh 3-gram Jaccard tren tap ung vien (va quet nhe toan corpus neu can tim fuzzy)
        GramMap = {}
        TapQuet3Gram = UngVien if UngVien else range(len(self._corpus))
        for Idx in TapQuet3Gram:
            J3 = max(
                _jaccard_3gram(GramTruyVan, self._doc_label_3grams[Idx]),
                _jaccard_3gram(GramTruyVan, self._doc_name_3grams[Idx]),
            )
            if J3 >= 0.12:
                GramMap[Idx] = J3
                UngVien.add(Idx)

        if not UngVien:
            return []

        # Xep hang tung nhanh de dua vao Reciprocal Rank Fusion (RRF)
        RankVec = {
            Idx: Rank
            for Rank, (Idx, _) in enumerate(
                sorted(
                    ((I, VecMap[I]) for I in UngVien if VecMap.get(I, 0.0) >= 0.18),
                    key=lambda X: X[1],
                    reverse=True,
                ),
                start=1,
            )
        }
        RankBm25 = {
            Idx: Rank
            for Rank, (Idx, _) in enumerate(
                sorted(
                    ((I, Bm25Raw[I]) for I in UngVien if Bm25Norm.get(I, 0.0) >= 0.16),
                    key=lambda X: X[1],
                    reverse=True,
                ),
                start=1,
            )
        }
        Rank3Gram = {
            Idx: Rank
            for Rank, (Idx, _) in enumerate(
                sorted(
                    ((I, GramMap[I]) for I in UngVien if GramMap.get(I, 0.0) >= 0.12),
                    key=lambda X: X[1],
                    reverse=True,
                ),
                start=1,
            )
        }
        RankConcept = {
            Idx: Rank
            for Rank, (Idx, _) in enumerate(
                sorted(
                    (
                        (I, ConceptMap.get(I, 0.0) + ExactBonusMap.get(I, 0.0))
                        for I in UngVien
                        if (ConceptMap.get(I, 0.0) + ExactBonusMap.get(I, 0.0)) > 0.0
                    ),
                    key=lambda X: X[1],
                    reverse=True,
                ),
                start=1,
            )
        }

        MaxRrfTheoretical = sum(_RRF_WEIGHTS.values()) / (_RRF_K + 1.0)
        DanhSachChamDiem = []

        for Idx in UngVien:
            RrfScore = 0.0
            if Idx in RankVec:
                RrfScore += _RRF_WEIGHTS["vector"] / (_RRF_K + RankVec[Idx])
            if Idx in RankBm25:
                RrfScore += _RRF_WEIGHTS["bm25"] / (_RRF_K + RankBm25[Idx])
            if Idx in Rank3Gram:
                RrfScore += _RRF_WEIGHTS["3gram"] / (_RRF_K + Rank3Gram[Idx])
            if Idx in RankConcept:
                RrfScore += _RRF_WEIGHTS["concept"] / (_RRF_K + RankConcept[Idx])

            if RrfScore <= 0.0:
                continue

            VecSim = VecMap.get(Idx, 0.0)
            Bm25Val = Bm25Norm.get(Idx, 0.0)
            GramVal = GramMap.get(Idx, 0.0)
            ConVal = ConceptMap.get(Idx, 0.0)
            ExactVal = ExactBonusMap.get(Idx, 0.0)

            RrfNorm = RrfScore / MaxRrfTheoretical
            BestSignal = max(VecSim, Bm25Val, GramVal, ConVal)
            SignalGate = min(1.0, BestSignal / 0.35)
            DoTinCay = min(1.0, (0.52 * RrfNorm + 0.38 * BestSignal) * SignalGate + 0.22 * ExactVal)

            if DoTinCay >= 0.18:
                DiemThuc = RrfScore * 10.0 + BestSignal * 0.5 + ExactVal
                DanhSachChamDiem.append((DiemThuc, DoTinCay, self._corpus[Idx]))

        DanhSachChamDiem.sort(key=lambda X: (X[1], X[0]), reverse=True)
        return DanhSachChamDiem

    def search_by_mode(self, spec_text, mode="hybrid", top_k=3):
        """Tim kiem theo che do cu the ('hybrid'|'bm25'|'keyword'|'vector') de ho tro benchmark."""
        if not self._corpus or not spec_text or not str(spec_text).strip() or top_k <= 0:
            return None, "CUSTOM", 0.0, []

        CheDo = str(mode or "hybrid").strip().lower()
        if CheDo in ("hybrid", "rrf"):
            DanhSachChamDiem = self._cham_diem_hybrid(spec_text)
        elif CheDo == "bm25":
            DanhSachChamDiem = self._cham_diem_bm25(spec_text)
        elif CheDo == "keyword":
            DanhSachChamDiem = self._cham_diem_keyword(spec_text)
        elif CheDo in ("vector", "semantic"):
            DanhSachChamDiem = self._cham_diem_vector(spec_text)
        else:
            raise ValueError(
                f"Che do tim kiem khong hop le: {mode!r}. "
                "Ho tro: 'hybrid', 'bm25', 'keyword', 'vector'."
            )

        if not DanhSachChamDiem:
            return None, "CUSTOM", 0.0, []

        MauDuyNhat = []
        KhoaDaGap = set()
        for _, _, Muc in DanhSachChamDiem:
            Khoa = self._khoa_loai_trung(Muc)
            if Khoa not in KhoaDaGap:
                KhoaDaGap.add(Khoa)
                MauDuyNhat.append(Muc)
            if len(MauDuyNhat) >= top_k:
                break

        _, DoTinCayCaoNhat, MauTotNhat = DanhSachChamDiem[0]

        if DoTinCayCaoNhat >= 0.70:
            LoaiKhop = "EXACT"
        elif DoTinCayCaoNhat >= 0.35:
            LoaiKhop = "SIMILAR"
        else:
            LoaiKhop = "CUSTOM"

        return MauTotNhat, LoaiKhop, round(DoTinCayCaoNhat, 3), MauDuyNhat

    def search(self, VanBanSpec, TopK=3, spec_text=None, top_k=None, mode="hybrid"):
        """Tim kiem mach phu hop nhat trong CSDL tri thuc bang Hybrid RRF Retrieval."""
        VanBanCanTim = spec_text if spec_text is not None else VanBanSpec
        SoLuongCanLay = top_k if top_k is not None else TopK
        return self.search_by_mode(VanBanCanTim, mode=mode, top_k=SoLuongCanLay)

    def format_rag_context(self, spec_text, top_k=2):
        """Tra ve chuoi ngan gon Top-K mau RTL tham khao (<= 45 dong/mau) cho LLM; tra '' neu khong dat nguong."""
        if not spec_text or not isinstance(spec_text, str) or not spec_text.strip() or top_k <= 0:
            return ""

        DanhSachChamDiem = self._cham_diem_hybrid(spec_text)
        if not DanhSachChamDiem:
            return ""

        CacDoan = []
        KhoaDaGap = set()
        for _, DoTinCay, Muc in DanhSachChamDiem:
            if DoTinCay < _NGUONG_RAG_TOI_THIEU:
                break
            Khoa = self._khoa_loai_trung(Muc)
            if Khoa in KhoaDaGap:
                continue
            Rtl = str(Muc.get("golden_rtl") or "").strip()
            if not Rtl:
                continue

            KhoaDaGap.add(Khoa)
            TenMod = Muc.get("module_name") or Muc.get("name") or "unknown_module"
            Nguon = Muc.get("source") or "Hardware Knowledge Base"
            DongRtl = Rtl.splitlines()
            if len(DongRtl) > _SO_DONG_RTL_TOI_DA:
                DongRtl = DongRtl[:_SO_DONG_RTL_TOI_DA - 1] + ["// ... (truncated)"]
            RtlRutGon = "\n".join(DongRtl)

            Stt = len(CacDoan) + 1
            CacDoan.append(
                f"### Mau tham khao {Stt}: `{TenMod}` (Nguon: {Nguon}, Do tin cay: {DoTinCay:.2f})\n"
                f"```verilog\n{RtlRutGon}\n```"
            )
            if len(CacDoan) >= top_k:
                break

        return "\n\n".join(CacDoan)

    def save_verified_design(self, module_name, spec_text, verilog_code,
                             category="Auto-Verified", source="Spec2RTL Closed-Loop EDA"):
        """Luu nguoc thiet ke da kiem chung thanh cong vao hardware_db.json neu hop le va khong trung."""
        if not module_name or not verilog_code:
            return False

        TenModSach = str(module_name).strip()
        CodeSach = str(verilog_code).strip()
        if not TenModSach or not CodeSach:
            return False

        TenModLower = TenModSach.lower()
        if TenModLower.startswith(_PREFIX_BO_QUA_LUU):
            return False

        for Muc in self.DanhSachMau:
            ModCu = str(Muc.get("module_name") or "").strip().lower()
            TenCu = str(Muc.get("name") or "").strip().lower()
            if TenModLower == ModCu or TenModLower == TenCu:
                return False

        HashCode = _chuan_hoa_code_md5(CodeSach)
        if not HashCode or HashCode in self._db_code_hashes:
            return False

        SpecSach = str(spec_text or "").strip()
        TuKhoaMoi = list(dict.fromkeys(_tach_tu_mo_rong(f"{TenModSach} {category} {SpecSach}")))[:20]

        IdMoi = f"verified_{TenModLower}"
        IdDaCo = {str(M.get("id") or "") for M in self.DanhSachMau}
        if IdMoi in IdDaCo:
            IdMoi = f"verified_{TenModLower}_{HashCode[:8]}"

        BanGhiMoi = {
            "id": IdMoi,
            "name": TenModSach,
            "module_name": TenModSach,
            "source": str(source or "Spec2RTL Closed-Loop EDA"),
            "category": str(category or "Auto-Verified"),
            "spec": SpecSach,
            "ports": [],
            "golden_rtl": CodeSach,
            "golden_tb": "",
            "keywords": TuKhoaMoi,
        }

        ThuMucDich = os.path.dirname(os.path.abspath(self.DuongDanDb))
        if ThuMucDich:
            os.makedirs(ThuMucDich, exist_ok=True)

        DanhSachMoi = list(self.DanhSachMau) + [BanGhiMoi]
        DuongDanTam = f"{self.DuongDanDb}.tmp"
        try:
            with open(DuongDanTam, "w", encoding="utf-8") as TepTin:
                json.dump(DanhSachMoi, TepTin, ensure_ascii=False, indent=2)
            os.replace(DuongDanTam, self.DuongDanDb)
        except OSError:
            if os.path.exists(DuongDanTam):
                try:
                    os.remove(DuongDanTam)
                except OSError:
                    pass
            return False

        self.DanhSachMau = DanhSachMoi
        self.entries = self.DanhSachMau
        self._xay_dung_chi_muc()
        return True


if __name__ == "__main__":
    BoTraCuu = KnowledgeMatcher()
    Info = BoTraCuu.get_vector_backend_info()
    print("=" * 75)
    print("   KIEM TRA BO TRA CUU TRI THUC (HYBRID RRF: VECTOR + BM25 + 3-GRAM + CONCEPT)")
    print(f"   DB chinh: {len(BoTraCuu.DanhSachMau)} mau | Teacher RAM: {len(BoTraCuu.TeacherMau)} mau")
    print(f"   Vector Backend: {Info['backend']} | Matrix: {Info['vector_shape']}")
    print("=" * 75)
    DanhSachCauHoi = [
        "Thiết kế máy bán nước tự động nhận 5k và 10k, lon nước giá 15k",
        "Thiết kế hệ thống đèn giao thông ngã tư với đèn đỏ, xanh, vàng và nút cho người đi bộ",
        "Mạch đếm lên xuống (up down counter) 4 bit đồng bộ",
        "Thiết kế bộ nhớ đệm bất đồng bộ FIFO (Asynchronous FIFO)",
        "Thiết kế mạch nhân 8 bit Booth multiplier",
        "Thiết kế bộ cộng BCD (BCD Adder)",
        "Hệ thống SoC AI Accelerator tích hợp CPU, DMA, AI Core và RAM",
        "Bo dem ma Gray 4 bit khong dau dong bo gray_counter_4bit",
    ]
    for CauHoi in DanhSachCauHoi:
        Mau, Loai, DoTinCay, DanhSachMauGoiY = BoTraCuu.search(CauHoi)
        print(f"\n[Truy van]: {CauHoi}")
        print(f" -> Ket qua: [{Loai}] Do tin cay: {DoTinCay*100:.1f}%")
        if Mau:
            print(f" -> Khop: {Mau['id']} ({Mau['name']}) | Nguon: {Mau['source']} | Nhom: {Mau['category']}")
        print(f" -> Top {len(DanhSachMauGoiY)} mau: {', '.join([M['name'] for M in DanhSachMauGoiY])}")

    RagSample = BoTraCuu.format_rag_context("Bo dem ma Gray 4 bit khong dau", top_k=2)
    RagEmpty = BoTraCuu.format_rag_context("xyzzy_khong_ton_tai_99999", top_k=2)
    print("\n" + "-" * 75)
    print(f"RAG context length (Gray counter): {len(RagSample)} chars | Empty query: {RagEmpty!r}")
