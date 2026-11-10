"""
Module: spec_analyzer.py
Description: Spec2RTL Specification Analyzer and Decomposition Engine.
Extracts structured hardware requirements, module lists, interface ports,
and verification benchmarks from natural language/markdown specifications.
"""

import re
import json

class SpecAnalyzer:
    def __init__(self, spec_path):
        self.spec_path = spec_path
        with open(spec_path, "r", encoding="utf-8") as f:
            self.content = f.read()

    def parse_modules(self):
        """Extracts modules defined in the specification."""
        modules = []
        # Find headings or sections mentioning modules
        pattern = r"###?\s*\d*\.?\d*\.?\s*([A-Za-z0-9_]+)\s*\(`([A-Za-z0-9_]+)`\)"
        matches = re.findall(pattern, self.content)
        for name, file_base in matches:
            modules.append({
                "module_name": file_base,
                "description": name
            })
        return modules

    def parse_ports(self):
        """Extracts port table from markdown."""
        ports = []
        table_pattern = r"\|\s*`?([A-Za-z0-9_]+)`?\s*\|\s*([A-Za-z]+)\s*\|\s*(\d+)\s*\|\s*([^\|]+)\|"
        for match in re.finditer(table_pattern, self.content):
            name, direction, width, desc = match.groups()
            if name.lower() not in ["port name", "name"]:
                ports.append({
                    "name": name.strip(),
                    "direction": direction.strip().lower(),
                    "width": int(width.strip()),
                    "description": desc.strip()
                })
        return ports

    def parse_verification_criteria(self):
        """Extracts expected test vectors and verification goals."""
        criteria = {}
        # Find expected result
        m_res = re.search(r"FINAL_RESULT\s*==\s*8'h([0-9A-Fa-f]+)", self.content)
        if m_res:
            criteria["expected_final_result_hex"] = m_res.group(1)
            criteria["expected_final_result_dec"] = int(m_res.group(1), 16)
        return criteria

    def to_json(self):
        return {
            "spec_file": self.spec_path,
            "modules": self.parse_modules(),
            "ports": self.parse_ports(),
            "verification": self.parse_verification_criteria()
        }

if __name__ == "__main__":
    import sys
    spec_file = sys.argv[1] if len(sys.argv) > 1 else "../specs/soc_ai_spec.md"
    analyzer = SpecAnalyzer(spec_file)
    print(json.dumps(analyzer.to_json(), indent=2))
