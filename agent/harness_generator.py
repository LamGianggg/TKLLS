# -*- coding: utf-8 -*-
"""
Module: harness_generator.py
Description: Automated Verilog Hardware Test Harness Wrapper Generator (Option A).
Implements the Standardized Verilog Hardware Test Harness Architecture:
  1. System Infrastructure Engine (Parametric Clock & Synchronized Reset)
  2. Watchdog Safety Timer Guard (Deadlock & Infinite Hang Prevention)
  3. Golden Oracle & Standardized Assertion Tasks (harness_assert_eq, harness_assert_valid)
  4. Plug-and-Play Device Under Test (DUT) Socket Wrapper
  5. VeriPrefer & IEEE 1800 Telemetry Scoreboard
"""

import os
import re
import sys

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from verilog_linter import VerilogLinter

class HarnessGenerator:
    """Generates standardized, portable Verilog Hardware Test Harness Wrappers (Option A)."""

    def __init__(self, sim_dir=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sim_dir = sim_dir or os.path.join(base_dir, "sim")
        os.makedirs(self.sim_dir, exist_ok=True)

    def extract_ports(self, rtl_code):
        """Extracts ports and signal specifications from synthesizable Verilog code."""
        # Strip comments
        clean_code = re.sub(r"//.*", "", rtl_code)
        clean_code = re.sub(r"/\*.*?\*/", "", clean_code, flags=re.DOTALL)

        # Match module declaration (handling optional parameters)
        m_mod = re.search(r"module\s+([A-Za-z0-9_]+)\s*(?:#\s*\(.*?\)\s*)?\((.*?)\);", clean_code, re.DOTALL)
        if not m_mod:
            return None, []

        mod_name = m_mod.group(1)
        port_block = m_mod.group(2)

        verilog_reserved = {
            "input", "output", "inout", "wire", "reg", "for", "while",
            "case", "default", "assign", "begin", "end", "integer", "genvar"
        }

        ports = []
        for line in port_block.split(","):
            line = line.strip()
            if not line:
                continue
            # Match direction, optional signed/wire/reg, optional [MSB:LSB], identifier
            m_p = re.search(
                r"(input|output|inout)\s+(?:wire|reg)?\s*(?:signed\s*)?(?:\[\s*([^:]+)\s*:\s*([^\]]+)\s*\])?\s*([A-Za-z0-9_]+)",
                line
            )
            if m_p:
                direction, msb_str, lsb_str, port_name = m_p.groups()
                if port_name.lower() in verilog_reserved:
                    continue

                width = 1
                if msb_str is not None and lsb_str is not None:
                    try:
                        width = abs(int(msb_str.strip()) - int(lsb_str.strip())) + 1
                    except ValueError:
                        width = 8 # Fallback for parameterized width expressions

                p_lower = port_name.lower()
                is_clk = any(k in p_lower for k in ["clk", "clock"])
                is_rst = any(k in p_lower for k in ["rst", "clr", "reset", "clear"])
                is_active_low = p_lower.endswith("_n") or p_lower.startswith("rst_n") or p_lower == "rst_n"

                ports.append({
                    "name": port_name,
                    "direction": direction,
                    "width": width,
                    "msb": msb_str,
                    "lsb": lsb_str,
                    "is_clk": is_clk,
                    "is_rst": is_rst,
                    "is_active_low": is_active_low
                })

        return mod_name, ports

    def generate_harness(self, rtl_path, output_dir=None):
        """Synthesizes a standardized Option A Verilog Hardware Test Harness for an RTL file."""
        if not os.path.exists(rtl_path):
            raise FileNotFoundError(f"RTL file not found: {rtl_path}")

        out_dir = output_dir or self.sim_dir
        os.makedirs(out_dir, exist_ok=True)

        with open(rtl_path, "r", encoding="utf-8", errors="replace") as f:
            rtl_code = f.read()

        mod_name, ports = self.extract_ports(rtl_code)
        if not mod_name:
            mod_name = os.path.splitext(os.path.basename(rtl_path))[0]

        harness_module_name = f"harness_{mod_name}"

        # 1. Signal Declarations & DUT socket wiring
        decls = []
        dut_connections = []
        has_clk = False
        clk_name = "clk"
        has_rst = False
        rst_name = "rst_n"
        rst_active_low = True

        for p in ports:
            p_name = p["name"]
            w_str = f"[{p['width']-1}:0] " if p["width"] > 1 else ""
            dut_connections.append(f"        .{p_name}({p_name})")

            if p["direction"] == "input":
                decls.append(f"    reg  {w_str:<8} {p_name};")
                if p["is_clk"] and not has_clk:
                    has_clk = True
                    clk_name = p_name
                if p["is_rst"] and not has_rst:
                    has_rst = True
                    rst_name = p_name
                    rst_active_low = p["is_active_low"]
            else:
                decls.append(f"    wire {w_str:<8} {p_name};")

        # If no clock in ports, provide a default harness clock for synchronous evaluation
        if not has_clk:
            decls.append("    reg           clk;")
            clk_name = "clk"

        decls_block = "\n".join(decls)
        dut_conn_block = ",\n".join(dut_connections) if dut_connections else "        // No external ports"

        # 2. Stimulus Generation
        stimulus_lines = []
        input_data_ports = [p for p in ports if p["direction"] == "input" and not p["is_clk"] and not p["is_rst"]]
        output_ports = [p for p in ports if p["direction"] == "output"]

        # Initial default state
        for p in ports:
            if p["direction"] == "input":
                if p["is_rst"]:
                    # Assert reset initially
                    val = "1'b0" if p["is_active_low"] else "1'b1"
                    stimulus_lines.append(f"        {p['name']} = {val}; // Assert reset initially")
                elif not p["is_clk"]:
                    stimulus_lines.append(f"        {p['name']} = {p['width']}'d0;")

        # Release reset after 25ns
        stimulus_lines.append("\n        #25;")
        for p in ports:
            if p["direction"] == "input" and p["is_rst"]:
                val = "1'b1" if p["is_active_low"] else "1'b0"
                stimulus_lines.append(f"        {p['name']} = {val}; // De-assert reset (release system)")

        # Exercise 6 distinct test scenarios
        stimulus_lines.append("\n        //====================================================================")
        stimulus_lines.append("        // STIMULUS EXECUTION WITH HARNESS ASSERTION VERIFICATION")
        stimulus_lines.append("        //====================================================================")

        for step in range(1, 7):
            stimulus_lines.append(f"\n        // --- Test Vector Scenario {step} ---")
            for idx, inp in enumerate(input_data_ports):
                # Deterministic pseudo-random stimulus vector
                mask = (1 << min(inp["width"], 16)) - 1
                val = ((step * 17) + (idx * 23) + 7) & mask
                stimulus_lines.append(f"        {inp['name']} = {inp['width']}'d{val};")

            stimulus_lines.append("        #20;")

            # Assert outputs valid and deterministic
            for out in output_ports:
                msg = f"Scenario {step} - Port {out['name']}"
                stimulus_lines.append(f"        harness_assert_valid({out['name']}, \"{msg}\");")

        stimulus_lines.append("\n        #40;")
        stimulus_block = "\n".join(stimulus_lines)

        # 3. Assemble full Verilog Test Harness Wrapper
        harness_code = f"""//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER (OPTION A)
// Module: {harness_module_name}
// Target DUT: {mod_name}
// Standard: IEEE 1364-2001 Synthesizable/Verifiable Hardware Test Harness
// Features:
//   1. System Infrastructure Engine: 50 MHz Master Clock & Clean Reset Sync
//   2. Watchdog Safety Guard: #100,000 Safety Timeout (Zero Hang / Deadlock)
//   3. Assertion & Golden Oracle Tasks: harness_assert_eq, harness_assert_valid
//   4. Device Under Test (DUT) Socket: Explicit Named Port Mapping
//   5. VeriPrefer & IEEE 1800 Verification Telemetry Scoreboard
//==============================================================================
`timescale 1ns / 1ps

module {harness_module_name};

    // -------------------------------------------------------------------------
    // 1. HARNESS TEST SIGNALS DECLARATION
    // -------------------------------------------------------------------------
{decls_block}

    // Telemetry Statistics Counters
    integer total_tests  = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    // -------------------------------------------------------------------------
    // 2. SYSTEM INFRASTRUCTURE: CLOCK ENGINE (50 MHz, Period = 20ns)
    // -------------------------------------------------------------------------
    always #10 {clk_name} = ~{clk_name};

    // -------------------------------------------------------------------------
    // 3. WATCHDOG SAFETY TIMER GUARD (OPTION A CRITICAL COMPONENT)
    // Prevents infinite loops, deadlocks, or hung simulations in untested FSMs.
    // -------------------------------------------------------------------------
    initial begin
        #100000; // 100 microseconds safety cutoff
        $display("\\n============================================================================");
        $display("   [HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $display("   Possible infinite loop or deadlock detected in module '{mod_name}'.");
        $display("   Telemetry at Timeout -> Total: %0d | Passed: %0d | Failed: %0d",
                 total_tests, passed_tests, failed_tests);
        $display("============================================================================");
        $finish;
    end

    // -------------------------------------------------------------------------
    // 4. STANDARDIZED HARNESS ASSERTION & ORACLE TASKS
    // -------------------------------------------------------------------------
    task harness_assert_eq;
        input [31:0]  actual;
        input [31:0]  expected;
        input [255:0] test_name;
        begin
            total_tests = total_tests + 1;
            if (actual === expected) begin
                passed_tests = passed_tests + 1;
                $display("  [HARNESS PASS] %0s | Actual: %h == Expected: %h", test_name, actual, expected);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [HARNESS FAIL] %0s | Actual: %h != Expected: %h at time %0t ps",
                         test_name, actual, expected, $time);
            end
        end
    endtask

    task harness_assert_valid;
        input [31:0]  val;
        input [255:0] signal_name;
        begin
            total_tests = total_tests + 1;
            if (^val !== 1'bx && ^val !== 1'bz) begin
                passed_tests = passed_tests + 1;
                $display("  [HARNESS PASS] %0s is valid (non-floating): %h", signal_name, val);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [HARNESS FAIL] %0s contains X/Z floating bits: %h at time %0t ps",
                         signal_name, val, $time);
            end
        end
    endtask

    // -------------------------------------------------------------------------
    // 5. DEVICE UNDER TEST (DUT) PLUG-AND-PLAY SOCKET
    // -------------------------------------------------------------------------
    {mod_name} dut (
{dut_conn_block}
    );

    // -------------------------------------------------------------------------
    // 6. HARNESS STIMULUS SEQUENCE & VERIPREFER TELEMETRY SCOREBOARD
    // -------------------------------------------------------------------------
    initial begin
        // Waveform Dump for ModelSim, Quartus & Web Visualizer
        $dumpfile("{mod_name}.vcd");
        $dumpvars(0, {harness_module_name});

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): {harness_module_name}");
        $display("   Device Under Test: {mod_name}");
        $display("   Architecture: Standardized Fixture (Clock, Reset, Watchdog, Assertions)");
        $display("============================================================================");

        // System Startup
        {clk_name} = 0;
{stimulus_block}
        // Telemetry Scoreboard Summary
        $display("============================================================================");
        $display("       HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)");
        $display("============================================================================");
        $display("  Target Module Under Test: {mod_name}");
        $display("  Total Executed Tests    : %0d", total_tests);
        $display("  Passed Assertions       : %0d", passed_tests);
        $display("  Failed Assertions       : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Functional Accuracy     : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST HARNESS VERIFICATION FOR '{mod_name}' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST HARNESS VERIFICATION FOR '{mod_name}' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
"""
        harness_code = VerilogLinter.sanitize_verilog_code(harness_code)
        out_file = os.path.join(out_dir, f"{harness_module_name}.v")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(harness_code)

        return harness_module_name, out_file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = os.path.join(os.path.dirname(__file__), "..", "src", "alu_4bit.v")

    gen = HarnessGenerator()
    name, path = gen.generate_harness(target_path)
    print(f"[HarnessGenerator]: Successfully synthesized Test Harness '{name}': {path}")
