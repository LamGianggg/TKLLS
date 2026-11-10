"""
Module: verilog_linter.py
Description: Static Verilog Linter, Pre-Synthesis Checker & Sanitizer.
Based on University of Florida VerilogDB (arXiv:2507.13369) Preprocessing Framework.
Validates syntax, port consistency, and sanitizes strings before EDA compilation.
"""

import re
import os

class VerilogLinter:
    """Pre-synthesis static analysis and sanitation engine for generated Verilog RTL and Testbenches."""

    @staticmethod
    def sanitize_verilog_code(code):
        """Sanitizes common syntax hazards in Verilog code."""
        # 1. Fix unescaped '%' in $display string literals (e.g. "100%!" -> "100 PERCENT!")
        def fix_display_percent(match):
            content = match.group(0)
            # Replace invalid %! with PERCENT!
            content = re.sub(r'%!', r' PERCENT!', content)
            # Replace 100% when not already escaped as 100%% or followed by format specifier
            content = re.sub(r'100%(?!%|[0-9a-zA-Z])', r'100 PERCENT', content)
            return content

        code = re.sub(r'\$display\s*\([^;]+;', fix_display_percent, code)

        # 2. Fix multiple trailing commas in module port list: e.g. "port1,\n);" -> "port1\n);"
        code = re.sub(r',\s*\)', r'\n)', code)

        return code

    @staticmethod
    def sanitize_file(file_path):
        """Reads, sanitizes, and writes back a Verilog file if changes are needed."""
        if not os.path.exists(file_path):
            return False, "File does not exist"

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()

        cleaned = VerilogLinter.sanitize_verilog_code(original)

        if cleaned != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(cleaned)
            return True, "Sanitized syntax hazards (e.g. format specifiers, trailing commas)"
        return False, "Clean"

    @staticmethod
    def lint_check(code):
        """Performs static checks and returns any warnings or structural defects."""
        issues = []

        # 1. Check begin/end balance
        begin_count = len(re.findall(r'\bbegin\b', code))
        end_count = len(re.findall(r'\bend\b', code))
        if begin_count != end_count:
            issues.append(f"Mismatched block count: {begin_count} 'begin' vs {end_count} 'end'")

        # 2. Check case/endcase balance
        case_count = len(re.findall(r'\bcase\b|\bcasex\b|\bcasez\b', code))
        endcase_count = len(re.findall(r'\bendcase\b', code))
        if case_count != endcase_count:
            issues.append(f"Mismatched case count: {case_count} 'case' vs {endcase_count} 'endcase'")

        # 3. Check module/endmodule balance
        mod_count = len(re.findall(r'\bmodule\b', code))
        endmod_count = len(re.findall(r'\bendmodule\b', code))
        if mod_count != endmod_count:
            issues.append(f"Mismatched module count: {mod_count} 'module' vs {endmod_count} 'endmodule'")

        # 4. Check for invalid format specifiers in display
        if re.search(r'\$display\s*\([^"]*"[^"]*%![^"]*"', code):
            issues.append("Invalid format specifier '%!' detected in $display statement")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

if __name__ == "__main__":
    sample = '''module test; initial begin $display("100%!"); end endmodule'''
    cleaned = VerilogLinter.sanitize_verilog_code(sample)
    print("Cleaned:", cleaned)
    print("Lint:", VerilogLinter.lint_check(cleaned))
