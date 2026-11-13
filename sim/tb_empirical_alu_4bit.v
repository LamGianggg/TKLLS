//==============================================================================
// Empirical Challenger Adversarial Testbench: alu_4bit
// Attempts to test alu_4bit according to the RTLLM benchmark specification
//==============================================================================
`timescale 1ns / 1ps

module tb_empirical_alu_4bit;
    reg clk;
    reg rst;
    reg [3:0] a;
    reg [3:0] b;
    reg [2:0] opcode;
    wire [3:0] alu_out;
    wire zero;
    wire carry;

    alu_4bit dut (
        .clk(clk),
        .rst(rst),
        .a(a),
        .b(b),
        .opcode(opcode),
        .alu_out(alu_out),
        .zero(zero),
        .carry(carry)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst = 1;
        #15;
        rst = 0;
        $finish;
    end
endmodule
