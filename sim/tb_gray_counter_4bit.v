//==============================================================================
// Testbench: tb_gray_counter_4bit
// Description: Autonomous Property-Checking Testbench for gray_counter_4bit
// Based on VerilogEval Benchmark Standard & Single-Bit Invariant Property
//==============================================================================
`timescale 1ns / 1ps

module tb_gray_counter_4bit;

    reg        clk;
    reg        rst;
    reg        enable;
    reg        up_down;
    wire [3:0] gray_out;
    wire [3:0] count;
    wire       tc;

    reg  [3:0] prev_gray;
    reg  [3:0] diff;
    integer    bit_flips;
    integer    step;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    gray_counter_4bit dut (
        .clk(clk),
        .rst(rst),
        .enable(enable),
        .gray_out(gray_out),
        .up_down(up_down),
        .count(count),
        .tc(tc)
    );

    always #10 clk = ~clk;

    initial begin
        $dumpfile("gray_counter_4bit.vcd");
        $dumpvars(0, tb_gray_counter_4bit);

        clk     = 0;
        rst     = 1;
        enable  = 0;
        up_down = 1;

        #25;
        rst    = 0;
        enable = 1;

        $display("============================================================================");
        $display("   AUTONOMOUS PROPERTY VERIFICATION FOR MODULE: gray_counter_4bit");
        $display("============================================================================");

        @(posedge clk);
        #1;
        prev_gray = gray_out;

        for (step = 1; step < 16; step = step + 1) begin
            @(posedge clk);
            #1;
            total_tests = total_tests + 1;
            diff = gray_out ^ prev_gray;
            bit_flips = diff[0] + diff[1] + diff[2] + diff[3];
            if (bit_flips == 1) begin
                passed_tests = passed_tests + 1;
                $display("  [PASS] Step %2d: %b -> %b (Bit flips = 1)", step, prev_gray, gray_out);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [ERROR] Step %2d: %b -> %b (VIOLATION: Bit flips = %0d != 1)", step, prev_gray, gray_out, bit_flips);
            end
            prev_gray = gray_out;
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'gray_counter_4bit' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'gray_counter_4bit' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
