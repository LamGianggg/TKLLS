//==============================================================================
// Empirical Challenger Adversarial Testbench: sequence_detector_1011
// Tests whether the detector is truly Non-overlapping as specified
//==============================================================================
`timescale 1ns / 1ps

module tb_empirical_seq_det;
    reg clk;
    reg rst;
    reg din;
    wire detected;
    wire [2:0] state_out;

    integer det_count = 0;

    sequence_detector_1011 dut (
        .clk(clk),
        .rst(rst),
        .din(din),
        .detected(detected),
        .state_out(state_out)
    );

    always #5 clk = ~clk;

    task send_bit(input b);
    begin
        @(posedge clk);
        din <= b;
        #1;
        if (detected) det_count = det_count + 1;
    end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        din = 0;
        #15;
        rst = 0;

        $display("=================================================================");
        $display(" EMPIRICAL ADVERSARIAL TEST: sequence_detector_1011");

        // Stream: 1 - 0 - 1 - 1 - 0 - 1 - 1
        // Bits:   1   2   3   4   5   6   7
        // At bit 4: '1011' completed -> detected=1 (1st detection)
        // Bit 5 is '0', Bit 6 is '1', Bit 7 is '1'.
        // In NON-OVERLAPPING: Bit 4 was consumed. Sequence starting at bit 5 is '0-1-1' -> NOT 1011!
        // So detection count should be EXACTLY 1!
        // In OVERLAPPING: Reusing bit 4 as start of new pattern? No, bit 4 is '1'. So bits 4,5,6,7 form '1-0-1-1' -> 2 detections!
        send_bit(1);
        send_bit(0);
        send_bit(1);
        send_bit(1);
        // Wait 1 cycle for Moore state S_1011 to be reached and sampled
        @(posedge clk);
        #1;
        if (detected) begin
            det_count = det_count + 1;
            $display(" Match 1 detected at time %0t (state=%0d)", $time, state_out);
        end

        send_bit(0);
        send_bit(1);
        send_bit(1);
        @(posedge clk);
        #1;
        if (detected) begin
            det_count = det_count + 1;
            $display(" Match 2 detected at time %0t (state=%0d)", $time, state_out);
        end

        $display(" Total Detections for stream 1-0-1-1-0-1-1: %0d", det_count);
        if (det_count > 1) begin
            $display(" [FAIL] Overlapping reuse detected! Spec requires NON-OVERLAPPING.");
        end else begin
            $display(" [PASS] Truly Non-overlapping.");
        end
        $display("=================================================================");
        $finish;
    end
endmodule
