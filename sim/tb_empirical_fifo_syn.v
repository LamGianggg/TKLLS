//==============================================================================
// Empirical Challenger Adversarial Testbench: fifo_syn
// Stress-tests FIFO buffer under overflow, underflow, and full wrap-around
//==============================================================================
`timescale 1ns / 1ps

module tb_empirical_fifo_syn;
    reg clk;
    reg rst;
    reg wr_en;
    reg rd_en;
    reg [7:0] data_in;
    wire [7:0] data_out;
    wire full;
    wire empty;

    integer i;
    integer errors = 0;
    integer total = 0;

    fifo_syn dut (
        .clk(clk),
        .rst(rst),
        .wr_en(wr_en),
        .rd_en(rd_en),
        .data_in(data_in),
        .data_out(data_out),
        .full(full),
        .empty(empty)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst = 1;
        wr_en = 0;
        rd_en = 0;
        data_in = 0;
        #15;
        rst = 0;

        // 1. Initial State: Must be empty and not full
        total = total + 1;
        if (!empty || full) begin
            $display("[FAIL] Initial state wrong: empty=%b, full=%b", empty, full);
            errors = errors + 1;
        end

        // 2. Underflow Attempt: Read from empty FIFO
        @(posedge clk);
        rd_en <= 1;
        @(posedge clk);
        rd_en <= 0;
        #1;
        total = total + 1;
        if (!empty) begin
            $display("[FAIL] FIFO not empty after read underflow!");
            errors = errors + 1;
        end

        // 3. Fill FIFO completely (8 elements: 10, 20, 30, 40, 50, 60, 70, 80)
        for (i = 1; i <= 8; i = i + 1) begin
            @(posedge clk);
            wr_en <= 1;
            data_in <= i * 10;
        end
        @(posedge clk);
        wr_en <= 0;
        #1;
        total = total + 1;
        if (!full || empty) begin
            $display("[FAIL] FIFO should be FULL: full=%b, empty=%b", full, empty);
            errors = errors + 1;
        end

        // 4. Overflow Attempt: Write 99 when full
        @(posedge clk);
        wr_en <= 1;
        data_in <= 8'd99;
        @(posedge clk);
        wr_en <= 0;
        #1;
        total = total + 1;
        if (!full) begin
            $display("[FAIL] FIFO not full after overflow write!");
            errors = errors + 1;
        end

        // 5. Read back elements 1..8 and verify order (FIFO property)
        for (i = 1; i <= 8; i = i + 1) begin
            @(posedge clk);
            rd_en <= 1;
            @(posedge clk);
            rd_en <= 0;
            #1;
            total = total + 1;
            if (data_out !== (i * 10)) begin
                $display("[FAIL] Read mismatch: got %0d, expected %0d", data_out, i * 10);
                errors = errors + 1;
            end
        end

        // After reading all 8, must be empty
        #1;
        total = total + 1;
        if (!empty) begin
            $display("[FAIL] FIFO should be empty after reading all items!");
            errors = errors + 1;
        end

        $display("=================================================================");
        $display(" EMPIRICAL ORACLE VERIFICATION: fifo_syn");
        $display(" Total Checks: %0d | Errors: %0d", total, errors);
        if (errors == 0)
            $display(" [ORACLE_PASS] FIFO SYNCHRONOUS BUFFER ACCURACY CONFIRMED");
        else
            $display(" [ORACLE_FAIL] FIFO FAILED %0d CHECKS!", errors);
        $display("=================================================================");
        $finish;
    end
endmodule
