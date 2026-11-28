"""
Module: verilog_linter.py
Mô tả: Bộ phân tích tĩnh AST và quy chuẩn phần cứng vi mạch (Hardware Linter):
- Chốt ẩn (Inferred Latches): case thiếu default, if thiếu else trong khối tổ hợp
- Chân lơ lửng (Dangling Pins): input cô lập (như lỗi button_debouncer), output không được gán
- Race condition & vi phạm quy chuẩn gán tuần tự/tổ hợp:
    + Dùng blocking '=' trong khối tuần tự @(posedge/negedge clk) -> dễ gây race condition giữa FF
    + Dùng non-blocking '<=' trong khối tổ hợp @(*) -> lệch hành vi mô phỏng & tổng hợp
Vai trò trong luồng Spec2RTL Fig. 3:
  Đóng vai trò "Gatekeeper tĩnh" ở Pha 2.5 (trước khi chạy mô phỏng EDA tốn thời gian)
  và làm điều kiện kiểm chuẩn tổng hợp được (Synthesizability Gate) ở Pha 4.5 trước khi
  cho phép nạp ngược mã RTL vào Knowledge DB.
"""

import os
import re

# shortcut: regex-based AST parsing instead of full C++ Icarus/PyVerilog preprocessor, upgrade if multi-file hierarchical macro expansion is needed.

