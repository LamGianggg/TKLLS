"""
Module: reflection_loop.py
Description: Adaptive Reflection & Verification Engine (based on NVIDIA Spec2RTL-Agent).
Analyzes compile and functional simulation errors, diagnoses root causes,
and provides iterative feedback prompts or automated self-healing.
"""

class ReflectionAgent:
    def __init__(self, simulator):
        self.simulator = simulator

    def diagnose_error(self, flow_result):
        """Diagnoses failure mode from simulator output."""
        stage = flow_result.get("stage", "unknown")
        errors = flow_result.get("errors", [])
        log = flow_result.get("log", "")

        diagnosis = {
            "stage": stage,
            "category": "Unknown",
            "root_cause": "",
            "suggested_fix": ""
        }

        if stage == "compile":
            diagnosis["category"] = "Syntax / Linting Error"
            diagnosis["root_cause"] = "Verilog compiler failed to resolve symbols, port widths, or syntax."
            diagnosis["suggested_fix"] = "Check module declarations, semicolons, wire/reg types, and port widths."
        elif stage == "simulate":
            if "TIMEOUT" in log:
                diagnosis["category"] = "FSM Deadlock / Handshake Timeout"
                diagnosis["root_cause"] = "FSM failed to advance or wait condition (e.g., DACK, SYSTEM_INTR) never met."
                diagnosis["suggested_fix"] = "Verify handshake logic (DREQ -> DACK) and state transition conditions."
            elif "MISMATCH" in log:
                diagnosis["category"] = "Functional Arithmetic Mismatch"
                diagnosis["root_cause"] = "Output value differed from expected golden reference (e.g. 0x00 != 0x0C)."
                diagnosis["suggested_fix"] = "Verify RAM write enable timing, MAC accumulation enable, and output register latch."

        return diagnosis

    def build_repair_prompt(self, module_name, code, diagnosis, error_details):
        """Generates an LLM prompt to automatically repair the module."""
        prompt = f"""[Spec2RTL Reflection & Repair Task]
You are an expert Digital IC Design Engineer fixing an automated hardware synthesis failure.

Target Module: `{module_name}`
Failure Stage: {diagnosis['stage']}
Category: {diagnosis['category']}
Root Cause: {diagnosis['root_cause']}

Error Log Details:
{error_details}

Current Code:
```verilog
{code}
```

Instructions:
1. Identify the exact line causing the compiler error or functional failure.
2. Maintain standard synthesizable Verilog (IEEE 1364-2001).
3. Return ONLY the complete, corrected Verilog module enclosed in ```verilog ... ```.
"""
        return prompt
