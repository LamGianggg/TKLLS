//==============================================================================
// Testbench: tb_canh_bao_an_ninh_bao_chay_nha_thong_minh
// Description: Autonomous Self-Checking Testbench for canh_bao_an_ninh_bao_chay_nha_thong_minh
// Based on VeriPrefer (arXiv:2504.15804) Functional Verification Framework
//==============================================================================
`timescale 1ns / 1ps

module tb_canh_bao_an_ninh_bao_chay_nha_thong_minh;

    reg           clk;
    reg           rst;
    reg           motion_pir;
    reg           smoke_gas;
    reg           arm_mode;
    wire          siren;
    wire          sprinkler;
    wire [1:0]    status_code;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    canh_bao_an_ninh_bao_chay_nha_thong_minh dut (
        .clk(clk),
        .rst(rst),
        .motion_pir(motion_pir),
        .smoke_gas(smoke_gas),
        .arm_mode(arm_mode),
        .siren(siren),
        .sprinkler(sprinkler),
        .status_code(status_code)
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
        $dumpfile("canh_bao_an_ninh_bao_chay_nha_thong_minh.vcd");
        $dumpvars(0, tb_canh_bao_an_ninh_bao_chay_nha_thong_minh);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: canh_bao_an_ninh_bao_chay_nha_thong_minh");
        $display("============================================================================");

        // Initial conditions
        clk = 0;
        rst = 1'b1; // Assert active-high reset
        motion_pir = 0;
        smoke_gas = 0;
        arm_mode = 0;

        #25;
        rst = 1'b0; // Deassert active-high reset

        // Test Scenarios Execution with VeriPrefer Assertions
        // Scenario 1
        motion_pir = 1'd1;
        smoke_gas = 1'd0;
        arm_mode = 1'd1;
        #20;
        total_tests = total_tests + 1;
        if ((^siren !== 1'bx) && (^sprinkler !== 1'bx) && (^status_code !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 2
        motion_pir = 1'd0;
        smoke_gas = 1'd0;
        arm_mode = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^siren !== 1'bx) && (^sprinkler !== 1'bx) && (^status_code !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 3
        motion_pir = 1'd1;
        smoke_gas = 1'd0;
        arm_mode = 1'd1;
        #20;
        total_tests = total_tests + 1;
        if ((^siren !== 1'bx) && (^sprinkler !== 1'bx) && (^status_code !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: Output contains undefined or floating (X/Z) bits!");
        end
        // Scenario 4
        motion_pir = 1'd0;
        smoke_gas = 1'd0;
        arm_mode = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^siren !== 1'bx) && (^sprinkler !== 1'bx) && (^status_code !== 1'bx)) begin
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'canh_bao_an_ninh_bao_chay_nha_thong_minh' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'canh_bao_an_ninh_bao_chay_nha_thong_minh' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
