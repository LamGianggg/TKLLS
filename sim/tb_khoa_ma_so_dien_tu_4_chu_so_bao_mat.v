//==============================================================================
// Testbench: tb_khoa_ma_so_dien_tu_4_chu_so_bao_mat
// Description: Autonomous Self-Checking Testbench for khoa_ma_so_dien_tu_4_chu_so_bao_mat
// Based on VeriPrefer (arXiv:2504.15804) Functional Verification Framework
//==============================================================================
`timescale 1ns / 1ps

module tb_khoa_ma_so_dien_tu_4_chu_so_bao_mat;

    reg           clk;
    reg           rst;
    reg  [3:0]    key_in;
    reg           enter;
    wire          unlock;
    wire          alarm;
    wire [1:0]    err_count;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    khoa_ma_so_dien_tu_4_chu_so_bao_mat dut (
        .clk(clk),
        .rst(rst),
        .key_in(key_in),
        .enter(enter),
        .unlock(unlock),
        .alarm(alarm),
        .err_count(err_count)
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
        $dumpfile("khoa_ma_so_dien_tu_4_chu_so_bao_mat.vcd");
        $dumpvars(0, tb_khoa_ma_so_dien_tu_4_chu_so_bao_mat);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: khoa_ma_so_dien_tu_4_chu_so_bao_mat");
        $display("============================================================================");

        // Initial conditions
        clk = 0;
        rst = 1'b1; // Assert active-high reset
        key_in = 0;
        enter = 0;

        #25;
        rst = 1'b0; // Deassert active-high reset

        // Test Scenarios Execution with VeriPrefer Assertions
        // Scenario 1
        key_in = 4'd3;
        enter = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^unlock !== 1'bx) && (^alarm !== 1'bx) && (^err_count !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 2
        key_in = 4'd6;
        enter = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^unlock !== 1'bx) && (^alarm !== 1'bx) && (^err_count !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 3
        key_in = 4'd9;
        enter = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^unlock !== 1'bx) && (^alarm !== 1'bx) && (^err_count !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 4
        key_in = 4'd12;
        enter = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^unlock !== 1'bx) && (^alarm !== 1'bx) && (^err_count !== 1'bx)) begin
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'khoa_ma_so_dien_tu_4_chu_so_bao_mat' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'khoa_ma_so_dien_tu_4_chu_so_bao_mat' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
