"""
Module: spec_analyzer.py
Mô tả: Bộ phân tích đặc tả yêu cầu phần cứng bằng ngôn ngữ tự nhiên (Tiếng Việt & Tiếng Anh).
Tự động trích xuất tên module, danh sách cổng vào/ra, độ rộng bus và phân loại vi kiến trúc.
"""

import os
import re
import unicodedata
import json

def remove_vietnamese_accents(VanBan):
    """Chuyển đổi tiếng Việt có dấu thành không dấu để so khớp ngữ nghĩa chuẩn xác."""
    VanBan = VanBan.replace('đ', 'd').replace('Đ', 'D')
    VanBan = unicodedata.normalize('NFKD', VanBan).encode('ascii', 'ignore').decode('ascii')
    return VanBan.lower()

def clean_identifier(VanBan):
    """Chuyển đổi chuỗi bất kỳ thành tên định danh Verilog hợp lệ."""
    ChuoiSach = remove_vietnamese_accents(VanBan)
    ChuoiSach = re.sub(r'[^a-zA-Z0-9_]+', '_', ChuoiSach).strip('_')
    # Loại bỏ các tiền tố mô tả thừa
    for TienTo in ["thiet_ke_", "xay_dung_", "mo_ta_", "mach_", "he_thong_", "bo_"]:
        if ChuoiSach.startswith(TienTo) and len(ChuoiSach) > len(TienTo):
            ChuoiSach = ChuoiSach[len(TienTo):]
    if not ChuoiSach:
        ChuoiSach = "custom_module"
    if ChuoiSach[0].isdigit():
        ChuoiSach = "mod_" + ChuoiSach
    return ChuoiSach

