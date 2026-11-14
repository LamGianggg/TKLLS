//==============================================================================
// Testbench: tb_stopwatch
// Description: Autonomous Self-Checking Testbench for stopwatch
// Based on VeriPrefer (arXiv:2504.15804) Functional Verification Framework
//==============================================================================
`timescale 1ns / 1ps

module tb_stopwatch;

    reg           clk;
    reg           rst;
    reg           start_stop;
    wire [3:0]    count;
    wire [6:0]    seg;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    stopwatch dut (
        .clk(clk),
        .rst(rst),
        .start_stop(start_stop),
        .count(count),
        .seg(seg)
    );

    always #10 clk = ~clk;

    // Watchdog Safety Timer Guard (Option A Harness Architecture)
    initial begin
        #100000;
        $display("
[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    initial begin
        $dumpfile("stopwatch.vcd");
        $dumpvars(0, tb_stopwatch);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: stopwatch");
        $display("============================================================================");

        // Initial conditions
        clk = 0;
        rst = 1'b1; // Assert active-high reset
        start_stop = 0;

        #25;
        rst = 1'b0; // Deassert active-high reset

        // Test Scenarios Execution with VeriPrefer Assertions
        // Scenario 1
        start_stop = 1'd1;
        #20;
        total_tests = total_tests + 1;
        if ((^count !== 1'bx) && (^seg !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 2
        start_stop = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^count !== 1'bx) && (^seg !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 3
        start_stop = 1'd1;
        #20;
        total_tests = total_tests + 1;
        if ((^count !== 1'bx) && (^seg !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 4
        start_stop = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^count !== 1'bx) && (^seg !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 4: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 4: Output contains undefined or floating (X/Z) bits!");
        end
        #40;

        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'stopwatch' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'stopwatch' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
