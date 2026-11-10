//==============================================================================
// Testbench: tb_top_soc
// Description: Self-Checking Testbench for Autonomous AI Accelerator SoC
// Asserts functional correctness: W * X = 3 * 4 = 12 (0x0C)
//==============================================================================
`timescale 1ns / 1ps

module tb_top_soc;

    reg        clk;
    reg        clr;
    wire       SYS_COMPLETE;
    wire [7:0] FINAL_RESULT;
    wire [3:0] CPU_STATE;
    wire       AI_DONE;
    wire       SYSTEM_INTR;
    wire       TC;
    wire       DACK;
    wire       DREQ;

    // Instantiate Top SoC
    top_soc dut (
        .clk(clk),
        .clr(clr),
        .SYS_COMPLETE(SYS_COMPLETE),
        .FINAL_RESULT(FINAL_RESULT),
        .CPU_STATE(CPU_STATE),
        .AI_DONE(AI_DONE),
        .SYSTEM_INTR(SYSTEM_INTR),
        .TC(TC),
        .DACK(DACK),
        .DREQ(DREQ)
    );

    // 50 MHz Clock generation (20 ns period)
    always #10 clk = ~clk;

    initial begin
        // Initialize VCD waveform dumping
        $dumpfile("dump.vcd");
        $dumpvars(0, tb_top_soc);

        // Header
        $display("============================================================================");
        $display("   Autonomous Single-Chip AI Accelerator SoC Simulation (Spec2RTL Verification)");
        $display("============================================================================");
        $display("Time (ns) | CPU_STATE | DREQ | DACK | TC | AI_DONE | INTR | COMPLETE | RESULT");
        $display("----------------------------------------------------------------------------");

        // Initialization
        clk = 0;
        clr = 1;
        #25;
        clr = 0; // Release reset
    end

    // Cycle Monitor
    always @(posedge clk) begin
        if (!clr) begin
            $display("%8.1f ns |    S%02d    |  %b   |  %b   | %b  |    %b    |  %b   |    %b     | 0x%02X (%0d)",
                $time, CPU_STATE, DREQ, DACK, TC, AI_DONE, SYSTEM_INTR, SYS_COMPLETE, FINAL_RESULT, FINAL_RESULT);
        end
    end

    // Verification and Timeout
    initial begin
        // Wait for completion or timeout
        fork
            begin: wait_done
                wait (SYS_COMPLETE == 1'b1);
                #20; // Allow 1 clock cycle for stable latch
                $display("----------------------------------------------------------------------------");
                if (FINAL_RESULT === 8'h0C) begin
                    $display("\n============================================================================");
                    $display("  [SUCCESS] TEST VERIFICATION PASSED 100 PERCENT!");
                    $display("  Dot Product: W (3) * X (4) = FINAL_RESULT: 0x%02X (%0d decimal)", FINAL_RESULT, FINAL_RESULT);
                    $display("  Hardware Handshake: DREQ -> DACK -> AI_DONE -> SYSTEM_INTR -> SYS_COMPLETE");
                    $display("============================================================================\n");
                end else begin
                    $display("\n[ERROR] MISMATCH: Expected 0x0C (12), but got 0x%02X (%0d)", FINAL_RESULT, FINAL_RESULT);
                end
                disable timeout_check;
                $finish;
            end

            begin: timeout_check
                #2000;
                $display("\n[ERROR] SIMULATION TIMEOUT at %0t ns! SYS_COMPLETE did not assert.", $time);
                $finish;
            end
        join
    end

endmodule
