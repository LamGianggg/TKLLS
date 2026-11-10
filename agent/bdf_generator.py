"""
Module: bdf_generator.py
Description: Automated BDF (Block Design File) and BSF (Block Symbol File) Generator.
Produces 100% compliant, editable, synthesizable Altera / Intel Quartus II 13.0sp1
schematic diagrams with proper pin ordering, bus line widths, and grid alignment.
"""

import os
import re

class BDFGenerator:
    def __init__(self):
        pass

    def generate_bsf_from_rtl(self, rtl_path, bsf_path):
        """Generates a valid Quartus .bsf symbol file directly from Verilog RTL.
        Used as a cross-platform fallback when quartus_map CLI is not available."""
        with open(rtl_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()

        # Strip comments
        clean_code = re.sub(r"//.*", "", code)
        clean_code = re.sub(r"/\*.*?\*/", "", clean_code, flags=re.DOTALL)

        m_mod = re.search(r"module\s+([A-Za-z0-9_]+)\s*\((.*?)\);", clean_code, re.DOTALL)
        if not m_mod:
            return None

        mod_name = m_mod.group(1)
        port_block = m_mod.group(2)

        inputs = []
        outputs = []
        for line in port_block.split(","):
            line = line.strip()
            m_p = re.search(r"(input|output)\s+(?:wire|reg)?\s*(?:\[(\d+):(\d+)\])?\s*([A-Za-z0-9_]+)", line)
            if m_p:
                direction, msb, lsb, p_name = m_p.groups()
                w = (int(msb) - int(lsb) + 1) if (msb and lsb) else 1
                p_info = {
                    "name": p_name,
                    "direction": direction,
                    "width": w,
                    "msb": msb,
                    "lsb": lsb,
                    "is_bus": w > 1
                }
                if direction == "input":
                    inputs.append(p_info)
                else:
                    outputs.append(p_info)

        max_ports = max(len(inputs), len(outputs), 2)
        sym_h = max(112, (max_ports + 2) * 24)
        sym_h = (sym_h // 16) * 16
        sym_w = 192

        port_lines = []
        # Inputs at left (x = 0)
        y_step = sym_h // (len(inputs) + 1)
        for idx, inp in enumerate(inputs):
            py = ((idx + 1) * y_step // 8) * 8
            w_str = f"[{inp['msb']}..{inp['lsb']}]" if inp["is_bus"] else ""
            full_name = f"{inp['name']}{w_str}"
            lw = 3 if inp["is_bus"] else 1
            port_lines.append(f"""\t(port
\t\t(pt 0 {py})
\t\t(input)
\t\t(text "{full_name}" (rect 0 0 {len(full_name)*7} 12)(font "Arial" ))
\t\t(text "{full_name}" (rect 21 {py-5} {21 + len(full_name)*7} {py+7})(font "Arial" ))
\t\t(line (pt 0 {py})(pt 16 {py})(line_width {lw}))
\t)""")

        # Outputs at right (x = sym_w)
        y_step_out = sym_h // (len(outputs) + 1)
        for idx, out in enumerate(outputs):
            py = ((idx + 1) * y_step_out // 8) * 8
            w_str = f"[{out['msb']}..{out['lsb']}]" if out["is_bus"] else ""
            full_name = f"{out['name']}{w_str}"
            lw = 3 if out["is_bus"] else 1
            text_x = sym_w - 21 - len(full_name)*7
            port_lines.append(f"""\t(port
\t\t(pt {sym_w} {py})
\t\t(output)
\t\t(text "{full_name}" (rect 0 0 {len(full_name)*7} 12)(font "Arial" ))
\t\t(text "{full_name}" (rect {text_x} {py-5} {text_x + len(full_name)*7} {py+7})(font "Arial" ))
\t\t(line (pt {sym_w} {py})(pt {sym_w - 16} {py})(line_width {lw}))
\t)""")

        bsf_code = f"""/*
WARNING: Do NOT edit the input and output ports in this file in a text
editor if you plan to continue editing the block that represents it in
the Block Editor! File corruption is VERY likely to occur.
*/
(header "symbol" (version "1.1"))
(symbol
\t(rect 16 16 {16 + sym_w} {16 + sym_h})
\t(text "{mod_name}" (rect 5 0 {5 + len(mod_name)*7} 12)(font "Arial" ))
\t(text "inst" (rect 8 {sym_h - 16} 20 {sym_h - 4})(font "Arial" ))
""" + "\n".join(port_lines) + f"""
\t(drawing
\t\t(rectangle (rect 16 16 {sym_w - 16} {sym_h - 16})(line_width 1))
\t)
)
"""
        with open(bsf_path, "w", encoding="utf-8") as f:
            f.write(bsf_code)
        return bsf_path

    def generate_bdf_from_bsf(self, bsf_path, bdf_path, sym_x=368, sym_y=176):
        """Reads a .bsf symbol and creates a 100% compliant, editable Quartus .bdf schematic.
        Adheres strictly to Quartus II syntax:
          1. Header
          2. All Pins (with line_width 3 for bus pins)
          3. Symbol block
          4. All Connectors (with '(bus)' tag for buses)
        """
        with open(bsf_path, "r", encoding="utf-8", errors="replace") as f:
            bsf_text = f.read()

        # Parse symbol rect
        m_rect = re.search(r'\(symbol\s*\n\s*\(rect\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\)', bsf_text)
        if not m_rect:
            raise ValueError(f"Invalid BSF file: {bsf_path}")

        orig_w = int(m_rect.group(3)) - int(m_rect.group(1))
        orig_h = int(m_rect.group(4)) - int(m_rect.group(2))

        # Round sym_x and sym_y to 8px grid
        sym_x = (sym_x // 8) * 8
        sym_y = (sym_y // 8) * 8
        sym_x2 = sym_x + orig_w
        sym_y2 = sym_y + orig_h

        # Extract port definitions
        port_blocks = re.findall(
            r'(\(port\s*\n\s*\(pt\s+(\d+)\s+(\d+)\)\s*\n\s*\((input|output)\)\s*\n\s*\(text\s+"([^"]+)".*?\n\t\))',
            bsf_text, re.DOTALL
        )

        # Extract inner symbol from BSF
        inner_symbol = bsf_text[bsf_text.find('(symbol'):]
        inner_symbol = re.sub(r'\(rect\s+\d+\s+\d+\s+\d+\s+\d+\)', f'(rect {sym_x} {sym_y} {sym_x2} {sym_y2})', inner_symbol, count=1)

        pins_code = []
        connectors_code = []

        in_pin_x = sym_x - 208
        out_pin_x = sym_x2 + 80

        for full_block, pt_x, pt_y, direction, port_name in port_blocks:
            px = int(pt_x)
            py = int(pt_y)
            abs_port_y = sym_y + py

            is_bus = ('[' in port_name and '..' in port_name) or ('[' in port_name and ':' in port_name)
            # Normalize [M:L] to [M..L] for Quartus BDF syntax
            bdf_port_name = re.sub(r'\[(\d+):(\d+)\]', r'[\1..\2]', port_name)

            if direction == "input":
                pin_y = abs_port_y - 8
                bus_line = "\t\t(line (pt 113 8)(pt 168 8)(line_width 3))\n" if is_bus else "\t\t(line (pt 113 8)(pt 168 8))\n"
                p_box = f"""(pin
\t(input)
\t(rect {in_pin_x} {pin_y} {in_pin_x + 168} {pin_y + 16})
\t(text "INPUT" (rect 125 0 153 10)(font "Arial" (font_size 6)))
\t(text "{bdf_port_name}" (rect 5 0 {5 + len(bdf_port_name)*7} 12)(font "Arial" ))
\t(pt 168 8)
\t(drawing
\t\t(line (pt 84 12)(pt 109 12))
\t\t(line (pt 84 4)(pt 109 4))
{bus_line}\t\t(line (pt 84 12)(pt 84 4))
\t\t(line (pt 109 4)(pt 113 8))
\t\t(line (pt 109 12)(pt 113 8))
\t)
\t(text "VCC" (rect 128 7 148 17)(font "Arial" (font_size 6)))
)"""
                pins_code.append(p_box)
                bus_tag = " (bus)" if is_bus else ""
                connectors_code.append(f"(connector (pt {in_pin_x + 168} {abs_port_y}) (pt {sym_x} {abs_port_y}){bus_tag})")

            elif direction == "output":
                pin_y = abs_port_y - 8
                bus_line = "\t\t(line (pt 0 8)(pt 52 8)(line_width 3))\n" if is_bus else "\t\t(line (pt 0 8)(pt 52 8))\n"
                p_box = f"""(pin
\t(output)
\t(rect {out_pin_x} {pin_y} {out_pin_x + 176} {pin_y + 16})
\t(text "OUTPUT" (rect 1 0 39 10)(font "Arial" (font_size 6)))
\t(text "{bdf_port_name}" (rect 90 0 {90 + len(bdf_port_name)*7} 12)(font "Arial" ))
\t(pt 0 8)
\t(drawing
{bus_line}\t\t(line (pt 52 4)(pt 78 4))
\t\t(line (pt 52 12)(pt 78 12))
\t\t(line (pt 52 12)(pt 52 4))
\t\t(line (pt 78 4)(pt 82 8))
\t\t(line (pt 82 8)(pt 78 12))
\t\t(line (pt 78 12)(pt 82 8))
\t)
)"""
                pins_code.append(p_box)
                bus_tag = " (bus)" if is_bus else ""
                connectors_code.append(f"(connector (pt {sym_x2} {abs_port_y}) (pt {out_pin_x} {abs_port_y}){bus_tag})")

        # Combine strictly in Quartus official BDF order: Header -> Pins -> Symbol -> Connectors
        bdf_lines = [
            '/* Auto-generated by Spec2RTL & Prompt2Silicon */',
            '(header "graphic" (version "1.4"))'
        ]
        bdf_lines.extend(pins_code)
        bdf_lines.append(inner_symbol.strip())
        bdf_lines.extend(connectors_code)

        with open(bdf_path, "w", encoding="utf-8") as f:
            f.write("\n".join(bdf_lines) + "\n")
        return bdf_path

if __name__ == "__main__":
    gen = BDFGenerator()
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bsf = os.path.join(base, "quartus", "vending_machine.bsf")
    bdf = os.path.join(base, "quartus", "top_vending_machine.bdf")
    if os.path.exists(bsf):
        gen.generate_bdf_from_bsf(bsf, bdf)
        print("Generated compliant BDF at:", bdf)
