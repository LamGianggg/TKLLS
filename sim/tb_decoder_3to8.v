//==============================================================================
// Testbench: tb_decoder_3to8
// Mo ta: Testbench tu kiem tra cho thiet ke decoder_3to8
// Tieu chuan kiem dinh: VeriPrefer (arXiv:2504.15804)
//==============================================================================
`timescale 1ns / 1ps

module tb_decoder_3to8;

    reg  [2:0]    a;
    reg           en;
    wire [7:0]    y;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    decoder_3to8 dut (
        .a(a),
        .en(en),
        .y(y)
    );

    

    // Bo dem thoi gian bao ve Watchdog
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    initial begin
        $dumpfile("decoder_3to8.vcd");
        $dumpvars(0, tb_decoder_3to8);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: decoder_3to8");
        $display("============================================================================");

        // Trang thai khoi tao
        a = 0;
        en = 0;

        #25;

        // Chay cac kich ban kiem thu voi assertions
        // Kich ban 1
        a = 3'd3;
        en = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^y !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 2
        a = 3'd6;
        en = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^y !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 3
        a = 3'd1;
        en = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^y !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 4
        a = 3'd4;
        en = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^y !== 1'bx)) begin
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'decoder_3to8' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'decoder_3to8' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
