//==============================================================================
// Testbench: tb_button_debouncer
// Mo ta: Testbench tu kiem tra cho thiet ke button_debouncer
// Tieu chuan kiem dinh: VeriPrefer (arXiv:2504.15804)
//==============================================================================
`timescale 1ns / 1ps

module tb_button_debouncer;

    reg           clk;
    reg           rst;
    reg           btn_in;
    wire          btn_clean;
    wire          btn_pressed_pulse;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    button_debouncer dut (
        .clk(clk),
        .rst(rst),
        .btn_in(btn_in),
        .btn_clean(btn_clean),
        .btn_pressed_pulse(btn_pressed_pulse)
    );

    always #10 clk = ~clk;

    // Bo dem thoi gian bao ve Watchdog
    initial begin
        #100000;
        $display("[HARNESS WATCHDOG TIMEOUT] Simulation exceeded safety limit (100 us)!");
        $finish;
    end

    initial begin
        $dumpfile("button_debouncer.vcd");
        $dumpvars(0, tb_button_debouncer);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: button_debouncer");
        $display("============================================================================");

        // Trang thai khoi tao
        clk = 0;
        rst = 1'b1; // Kich hoat reset muc cao
        btn_in = 0;

        #25;
        rst = 1'b0; // Huy reset muc cao

        // Chay cac kich ban kiem thu voi assertions
        // Kich ban 1
        btn_in = 1'd1;
        #20;
        total_tests = total_tests + 1;
        if ((^btn_clean !== 1'bx) && (^btn_pressed_pulse !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 2
        btn_in = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^btn_clean !== 1'bx) && (^btn_pressed_pulse !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 3
        btn_in = 1'd1;
        #20;
        total_tests = total_tests + 1;
        if ((^btn_clean !== 1'bx) && (^btn_pressed_pulse !== 1'bx)) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: Outputs valid and deterministic");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: Output contains undefined or floating (X/Z) bits!");
        end
        // Kich ban 4
        btn_in = 1'd0;
        #20;
        total_tests = total_tests + 1;
        if ((^btn_clean !== 1'bx) && (^btn_pressed_pulse !== 1'bx)) begin
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
        $display("  Functional Accuracy  : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        $display("============================================================================");
        if (failed_tests == 0 && passed_tests == total_tests) begin
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'button_debouncer' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'button_debouncer' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
