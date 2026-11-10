//==============================================================================
// Module: top_soc
// Description: Autonomous Single-Chip SoC integrating CPU Micro-sequencer,
// 16x4 SRAM, 8237 DMA Controller, and 8-bit AI Accelerator Core
//==============================================================================
module top_soc (
    input  wire       clk,
    input  wire       clr,
    output wire       SYS_COMPLETE,
    output wire [7:0] FINAL_RESULT,
    output wire [3:0] CPU_STATE,
    output wire       AI_DONE,
    output wire       SYSTEM_INTR,
    output wire       TC,
    output wire       DACK,
    output wire       DREQ
);

    // CPU Interconnect
    wire [1:0]  cpu_ram_addr;
    wire        cpu_ram_cs;
    wire        cpu_ram_rws;
    wire [3:0]  cpu_ram_din;
    wire [1:0]  dma_cfg_addr;
    wire        dma_cs_n;
    wire        dma_iow_n;
    wire [15:0] dma_cfg_data;
    wire        dma_hlda;
    wire        dma_mode_sel;
    wire        start_ai;
    wire        ai_ie;

    // DMA Interconnect
    wire [15:0] dma_addr_bus;
    wire        dma_ram_cs;
    wire        dma_ram_rws;
    wire        hrq;

    // RAM MUXed Signals
    wire [1:0]  ram_mux_addr;
    wire        ram_mux_cs;
    wire        ram_mux_rws;
    wire [3:0]  ram_dout;

    // AI Core Interconnect
    wire [7:0]  ai_result_raw;

    // 2-to-1 Multiplexers for RAM bus arbitration
    assign ram_mux_addr = (dma_mode_sel) ? dma_addr_bus[1:0] : cpu_ram_addr;
    assign ram_mux_cs   = (dma_mode_sel) ? dma_ram_cs        : cpu_ram_cs;
    assign ram_mux_rws  = (dma_mode_sel) ? dma_ram_rws       : cpu_ram_rws;

    // Instantiate CPU Controller
    cpu_controller u_cpu (
        .clk(clk),
        .clr(clr),
        .system_intr(SYSTEM_INTR),
        .ai_result_in(ai_result_raw),
        .cpu_state(CPU_STATE),
        .ram_addr(cpu_ram_addr),
        .ram_cs(cpu_ram_cs),
        .ram_rws(cpu_ram_rws),
        .ram_din(cpu_ram_din),
        .dma_addr(dma_cfg_addr),
        .dma_cs_n(dma_cs_n),
        .dma_iow_n(dma_iow_n),
        .dma_data(dma_cfg_data),
        .dma_hlda(dma_hlda),
        .dma_mode_sel(dma_mode_sel),
        .start_ai(start_ai),
        .ai_ie(ai_ie),
        .sys_complete(SYS_COMPLETE),
        .final_result(FINAL_RESULT)
    );

    // Instantiate On-Chip SRAM
    ram_16x4 u_ram (
        .clk(clk),
        .cs(ram_mux_cs),
        .rws(ram_mux_rws),
        .addr(ram_mux_addr),
        .din(cpu_ram_din),
        .dout(ram_dout)
    );

    // Instantiate DMA Controller
    dma_8237 u_dma (
        .clk(clk),
        .clr(clr),
        .cpu_cs_n(dma_cs_n),
        .cpu_iow_n(dma_iow_n),
        .cpu_addr(dma_cfg_addr),
        .cpu_data(dma_cfg_data),
        .hlda(dma_hlda),
        .dreq(DREQ),
        .dack(DACK),
        .hrq(hrq),
        .tc(TC),
        .addr_bus(dma_addr_bus),
        .ram_cs(dma_ram_cs),
        .ram_rws(dma_ram_rws)
    );

    // Instantiate AI Accelerator Core
    ai_core u_ai (
        .clk(clk),
        .clr(clr),
        .start_ai(start_ai),
        .dack(DACK),
        .data_in(ram_dout),
        .vec_len(4'b0001), // VEC_LEN = 1 (1 element dot product W*X)
        .dreq(DREQ),
        .ai_done(AI_DONE),
        .system_intr(SYSTEM_INTR),
        .result_out(ai_result_raw)
    );

endmodule
