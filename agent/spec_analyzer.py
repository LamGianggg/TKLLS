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
            # Check for parenthesized identifier in H1 line first (allow spaces, e.g. (Stepper Motor))
            m_h1_paren = re.search(r"\(([A-Za-z0-9_\s]{2,})\)", h1_line)
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

        # Specific peripherals & protocols (evaluated before simple arithmetic / counters)
        if any(k in text for k in ["khoa", "khoa so", "password", "mat khau", "digital lock", "safe lock", "an ninh", "unlock"]):
            return "DIGITAL_LOCK"
        if any(k in text for k in ["uart", "uart_tx", "truyen noi tiep", "serial tx", "tx_data", "tx_serial"]):
            return "UART_TX"
        if any(k in text for k in ["dong co buoc", "stepper", "step motor", "motor buoc", "phase_out"]):
            return "STEPPER_MOTOR"
        if any(k in text for k in ["may giat", "washing", "washing_machine", "giat tu dong"]):
            return "WASHING_MACHINE"
        if any(k in text for k in ["bao chay", "bao trom", "smart home", "nha thong minh", "smoke_gas", "motion_pir"]):
            return "SMART_ALARM"
        if any(k in text for k in ["pwm", "do rong xung", "duty cycle", "xung pwm"]):
            return "PWM"
        if any(k in text for k in ["fifo", "queue", "hang doi", "buffer"]):
            return "FIFO"

        # Multiplier
        if any(k in text for k in ["multiplier", "nhan 4 bit", "nhan 8 bit", "nhan 16 bit", "mach nhan", "bo nhan", "multi_"]):
            return "MULTIPLIER"
        # Adder
        if any(k in text for k in ["adder", "cong 4 bit", "cong 8 bit", "cong 16 bit", "mach cong", "bo cong", "full adder", "half adder"]):
            return "ADDER"
        # Subtractor (use word boundaries to avoid matching 'bo truyen')
        if re.search(r"\b(?:subtractor|tru\s+\d+\s*bit|mach\s+tru|bo\s+tru|phep\s+tru)\b", text):
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
        # Counter (exclude FIFO buffers)
        if any(k in text for k in ["counter", "dem len", "dem xuong", "up down", "up_down", "dem 1 bit", "dem 4 bit", "dem 8 bit", "dem nhi phan"]) or (re.search(r"\b(?:bo\s+dem|mach\s+dem)\b", text) and not any(f in text for f in ["fifo", "buffer", "hang doi", "queue"])):
            return "COUNTER"
        if any(k in text for k in ["shift", "thanh ghi dich", "thanh ghi", "dich trai", "dich phai", "sipo", "piso"]):
            return "SHIFT_REG"
        if any(k in text for k in ["do chuoi", "phat hien chuoi", "sequence detector", "nhan dang chuoi", "tim chuoi", "sequence_detector"]) or re.search(r"\b(?:chuoi\s+bit|sequence\s+of\s+bits|chuoi\s+1011|chuoi\s+1101)\b", text):
            return "SEQUENCE_DETECTOR"
        if any(k in text for k in ["fsm", "trang thai", "state machine", "chuyen trang thai"]):
            return "CUSTOM_FSM"

        return "CUSTOM_LOGIC"

    def extract_ports(self):
        """Extracts input and output ports from tables, bullet points, numbered lists, or prose."""
        ports = []
        seen = set()

        EXCLUDED_PORT_NAMES = {
            "port", "port_name", "name", "ten_chan", "ten_cong", "mo_ta", "input", "output",
            "dau_vao", "dau_ra", "tin_hieu", "khi", "neu", "gia_tri", "truong_hop", "so", "chu_so",
            "buoc", "chu_ky", "chu_ky_sau", "thoi_gian", "muc", "che_do", "note", "luu_y", "chu_y",
            "wire", "reg", "logic", "ra", "vao"
        }

        # 1. Parse markdown tables
        table_pattern = r"\|\s*`?\*?\*?([A-Za-z0-9_]+)\*?\*?`?\s*\|\s*([A-Za-z\s]+)\s*\|\s*([^\|]+)\|\s*([^\|]+)\|"
        for match in re.finditer(table_pattern, self.content):
            name, direction, width_str, desc = match.groups()
            name_clean = name.strip()
            if name_clean.lower() not in EXCLUDED_PORT_NAMES and not name_clean.isdigit():
                w = 1
                m_bus = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", width_str)
                m_bit = re.search(r"(\d+)\s*(?:bit|b)?", width_str.lower())
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

        # 2. Section-aware Markdown bullet & numbered points parser
        current_section = None
        for raw_line in self.content.splitlines():
            line = raw_line.strip()
            # Clean markdown bold/code markers while preserving underscores _
            line_clean = re.sub(r"\*{1,2}|`", "", line).strip()
            line_no_accent = remove_vietnamese_accents(line_clean.lower())

            # Section header check (e.g. ## 1. Đầu vào (Inputs): / 2. Đầu ra: / Ngõ vào:)
            m_sec = re.search(r"\b(dau vao|inputs?|ngo vao|dau ra|outputs?|ngo ra|hoat dong|chuc nang|nguyen ly|logic)\b", line_no_accent)
            is_section_header = False
            if m_sec:
                # Disambiguate section headers from port bullets mentioning "tín hiệu ra/vào"
                is_bullet = bool(re.match(r"^[-*+•]\s*(?:\[|\w+\s*[:\-])", line_clean))
                if not is_bullet:
                    if ":" in line_clean:
                        before_col = line_no_accent.split(":")[0]
                        if m_sec.group(1) in before_col:
                            is_section_header = True
                    else:
                        is_section_header = True

            if is_section_header:
                if any(k in line_no_accent for k in ["dau vao", "dau_vao", "inputs", "input", "ngo vao", "tin hieu vao"]):
                    current_section = "input"
                elif any(k in line_no_accent for k in ["dau ra", "dau_ra", "outputs", "output", "ngo ra", "tin hieu ra"]):
                    current_section = "output"
                else:
                    current_section = "other"
                continue

            # Ignore lines in 'other' (logic descriptions) unless explicit input/output keyword is present
            if current_section == "other" and not any(k in line_no_accent for k in ["input", "output", "dau vao", "dau ra", "ngo vao", "ngo ra"]):
                continue

            # Detect item targets: bullets (-, *, +, •), numbered (1., 2.), or bare 'name: desc' in I/O sections
            m_item = re.match(r"^(?:[-*+•]|\d+[\.\)])\s*(.*)$", line_clean)
            target = m_item.group(1).strip() if m_item else (line_clean if current_section in ["input", "output"] and ":" in line_clean else None)
            if not target:
                continue

            target_no_accent = remove_vietnamese_accents(target.lower())
            explicit_dir = None
            m_dir = re.search(r"\b(input|output|ngo vao|ngo ra|dau vao|dau ra)\b", target_no_accent)
            if m_dir:
                explicit_dir = "output" if any(k in m_dir.group(1) for k in ["out", "ra"]) else "input"

            # Syntax variations for port names and bit widths
            m1 = re.search(r"(?:(?:wire|reg)\s+)?\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*([A-Za-z0-9_]+)\s*[:\-\s](.*)", target)
            m2 = re.search(r"([A-Za-z0-9_]+)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*[:\-\s](.*)", target)
            m3 = re.search(r"([A-Za-z0-9_]+)\s*\(\s*(\d+)\s*(?:bit|b)?\s*\)\s*[:\-\s](.*)", target)
            m4 = re.search(r"([A-Za-z0-9_]+)\s*[:\-]\s*(.*)", target)

            p_name, w, p_desc = None, 1, ""
            if m1:
                msb, lsb, p_name, p_desc = m1.groups()
                w = abs(int(msb) - int(lsb)) + 1
            elif m2:
                p_name, msb, lsb, p_desc = m2.groups()
                w = abs(int(msb) - int(lsb)) + 1
            elif m3:
                p_name, bit_w, p_desc = m3.groups()
                w = int(bit_w)
            elif m4:
                p_name, p_desc = m4.groups()
                m_wdesc = re.search(r"\b(\d+)\s*(?:bit|b)\b", p_desc.lower())
                if m_wdesc:
                    w = int(m_wdesc.group(1))

            if p_name:
                clean_name = p_name.strip()
                if clean_name.lower() in EXCLUDED_PORT_NAMES or clean_name.isdigit() or len(clean_name) < 1:
                    continue
                if clean_name.lower() in seen:
                    continue

                dir_val = explicit_dir if explicit_dir else (
                    current_section if current_section in ["input", "output"] else (
                        "output" if any(k in target_no_accent for k in ["out", "ra"]) else "input"
                    )
                )

                ports.append({
                    "name": clean_name,
                    "direction": dir_val,
                    "width": w,
                    "is_clk": any(k in clean_name.lower() for k in ["clk", "clock"]),
                    "is_rst": any(k in clean_name.lower() for k in ["rst", "clr", "reset", "clear"]),
                    "desc": p_desc.strip() if p_desc else ""
                })
                seen.add(clean_name.lower())

        # 3. Fallback Prose Parser (if no table or bullet ports were detected)
        if not ports:
            content_no_accent = remove_vietnamese_accents(self.content.lower())
            m_in = re.search(r"(?:dau vao|ngo vao|inputs?)\s*(?:la|gom|:|cac tin hieu)?\s*([^.]+?)(?:dau ra|ngo ra|outputs?|$)", content_no_accent)
            m_out = re.search(r"(?:dau ra|ngo ra|outputs?)\s*(?:la|gom|:|cac tin hieu)?\s*([^.]+?)(?:dau vao|ngo vao|inputs?|$)", content_no_accent)

            def extract_from_clause(clause, direction):
                clause_ports = []
                tokens = re.split(r"[,;]|\s+\bva\b\s+|\s+\band\b\s+", clause)
                for tok in tokens:
                    tok = tok.strip()
                    if not tok: continue
                    m_w = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", tok)
                    m_b = re.search(r"(\d+)\s*(?:bit|b)", tok)
                    w = 1
                    if m_w: w = abs(int(m_w.group(1)) - int(m_w.group(2))) + 1
                    elif m_b: w = int(m_b.group(1))
                    names = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", tok)
                    for n in names:
                        if n.lower() not in EXCLUDED_PORT_NAMES and n.lower() not in ["bit", "b", "la", "gom", "cac", "tin", "hieu", "so", "va", "and", "with", "cho"]:
                            if n.lower() not in seen:
                                clause_ports.append({
                                    "name": n,
                                    "direction": direction,
                                    "width": w,
                                    "is_clk": any(k in n.lower() for k in ["clk", "clock"]),
                                    "is_rst": any(k in n.lower() for k in ["rst", "clr", "reset", "clear"]),
                                    "desc": "Extracted from prose"
                                })
                                seen.add(n.lower())
                return clause_ports

            if m_in:
                ports.extend(extract_from_clause(m_in.group(1), "input"))
            if m_out:
                ports.extend(extract_from_clause(m_out.group(1), "output"))

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
