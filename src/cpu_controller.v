//==============================================================================
// Module: cpu_controller
// Description: CPU Micro-sequencer Controller
// Manages system initialization, DMA setup, RAM loading, and AI handoff
//==============================================================================
module cpu_controller (
    input  wire        clk,
    input  wire        clr,
    input  wire        system_intr,
    input  wire [7:0]  ai_result_in,
    // CPU State Observation
    output reg  [3:0]  cpu_state,
    // RAM Direct Control (Active when dma_mode_sel == 0)
    output reg  [1:0]  ram_addr,
    output reg         ram_cs,
    output reg         ram_rws,
    output reg  [3:0]  ram_din,
    // DMA Configuration Interface
    output reg  [1:0]  dma_addr,
    output reg         dma_cs_n,
    output reg         dma_iow_n,
    output reg  [15:0] dma_data,
    output reg         dma_hlda,
    output reg         dma_mode_sel,
    // AI Control Interface
    output reg         start_ai,
    output reg         ai_ie,
    // Final System Outputs
    output reg         sys_complete,
    output reg  [7:0]  final_result
);

    localparam S00 = 4'h0; // Idle
    localparam S01 = 4'h1; // Write W to RAM addr 0
    localparam S02 = 4'h2; // Write W latch
    localparam S03 = 4'h3; // Write X to RAM addr 1
    localparam S04 = 4'h4; // Write X latch
    localparam S05 = 4'h5; // Config DMA MAR = 0x0000
    localparam S06 = 4'h6; // Config DMA WCR = 0x0001
    localparam S07 = 4'h7; // Trigger START_AI
    localparam S08 = 4'h8; // Bus grant to DMA, wait for INTR
    localparam S09 = 4'h9; // INTR acknowledge, reclaim bus
    localparam S10 = 4'hA; // Latch result, SYS_COMPLETE

    reg [3:0] state, next_state;

    always @(posedge clk or posedge clr) begin
        if (clr)
            state <= S00;
        else
            state <= next_state;
    end

    always @(*) begin
        next_state   = state;
        cpu_state    = state;
        ram_addr     = 2'b00;
        ram_cs       = 1'b0;
        ram_rws      = 1'b0;
        ram_din      = 4'h0;
        dma_addr     = 2'b00;
        dma_cs_n     = 1'b1;
        dma_iow_n    = 1'b1;
        dma_data     = 16'h0000;
        dma_hlda     = 1'b0;
        dma_mode_sel = 1'b0;
        start_ai     = 1'b0;
        ai_ie        = 1'b0;

        case (state)
            S00: begin
                next_state = S01;
            end

            S01: begin
                // Write Weight W = 3 to RAM[0]
                ram_addr   = 2'b00;
                ram_din    = 4'h3;
                ram_cs     = 1'b1;
                ram_rws    = 1'b1;
                next_state = S02;
            end

            S02: begin
                ram_addr   = 2'b00;
                ram_din    = 4'h3;
                ram_cs     = 1'b1;
                ram_rws    = 1'b1;
                next_state = S03;
            end

            S03: begin
                // Write Input X = 4 to RAM[1]
                ram_addr   = 2'b01;
                ram_din    = 4'h4;
                ram_cs     = 1'b1;
                ram_rws    = 1'b1;
                next_state = S04;
            end

            S04: begin
                ram_addr   = 2'b01;
                ram_din    = 4'h4;
                ram_cs     = 1'b1;
                ram_rws    = 1'b1;
                next_state = S05;
            end

            S05: begin
                // Configure DMA MAR = 0x0000
                dma_cs_n   = 1'b0;
                dma_iow_n  = 1'b0;
                dma_addr   = 2'b00;
                dma_data   = 16'h0000;
                next_state = S06;
            end

            S06: begin
                // Configure DMA WCR = 0x0001 (2 words transfer)
                dma_cs_n   = 1'b0;
                dma_iow_n  = 1'b0;
                dma_addr   = 2'b01;
                dma_data   = 16'h0001;
                next_state = S07;
            end

            S07: begin
                start_ai   = 1'b1;
                ai_ie      = 1'b1;
                next_state = S08;
            end

            S08: begin
                dma_mode_sel = 1'b1;
                dma_hlda     = 1'b1;
                ai_ie        = 1'b1;
                if (system_intr) begin
                    next_state = S09;
                end
            end

            S09: begin
                dma_mode_sel = 1'b0;
                next_state   = S10;
            end

            S10: begin
                // Stay in S10
            end

            default: next_state = S00;
        endcase
    end

    // Result Latching and System Complete flag
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            final_result <= 8'h00;
            sys_complete <= 1'b0;
        end else if (state == S10) begin
            final_result <= ai_result_in;
            sys_complete <= 1'b1;
        end
    end

endmodule
