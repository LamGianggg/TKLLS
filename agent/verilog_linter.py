"""
Module: verilog_linter.py
Mô tả: Bộ phân tích tĩnh AST và quy chuẩn phần cứng vi mạch (Hardware Linter):
- Chốt ẩn (Inferred Latches): case thiếu default, if thiếu else
- Chân lơ lửng (Dangling Pins): input cô lập (như lỗi button_debouncer), output không gán
- Race condition & vi phạm quy chuẩn gán tuần tự/tổ hợp (blocking '=' trong posedge clk)
Tự động dọn dẹp format và chuẩn hóa cú pháp Verilog trước khi biên dịch EDA.
"""

import os
import re

# shortcut: regex-based AST parsing instead of full C++ Icarus/PyVerilog preprocessor, upgrade if multi-file hierarchical macro expansion is needed.

class VerilogLinter:
    """Bộ kiểm tra tĩnh AST và chuẩn hóa cú pháp Verilog RTL & Testbench."""

    @staticmethod
    def sanitize_verilog_code(MaNguon):
        """Dọn dẹp các lỗi cú pháp phổ biến trong mã Verilog."""
        def SuaKyTuPhanTram(Khop):
            NoiDung = Khop.group(0)
            NoiDung = re.sub(r'%!', r' PERCENT!', NoiDung)
            NoiDung = re.sub(r'100%(?!%|[0-9a-zA-Z])', r'100 PERCENT', NoiDung)
            return NoiDung

        MaNguon = re.sub(r'\$display\s*\([^;]+;', SuaKyTuPhanTram, MaNguon)
        MaNguon = re.sub(r',\s*\)', r'\n)', MaNguon)
        return MaNguon

    @staticmethod
    def sanitize_file(DuongDanFile):
        """Đọc, chuẩn hóa cú pháp và lưu lại file Verilog nếu có lỗi."""
        if not os.path.exists(DuongDanFile):
            return False, "File không tồn tại"

        with open(DuongDanFile, "r", encoding="utf-8", errors="replace") as TepTin:
            NoiDungGoc = TepTin.read()

        NoiDungSach = VerilogLinter.sanitize_verilog_code(NoiDungGoc)
        if NoiDungSach != NoiDungGoc:
            with open(DuongDanFile, "w", encoding="utf-8") as TepTin:
                TepTin.write(NoiDungSach)
            return True, "Đã chuẩn hóa cú pháp"
        return False, "Chuẩn cú pháp"

    @staticmethod
    def strip_comments_and_strings(code):
        """Loại bỏ chú thích, chuỗi ký tự và bóc tách block markdown (nếu có)."""
        # Trích xuất mã Verilog nếu được bao bọc trong block markdown
        m_code = re.search(r'```(?:verilog)?\s*([\s\S]*?)```', code)
        if m_code:
            code = m_code.group(1)
        code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
        return code

    @staticmethod
    def extract_module_info(module_str):
        """Trích xuất tên module, cổng input, output và thân logic (cả chuẩn ANSI và Legacy)."""
        m = re.search(r'\bmodule\s+([A-Za-z0-9_]+)\s*(?:#\s*\([\s\S]*?\))?\s*\(([\s\S]*?)\);([\s\S]*?)\bendmodule\b', module_str)
        if not m:
            return None, [], [], ""
        mod_name = m.group(1)
        header = m.group(2)
        body = m.group(3)

        inputs, outputs = [], []
        if re.search(r'\b(input|output)\b', header):
            # Cổng kiểu ANSI
            for port_decl in header.split(','):
                port_decl = port_decl.strip()
                m_in = re.search(r'\binput\b\s*(?:wire|reg)?\s*(?:signed)?\s*(?:\[[^\]]+\])?\s*([A-Za-z0-9_]+)', port_decl)
                if m_in:
                    inputs.append(m_in.group(1).strip())
                m_out = re.search(r'\boutput\b\s*(?:wire|reg)?\s*(?:signed)?\s*(?:\[[^\]]+\])?\s*([A-Za-z0-9_]+)', port_decl)
                if m_out:
                    outputs.append(m_out.group(1).strip())
        else:
            # Cổng kiểu Legacy Verilog-1995 trong thân module
            for m_in in re.finditer(r'\binput\b\s*(?:wire|reg)?\s*(?:signed)?\s*(?:\[[^\]]+\])?\s*([^;]+);', body):
                for name in m_in.group(1).split(','):
                    name = name.strip()
                    if name: inputs.append(name)
            for m_out in re.finditer(r'\boutput\b\s*(?:wire|reg)?\s*(?:signed)?\s*(?:\[[^\]]+\])?\s*([^;]+);', body):
                for name in m_out.group(1).split(','):
                    name = name.strip()
                    if name: outputs.append(name)

        return mod_name, inputs, outputs, body

    @staticmethod
    def check_dangling_pins(clean_code):
        """Phát hiện chân lơ lửng: input không được đọc, output không được gán."""
        dangling = []
        # Tìm từng module trong file
        modules = re.finditer(r'\bmodule\s+([A-Za-z0-9_]+)[\s\S]*?\bendmodule\b', clean_code)
        for mod in modules:
            mod_str = mod.group(0)
            mod_name, inputs, outputs, body = VerilogLinter.extract_module_info(mod_str)
            if not mod_name:
                continue

            # Xóa khai báo biến khỏi thân để kiểm tra sử dụng thực tế
            body_logic = re.sub(r'\b(?:input|output|inout|wire|reg)\s+[^;]+;', '', body)

            for pin in inputs:
                escaped_pin = re.escape(pin)
                if not re.search(r'\b' + escaped_pin + r'\b', body_logic):
                    dangling.append(f"DANGLING_INPUT: Cổng vào '{pin}' ở module '{mod_name}' không được kết nối tới logic nào")

            for pin in outputs:
                escaped_pin = re.escape(pin)
                is_assigned = (
                    re.search(r'\bassign\s+[^;=]*\b' + escaped_pin + r'\b[^;]*=', body_logic) or
                    re.search(r'\b' + escaped_pin + r'(?:\s*\[[^\]]+\])?\s*(?:<=|=)', body_logic) or
                    re.search(r'\.\w+\s*\([^)]*\b' + escaped_pin + r'\b', body_logic)
                )
                if not is_assigned:
                    dangling.append(f"UNASSIGNED_OUTPUT: Cổng ra '{pin}' ở module '{mod_name}' không được gán giá trị")

        return dangling

    @staticmethod
    def check_inferred_latches_and_races(clean_code):
        """Phát hiện chốt ẩn (latches) và vi phạm gán tuần tự/tổ hợp (race conditions)."""
        latches = []
        races = []

        # 1. Khối tuần tự @(posedge / negedge)
        seq_blocks = re.finditer(r'\balways\s*@\s*\(([^)]*(?:posedge|negedge)[^)]*)\)([\s\S]*?)(?=\balways\b|\bendmodule\b|$)', clean_code)
        for sb in seq_blocks:
            sens, body = sb.group(1).strip(), sb.group(2)
            body_no_for = re.sub(r'\bfor\s*\([^;]+;[^;]+;[^)]+\)', '', body)
            blocking_assigns = re.finditer(r'\b([A-Za-z0-9_]+(?:\s*\[[^\]]+\])?)\s*=(?!=)\s*([^;]+);', body_no_for)
            for ba in blocking_assigns:
                var = ba.group(1).strip()
                races.append(f"BLOCKING_IN_SEQUENTIAL: Gán '=' cho '{var}' trong khối tuần tự @({sens}) - Nguy cơ Race Condition")

        # 2. Khối tổ hợp @(*)
        comb_blocks = re.finditer(r'\balways\s*@\s*\((?![^)]*posedge)(?![^)]*negedge)([^)]*)\)([\s\S]*?)(?=\balways\b|\bendmodule\b|$)', clean_code)
        for cb in comb_blocks:
            body = cb.group(2)
            # Kiểm tra gán <= trong khối tổ hợp
            nb_assigns = re.finditer(r'\b([A-Za-z0-9_]+(?:\s*\[[^\]]+\])?)\s*<=\s*([^;]+);', body)
            for nba in nb_assigns:
                var = nba.group(1).strip()
                races.append(f"NONBLOCKING_IN_COMBINATIONAL: Gán '<=' cho '{var}' trong khối tổ hợp - Nên dùng '='")

            # Kiểm tra case thiếu default
            cases = re.finditer(r'\bcase\s*\((.*?)\)([\s\S]*?)\bendcase\b', body)
            for c in cases:
                if not re.search(r'\bdefault\s*:', c.group(2)):
                    latches.append(f"INFERRED_LATCH: Khối case({c.group(1).strip()}) thiếu nhánh 'default:'")

            # Kiểm tra if thiếu else không có giá trị gán mặc định trước đó
            if_matches = re.finditer(r'\bif\s*\((.*?)\)([\s\S]*?)(?=\belse\b|\bend\b|\bendcase\b|\balways\b|$)', body)
            for im in if_matches:
                after_if = body[im.end():]
                if not re.match(r'^\s*else\b', after_if):
                    assigned_vars = re.findall(r'\b([A-Za-z0-9_]+)\s*(?:\[[^\]]+\])?\s*=', im.group(2))
                    prior_code = body[:im.start()]
                    for v in set(assigned_vars):
                        if not re.search(r'\b' + re.escape(v) + r'\b\s*(?:\[[^\]]+\])?\s*=', prior_code):
                            latches.append(f"INFERRED_LATCH: Tín hiệu '{v}' trong 'if' thiếu nhánh 'else' và không có gán mặc định")

        return latches, races

    @staticmethod
    def lint_check(MaNguon):
        """Kiểm tra toàn diện cú pháp và quy chuẩn phần cứng AST."""
        clean = VerilogLinter.strip_comments_and_strings(MaNguon)
        syntax_issues = []

        # 1. Kiểm tra cặp từ khóa cân bằng
        for open_kw, close_kw, name in [('begin', 'end', 'begin/end'), ('case|casex|casez', 'endcase', 'case/endcase'), ('module', 'endmodule', 'module/endmodule')]:
            open_count = len(re.findall(r'\b(?:' + open_kw + r')\b', clean))
            close_count = len(re.findall(r'\b(?:' + close_kw + r')\b', clean))
            if open_count != close_count:
                syntax_issues.append(f"Lệch số lượng khối {name}: {open_count} '{open_kw}' so với {close_count} '{close_kw}'")

        # 2. Kiểm tra format $display
        if re.search(r'\$display\s*\([^"]*"[^"]*%![^"]*"', MaNguon):
            syntax_issues.append("Phát hiện format '%!' không hợp lệ trong lệnh $display")

        # 3. Kiểm tra phần cứng
        dangling_pins = VerilogLinter.check_dangling_pins(clean)
        latches, races = VerilogLinter.check_inferred_latches_and_races(clean)

        all_issues = syntax_issues + dangling_pins + latches + races
        return {
            "valid": len(all_issues) == 0,
            "syntax_issues": syntax_issues,
            "dangling_pins": dangling_pins,
            "latches": latches,
            "race_conditions": races,
            "issues": all_issues
        }

    @staticmethod
    def format_linter_report(lint_res, module_name="Module"):
        """Định dạng báo cáo kiểm tra phần cứng dạng bảng trực quan."""
        status = "PASS (100% SẠCH LATCH & DANGLING)" if lint_res["valid"] else "WARNING / DETECTED ISSUES"
        lines = [
            "+----------------------------------------------------------------------------+",
            "|           BÁO CÁO PHÂN TÍCH TĨNH PHẦN CỨNG & AST (HARDWARE LINTER)         |",
            "+----------------------------------------------------------------------------+",
            f"| Tên thiết kế               : {module_name:<45} |",
            f"| Trạng thái kiểm tra        : {status:<45} |",
            f"| Chốt ẩn (Inferred Latches) : {str(len(lint_res.get('latches', []))) + ' lỗi':<45} |",
            f"| Chân lơ lửng (Dangling)    : {str(len(lint_res.get('dangling_pins', []))) + ' chân':<45} |",
            f"| Vi phạm gán / Race Cond    : {str(len(lint_res.get('race_conditions', []))) + ' điểm':<45} |",
            f"| Lỗi cấu trúc cú pháp       : {str(len(lint_res.get('syntax_issues', []))) + ' lỗi':<45} |",
            "+----------------------------------------------------------------------------+"
        ]
        if not lint_res["valid"]:
            lines.append("| CHI TIẾT CẢNH BÁO PHẦN CỨNG:")
            for issue in lint_res["issues"]:
                lines.append(f"|  * {issue[:72]}")
            lines.append("+----------------------------------------------------------------------------+")
        return "\n".join(lines)

    @staticmethod
    def lint_file(file_path):
        """Kiểm tra và in báo cáo linter cho một file Verilog."""
        if not os.path.exists(file_path):
            return False, {}
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        res = VerilogLinter.lint_check(code)
        report = VerilogLinter.format_linter_report(res, os.path.basename(file_path))
        print(report)
        return res["valid"], res

if __name__ == "__main__":
    MauThu = '''module test; initial begin $display("100%!"); end endmodule'''
    KetQuaSach = VerilogLinter.sanitize_verilog_code(MauThu)
    print("Mã sau dọn dẹp:", KetQuaSach)
    res = VerilogLinter.lint_check(KetQuaSach)
    print(VerilogLinter.format_linter_report(res, "test"))
