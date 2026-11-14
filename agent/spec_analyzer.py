"""
Module: spec_analyzer.py
Description: Advanced Natural Language Specification Analyzer for Spec2RTL & Prompt2Silicon.
Extracts module entities, ports, system category, and functional requirements from arbitrary specifications
(Vietnamese or English) so that ANY custom hardware design can be autonomously synthesized.
"""

import os
import re
import unicodedata
import json

def remove_vietnamese_accents(text):
    """Converts Vietnamese characters to ASCII lowercase for robust semantic matching."""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return text.lower()

def clean_identifier(text):
    """Converts arbitrary text (including Vietnamese with diacritics) into a valid Verilog identifier."""
    clean = remove_vietnamese_accents(text)
    clean = re.sub(r'[^a-zA-Z0-9_]+', '_', clean).strip('_')
    # Strip common noise prefixes
    for prefix in ["thiet_ke_", "xay_dung_", "mo_ta_", "mach_", "he_thong_", "bo_"]:
        if clean.startswith(prefix) and len(clean) > len(prefix):
            clean = clean[len(prefix):]
    if not clean:
        clean = "custom_module"
    if clean[0].isdigit():
        clean = "mod_" + clean
    return clean

class SpecAnalyzer:
    def __init__(self, spec_path):
        self.spec_path = spec_path
        if os.path.exists(spec_path):
            with open(spec_path, "r", encoding="utf-8", errors="replace") as f:
                self.content = f.read()
        else:
            self.content = str(spec_path)

    def extract_module_name(self):
        """Extracts or deduces a clean Verilog module name from the spec content or filename."""
        EXCLUDED_NAMES = {"name", "entity", "top", "inputs", "outputs", "input", "output", 
                          "dau_vao", "dau_ra", "io", "ports", "tin_hieu", "state", "step"}

        # 1. Look for explicit module declaration: "module <name>" or "Module: <name>"
        m = re.search(r"(?:module|Module|Tên module|Module Name)\s*[:=]?\s*[`\*]?([A-Za-z0-9_]+)[`\*]?", self.content)
        if m and m.group(1).lower() not in EXCLUDED_NAMES:
            return m.group(1).lower()

        # 2. Look for primary Markdown H1 / H2 header: e.g. "# Thiết kế khóa số (digital_lock)"
        m_h1 = re.search(r"^#+\s+(.+)$", self.content, re.MULTILINE)
        if m_h1:
            h1_line = m_h1.group(1).strip()
            # Check for parenthesized identifier in H1 line first
            m_h1_paren = re.search(r"\(([A-Za-z0-9_]{2,})\)", h1_line)
            if m_h1_paren:
                candidate = clean_identifier(m_h1_paren.group(1))
                if candidate and len(candidate) > 2 and candidate not in EXCLUDED_NAMES:
                    return candidate
            header_text = h1_line.split("–")[0].split("-")[0].strip()
            candidate = clean_identifier(header_text)
            if candidate and len(candidate) > 2 and candidate != "custom_module" and candidate not in EXCLUDED_NAMES:
                return candidate

        # 3. Look for name in parentheses elsewhere in document, excluding section headers
        for m_paren in re.finditer(r"\(([A-Za-z0-9_]{2,})\)", self.content):
            candidate = clean_identifier(m_paren.group(1))
            if candidate and len(candidate) > 2 and candidate not in EXCLUDED_NAMES:
                return candidate

        # 4. If filename is generic (a, test, temp, spec, demo), deduce from first prompt sentence
        if os.path.exists(self.spec_path):
            stem = os.path.splitext(os.path.basename(self.spec_path))[0]
            clean_stem = clean_identifier(stem)
            if clean_stem in ["a", "test", "temp", "spec", "demo", "input"]:
                non_empty = [l.strip() for l in self.content.splitlines() if l.strip()]
                if non_empty:
                    candidate = clean_identifier(non_empty[0].split(".")[0].split(":")[0])
                    if candidate and len(candidate) > 2 and candidate != "custom_module" and candidate not in EXCLUDED_NAMES:
                        return candidate
            if clean_stem and clean_stem not in EXCLUDED_NAMES:
                return clean_stem

        return "custom_hw_module"

    def classify_system(self):
        """Classifies the specification into a known or generic hardware architecture."""
        raw_text = (os.path.basename(self.spec_path) + " " + self.content)
        text = remove_vietnamese_accents(raw_text)

        if "soc" in text or ("dma" in text and "relu" in text) or "mac_unit" in text:
            return "SOC_AI"
        if "vend" in text or "ban nuoc" in text:
            return "VENDING"
        if "thang" in text or "elevator" in text:
            return "ELEVATOR"
        if "traffic" in text or "giao thong" in text:
            return "TRAFFIC"

        # Multiplier
        if any(k in text for k in ["multiplier", "nhan 4 bit", "nhan 8 bit", "nhan 16 bit", "mach nhan", "bo nhan", "multi_"]):
            return "MULTIPLIER"
        # Adder
        if any(k in text for k in ["adder", "cong 4 bit", "cong 8 bit", "cong 16 bit", "mach cong", "bo cong", "full adder", "half adder"]):
            return "ADDER"
        # Subtractor
        if any(k in text for k in ["subtractor", "tru 4 bit", "tru 8 bit", "mach tru", "bo tru"]):
            return "SUBTRACTOR"
        # ALU (must be evaluated BEFORE COMPARATOR because ALU specs include comparisons like a == b)
        if any(k in text for k in ["alu", "toan hoc", "arithmetic", "opcode"]):
            return "ALU"
        # Comparator
        if any(k in text for k in ["comparator", "so sanh", "bo so sanh", "mach so sanh"]):
            return "COMPARATOR"
        # Gray Counter (must be evaluated BEFORE generic COUNTER)
        if any(k in text for k in ["gray", "gray_counter", "ma gray"]):
            return "GRAY_COUNTER"
        # Stopwatch / 7-Segment Counter (must be evaluated BEFORE generic COUNTER)
        if any(k in text for k in ["stopwatch", "dong ho", "7 doan", "7-segment", "seg", "led 7"]):
            return "STOPWATCH"
        # Counter
        if any(k in text for k in ["counter", "dem len", "dem xuong", "up down", "up_down", "mach dem", "bo dem", "dem 1 bit", "dem 4 bit", "dem 8 bit", "dem nhi phan"]):
            return "COUNTER"
        if any(k in text for k in ["fifo", "queue", "hang doi"]):
            return "FIFO"
        if any(k in text for k in ["encoder", "priority", "u tien", "ma hoa"]):
            return "ENCODER"
        if any(k in text for k in ["pulse", "edge", "canh xung", "phat hien xung"]):
            return "PULSE_DETECTOR"
        if any(k in text for k in ["barrel", "dich vong", "rotat"]):
            return "BARREL_SHIFTER"
        if any(k in text for k in ["pwm", "do rong xung", "duty cycle", "xung pwm"]):
            return "PWM"
        if any(k in text for k in ["shift", "thanh ghi dich", "thanh ghi", "dich trai", "dich phai", "sipo", "piso"]):
            return "SHIFT_REG"
        if any(k in text for k in ["chuoi", "sequence", "phat hien", "detector", "1011", "1101"]):
            return "SEQUENCE_DETECTOR"
        if any(k in text for k in ["khoa", "khoa so", "password", "mat khau", "lock", "an ninh"]):
            return "DIGITAL_LOCK"
        if any(k in text for k in ["fsm", "trang thai", "state machine", "chuyen trang thai"]):
            return "CUSTOM_FSM"

        return "CUSTOM_LOGIC"

    def extract_ports(self):
        """Extracts input and output ports from tables, bullet points, or Verilog syntax."""
        ports = []
        seen = set()

        # 1. Parse markdown tables
        table_pattern = r"\|\s*`?([A-Za-z0-9_]+)`?\s*\|\s*([A-Za-z\s]+)\s*\|\s*([^\|]+)\|\s*([^\|]+)\|"
        for match in re.finditer(table_pattern, self.content):
            name, direction, width_str, desc = match.groups()
            name_clean = name.strip()
            if name_clean.lower() not in ["port", "port name", "name", "tên chân", "tên cổng"]:
                w = 1
                m_bit = re.search(r"(\d+)\s*(?:bit|b)?", width_str.lower())
                m_bus = re.search(r"\[(\d+):(\d+)\]", width_str)
                if m_bus:
                    w = abs(int(m_bus.group(1)) - int(m_bus.group(2))) + 1
                elif m_bit:
                    w = int(m_bit.group(1))

                dir_c = direction.strip().lower()
                dir_val = "output" if any(k in dir_c for k in ["out", "ra", "output"]) else "input"
                ports.append({
                    "name": name_clean,
                    "direction": dir_val,
                    "width": w,
                    "is_clk": any(k in name_clean.lower() for k in ["clk", "clock"]),
                    "is_rst": any(k in name_clean.lower() for k in ["rst", "clr", "reset", "clear"]),
                    "desc": desc.strip()
                })
                seen.add(name_clean.lower())

        # 2. Section-aware Markdown bullet points parser
        EXCLUDED_PORT_NAMES = {
            "port", "port_name", "name", "ten_chan", "ten_cong", "mo_ta", "input", "output",
            "dau_vao", "dau_ra", "tin_hieu", "khi", "neu", "gia_tri", "truong_hop", "so", "chu_so"
        }
        current_section = None
        for raw_line in self.content.splitlines():
            line = raw_line.strip()
            line_low = line.lower()

            # Track section headers (e.g. ## 1. Đầu vào (Inputs): / ## 2. Đầu ra (Outputs):)
            if line.startswith("#"):
                if any(k in line_low for k in ["dau vao", "dau_vao", "inputs", "input", "ngõ vào", "ngo vao"]):
                    current_section = "input"
                elif any(k in line_low for k in ["dau ra", "dau_ra", "outputs", "output", "ngõ ra", "ngo ra"]):
                    current_section = "output"
                else:
                    current_section = "other"
                continue

            # Parse bullet line only in input or output sections (or if line explicitly says input/output)
            if line.startswith(("-", "*")):
                m_bullet = re.search(
                    r"^[-*]\s*(?:(input|output|ngõ vào|ngõ ra|đầu vào|đầu ra)\s+)?(?:(?:wire|reg)\s+)?(?:\[(\d+):(\d+)\])?\s*`?([A-Za-z0-9_]+)`?\s*[:\-]\s*(.*)$",
                    line, re.IGNORECASE
                )
                if m_bullet:
                    explicit_dir, msb, lsb, p_name, p_desc = m_bullet.groups()
                    clean_name = p_name.strip()
                    if clean_name.lower() in EXCLUDED_PORT_NAMES or clean_name.isdigit() or len(clean_name) < 2:
                        continue
                    if clean_name.lower() in seen:
                        continue

                    # Determine direction based on section context
                    if explicit_dir:
                        dir_val = "output" if any(k in explicit_dir.lower() for k in ["out", "ra"]) else "input"
                    elif current_section in ["input", "output"]:
                        dir_val = current_section
                    else:
                        dir_val = "output" if any(k in line_low for k in ["output", "ngõ ra", "đầu ra", "out"]) else "input"

                    w = (abs(int(msb) - int(lsb)) + 1) if (msb and lsb) else 1
                    ports.append({
                        "name": clean_name,
                        "direction": dir_val,
                        "width": w,
                        "is_clk": any(k in clean_name.lower() for k in ["clk", "clock"]),
                        "is_rst": any(k in clean_name.lower() for k in ["rst", "clr", "reset", "clear"]),
                        "desc": p_desc.strip() if p_desc else ""
                    })
                    seen.add(clean_name.lower())

        return ports

    def get_friendly_description(self):
        """Returns human-readable description for UI / menu."""
        cat = self.classify_system()
        name = self.extract_module_name()

        # If header exists, use it
        m_h1 = re.search(r"^#+\s+(.+)$", self.content, re.MULTILINE)
        if m_h1:
            title = m_h1.group(1).strip()
            if len(title) < 70:
                return f"{title} [{cat}]"

        cat_names = {
            "SOC_AI": "Autonomous SoC AI Accelerator (CPU + RAM + DMA + AI MAC Core)",
            "VENDING": "Máy bán nước tự động 15.000đ (Vending Machine FSM)",
            "ELEVATOR": "Bộ điều khiển Thang máy 5 tầng (5-Floor Intelligent Elevator FSM)",
            "TRAFFIC": "Bộ điều khiển Đèn giao thông ngã tư (Intersection Traffic Light FSM)",
            "ALU": f"Khối xử lý số học và logic ALU ({name})",
            "COUNTER": f"Bộ đếm đồng bộ ({name})",
            "PWM": f"Bộ tạo xung điều chế PWM ({name})",
            "SHIFT_REG": f"Thanh ghi dịch dữ liệu ({name})",
            "SEQUENCE_DETECTOR": f"Bộ phát hiện chuỗi tuần tự ({name})",
            "DIGITAL_LOCK": f"Hệ thống khóa mã số an ninh ({name})",
            "CUSTOM_FSM": f"Máy trạng thái hữu hạn tùy biến ({name})",
            "CUSTOM_LOGIC": f"Mạch kỹ thuật số tự do ({name})"
        }
        return cat_names.get(cat, f"Mô-đun phần cứng: {name}")

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
    sp = sys.argv[1] if len(sys.argv) > 1 else "../specs/soc_ai_spec.md"
    an = SpecAnalyzer(sp)
    print(json.dumps(an.to_dict(), indent=2, ensure_ascii=False))
