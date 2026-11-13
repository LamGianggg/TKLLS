//==============================================================================
// Testbench: tb_digital_lock_fsm
// Description: Autonomous Self-Checking Testbench for digital_lock_fsm (Digital Lock)
// Based on VeriPrefer Benchmark Standard & Security Lockout Oracle
//==============================================================================
`timescale 1ns / 1ps

module tb_digital_lock_fsm;

    reg        clk;
    reg        rst;
    reg  [3:0] key_code;
    reg        enter_btn;
    wire       unlocked;
    wire       alarm;
    wire [1:0] attempts_left;
    wire [2:0] state_out;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

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

    always #10 clk = ~clk;

    task press_key;
        input [3:0] k;
        begin
            @(posedge clk);
            key_code  <= k;
            enter_btn <= 1'b1;
            @(posedge clk);
            enter_btn <= 1'b0;
            #1;
        end
    endtask

    initial begin
        $dumpfile("digital_lock_fsm.vcd");
        $dumpvars(0, tb_digital_lock_fsm);

        clk       = 0;
        rst       = 1;
        key_code  = 0;
        enter_btn = 0;

        #25;
        rst = 0;

        $display("============================================================================");
        $display("   AUTONOMOUS SECURITY VERIFICATION FOR MODULE: digital_lock_fsm");
        $display("============================================================================");

        // Kich ban 1: Nhap dung mat khau 1 - 2 - 3 -> Mo khoa (unlocked=1)
        $display("\n>>> [KICH BAN 1]: Nhap dung mat khau 1 - 2 - 3...");
        press_key(4'd1);
        press_key(4'd2);
        press_key(4'd3);
        total_tests = total_tests + 1;
        if (unlocked === 1'b1 && alarm === 1'b0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Mo khoa thanh cong: unlocked=1, alarm=0");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Mo khoa that bai: unlocked=%b, alarm=%b", unlocked, alarm);
        end

        // Kich ban 2: Reset va thu sai 3 lan -> Khoa he thong (alarm=1)
        $display("\n>>> [KICH BAN 2]: Thu nhap sai de kiem tra co che bao mat lockout...");
        rst = 1; #20; rst = 0; #20;
        
        // Sai lan 1
        press_key(4'd9);
        total_tests = total_tests + 1;
        if (attempts_left === 2'd2 && alarm === 1'b0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Sai lan 1: attempts_left=2, alarm=0");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Sai lan 1 loi: attempts_left=%0d, alarm=%b", attempts_left, alarm);
        end

        // Sai lan 2
        press_key(4'd9);
        total_tests = total_tests + 1;
        if (attempts_left === 2'd1 && alarm === 1'b0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Sai lan 2: attempts_left=1, alarm=0");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Sai lan 2 loi: attempts_left=%0d, alarm=%b", attempts_left, alarm);
        end

        // Sai lan 3 -> Phai kich hoat alarm va attempts_left=0
        press_key(4'd9);
        total_tests = total_tests + 1;
        if (attempts_left === 2'd0 && alarm === 1'b1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Sai lan 3: attempts_left=0, alarm=1 (LOCKOUT ACTIVATED)");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Sai lan 3 loi: attempts_left=%0d, alarm=%b", attempts_left, alarm);
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'digital_lock_fsm' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'digital_lock_fsm' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
