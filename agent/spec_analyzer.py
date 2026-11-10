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

def clean_identifier(text):
    """Converts arbitrary text (including Vietnamese with diacritics) into a valid Verilog identifier."""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9_]+', '_', text).strip('_').lower()
    # Strip common noise prefixes
    for prefix in ["thiet_ke_", "xay_dung_", "mo_ta_", "mach_", "he_thong_"]:
        if text.startswith(prefix) and len(text) > len(prefix):
            text = text[len(prefix):]
    if not text:
        text = "custom_module"
    if text[0].isdigit():
        text = "mod_" + text
    return text

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
        # 1. Look for explicit module declaration: "module <name>" or "Module: <name>"
        m = re.search(r"(?:module|Module|Tên module|Module Name)\s*[:=]?\s*[`\*]?([A-Za-z0-9_]+)[`\*]?", self.content)
        if m and m.group(1).lower() not in ["name", "entity", "top"]:
            return m.group(1).lower()

        # 2. Look for English name in parentheses in header, e.g. "# Thiết kế bộ đếm 4 bit (Counter_4bit)"
        m_paren = re.search(r"#\s*.*?\(([A-Za-z0-9_\s\-]+)\)", self.content)
        if m_paren:
            candidate = clean_identifier(m_paren.group(1))
            if candidate and len(candidate) > 2:
                return candidate

        # 3. Look for primary Markdown H1 / H2 header
        m_h1 = re.search(r"^#+\s+(.+)$", self.content, re.MULTILINE)
        if m_h1:
            header_text = m_h1.group(1).split("–")[0].split("-")[0].strip()
            candidate = clean_identifier(header_text)
            if candidate and len(candidate) > 2 and candidate != "custom_module":
                return candidate

        # 4. Fallback to file name stem
        if os.path.exists(self.spec_path):
            stem = os.path.splitext(os.path.basename(self.spec_path))[0]
            clean_stem = clean_identifier(stem)
            if clean_stem:
                return clean_stem

        return "custom_hw_module"

    def classify_system(self):
        """Classifies the specification into a known or generic hardware architecture."""
        text = (os.path.basename(self.spec_path) + " " + self.content).lower()

        if "soc" in text or "dma" in text and "relu" in text or "mac_unit" in text:
            return "SOC_AI"
        if "vend" in text or "bán nước" in text or "ban nuoc" in text:
            return "VENDING"
        if "thang" in text or "elevator" in text:
            return "ELEVATOR"
        if "traffic" in text or "giao thông" in text or "giao thong" in text:
            return "TRAFFIC"

        if any(k in text for k in ["alu", "toán học", "arithmetic", "cộng", "trừ", "nhân", "chia", "opcode"]):
            return "ALU"
        if any(k in text for k in ["fifo", "queue", "hàng đợi", "hang doi"]):
            return "FIFO"
        if any(k in text for k in ["gray", "gray_counter", "mã gray", "ma gray"]):
            return "GRAY_COUNTER"
        if any(k in text for k in ["counter", "bộ đếm", "bo dem", "đếm lên", "đếm xuống", "up_down"]):
            return "COUNTER"
        if any(k in text for k in ["encoder", "priority", "ưu tiên", "u tien", "mã hóa", "ma hoa"]):
            return "ENCODER"
        if any(k in text for k in ["pulse", "edge", "cạnh xung", "canh xung", "phát hiện xung"]):
            return "PULSE_DETECTOR"
        if any(k in text for k in ["barrel", "dịch vòng", "dich vong", "rotat"]):
            return "BARREL_SHIFTER"
        if any(k in text for k in ["pwm", "độ rộng xung", "duty cycle", "xung pwm"]):
            return "PWM"
        if any(k in text for k in ["shift", "thanh ghi dịch", "thanh ghi", "dịch trái", "dịch phải", "sipo", "piso"]):
            return "SHIFT_REG"
        if any(k in text for k in ["chuỗi", "sequence", "phát hiện", "detector", "1011", "1101"]):
            return "SEQUENCE_DETECTOR"
        if any(k in text for k in ["khóa", "khoa so", "password", "mật khẩu", "lock", "an ninh"]):
            return "DIGITAL_LOCK"
        if any(k in text for k in ["fsm", "trạng thái", "state machine", "chuyển trạng thái"]):
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
                # Parse width flexibly: "16 bit", "16", "[15:0]", "8-bit", etc.
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

        # 2. Parse bullet points: e.g. "- clk: xung clock", "- input [3:0] a: toán hạng", etc.
        bullet_pattern = r"[-*]\s*(?:input|output|ngõ vào|ngõ ra|đầu vào|đầu ra)?\s*(?:(?:wire|reg)\s+)?(?:\[(\d+):(\d+)\])?\s*`?([A-Za-z0-9_]+)`?\s*[:\-]?\s*(.*)"
        for match in re.finditer(bullet_pattern, self.content, re.IGNORECASE):
            msb, lsb, name, desc = match.groups()
            name_clean = name.strip()
            if name_clean.lower() not in seen and len(name_clean) > 0 and name_clean.lower() not in ["input", "output", "đầu vào", "đầu ra", "mô tả"]:
                w = (int(msb) - int(lsb) + 1) if (msb and lsb) else 1
                line_lower = match.group(0).lower()
                dir_val = "output" if any(k in line_lower for k in ["output", "ngõ ra", "đầu ra", "out"]) else "input"
                ports.append({
                    "name": name_clean,
                    "direction": dir_val,
                    "width": w,
                    "is_clk": any(k in name_clean.lower() for k in ["clk", "clock"]),
                    "is_rst": any(k in name_clean.lower() for k in ["rst", "clr", "reset", "clear"]),
                    "desc": desc.strip() if desc else ""
                })
                seen.add(name_clean.lower())

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
