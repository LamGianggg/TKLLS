//==============================================================================
// Empirical Challenger Adversarial Testbench: gray_counter_4bit
// Verifies Gray Code Property: Exactly 1 bit flip between consecutive cycles
//==============================================================================
`timescale 1ns / 1ps

module tb_empirical_gray_counter;
    reg clk;
    reg rst;
    reg enable;
    reg up_down;
    wire [3:0] count;
    wire tc;

    reg [3:0] prev_count;
    reg [3:0] diff;
    integer bit_flips;
    integer step;
    integer gray_violations = 0;

    gray_counter_4bit dut (
        .clk(clk),
        .rst(rst),
        .enable(enable),
        .up_down(up_down),
        .count(count),
        .tc(tc)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst = 1;
        enable = 0;
        up_down = 1;
        #15;
        rst = 0;
        enable = 1;

        $display("=================================================================");
        $display(" EMPIRICAL ADVERSARIAL TEST: gray_counter_4bit (Gray Code Property)");

        @(posedge clk);
        #1;
        prev_count = count;

        for (step = 1; step < 16; step = step + 1) begin
            @(posedge clk);
            #1;
            diff = count ^ prev_count;
            bit_flips = diff[0] + diff[1] + diff[2] + diff[3];
            $display(" Cycle %2d: %b -> %b (Bit flips = %0d)", step, prev_count, count, bit_flips);
            if (bit_flips != 1) begin
                $display("   [VIOLATION]: Gray code requires EXACTLY 1 bit flip! Found %0d bit flips.", bit_flips);
                gray_violations = gray_violations + 1;
            end
            prev_count = count;
        end

        $display("-----------------------------------------------------------------");
        $display(" Total Steps: 15 | Gray Code Violations: %0d", gray_violations);
        if (gray_violations > 0)
            $display(" [FAIL] Module is NOT a Gray code counter (violates single-bit change property)!");
        else
            $display(" [PASS] Valid Gray code counter.");
        $display("=================================================================");
        $finish;
    end
endmodule
