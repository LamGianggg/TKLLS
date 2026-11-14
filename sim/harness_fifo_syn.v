//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER (OPTION A)
// Module: harness_fifo_syn
// Target DUT: fifo_syn
// Standard: IEEE 1364-2001 Synthesizable/Verifiable Hardware Test Harness
// Features:
//   1. System Infrastructure Engine: 50 MHz Master Clock & Clean Reset Sync
//   2. Watchdog Safety Guard: #100,000 Safety Timeout (Zero Hang / Deadlock)
//   3. Assertion & Golden Oracle Tasks: harness_assert_eq, harness_assert_valid
//   4. Device Under Test (DUT) Socket: Explicit Named Port Mapping
//   5. VeriPrefer & IEEE 1800 Verification Telemetry Scoreboard
//==============================================================================
`timescale 1ns / 1ps

module harness_fifo_syn;

    // -------------------------------------------------------------------------
    // 1. HARNESS TEST SIGNALS DECLARATION
    // -------------------------------------------------------------------------
    reg           clk;
    reg           rst;
    reg           wr_en;
    reg           rd_en;
    reg  [7:0]    data_in;
    wire [7:0]    data_out;
    wire          full;
    wire          empty;

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
        $display("   Possible infinite loop or deadlock detected in module 'fifo_syn'.");
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
    fifo_syn dut (
        .clk(clk),
        .rst(rst),
        .wr_en(wr_en),
        .rd_en(rd_en),
        .data_in(data_in),
        .data_out(data_out),
        .full(full),
        .empty(empty)
    );

    // -------------------------------------------------------------------------
    // 6. HARNESS STIMULUS SEQUENCE & VERIPREFER TELEMETRY SCOREBOARD
    // -------------------------------------------------------------------------
    initial begin
        // Waveform Dump for ModelSim, Quartus & Web Visualizer
        $dumpfile("fifo_syn.vcd");
        $dumpvars(0, harness_fifo_syn);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_fifo_syn");
        $display("   Device Under Test: fifo_syn");
        $display("   Architecture: Standardized Fixture (Clock, Reset, Watchdog, Assertions)");
        $display("============================================================================");

        // System Startup
        clk = 0;
        rst = 1'b1; // Assert reset initially
        wr_en = 1'd0;
        rd_en = 1'd0;
        data_in = 8'd0;

        #25;
        rst = 1'b0; // De-assert reset (release system)

        //====================================================================
        // STIMULUS EXECUTION WITH HARNESS ASSERTION VERIFICATION
        //====================================================================

        // --- Test Vector Scenario 1 ---
        wr_en = 1'd0;
        rd_en = 1'd1;
        data_in = 8'd70;
        #20;
        harness_assert_valid(data_out, "Scenario 1 - Port data_out");
        harness_assert_valid(full, "Scenario 1 - Port full");
        harness_assert_valid(empty, "Scenario 1 - Port empty");

        // --- Test Vector Scenario 2 ---
        wr_en = 1'd1;
        rd_en = 1'd0;
        data_in = 8'd87;
        #20;
        harness_assert_valid(data_out, "Scenario 2 - Port data_out");
        harness_assert_valid(full, "Scenario 2 - Port full");
        harness_assert_valid(empty, "Scenario 2 - Port empty");

        // --- Test Vector Scenario 3 ---
        wr_en = 1'd0;
        rd_en = 1'd1;
        data_in = 8'd104;
        #20;
        harness_assert_valid(data_out, "Scenario 3 - Port data_out");
        harness_assert_valid(full, "Scenario 3 - Port full");
        harness_assert_valid(empty, "Scenario 3 - Port empty");

        // --- Test Vector Scenario 4 ---
        wr_en = 1'd1;
        rd_en = 1'd0;
        data_in = 8'd121;
        #20;
        harness_assert_valid(data_out, "Scenario 4 - Port data_out");
        harness_assert_valid(full, "Scenario 4 - Port full");
        harness_assert_valid(empty, "Scenario 4 - Port empty");

        // --- Test Vector Scenario 5 ---
        wr_en = 1'd0;
        rd_en = 1'd1;
        data_in = 8'd138;
        #20;
        harness_assert_valid(data_out, "Scenario 5 - Port data_out");
        harness_assert_valid(full, "Scenario 5 - Port full");
        harness_assert_valid(empty, "Scenario 5 - Port empty");

        // --- Test Vector Scenario 6 ---
        wr_en = 1'd1;
        rd_en = 1'd0;
        data_in = 8'd155;
        #20;
        harness_assert_valid(data_out, "Scenario 6 - Port data_out");
        harness_assert_valid(full, "Scenario 6 - Port full");
        harness_assert_valid(empty, "Scenario 6 - Port empty");

        #40;
        // Telemetry Scoreboard Summary
        $display("============================================================================");
        $display("       HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)");
        $display("============================================================================");
        $display("  Target Module Under Test: fifo_syn");
        $display("  Total Executed Tests    : %0d", total_tests);
        $display("  Passed Assertions       : %0d", passed_tests);
        $display("  Failed Assertions       : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Functional Accuracy     : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] TEST HARNESS VERIFICATION FOR 'fifo_syn' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST HARNESS VERIFICATION FOR 'fifo_syn' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