class SpecAnalyzer:
    def __init__(self, DuongDanSpec):
        DuongDanGiaiQuyet = DuongDanSpec
        if isinstance(DuongDanSpec, str) and not os.path.exists(DuongDanGiaiQuyet):
            ThuMucHienTai = os.path.dirname(os.path.abspath(__file__))
            ThuMucGoc = os.path.abspath(os.path.join(ThuMucHienTai, ".."))
            TenFile = os.path.basename(DuongDanSpec)
            CacUngVien = [
                DuongDanSpec,
                os.path.join(ThuMucHienTai, DuongDanSpec),
                os.path.join(ThuMucHienTai, "..", DuongDanSpec),
                os.path.join(ThuMucGoc, "specs", TenFile),
                os.path.join(os.getcwd(), DuongDanSpec),
                os.path.join(os.getcwd(), "specs", TenFile),
            ]
            for UngVien in CacUngVien:
                if os.path.exists(UngVien):
                    DuongDanGiaiQuyet = os.path.abspath(UngVien)
                    break

        self.spec_path = DuongDanGiaiQuyet
        if os.path.exists(DuongDanGiaiQuyet):
            with open(DuongDanGiaiQuyet, "r", encoding="utf-8-sig", errors="replace") as TepTin:
                self.content = TepTin.read().lstrip('\ufeff')
        else:
            self.content = str(DuongDanSpec).lstrip('\ufeff')

    def extract_module_name(self):
        """Trích xuất hoặc suy luận tên module Verilog từ file đặc tả."""
        TuKhoaLoaiTru = {"name", "entity", "top", "inputs", "outputs", "input", "output", 
                          "dau_vao", "dau_ra", "io", "ports", "tin_hieu", "state", "step",
                          "1_dau_vao_inputs", "dau_vao_inputs", "2_dau_ra_outputs", "dau_ra_outputs",
                          "3_hoat_dong_logic", "hoat_dong_logic"}

        # 1. Tìm khai báo trực tiếp: "module <tên>" hoặc "Module: <tên>"
        KhopKhaiBao = re.search(r"(?:module|Module|Tên module|Module Name)\s*[:=]?\s*[`\*]?([A-Za-z0-9_]+)[`\*]?", self.content)
        if KhopKhaiBao and KhopKhaiBao.group(1).lower() not in TuKhoaLoaiTru:
            return KhopKhaiBao.group(1).lower()

        # 2. Tìm trong tiêu đề Markdown H1 / H2
        KhopTieuDe = re.search(r"^#+\s+(.+)$", self.content, re.MULTILINE)
        if KhopTieuDe:
            DongTieuDe = KhopTieuDe.group(1).strip()
            KhopNgoac = re.search(r"\(([A-Za-z0-9_\s]{2,})\)", DongTieuDe)
            if KhopNgoac:
                UngVien = clean_identifier(KhopNgoac.group(1))
                if UngVien and len(UngVien) > 2 and UngVien not in TuKhoaLoaiTru:
                    return UngVien
            ChuoiTieuDe = DongTieuDe.split("–")[0].split("-")[0].strip()
            UngVien = clean_identifier(ChuoiTieuDe)
            if UngVien and len(UngVien) > 2 and UngVien != "custom_module" and UngVien not in TuKhoaLoaiTru:
                return UngVien

        # 3. Tìm tên tiếng Anh trong dấu ngoặc đơn ở toàn bộ văn bản
        for KhopNgoac in re.finditer(r"\(([A-Za-z0-9_]{2,})\)", self.content):
            UngVien = clean_identifier(KhopNgoac.group(1))
            if UngVien and len(UngVien) > 2 and UngVien not in TuKhoaLoaiTru:
                return UngVien

        # 4. Nếu tên file là dạng chung chung (a, b, spec), lấy từ câu đầu tiên
        if os.path.exists(self.spec_path):
            PhanTenFile = os.path.splitext(os.path.basename(self.spec_path))[0]
            TenFileSach = clean_identifier(PhanTenFile)
            if TenFileSach in ["a", "test", "temp", "spec", "demo", "input"]:
                DongCoChu = [Dong.strip() for Dong in self.content.splitlines() if Dong.strip()]
                if DongCoChu:
                    UngVien = clean_identifier(DongCoChu[0].split(".")[0].split(":")[0])
                    if UngVien and len(UngVien) > 2 and UngVien != "custom_module" and UngVien not in TuKhoaLoaiTru:
                        return UngVien
            if TenFileSach and TenFileSach not in TuKhoaLoaiTru:
                return TenFileSach

        return "custom_hw_module"

    def is_30_percent_architecture(self):
        """Phát hiện các hệ thống vi kiến trúc phức hợp SoC AI vượt ngưỡng 1 câu prompt."""
        VanBanTho = (os.path.basename(self.spec_path) + " " + self.content)
        VanBan = remove_vietnamese_accents(VanBanTho)

        if any(TuKhoa in VanBan for TuKhoa in [
            "top_soc", "top soc", "ai accelerator core", "ai_accelerator_core",
            "he thong ai accelerator", "bo xu ly ai da loi", "systolic array processor",
            "mang tam thu 2d", "mang tam thu npu", "multi-channel dma controller",
            "npu_core", "ai_core_top"
        ]):
            return True

        if "soc" in VanBan and any(TuKhoa in VanBan for TuKhoa in ["accelerator", "core", "datapath", "dma", "cpu", "he thong"]):
            return True

        if ("dma" in VanBan and "relu" in VanBan and "ai" in VanBan):
            return True

        return False

    def check_unsupported_domain(self):
        """Phát hiện các yêu cầu nằm ngoài phạm vi logic số có thể tổng hợp (Analog, PHY Hard IP)."""
        VanBanTho = (os.path.basename(self.spec_path) + " " + self.content)
        VanBan = remove_vietnamese_accents(VanBanTho)

        AnalogTuKhoa = [
            "op-amp", "opamp", "khuech dai thuat toan", "mach tuong tu", "analog",
            "bandgap", "analog pll", "khuech dai vi sai analog"
        ]
        for Tu in AnalogTuKhoa:
            if Tu in VanBan:
                return True, "ANALOG_AMS", (
                    "Yêu cầu thiết kế Mạch Tương Tự (Analog / Mixed-Signal). "
                    "Hệ thống Spec2RTL chuyên biệt cho Logic Số Đồng Bộ (Synthesizable Synchronous Digital Logic). "
                    "Mạch Analog đòi hỏi công cụ SPICE / Cadence Virtuoso và định cỡ Transistor (W/L), "
                    "không thể tổng hợp bằng trình tổng hợp FPGA/ASIC (Quartus II)."
                )

        PhyTuKhoa = ["pcie phy", "ddr phy", "ddr4 phy", "ddr5 phy", "serdes phy", "gigabit phy", "usb3 phy"]
        for Tu in PhyTuKhoa:
            if Tu in VanBan:
                return True, "HIGH_SPEED_PHY", (
                    "Yêu cầu thiết kế Khối Vật Lý Siêu Cao Tần (Gigahertz SerDes PHY). "
                    "Khối mạch này đòi hỏi thư viện Hard Macro PDK từ nhà máy đúc chip (Foundry: TSMC, Intel, GF), "
                    "không thể tổng hợp từ mã Soft RTL thuần túy."
                )

        # Phát hiện nội dung không liên quan đến thiết kế phần cứng vi mạch (Out-of-Domain / Irrelevant Input)
        TuKhoaPhanCung = [
            "mach", "circuit", "module", "port", "cong", "chan", "pin", "input", "output", "inout",
            "wire", "reg", "clk", "clock", "rst", "reset", "fsm", "trang thai", "state", "bit",
            "logic", "dem", "counter", "alu", "nhan", "cong", "tru", "chia", "shift", "dich",
            "mux", "demux", "giai ma", "decoder", "ma hoa", "encoder", "thang may", "elevator",
            "giao thong", "traffic", "ban nuoc", "vending", "khoa", "lock", "uart", "spi", "i2c",
            "pwm", "ram", "rom", "dma", "soc", "npu", "fpga", "verilog", "hdl", "rtl", "7seg",
            "led", "sensor", "cam bien", "nhiet do", "bao chay", "bao dong", "step motor", "debounc",
            "chong rung", "so do", "datapath", "register", "flip flop"
        ]
        if not any(Tu in VanBan for Tu in TuKhoaPhanCung) and not self.extract_ports():
            return True, "IRRELEVANT_INPUT", (
                "Văn bản đầu vào không chứa bất kỳ thông tin, tín hiệu I/O hoặc yêu cầu thiết kế logic vi mạch nào. "
                "Hệ thống Spec2RTL & Prompt2Silicon chuyên biệt cho thiết kế vi mạch kỹ thuật số (ví dụ: bộ đếm, FSM, ALU, UART, v.v.). "
                "Vui lòng cung cấp mô tả mạch phần cứng để tiếp tục."
            )

        return False, None, None

    def classify_system(self):
        """Phân loại vi mạch vào các nhóm kiến trúc phần cứng."""
        is_unsup, cat_code, _ = self.check_unsupported_domain()
        if is_unsup:
            return cat_code

        VanBanTho = (os.path.basename(self.spec_path) + " " + self.content)
        VanBan = remove_vietnamese_accents(VanBanTho)

        if self.is_30_percent_architecture():
            return "SOC_AI"
        if "vend" in VanBan or "ban nuoc" in VanBan:
            return "VENDING"
        if any(TuKhoa in VanBan for TuKhoa in ["thang may", "elevator", "lift_ctrl", "cabin_floor"]):
            return "ELEVATOR"
        if "traffic" in VanBan or "giao thong" in VanBan:
            return "TRAFFIC"

        if any(TuKhoa in VanBan for TuKhoa in ["debounc", "khu rung", "chong rung", "button_debouncer"]):
            return "DEBOUNCER"
        if any(TuKhoa in VanBan for TuKhoa in ["bao chay", "bao trom", "smart home", "nha thong minh", "smoke_gas", "motion_pir", "sprinkler"]):
            return "SMART_ALARM"
        if any(TuKhoa in VanBan for TuKhoa in ["khoa so", "khoa dien tu", "khoa ma", "password", "mat khau", "digital lock", "safe lock", "unlock", "ket sat"]):
            return "DIGITAL_LOCK"
        if any(TuKhoa in VanBan for TuKhoa in ["uart", "uart_tx", "truyen noi tiep", "serial tx", "tx_data", "tx_serial"]):
            return "UART_TX"
        if any(TuKhoa in VanBan for TuKhoa in ["dong co buoc", "stepper", "step motor", "motor buoc", "phase_out"]):
            return "STEPPER_MOTOR"
        if any(TuKhoa in VanBan for TuKhoa in ["may giat", "washing", "washing_machine", "giat tu dong"]):
            return "WASHING_MACHINE"
        if any(TuKhoa in VanBan for TuKhoa in ["nhiet do", "temperature", "temp_celsius", "max_temp_limit", "overtemp", "giam sat nhiet do"]):
            return "TEMPERATURE_MONITOR"
        if any(TuKhoa in VanBan for TuKhoa in ["giai ma", "decoder", "address decoder", "address_decoder", "giai ma dia chi", "bo giai ma", "mach giai ma"]):
            return "DECODER"
        if any(TuKhoa in VanBan for TuKhoa in ["bao chay", "bao trom", "smart home", "nha thong minh", "smoke_gas", "motion_pir"]):
            return "SMART_ALARM"
        if any(TuKhoa in VanBan for TuKhoa in ["pwm", "do rong xung", "duty cycle", "xung pwm"]):
            return "PWM"
        if any(TuKhoa in VanBan for TuKhoa in ["fifo", "queue", "hang doi", "buffer"]):
            return "FIFO"

        if any(TuKhoa in VanBan for TuKhoa in ["multiplier", "nhan 4 bit", "nhan 8 bit", "nhan 16 bit", "mach nhan", "bo nhan", "multi_"]):
            return "MULTIPLIER"
        if any(TuKhoa in VanBan for TuKhoa in ["adder", "cong 4 bit", "cong 8 bit", "cong 16 bit", "mach cong", "bo cong", "full adder", "half adder"]):
            return "ADDER"
        if re.search(r"\b(?:subtractor|tru\s+\d+\s*bit|mach\s+tru|bo\s+tru|phep\s+tru)\b", VanBan):
            return "SUBTRACTOR"
        if any(TuKhoa in VanBan for TuKhoa in ["alu", "toan hoc", "arithmetic", "opcode"]):
            return "ALU"
        if any(TuKhoa in VanBan for TuKhoa in ["comparator", "so sanh", "bo so sanh", "mach so sanh"]):
            return "COMPARATOR"
        if any(TuKhoa in VanBan for TuKhoa in ["gray", "gray_counter", "ma gray"]):
            return "GRAY_COUNTER"
        if any(TuKhoa in VanBan for TuKhoa in ["stopwatch", "dong ho", "7 doan", "7-segment", "seg", "led 7"]):
            return "STOPWATCH"
        if any(TuKhoa in VanBan for TuKhoa in ["counter", "dem len", "dem xuong", "up down", "up_down", "dem 1 bit", "dem 4 bit", "dem 8 bit", "dem nhi phan"]) or (re.search(r"\b(?:bo\s+dem|mach\s+dem)\b", VanBan) and not any(f in VanBan for f in ["fifo", "buffer", "hang doi", "queue"])):
            return "COUNTER"
        if any(TuKhoa in VanBan for TuKhoa in ["shift", "thanh ghi dich", "thanh ghi", "dich trai", "dich phai", "sipo", "piso"]):
            return "SHIFT_REG"
        if any(TuKhoa in VanBan for TuKhoa in ["do chuoi", "phat hien chuoi", "sequence detector", "nhan dang chuoi", "tim chuoi", "sequence_detector"]) or re.search(r"\b(?:chuoi\s+bit|sequence\s+of\s+bits|chuoi\s+1011|chuoi\s+1101)\b", VanBan):
            return "SEQUENCE_DETECTOR"
        if any(TuKhoa in VanBan for TuKhoa in ["fsm", "trang thai", "state machine", "chuyen trang thai"]):
            return "CUSTOM_FSM"

        return "CUSTOM_LOGIC"

    def extract_ports(self):
        """Trích xuất danh sách cổng tín hiệu từ bảng Markdown, danh sách hoặc đoạn văn bản."""
        DanhSachCong = []
        DaGap = set()

        TuKhoaLoaiTruCong = {
            "port", "port_name", "name", "ten_chan", "ten_cong", "mo_ta", "input", "output",
            "dau_vao", "dau_ra", "tin_hieu", "khi", "neu", "gia_tri", "truong_hop", "so", "chu_so",
            "buoc", "chu_ky", "chu_ky_sau", "thoi_gian", "muc", "che_do", "note", "luu_y", "chu_y",
            "wire", "reg", "logic", "ra", "vao"
        }

        # 1. Trích xuất từ bảng Markdown (hỗ trợ cả tiếng Việt 'Đầu vào', 'Đầu ra' có dấu)
        MauBang = r"\|\s*`?\*?\*?([A-Za-z0-9_]+)\*?\*?`?\s*\|\s*([^\|]+)\|\s*([^\|]+)\|\s*([^\|]+)\|"
        for KhopBang in re.finditer(MauBang, self.content):
            Ten, Huong, ChuoiRong, MoTa = KhopBang.groups()
            TenSach = Ten.strip()
            if TenSach.lower() not in TuKhoaLoaiTruCong and not TenSach.isdigit():
                DoRong = 1
                KhopBus = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", ChuoiRong)
                KhopBit = re.search(r"(\d+)\s*(?:bit|b)?", ChuoiRong.lower())
                if KhopBus:
                    DoRong = abs(int(KhopBus.group(1)) - int(KhopBus.group(2))) + 1
                elif KhopBit:
                    DoRong = int(KhopBit.group(1))

                HuongSach = remove_vietnamese_accents(Huong.strip().lower())
                HuongChuan = "output" if any(TuKhoa in HuongSach for TuKhoa in ["out", "ra", "output", "dau ra", "ngo ra"]) else "input"
                DanhSachCong.append({
                    "name": TenSach,
                    "direction": HuongChuan,
                    "width": DoRong,
                    "is_clk": any(TuKhoa in TenSach.lower() for TuKhoa in ["clk", "clock"]),
                    "is_rst": any(TuKhoa in TenSach.lower() for TuKhoa in ["rst", "clr", "reset", "clear"]),
                    "desc": MoTa.strip()
                })
                DaGap.add(TenSach.lower())

        # 2. Trích xuất từ danh sách gạch đầu dòng Markdown
        PhanHienTai = None
        for DongTho in self.content.splitlines():
            Dong = DongTho.strip()
            DongSach = re.sub(r"\*{1,2}|`", "", Dong).strip()
            DongKhongDau = remove_vietnamese_accents(DongSach.lower())

            KhopPhanMuc = re.search(r"\b(dau vao|inputs?|ngo vao|dau ra|outputs?|ngo ra|hoat dong|chuc nang|nguyen ly|logic)\b", DongKhongDau)
            LaTieuDePhanMuc = False
            if KhopPhanMuc:
                LaDauDong = bool(re.match(r"^[-*+•]\s*(?:\[|\w+\s*[:\-])", DongSach))
                if not LaDauDong:
                    if ":" in DongSach:
                        TruocDauHaiCham = DongKhongDau.split(":")[0]
                        if KhopPhanMuc.group(1) in TruocDauHaiCham:
                            LaTieuDePhanMuc = True
                    else:
                        LaTieuDePhanMuc = True

            if LaTieuDePhanMuc:
                if any(TuKhoa in DongKhongDau for TuKhoa in ["dau vao", "dau_vao", "inputs", "input", "ngo vao", "tin hieu vao"]):
                    PhanHienTai = "input"
                elif any(TuKhoa in DongKhongDau for TuKhoa in ["dau ra", "dau_ra", "outputs", "output", "ngo ra", "tin hieu ra"]):
                    PhanHienTai = "output"
                else:
                    PhanHienTai = "other"
                continue

            if PhanHienTai == "other" and not any(TuKhoa in DongKhongDau for TuKhoa in ["input", "output", "dau vao", "dau ra", "ngo vao", "ngo ra"]):
                continue

            KhopDongMuc = re.match(r"^(?:[-*+•]|\d+[\.\)])\s*(.*)$", DongSach)
            MucTieu = KhopDongMuc.group(1).strip() if KhopDongMuc else (DongSach if PhanHienTai in ["input", "output"] and ":" in DongSach else None)
            if not MucTieu:
                continue

            MucTieuKhongDau = remove_vietnamese_accents(MucTieu.lower())
            HuongRoRang = None
            KhopHuong = re.search(r"\b(input|output|ngo vao|ngo ra|dau vao|dau ra)\b", MucTieuKhongDau)
            if KhopHuong:
                HuongRoRang = "output" if any(TuKhoa in KhopHuong.group(1) for TuKhoa in ["out", "ra"]) else "input"

            Khop1 = re.search(r"(?:(?:wire|reg)\s+)?\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*([A-Za-z0-9_]+)\s*[:\-\s](.*)", MucTieu)
            Khop2 = re.search(r"([A-Za-z0-9_]+)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*[:\-\s](.*)", MucTieu)
            Khop3 = re.search(r"([A-Za-z0-9_]+)\s*\(\s*(\d+)\s*(?:bit|b)?\s*\)\s*[:\-\s](.*)", MucTieu)
            Khop4 = re.search(r"([A-Za-z0-9_]+)\s*[:\-]\s*(.*)", MucTieu)

            TenCong, DoRong, MoTaCong = None, 1, ""
            if Khop1:
                Msb, Lsb, TenCong, MoTaCong = Khop1.groups()
                DoRong = abs(int(Msb) - int(Lsb)) + 1
            elif Khop2:
                TenCong, Msb, Lsb, MoTaCong = Khop2.groups()
                DoRong = abs(int(Msb) - int(Lsb)) + 1
            elif Khop3:
                TenCong, DoRongBit, MoTaCong = Khop3.groups()
                DoRong = int(DoRongBit)
            elif Khop4:
                TenCong, MoTaCong = Khop4.groups()
                KhopMoTaRong = re.search(r"\b(\d+)\s*(?:bit|b)\b", MoTaCong.lower())
                if KhopMoTaRong:
                    DoRong = int(KhopMoTaRong.group(1))

            if TenCong:
                TenSach = TenCong.strip()
                if TenSach.lower() in TuKhoaLoaiTruCong or TenSach.isdigit() or len(TenSach) < 1:
                    continue
                if TenSach.lower() in DaGap:
                    continue

                HuongCuoi = HuongRoRang if HuongRoRang else (
                    PhanHienTai if PhanHienTai in ["input", "output"] else (
                        "output" if any(TuKhoa in MucTieuKhongDau for TuKhoa in ["out", "ra"]) else "input"
                    )
                )

                DanhSachCong.append({
                    "name": TenSach,
                    "direction": HuongCuoi,
                    "width": DoRong,
                    "is_clk": any(TuKhoa in TenSach.lower() for TuKhoa in ["clk", "clock"]),
                    "is_rst": any(TuKhoa in TenSach.lower() for TuKhoa in ["rst", "clr", "reset", "clear"]),
                    "desc": MoTaCong.strip() if MoTaCong else ""
                })
                DaGap.add(TenSach.lower())

        # 3. Trích xuất dự phòng từ đoạn văn xuôi
        if not DanhSachCong:
            NoiDungKhongDau = remove_vietnamese_accents(self.content.lower())
            KhopVao = re.search(r"(?:dau vao|ngo vao|inputs?)\s*(?:la|gom|:|cac tin hieu)?\s*([^.]+?)(?:dau ra|ngo ra|outputs?|$)", NoiDungKhongDau)
            KhopRa = re.search(r"(?:dau ra|ngo ra|outputs?)\s*(?:la|gom|:|cac tin hieu)?\s*([^.]+?)(?:dau vao|ngo vao|inputs?|$)", NoiDungKhongDau)

            def TrichXuatTuDoan(DoanVan, Huong):
                CongTrichXuat = []
                CacTu = re.split(r"[,;]|\s+\bva\b\s+|\s+\band\b\s+", DoanVan)
                for Tu in CacTu:
                    Tu = Tu.strip()
                    if not Tu: continue
                    KhopRongBus = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", Tu)
                    KhopRongBit = re.search(r"(\d+)\s*(?:bit|b)", Tu)
                    DoRong = 1
                    if KhopRongBus: DoRong = abs(int(KhopRongBus.group(1)) - int(KhopRongBus.group(2))) + 1
                    elif KhopRongBit: DoRong = int(KhopRongBit.group(1))
                    DanhSachTen = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", Tu)
                    for Ten in DanhSachTen:
                        if Ten.lower() not in TuKhoaLoaiTruCong and Ten.lower() not in ["bit", "b", "la", "gom", "cac", "tin", "hieu", "so", "va", "and", "with", "cho"]:
                            if Ten.lower() not in DaGap:
                                CongTrichXuat.append({
                                    "name": Ten,
                                    "direction": Huong,
                                    "width": DoRong,
                                    "is_clk": any(TuKhoa in Ten.lower() for TuKhoa in ["clk", "clock"]),
                                    "is_rst": any(TuKhoa in Ten.lower() for TuKhoa in ["rst", "clr", "reset", "clear"]),
                                    "desc": "Trích xuất từ văn bản"
                                })
                                DaGap.add(Ten.lower())
                return CongTrichXuat

            if KhopVao:
                DanhSachCong.extend(TrichXuatTuDoan(KhopVao.group(1), "input"))
            if KhopRa:
                DanhSachCong.extend(TrichXuatTuDoan(KhopRa.group(1), "output"))

        return DanhSachCong

    def get_friendly_description(self):
        """Trả về mô tả thân thiện cho giao diện người dùng."""
        PhanLoai = self.classify_system()
        TenModule = self.extract_module_name()

        KhopTieuDe = re.search(r"^#+\s+(.+)$", self.content, re.MULTILINE)
        if KhopTieuDe:
            TieuDe = KhopTieuDe.group(1).strip()
            if len(TieuDe) < 70:
                return f"{TieuDe} [{PhanLoai}]"

        TenTheoLoai = {
            "SOC_AI": "Autonomous SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core)",
            "VENDING": "Máy bán nước tự động 15.000đ (Vending Machine FSM)",
            "ELEVATOR": "Bộ điều khiển Thang máy 5 tầng (5-Floor Intelligent Elevator FSM)",
            "TRAFFIC": "Bộ điều khiển Đèn giao thông ngã tư (Intersection Traffic Light FSM)",
            "ALU": f"Khối xử lý số học và logic ALU ({TenModule})",
            "COUNTER": f"Bộ đếm đồng bộ ({TenModule})",
            "PWM": f"Bộ tạo xung điều chế PWM ({TenModule})",
            "SHIFT_REG": f"Thanh ghi dịch dữ liệu ({TenModule})",
            "SEQUENCE_DETECTOR": f"Bộ phát hiện chuỗi tuần tự ({TenModule})",
            "DIGITAL_LOCK": f"Hệ thống khóa mã số an ninh ({TenModule})",
            "DECODER": f"Bộ giải mã địa chỉ / dữ liệu ({TenModule})",
            "TEMPERATURE_MONITOR": f"Hệ thống giám sát và cảnh báo nhiệt độ ({TenModule})",
            "CUSTOM_FSM": f"Máy trạng thái hữu hạn tùy biến ({TenModule})",
            "CUSTOM_LOGIC": f"Mạch kỹ thuật số tự do ({TenModule})"
        }
        return TenTheoLoai.get(PhanLoai, f"Mô-đun phần cứng: {TenModule}")

    def to_dict(self):
        return {
            "spec_path": self.spec_path,
            "module_name": self.extract_module_name(),
            "category": self.classify_system(),
            "ports": self.extract_ports(),
            "description": self.get_friendly_description()
        }

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if len(sys.argv) > 1:
        DuongDan = sys.argv[1]
    else:
        ThuMucHienTai = os.path.dirname(os.path.abspath(__file__))
        UngVien1 = os.path.join(ThuMucHienTai, "..", "specs", "a.txt")
        UngVien2 = os.path.join(os.getcwd(), "specs", "a.txt")
        if os.path.exists(UngVien1):
            DuongDan = os.path.abspath(UngVien1)
        elif os.path.exists(UngVien2):
            DuongDan = os.path.abspath(UngVien2)
        else:
            DuongDan = "specs/a.txt"
    BoPhanTich = SpecAnalyzer(DuongDan)
    print(json.dumps(BoPhanTich.to_dict(), indent=2, ensure_ascii=False))
