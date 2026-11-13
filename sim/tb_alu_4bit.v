//==============================================================================
// Testbench: tb_alu_4bit
// Description: Autonomous Self-Checking Testbench for alu_4bit (ALU)
// Based on VeriPrefer (arXiv:2504.15804) & RTLLM Benchmark Standard
//==============================================================================
`timescale 1ns / 1ps

module tb_alu_4bit;

    reg        clk;
    reg        rst;
    reg  [3:0] a;
    reg  [3:0] b;
    reg  [2:0] opcode;
    wire [3:0] alu_out;
    wire       zero;
    wire       carry;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

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

    always #10 clk = ~clk;

    task check_alu;
        input [3:0] in_a;
        input [3:0] in_b;
        input [2:0] op;
        input [3:0] exp_out;
        input       exp_zero;
        input       exp_carry;
        begin
            @(posedge clk);
            a      <= in_a;
            b      <= in_b;
            opcode <= op;
            @(posedge clk);
            #1;
            total_tests = total_tests + 1;
            if (alu_out === exp_out && zero === exp_zero && carry === exp_carry) begin
                passed_tests = passed_tests + 1;
                $display("  [PASS] Op %3b (a=%0d, b=%0d) => out=%0d, zero=%b, carry=%b",
                         op, in_a, in_b, alu_out, zero, carry);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [ERROR] Op %3b (a=%0d, b=%0d) => EXPECT out=%0d z=%b c=%b, GOT out=%0d z=%b c=%b",
                         op, in_a, in_b, exp_out, exp_zero, exp_carry, alu_out, zero, carry);
            end
        end
    endtask

    initial begin
        $dumpfile("alu_4bit.vcd");
        $dumpvars(0, tb_alu_4bit);

        clk = 0;
        rst = 1;
        a   = 0;
        b   = 0;
        opcode = 0;

        #25;
        rst = 0;

        $display("============================================================================");
        $display("   AUTONOMOUS ORACLE VERIFICATION FOR MODULE: alu_4bit");
        $display("============================================================================");

        // Opcode 000: ADD
        check_alu(4'd5,  4'd3,  3'b000, 4'd8,  1'b0, 1'b0);
        check_alu(4'd12, 4'd6,  3'b000, 4'd2,  1'b0, 1'b1);
        check_alu(4'd0,  4'd0,  3'b000, 4'd0,  1'b1, 1'b0);

        // Opcode 001: SUB
        check_alu(4'd9,  4'd4,  3'b001, 4'd5,  1'b0, 1'b0);
        check_alu(4'd7,  4'd7,  3'b001, 4'd0,  1'b1, 1'b0);
        check_alu(4'd3,  4'd5,  3'b001, 4'd14, 1'b0, 1'b1);

        // Opcode 010: AND
        check_alu(4'b1100, 4'b1010, 3'b010, 4'b1000, 1'b0, 1'b0);

        // Opcode 011: OR
        check_alu(4'b1100, 4'b1010, 3'b011, 4'b1110, 1'b0, 1'b0);

        // Opcode 100: XOR
        check_alu(4'b1100, 4'b1010, 3'b100, 4'b0110, 1'b0, 1'b0);

        // Opcode 101: NOT
        check_alu(4'b1010, 4'b0000, 3'b101, 4'b0101, 1'b0, 1'b0);

        // Opcode 110: SHL
        check_alu(4'b0101, 4'b0000, 3'b110, 4'b1010, 1'b0, 1'b0);
        check_alu(4'b1001, 4'b0000, 3'b110, 4'b0010, 1'b0, 1'b1);

        // Opcode 111: COMP
        check_alu(4'd7, 4'd7, 3'b111, 4'd1, 1'b0, 1'b0);
        check_alu(4'd3, 4'd8, 3'b111, 4'd0, 1'b1, 1'b1);

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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'alu_4bit' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'alu_4bit' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
