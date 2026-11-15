`timescale 1ns / 1ps

module tb_memory_address_decoder;

    reg  [15:0] addr;
    reg         mem_en;
    wire        cs_ram;
    wire        cs_rom;
    wire        cs_io;

    integer total_tests = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    memory_address_decoder dut (
        .addr(addr),
        .mem_en(mem_en),
        .cs_ram(cs_ram),
        .cs_rom(cs_rom),
        .cs_io(cs_io)
    );

    initial begin
        $dumpfile("memory_address_decoder.vcd");
        $dumpvars(0, tb_memory_address_decoder);

        $display("============================================================================");
        $display("   AUTONOMOUS HARDWARE VERIFICATION FOR MODULE: memory_address_decoder");
        $display("============================================================================");

        // Kich ban 1: mem_en = 0 (Tat ca CS phai bang 0)
        addr = 16'h1234;
        mem_en = 1'b0;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 0 && cs_rom == 0 && cs_io == 0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 1: mem_en=0 disables all chip selects");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 1: Output active when mem_en=0");
        end

        // Kich ban 2: SRAM (0x0000 - 0x7FFF)
        addr = 16'h2000;
        mem_en = 1'b1;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 1 && cs_rom == 0 && cs_io == 0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 2: SRAM region 0x2000 activates cs_ram");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 2: SRAM selection failed");
        end

        // Kich ban 3: ROM (0x8000 - 0xBFFF)
        addr = 16'h9000;
        mem_en = 1'b1;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 0 && cs_rom == 1 && cs_io == 0) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 3: ROM region 0x9000 activates cs_rom");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 3: ROM selection failed");
        end

        // Kich ban 4: I/O (0xC000 - 0xFFFF)
        addr = 16'hE000;
        mem_en = 1'b1;
        #20;
        total_tests = total_tests + 1;
        if (cs_ram == 0 && cs_rom == 0 && cs_io == 1) begin
            passed_tests = passed_tests + 1;
            $display("  [PASS] Scenario 4: I/O region 0xE000 activates cs_io");
        end else begin
            failed_tests = failed_tests + 1;
            $display("  [ERROR] Scenario 4: I/O selection failed");
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
            $display("  [SUCCESS] TEST VERIFICATION FOR MODULE 'memory_address_decoder' PASSED 100 PERCENT!");
        end else begin
            $display("  [ERROR] TEST VERIFICATION FOR MODULE 'memory_address_decoder' FAILED WITH %0d ERRORS!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
