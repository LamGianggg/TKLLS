//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER (OPTION A)
// Module: harness_fsm_controller
// Target DUT: fsm_controller
// Standard: IEEE 1364-2001 Synthesizable/Verifiable Hardware Test Harness
// Features:
//   1. System Infrastructure Engine: 50 MHz Master Clock & Clean Reset Sync
//   2. Watchdog Safety Guard: #100,000 Safety Timeout (Zero Hang / Deadlock)
//   3. Assertion & Golden Oracle Tasks: harness_assert_eq, harness_assert_valid
//   4. Device Under Test (DUT) Socket: Explicit Named Port Mapping
//   5. VeriPrefer & IEEE 1800 Verification Telemetry Scoreboard
//==============================================================================
`timescale 1ns / 1ps

module harness_fsm_controller;

    // -------------------------------------------------------------------------
    // 1. HARNESS TEST SIGNALS DECLARATION
    // -------------------------------------------------------------------------
    reg           clk;
    reg           rst;
    reg           start_btn;
    reg           water_full;
    reg           lid_closed;
    wire [1:0]    state;
    wire          water_valve;
    wire          motor_run;
    wire          warning;

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
        $display("   Possible infinite loop or deadlock detected in module 'fsm_controller'.");
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
    fsm_controller dut (
        .clk(clk),
        .rst(rst),
        .start_btn(start_btn),
        .water_full(water_full),
        .lid_closed(lid_closed),
        .state(state),
        .water_valve(water_valve),
        .motor_run(motor_run),
        .warning(warning)
    );

    // -------------------------------------------------------------------------
    // 6. HARNESS STIMULUS SEQUENCE & VERIPREFER TELEMETRY SCOREBOARD
    // -------------------------------------------------------------------------
    initial begin
        // Waveform Dump for ModelSim, Quartus & Web Visualizer
        $dumpfile("fsm_controller.vcd");
        $dumpvars(0, harness_fsm_controller);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_fsm_controller");
        $display("   Device Under Test: fsm_controller");
        $display("   Architecture: Standardized Fixture (Clock, Reset, Watchdog, Assertions)");
        $display("============================================================================");

        // System Startup
        clk = 0;
        rst = 1'b1; // Assert reset initially
        start_btn = 1'd0;
        water_full = 1'd0;
        lid_closed = 1'd0;

        #25;
        rst = 1'b0; // De-assert reset (release system)

        //====================================================================
        // STIMULUS EXECUTION WITH HARNESS ASSERTION VERIFICATION
        //====================================================================

        // --- Test Vector Scenario 1 ---
        start_btn = 1'd0;
        water_full = 1'd1;
        lid_closed = 1'd0;
        #20;
        harness_assert_valid(state, "Scenario 1 - Port state");
        harness_assert_valid(water_valve, "Scenario 1 - Port water_valve");
        harness_assert_valid(motor_run, "Scenario 1 - Port motor_run");
        harness_assert_valid(warning, "Scenario 1 - Port warning");

        // --- Test Vector Scenario 2 ---
        start_btn = 1'd1;
        water_full = 1'd0;
        lid_closed = 1'd1;
        #20;
        harness_assert_valid(state, "Scenario 2 - Port state");
        harness_assert_valid(water_valve, "Scenario 2 - Port water_valve");
        harness_assert_valid(motor_run, "Scenario 2 - Port motor_run");
        harness_assert_valid(warning, "Scenario 2 - Port warning");

        // --- Test Vector Scenario 3 ---
        start_btn = 1'd0;
        water_full = 1'd1;
        lid_closed = 1'd0;
        #20;
        harness_assert_valid(state, "Scenario 3 - Port state");
        harness_assert_valid(water_valve, "Scenario 3 - Port water_valve");
        harness_assert_valid(motor_run, "Scenario 3 - Port motor_run");
        harness_assert_valid(warning, "Scenario 3 - Port warning");

        // --- Test Vector Scenario 4 ---
        start_btn = 1'd1;
        water_full = 1'd0;
        lid_closed = 1'd1;
        #20;
        harness_assert_valid(state, "Scenario 4 - Port state");
        harness_assert_valid(water_valve, "Scenario 4 - Port water_valve");
        harness_assert_valid(motor_run, "Scenario 4 - Port motor_run");
        harness_assert_valid(warning, "Scenario 4 - Port warning");

        // --- Test Vector Scenario 5 ---
        start_btn = 1'd0;
        water_full = 1'd1;
        lid_closed = 1'd0;
        #20;
        harness_assert_valid(state, "Scenario 5 - Port state");
        harness_assert_valid(water_valve, "Scenario 5 - Port water_valve");
        harness_assert_valid(motor_run, "Scenario 5 - Port motor_run");
        harness_assert_valid(warning, "Scenario 5 - Port warning");

        // --- Test Vector Scenario 6 ---
        start_btn = 1'd1;
        water_full = 1'd0;
        lid_closed = 1'd1;
        #20;
        harness_assert_valid(state, "Scenario 6 - Port state");
        harness_assert_valid(water_valve, "Scenario 6 - Port water_valve");
        harness_assert_valid(motor_run, "Scenario 6 - Port motor_run");
        harness_assert_valid(warning, "Scenario 6 - Port warning");

        #40;
        // Telemetry Scoreboard Summary
        $display("============================================================================");
        $display("       HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)");
        $display("============================================================================");
        $display("  Target Module Under Test: fsm_controller");
        $display("  Total Executed Tests    : %0d", total_tests);
        $display("  Passed Assertions       : %0d", passed_tests);
        $display("  Failed Assertions       : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Functional Accuracy     : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST HARNESS VERIFICATION FOR 'fsm_controller' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST HARNESS VERIFICATION FOR 'fsm_controller' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
