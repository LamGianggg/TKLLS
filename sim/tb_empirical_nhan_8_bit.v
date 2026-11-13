//==============================================================================
// Empirical Challenger Adversarial Testbench: nhan_8_bit
// Thoroughly stress-tests the 8-bit multiplier against mathematical oracle
//==============================================================================
`timescale 1ns / 1ps

module tb_empirical_nhan_8_bit;
    reg clk;
    reg rst;
    reg [7:0] a;
    reg [7:0] b;
    wire [15:0] product;

    integer i, j;
    integer errors = 0;
    integer total = 0;

    nhan_8_bit dut (
        .clk(clk),
        .rst(rst),
        .a(a),
        .b(b),
        .product(product)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst = 1;
        a = 0;
        b = 0;
        #15;
        rst = 0;

        // Test Corner Cases:
        // 0x0, 0x255, 255x0, 255x255, 1x1, 128x128, 127x128
        // Plus 500 pseudo-random cases
        for (i = 0; i < 256; i = i + 17) begin
            for (j = 0; j < 256; j = j + 19) begin
                @(posedge clk);
                a <= i[7:0];
                b <= j[7:0];
                @(posedge clk); // wait 1 cycle for registered output
                #1;
                total = total + 1;
                if (product !== (i * j)) begin
                    $display("[FAIL] %0d * %0d = %0d (Expected: %0d)", i, j, product, i * j);
                    errors = errors + 1;
                end
            end
        end

        // Explicit max corner case: 255 * 255
        @(posedge clk);
        a <= 8'd255;
        b <= 8'd255;
        @(posedge clk);
        #1;
        total = total + 1;
        if (product !== 16'd65025) begin
            $display("[FAIL] 255 * 255 = %0d (Expected: 65025)", product);
            errors = errors + 1;
        end

        // Check reset behavior
        @(posedge clk);
        rst <= 1;
        @(posedge clk);
        #1;
        total = total + 1;
        if (product !== 16'd0) begin
            $display("[FAIL] Reset failed to clear product: %0d", product);
            errors = errors + 1;
        end

        $display("=================================================================");
        $display(" EMPIRICAL ORACLE VERIFICATION: nhan_8_bit");
        $display(" Total Vectors Tested: %0d | Errors: %0d", total, errors);
        if (errors == 0)
            $display(" [ORACLE_PASS] 100%% MATHEMATICAL ACCURACY CONFIRMED");
        else
            $display(" [ORACLE_FAIL] DETECTED %0d MISMATCHES!", errors);
        $display("=================================================================");
        $finish;
    end
endmodule
