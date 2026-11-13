//==============================================================================
// Testbench: tb_sequence_detector_1011
// Description: Autonomous Self-Checking Testbench for sequence_detector_1011
// Based on VeriPrefer Benchmark Standard & Non-Overlapping Verification Oracle
//==============================================================================
`timescale 1ns / 1ps

module tb_sequence_detector_1011;

    reg        clk;
    reg        rst;
    reg        din;
    wire       detected;
    wire [2:0] state_out;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;
    integer det_count = 0;

    sequence_detector_1011 dut (
        .clk(clk),
        .rst(rst),
        .din(din),
        .detected(detected),
        .state_out(state_out)
    );

    always #10 clk = ~clk;

    task send_bit;
        input b;
        begin
            @(posedge clk);
            din <= b;
            #1;
            if (detected) det_count = det_count + 1;
        end
    endtask

    initial begin
        $dumpfile("sequence_detector_1011.vcd");
        $dumpvars(0, tb_sequence_detector_1011);

        clk = 0;
        rst = 1;
        din = 0;

        #25;
        rst = 0;

        $display("============================================================================");
        $display("   AUTONOMOUS SEQUENCE DETECTOR VERIFICATION: sequence_detector_1011");
        $display("============================================================================");

        // Scenario 1: Send exact pattern 1 - 0 - 1 - 1
        $display("\n>>> [KICH BAN 1]: Truyen mau chuan 1 - 0 - 1 - 1...");
        send_bit(1);
        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        total_tests = total_tests + 1;
        if (detected === 1'b1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Phat hien thanh cong chuoi 1011!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Khong phat hien chuoi 1011: detected=%b", detected);
        end

        // Scenario 2: Test Non-Overlapping stream: 1 - 0 - 1 - 1 - 0 - 1 - 1
        $display("\n>>> [KICH BAN 2]: Kiem tra dac tinh Non-Overlapping voi stream 1011011...");
        rst = 1; #20; rst = 0; #20;
        det_count = 0;
        send_bit(1);
        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        if (detected) det_count = det_count + 1;

        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        if (detected) det_count = det_count + 1;

        total_tests = total_tests + 1;
        if (det_count === 1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Xac nhan Non-Overlapping chuan: dung 1 lan phat hien!");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Vi pham Non-Overlapping: phat hien %0d lan!", det_count);
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'sequence_detector_1011' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'sequence_detector_1011' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
