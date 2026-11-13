//==============================================================================
// Empirical Challenger Adversarial Testbench: digital_lock_fsm
// Demonstrates Security Vulnerability: Infinite Guess Attack on First 2 Digits
//==============================================================================
`timescale 1ns / 1ps

module tb_empirical_digital_lock;
    reg clk;
    reg rst;
    reg [3:0] key_code;
    reg enter_btn;
    wire unlocked;
    wire alarm;
    wire [1:0] attempts_left;
    wire [2:0] state_out;

    integer i;

    digital_lock_fsm dut (
        .clk(clk),
        .rst(rst),
        .key_code(key_code),
        .enter_btn(enter_btn),
        .unlocked(unlocked),
        .alarm(alarm),
        .attempts_left(attempts_left),
        .state_out(state_out)
    );

    always #5 clk = ~clk;

    task press_key(input [3:0] key);
    begin
        @(posedge clk);
        key_code <= key;
        enter_btn <= 1;
        @(posedge clk);
        enter_btn <= 0;
        #1;
    end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        key_code = 0;
        enter_btn = 0;
        #15;
        rst = 0;

        $display("=================================================================");
        $display(" EMPIRICAL ADVERSARIAL ATTACK: digital_lock_fsm");
        $display(" Initial attempts_left = %0d, alarm = %b", attempts_left, alarm);

        // Attacker attempts 10 wrong digits at S_INIT:
        for (i = 0; i < 10; i = i + 1) begin
            press_key(4'd9); // 9 is wrong (correct is 1)
        end

        $display(" After 10 WRONG guesses at digit 1: attempts_left = %0d, alarm = %b", attempts_left, alarm);
        if (attempts_left == 2'd3 && alarm == 1'b0) begin
            $display(" [VULNERABILITY CONFIRMED] Infinite Brute-Force allowed on Digit 1 without penalty!");
        end

        // Now enter correct digit 1 (PASS_1 = 1)
        press_key(4'd1);
        $display(" Entered digit 1=1 -> State is now S_DIGIT1 (%0d)", state_out);

        // Attacker attempts 10 wrong digits at S_DIGIT1:
        for (i = 0; i < 10; i = i + 1) begin
            press_key(4'd9); // 9 is wrong (correct is 2)
            // It goes back to S_INIT, let's re-enter 1 then 9
            press_key(4'd1);
        end

        $display(" After 10 WRONG guesses at digit 2: attempts_left = %0d, alarm = %b", attempts_left, alarm);
        if (attempts_left == 2'd3 && alarm == 1'b0) begin
            $display(" [VULNERABILITY CONFIRMED] Infinite Brute-Force allowed on Digit 2 without penalty!");
        end

        $display("=================================================================");
        $finish;
    end
endmodule
