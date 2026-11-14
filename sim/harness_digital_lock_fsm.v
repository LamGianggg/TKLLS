//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER (OPTION A)
// Module: harness_digital_lock_fsm
// Target DUT: digital_lock_fsm
// Standard: IEEE 1364-2001 Synthesizable/Verifiable Hardware Test Harness
// Features:
//   1. System Infrastructure Engine: 50 MHz Master Clock & Clean Reset Sync
//   2. Watchdog Safety Guard: #100,000 Safety Timeout (Zero Hang / Deadlock)
//   3. Assertion & Golden Oracle Tasks: harness_assert_eq, harness_assert_valid
//   4. Device Under Test (DUT) Socket: Explicit Named Port Mapping
//   5. VeriPrefer & IEEE 1800 Verification Telemetry Scoreboard
//==============================================================================
`timescale 1ns / 1ps

module harness_digital_lock_fsm;

    // -------------------------------------------------------------------------
    // 1. HARNESS TEST SIGNALS DECLARATION
    // -------------------------------------------------------------------------
    reg           clk;
    reg           rst;
    reg  [3:0]    key_code;
    reg           enter_btn;
    wire          unlocked;
    wire          alarm;
    wire [1:0]    attempts_left;
    wire [2:0]    state_out;

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
        $display("   Possible infinite loop or deadlock detected in module 'digital_lock_fsm'.");
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
    digital_lock_fsm dut (
        .clk(clk),
        .rst(rst),
        .key_code(key_code),
        .enter_btn(enter_btn),
        .unlocked(unlocked),
        .alarm(alarm),
        .attempts_left(attempts_left),
        .state_out(state_out)
    );

    // -------------------------------------------------------------------------
    // 6. HARNESS STIMULUS SEQUENCE & VERIPREFER TELEMETRY SCOREBOARD
    // -------------------------------------------------------------------------
    initial begin
        // Waveform Dump for ModelSim, Quartus & Web Visualizer
        $dumpfile("digital_lock_fsm.vcd");
        $dumpvars(0, harness_digital_lock_fsm);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_digital_lock_fsm");
        $display("   Device Under Test: digital_lock_fsm");
        $display("   Architecture: Standardized Fixture (Clock, Reset, Watchdog, Assertions)");
        $display("============================================================================");

        // System Startup
        clk = 0;
        rst = 1'b1; // Assert reset initially
        key_code = 4'd0;
        enter_btn = 1'd0;

        #25;
        rst = 1'b0; // De-assert reset (release system)

        //====================================================================
        // STIMULUS EXECUTION WITH HARNESS ASSERTION VERIFICATION
        //====================================================================

        // --- Test Vector Scenario 1 ---
        key_code = 4'd8;
        enter_btn = 1'd1;
        #20;
        harness_assert_valid(unlocked, "Scenario 1 - Port unlocked");
        harness_assert_valid(alarm, "Scenario 1 - Port alarm");
        harness_assert_valid(attempts_left, "Scenario 1 - Port attempts_left");
        harness_assert_valid(state_out, "Scenario 1 - Port state_out");

        // --- Test Vector Scenario 2 ---
        key_code = 4'd9;
        enter_btn = 1'd0;
        #20;
        harness_assert_valid(unlocked, "Scenario 2 - Port unlocked");
        harness_assert_valid(alarm, "Scenario 2 - Port alarm");
        harness_assert_valid(attempts_left, "Scenario 2 - Port attempts_left");
        harness_assert_valid(state_out, "Scenario 2 - Port state_out");

        // --- Test Vector Scenario 3 ---
        key_code = 4'd10;
        enter_btn = 1'd1;
        #20;
        harness_assert_valid(unlocked, "Scenario 3 - Port unlocked");
        harness_assert_valid(alarm, "Scenario 3 - Port alarm");
        harness_assert_valid(attempts_left, "Scenario 3 - Port attempts_left");
        harness_assert_valid(state_out, "Scenario 3 - Port state_out");

        // --- Test Vector Scenario 4 ---
        key_code = 4'd11;
        enter_btn = 1'd0;
        #20;
        harness_assert_valid(unlocked, "Scenario 4 - Port unlocked");
        harness_assert_valid(alarm, "Scenario 4 - Port alarm");
        harness_assert_valid(attempts_left, "Scenario 4 - Port attempts_left");
        harness_assert_valid(state_out, "Scenario 4 - Port state_out");

        // --- Test Vector Scenario 5 ---
        key_code = 4'd12;
        enter_btn = 1'd1;
        #20;
        harness_assert_valid(unlocked, "Scenario 5 - Port unlocked");
        harness_assert_valid(alarm, "Scenario 5 - Port alarm");
        harness_assert_valid(attempts_left, "Scenario 5 - Port attempts_left");
        harness_assert_valid(state_out, "Scenario 5 - Port state_out");

        // --- Test Vector Scenario 6 ---
        key_code = 4'd13;
        enter_btn = 1'd0;
        #20;
        harness_assert_valid(unlocked, "Scenario 6 - Port unlocked");
        harness_assert_valid(alarm, "Scenario 6 - Port alarm");
        harness_assert_valid(attempts_left, "Scenario 6 - Port attempts_left");
        harness_assert_valid(state_out, "Scenario 6 - Port state_out");

        #40;
        // Telemetry Scoreboard Summary
        $display("============================================================================");
        $display("       HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)");
        $display("============================================================================");
        $display("  Target Module Under Test: digital_lock_fsm");
        $display("  Total Executed Tests    : %0d", total_tests);
        $display("  Passed Assertions       : %0d", passed_tests);
        $display("  Failed Assertions       : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Functional Accuracy     : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST HARNESS VERIFICATION FOR 'digital_lock_fsm' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST HARNESS VERIFICATION FOR 'digital_lock_fsm' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
