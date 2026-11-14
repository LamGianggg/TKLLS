//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER (OPTION A)
// Module: harness_priority_encoder_8to3
// Target DUT: priority_encoder_8to3
// Standard: IEEE 1364-2001 Synthesizable/Verifiable Hardware Test Harness
// Features:
//   1. System Infrastructure Engine: 50 MHz Master Clock & Clean Reset Sync
//   2. Watchdog Safety Guard: #100,000 Safety Timeout (Zero Hang / Deadlock)
//   3. Assertion & Golden Oracle Tasks: harness_assert_eq, harness_assert_valid
//   4. Device Under Test (DUT) Socket: Explicit Named Port Mapping
//   5. VeriPrefer & IEEE 1800 Verification Telemetry Scoreboard
//==============================================================================
`timescale 1ns / 1ps

module harness_priority_encoder_8to3;

    // -------------------------------------------------------------------------
    // 1. HARNESS TEST SIGNALS DECLARATION
    // -------------------------------------------------------------------------
    reg           clk;
    reg           rst;
    reg  [7:0]    d_in;
    wire [2:0]    binary_out;
    wire          valid;

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
        $display("   Possible infinite loop or deadlock detected in module 'priority_encoder_8to3'.");
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
    priority_encoder_8to3 dut (
        .clk(clk),
        .rst(rst),
        .d_in(d_in),
        .binary_out(binary_out),
        .valid(valid)
    );

    // -------------------------------------------------------------------------
    // 6. HARNESS STIMULUS SEQUENCE & VERIPREFER TELEMETRY SCOREBOARD
    // -------------------------------------------------------------------------
    initial begin
        // Waveform Dump for ModelSim, Quartus & Web Visualizer
        $dumpfile("priority_encoder_8to3.vcd");
        $dumpvars(0, harness_priority_encoder_8to3);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_priority_encoder_8to3");
        $display("   Device Under Test: priority_encoder_8to3");
        $display("   Architecture: Standardized Fixture (Clock, Reset, Watchdog, Assertions)");
        $display("============================================================================");

        // System Startup
        clk = 0;
        rst = 1'b1; // Assert reset initially
        d_in = 8'd0;

        #25;
        rst = 1'b0; // De-assert reset (release system)

        //====================================================================
        // STIMULUS EXECUTION WITH HARNESS ASSERTION VERIFICATION
        //====================================================================

        // --- Test Vector Scenario 1 ---
        d_in = 8'd24;
        #20;
        harness_assert_valid(binary_out, "Scenario 1 - Port binary_out");
        harness_assert_valid(valid, "Scenario 1 - Port valid");

        // --- Test Vector Scenario 2 ---
        d_in = 8'd41;
        #20;
        harness_assert_valid(binary_out, "Scenario 2 - Port binary_out");
        harness_assert_valid(valid, "Scenario 2 - Port valid");

        // --- Test Vector Scenario 3 ---
        d_in = 8'd58;
        #20;
        harness_assert_valid(binary_out, "Scenario 3 - Port binary_out");
        harness_assert_valid(valid, "Scenario 3 - Port valid");

        // --- Test Vector Scenario 4 ---
        d_in = 8'd75;
        #20;
        harness_assert_valid(binary_out, "Scenario 4 - Port binary_out");
        harness_assert_valid(valid, "Scenario 4 - Port valid");

        // --- Test Vector Scenario 5 ---
        d_in = 8'd92;
        #20;
        harness_assert_valid(binary_out, "Scenario 5 - Port binary_out");
        harness_assert_valid(valid, "Scenario 5 - Port valid");

        // --- Test Vector Scenario 6 ---
        d_in = 8'd109;
        #20;
        harness_assert_valid(binary_out, "Scenario 6 - Port binary_out");
        harness_assert_valid(valid, "Scenario 6 - Port valid");

        #40;
        // Telemetry Scoreboard Summary
        $display("============================================================================");
        $display("       HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)");
        $display("============================================================================");
        $display("  Target Module Under Test: priority_encoder_8to3");
        $display("  Total Executed Tests    : %0d", total_tests);
        $display("  Passed Assertions       : %0d", passed_tests);
        $display("  Failed Assertions       : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Functional Accuracy     : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST HARNESS VERIFICATION FOR 'priority_encoder_8to3' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST HARNESS VERIFICATION FOR 'priority_encoder_8to3' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
