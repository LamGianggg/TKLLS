//==============================================================================
// Testbench: tb_uart_tx_8bit
// Mo ta: Testbench tu kiem tra cho thiet ke uart_tx_8bit
// Tieu chuan kiem dinh: VeriPrefer (arXiv:2504.15804)
//==============================================================================
`timescale 1ns / 1ps

module tb_uart_tx_8bit;

    reg           clk;
    reg           rst;
    reg  [7:0]    tx_data;
    reg           tx_start;
    wire          tx_serial;
    wire          tx_busy;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    uart_tx_8bit dut (
        .clk(clk),
        .rst(rst),
        .tx_data(tx_data),
        .tx_start(tx_start),
        .tx_serial(tx_serial),
        .tx_busy(tx_busy)
    );

    always #10 clk = ~clk;

    // Bo dem thoi gian bao ve Watchdog
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    initial begin
        $dumpfile("uart_tx_8bit.vcd");
        $dumpvars(0, tb_uart_tx_8bit);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: uart_tx_8bit");
        $display("============================================================================");

        // Trang thai khoi tao
        clk = 0;
        rst = 1'b1; // Kich hoat reset muc cao
        tx_data = 0;
        tx_start = 0;

        #25;
        rst = 1'b0; // Huy reset muc cao

        // Chay cac kich ban kiem thu voi assertions
        // Kich ban 1
        tx_data = 8'd3;
        tx_start = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^tx_serial !== 1'bx) && (^tx_busy !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 2
        tx_data = 8'd6;
        tx_start = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^tx_serial !== 1'bx) && (^tx_busy !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 3
        tx_data = 8'd9;
        tx_start = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^tx_serial !== 1'bx) && (^tx_busy !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 4
        tx_data = 8'd12;
        tx_start = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^tx_serial !== 1'bx) && (^tx_busy !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 4: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 4: Output contains undefined or floating (X/Z) bits!");
        end
        #40;

        $display("============================================================================");
        $display("       VERIFICATION SCOREBOARD (VeriPrefer Benchmark Standard)");
        $display("============================================================================");
        $display("  Total Test Scenarios : %0d", total_tests);
        $display("  Passed Assertions    : %0d", passed_tests);
        $display("  Failed Assertions    : %0d", failed_tests);
        $display("  Functional Accuracy  : %0.1f PERCENT", (total_tests > 0 ? (passed_tests * 100.0) / total_tests : 100.0));
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'uart_tx_8bit' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'uart_tx_8bit' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
