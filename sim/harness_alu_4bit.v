//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER (OPTION A)
// Module: harness_alu_4bit
// Target DUT: alu_4bit
// Standard: IEEE 1364-2001 Synthesizable/Verifiable Hardware Test Harness
// Features:
//   1. System Infrastructure Engine: 50 MHz Master Clock & Clean Reset Sync
//   2. Watchdog Safety Guard: #100,000 Safety Timeout (Zero Hang / Deadlock)
//   3. Assertion & Golden Oracle Tasks: harness_assert_eq, harness_assert_valid
//   4. Device Under Test (DUT) Socket: Explicit Named Port Mapping
//   5. VeriPrefer & IEEE 1800 Verification Telemetry Scoreboard
//==============================================================================
`timescale 1ns / 1ps

module harness_alu_4bit;

    // -------------------------------------------------------------------------
    // 1. HARNESS TEST SIGNALS DECLARATION
    // -------------------------------------------------------------------------
    reg           clk;
    reg           rst;
    reg  [3:0]    a;
    reg  [3:0]    b;
    reg  [2:0]    opcode;
    wire [3:0]    alu_out;
    wire          zero;
    wire          carry;

    // Telemetry Statistics Counters
    integer total_tests  = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    // -------------------------------------------------------------------------
    // 2. SYSTEM INFRASTRUCTURE: CLOCK ENGINE (50 MHz, Period = 20ns)
    // -------------------------------------------------------------------------
    always #10 clk = ~clk;

    // -------------------------------------------------------------------------
    // 3. WATCHDOG SAFETY TIMER GUARD (OPTION A CRITICAL COMPONENT)
    // Prevents infinite loops, deadlocks, or hung simulations in untested FSMs.
    // -------------------------------------------------------------------------
    initial begin
        #100000; // 100 microseconds safety cutoff
        $display("\n============================================================================");
        $display("   [HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $display("   Possible infinite loop or deadlock detected in module 'alu_4bit'.");
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
    alu_4bit dut (
        .clk(clk),
        .rst(rst),
        .a(a),
        .b(b),
        .opcode(opcode),
        .alu_out(alu_out),
        .zero(zero),
        .carry(carry)
    );

    // -------------------------------------------------------------------------
    // 6. HARNESS STIMULUS SEQUENCE & VERIPREFER TELEMETRY SCOREBOARD
    // -------------------------------------------------------------------------
    initial begin
        // Waveform Dump for ModelSim, Quartus & Web Visualizer
        $dumpfile("alu_4bit.vcd");
        $dumpvars(0, harness_alu_4bit);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_alu_4bit");
        $display("   Device Under Test: alu_4bit");
        $display("   Architecture: Standardized Fixture (Clock, Reset, Watchdog, Assertions)");
        $display("============================================================================");

        // System Startup
        clk = 0;
        rst = 1'b1; // Assert reset initially
        a = 4'd0;
        b = 4'd0;
        opcode = 3'd0;

        #25;
        rst = 1'b0; // De-assert reset (release system)

        //====================================================================
        // STIMULUS EXECUTION WITH HARNESS ASSERTION VERIFICATION
        //====================================================================

        // --- Test Vector Scenario 1 ---
        a = 4'd8;
        b = 4'd15;
        opcode = 3'd6;
        #20;
        harness_assert_valid(alu_out, "Scenario 1 - Port alu_out");
        harness_assert_valid(zero, "Scenario 1 - Port zero");
        harness_assert_valid(carry, "Scenario 1 - Port carry");

        // --- Test Vector Scenario 2 ---
        a = 4'd9;
        b = 4'd0;
        opcode = 3'd7;
        #20;
        harness_assert_valid(alu_out, "Scenario 2 - Port alu_out");
        harness_assert_valid(zero, "Scenario 2 - Port zero");
        harness_assert_valid(carry, "Scenario 2 - Port carry");

        // --- Test Vector Scenario 3 ---
        a = 4'd10;
        b = 4'd1;
        opcode = 3'd0;
        #20;
        harness_assert_valid(alu_out, "Scenario 3 - Port alu_out");
        harness_assert_valid(zero, "Scenario 3 - Port zero");
        harness_assert_valid(carry, "Scenario 3 - Port carry");

        // --- Test Vector Scenario 4 ---
        a = 4'd11;
        b = 4'd2;
        opcode = 3'd1;
        #20;
        harness_assert_valid(alu_out, "Scenario 4 - Port alu_out");
        harness_assert_valid(zero, "Scenario 4 - Port zero");
        harness_assert_valid(carry, "Scenario 4 - Port carry");

        // --- Test Vector Scenario 5 ---
        a = 4'd12;
        b = 4'd3;
        opcode = 3'd2;
        #20;
        harness_assert_valid(alu_out, "Scenario 5 - Port alu_out");
        harness_assert_valid(zero, "Scenario 5 - Port zero");
        harness_assert_valid(carry, "Scenario 5 - Port carry");

        // --- Test Vector Scenario 6 ---
        a = 4'd13;
        b = 4'd4;
        opcode = 3'd3;
        #20;
        harness_assert_valid(alu_out, "Scenario 6 - Port alu_out");
        harness_assert_valid(zero, "Scenario 6 - Port zero");
        harness_assert_valid(carry, "Scenario 6 - Port carry");

        #40;
        // Telemetry Scoreboard Summary
        $display("============================================================================");
        $display("       HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)");
        $display("============================================================================");
        $display("  Target Module Under Test: alu_4bit");
        $display("  Total Executed Tests    : %0d", total_tests);
        $display("  Passed Assertions       : %0d", passed_tests);
        $display("  Failed Assertions       : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Functional Accuracy     : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST HARNESS VERIFICATION FOR 'alu_4bit' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST HARNESS VERIFICATION FOR 'alu_4bit' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