class VerilogLinter:
    """Bộ kiểm tra tĩnh AST và chuẩn hóa cú pháp Verilog RTL & Testbench."""

    @staticmethod
    def sanitize_verilog_code(MaNguon):
        """
        Dọn dẹp các lỗi cú pháp phổ biến trong mã Verilog do AI hoặc generator sinh ra:
        - Ký tự '%!' hoặc '100%' trong $display(...) khiến ModelSim/Icarus báo lỗi 'Invalid format specifier'.
        - Dấu phẩy thừa ngay trước dấu ngoặc đóng ',)' ở danh sách khai báo cổng hoặc nối cổng instance.
        """
        def SuaKyTuPhanTram(Khop):
            # Tránh trình biên dịch hiểu nhầm '%' đứng trước '!' hoặc khoảng trắng là format specifier (%d, %b...)
            NoiDung = Khop.group(0)
            NoiDung = re.sub(r'%!', r' PERCENT!', NoiDung)
            NoiDung = re.sub(r'100%(?!%|[0-9a-zA-Z])', r'100 PERCENT', NoiDung)
            return NoiDung

        MaNguon = re.sub(r'\$display\s*\([^;]+;', SuaKyTuPhanTram, MaNguon)
        MaNguon = re.sub(r',\s*\)', r'\n)', MaNguon)
        return MaNguon

    @staticmethod
    def sanitize_file(DuongDanFile):
        """Đọc file Verilog, chuẩn hóa cú pháp và chỉ ghi đè lại đĩa nếu nội dung có thay đổi."""
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
        """
        Tiền xử lý mã nguồn trước khi phân tích AST bằng regex:
        1) Bóc tách mã bên trong block markdown ```verilog ... ``` (nếu còn sót từ output AI).
        2) Xóa chú thích // và /* ... */.
        3) Thay chuỗi "..." bằng "" để tránh nhận diện nhầm từ khóa (if/case/module...) nằm trong chuỗi $display.
        """
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
        """
        Trích xuất tên module, danh sách cổng input, output và thân logic (hỗ trợ cả 2 chuẩn Verilog):
        - Chuẩn ANSI (Verilog-2001): khai báo hướng nằm ngay trong danh sách ngoặc `module foo(input a, b, output reg y);`.
        - Chuẩn Legacy (Verilog-1995): danh sách tên cổng trong ngoặc, còn `input`/`output` khai báo riêng trong thân module.
        """
        m = re.search(r'\bmodule\s+([A-Za-z0-9_]+)\s*(?:#\s*\([\s\S]*?\))?\s*\(([\s\S]*?)\);([\s\S]*?)\bendmodule\b', module_str)
        if not m:
            return None, [], [], ""
        mod_name = m.group(1)
        header = m.group(2)
        body = m.group(3)

        inputs, outputs = [], []
        if re.search(r'\b(input|output|inout)\b', header):
            # Cổng kiểu ANSI: lưu hướng cur_dir để không bị sót các cổng viết chung dòng phân tách bởi dấu phẩy (vd: input wire a, b)
            cur_dir = "input"
            for port_decl in header.split(','):
                port_decl = port_decl.strip()
                if not port_decl:
                    continue
                if re.search(r'\binput\b', port_decl):
                    cur_dir = "input"
                elif re.search(r'\boutput\b', port_decl):
                    cur_dir = "output"
                elif re.search(r'\binout\b', port_decl):
                    cur_dir = "inout"

                # Lấy định danh cuối cùng trong cụm khai báo (bỏ qua độ rộng bit [N:0] và kiểu wire/reg)
                m_name = re.search(r'([A-Za-z0-9_]+)\s*$', port_decl)
                if m_name:
                    name = m_name.group(1).strip()
                    if name.lower() not in {"input", "output", "inout", "wire", "reg", "logic", "signed"}:
                        if cur_dir == "input":
                            inputs.append(name)
                        elif cur_dir in ["output", "inout"]:
                            outputs.append(name)
        else:
            # Cổng kiểu Legacy Verilog-1995: hướng cổng được khai báo bên trong thân module
            for m_in in re.finditer(r'\binput\b\s*(?:wire|reg)?\s*(?:signed)?\s*(?:\[[^\]]+\])?\s*([^;]+);', body):
                for name in m_in.group(1).split(','):
                    name = name.strip()
                    if name: inputs.append(name)
            for m_out in re.finditer(r'\b(?:output|inout)\b\s*(?:wire|reg)?\s*(?:signed)?\s*(?:\[[^\]]+\])?\s*([^;]+);', body):
                for name in m_out.group(1).split(','):
                    name = name.strip()
                    if name: outputs.append(name)

        return mod_name, inputs, outputs, body

    @staticmethod
    def check_dangling_pins(clean_code):
        """
        [Bẫy AST #1: Chân lơ lửng - Dangling Pins]
        Phát hiện các cổng bị ngắt kết nối khỏi mạch thực tế:
        - DANGLING_INPUT: cổng input có khai báo nhưng không hề được đọc trong thân logic (bị cô lập).
        - UNASSIGNED_OUTPUT: cổng output/inout không hề được lái bởi `assign`, phép gán `=`/`<=`,
          hoặc nối vào cổng của một module con `.sub_port(pin)`.
        """
        dangling = []
        # Tìm từng module trong file (hỗ trợ file có nhiều module)
        modules = re.finditer(r'\bmodule\s+([A-Za-z0-9_]+)[\s\S]*?\bendmodule\b', clean_code)
        for mod in modules:
            mod_str = mod.group(0)
            mod_name, inputs, outputs, body = VerilogLinter.extract_module_info(mod_str)
            if not mod_name:
                continue

            # Xóa các câu lệnh khai báo biến (input/output/wire/reg) khỏi thân để tránh regex tự khớp nhầm vào chính dòng khai báo
            body_logic = re.sub(r'\b(?:input|output|inout|wire|reg)\s+[^;]+;', '', body)

            # Kiểm tra từng chân vào: nếu không xuất hiện ở bất kỳ biểu thức nào -> cô lập (dangling)
            for pin in inputs:
                escaped_pin = re.escape(pin)
                if not re.search(r'\b' + escaped_pin + r'\b', body_logic):
                    dangling.append(f"DANGLING_INPUT: Cổng vào '{pin}' ở module '{mod_name}' không được kết nối tới logic nào")

            # Kiểm tra từng chân ra: phải có ít nhất một điểm lái (assign / procedural assignment / port map)
            for pin in outputs:
                escaped_pin = re.escape(pin)
                is_assigned = (
                    re.search(r'\bassign\s+[^;=]*\b' + escaped_pin + r'\b[^;]*=', body_logic) or
                    re.search(r'\b' + escaped_pin + r'(?:\s*\[[^\]]+\])*\s*(?:<=|=(?!=))[^;]+;', body_logic) or
                    re.search(r'\.\w+\s*\([^)]*\b' + escaped_pin + r'\b', body_logic)
                )
                if not is_assigned:
                    dangling.append(f"UNASSIGNED_OUTPUT: Cổng ra '{pin}' ở module '{mod_name}' không được gán giá trị")

        return dangling

    @staticmethod
    def check_inferred_latches_and_races(clean_code):
        """
        [Bẫy AST #2 & #3: Chốt ẩn (Inferred Latches) & Sai quy chuẩn gán Blocking/Non-blocking]
        1. Khối tuần tự @(posedge/negedge):
           - Bẫy BLOCKING_IN_SEQUENTIAL: dùng '=' thay vì '<=' dễ gây race condition giữa các tầng FF.
           - (Bỏ qua biểu thức trong vòng lặp `for(...)` vì biến đếm vòng lặp dùng '=' là hợp lệ).
        2. Khối tổ hợp @(*)/@*:
           - Bẫy NONBLOCKING_IN_COMBINATIONAL: dùng '<=' trong mạch tổ hợp dễ gây sai lệch giữa sim & synthesis.
           - Bẫy INFERRED_LATCH (case): khối `case` thiếu nhánh `default:` -> Quartus tự suy diễn chốt nhớ giữ trạng thái cũ.
           - Bẫy INFERRED_LATCH (if): khối `if` không có `else` đi kèm VÀ tín hiệu được gán bên trong chưa từng
             được gán giá trị mặc định ở phía trên khối `if` (`prior_code`).
        """
        latches = []
        races = []

        # 1. Khối tuần tự @(posedge / negedge) -> bắt buộc dùng non-blocking '<='
        seq_blocks = re.finditer(r'\balways\s*@\s*\(([^)]*(?:posedge|negedge)[^)]*)\)([\s\S]*?)(?=\balways\b|\bendmodule\b|$)', clean_code)
        for sb in seq_blocks:
            sens, body = sb.group(1).strip(), sb.group(2)
            # Loại bỏ header vòng lặp for(...) và assign (nếu có) trước khi quét phép gán '='
            body_no_for = re.sub(r'\bfor\s*\([^;]+;[^;]+;[^)]+\)', '', body)
            body_no_assign = re.sub(r'\bassign\s+[^;]+;', '', body_no_for)
            blocking_assigns = re.finditer(r'\b([A-Za-z0-9_]+(?:\s*\[[^\]]+\])*)\s*=(?!=)\s*([^;]+);', body_no_assign)
            for ba in blocking_assigns:
                var = ba.group(1).strip()
                races.append(f"BLOCKING_IN_SEQUENTIAL: Gán '=' cho '{var}' trong khối tuần tự @({sens}) - Nguy cơ Race Condition")

        # 2. Khối tổ hợp @(*) hoặc @* (không chứa posedge/negedge) -> bắt buộc dùng blocking '=' và phủ kín mọi nhánh
        comb_blocks = re.finditer(r'\balways\s*@\s*(?:\((?![^)]*posedge)(?![^)]*negedge)[^)]*\)|\*)\s*([\s\S]*?)(?=\balways\b|\bendmodule\b|$)', clean_code)
        for cb in comb_blocks:
            body = cb.group(1)
            # Kiểm tra gán <= trong khối tổ hợp
            nb_assigns = re.finditer(r'\b([A-Za-z0-9_]+(?:\s*\[[^\]]+\])*)\s*<=\s*([^;]+);', body)
            for nba in nb_assigns:
                var = nba.group(1).strip()
                races.append(f"NONBLOCKING_IN_COMBINATIONAL: Gán '<=' cho '{var}' trong khối tổ hợp - Nên dùng '='")

            # Kiểm tra case thiếu default (gây Inferred Latch cho mọi biến gán trong case)
            cases = re.finditer(r'\bcase\s*\((.*?)\)([\s\S]*?)\bendcase\b', body)
            for c in cases:
                if not re.search(r'\bdefault\s*:', c.group(2)):
                    latches.append(f"INFERRED_LATCH: Khối case({c.group(1).strip()}) thiếu nhánh 'default:'")

            # Kiểm tra if thiếu else mà không có giá trị gán mặc định trước đó trong cùng khối always @(*)
            if_matches = re.finditer(r'\bif\s*\((.*?)\)([\s\S]*?)(?=\belse\b|\bend\b|\bendcase\b|\balways\b|$)', body)
            for im in if_matches:
                after_if = body[im.end():]
                has_else = bool(re.match(r'^\s*(?:end\s*)*\s*else\b', after_if))
                if not has_else:
                    assigned_vars = re.findall(r'\b([A-Za-z0-9_]+)\s*(?:\[[^\]]+\])*\s*=(?!=)', im.group(2))
                    prior_code = body[:im.start()]
                    for v in set(assigned_vars):
                        # Nếu biến chưa được gán mặc định ở prior_code trước lệnh if -> chắc chắn sinh latch khi điều kiện sai
                        if not re.search(r'\b' + re.escape(v) + r'\b\s*(?:\[[^\]]+\])*\s*=(?!=)', prior_code):
                            latches.append(f"INFERRED_LATCH: Tín hiệu '{v}' trong 'if' thiếu nhánh 'else' và không có gán mặc định")

        return latches, races

    @staticmethod
    def lint_check(MaNguon):
        """
        Kiểm tra toàn diện cú pháp và quy chuẩn phần cứng AST qua 3 tầng:
          Tầng 1: Đếm cân bằng cặp từ khóa khối (begin/end, case/endcase, module/endmodule).
          Tầng 2: Phát hiện format '%!' gây lỗi biên dịch trong $display.
          Tầng 3: Kiểm tra Dangling Pins, Inferred Latches và Blocking/Non-blocking Race Conditions.
        Điều kiện PASS: `valid == True` khi tổng số lỗi `all_issues` bằng 0.
        """
        clean = VerilogLinter.strip_comments_and_strings(MaNguon)
        syntax_issues = []

        # 1. Kiểm tra cặp từ khóa cân bằng (phát hiện sớm trường hợp AI cắt cụt code hoặc thiếu end/endmodule)
        for open_kw, close_kw, name in [('begin', 'end', 'begin/end'), ('case|casex|casez', 'endcase', 'case/endcase'), ('module', 'endmodule', 'module/endmodule')]:
            open_count = len(re.findall(r'\b(?:' + open_kw + r')\b', clean))
            close_count = len(re.findall(r'\b(?:' + close_kw + r')\b', clean))
            if open_count != close_count:
                syntax_issues.append(f"Lệch số lượng khối {name}: {open_count} '{open_kw}' so với {close_count} '{close_kw}'")

        # 2. Kiểm tra format $display
        if re.search(r'\$display\s*\([^"]*"[^"]*%![^"]*"', MaNguon):
            syntax_issues.append("Phát hiện format '%!' không hợp lệ trong lệnh $display")

        # 3. Kiểm tra quy chuẩn phần cứng AST (chân lơ lửng, chốt ẩn, race condition)
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
        """Định dạng kết quả phân tích tĩnh thành bảng báo cáo trực quan trên console (PASS/WARNING)."""
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
        """Đọc file Verilog trên đĩa, chạy `lint_check`, in bảng báo cáo và trả về `(valid, result_dict)`."""
        if not os.path.exists(file_path):
            return False, {}
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        res = VerilogLinter.lint_check(code)
        report = VerilogLinter.format_linter_report(res, os.path.basename(file_path))
        print(report)
        return res["valid"], res

if __name__ == "__main__":
    # Kiểm thử nhanh quy trình sanitize + lint khi chạy trực tiếp module
    MauThu = '''module test; initial begin $display("100%!"); end endmodule'''
    KetQuaSach = VerilogLinter.sanitize_verilog_code(MauThu)
    print("Mã sau dọn dẹp:", KetQuaSach)
    res = VerilogLinter.lint_check(KetQuaSach)
    print(VerilogLinter.format_linter_report(res, "test"))
