//==============================================================================
// Module: dma_8237
// Description: 8237-Compatible DMA Controller
// Handles auto-incrementing memory address generation and DREQ/DACK handshaking
//==============================================================================
module dma_8237 (
    input  wire        clk,
    input  wire        clr,
    // CPU Configuration Interface
    input  wire        cpu_cs_n,
    input  wire        cpu_iow_n,
    input  wire [1:0]  cpu_addr,
    input  wire [15:0] cpu_data,
    input  wire        hlda,
    // Peripheral (AI Core) Interface
    input  wire        dreq,
    output reg         dack,
    output wire        hrq,
    output wire        tc,
    // Memory Interface
    output wire [15:0] addr_bus,
    output wire        ram_cs,
    output wire        ram_rws
);

    reg [15:0] mar; // Memory Address Register
    reg [15:0] wcr; // Word Count Register

    assign hrq = dreq;
    assign tc  = (wcr == 16'h0000);

    // CPU Configuration Write
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            mar <= 16'h0000;
            wcr <= 16'h0000;
        end else if (!cpu_cs_n && !cpu_iow_n) begin
            case (cpu_addr)
                2'b00: mar <= cpu_data; // Write MAR
                2'b01: wcr <= cpu_data; // Write WCR
                default: ;
            endcase
        end else if (dack && (wcr > 16'h0000)) begin
            // Post-transfer auto-increment/decrement
            mar <= mar + 1'b1;
            wcr <= wcr - 1'b1;
        end
    end

    // DMA Handshake and transfer pulse
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            dack <= 1'b0;
        end else begin
            if (dreq && hlda && !dack) begin
                dack <= 1'b1;
            end else begin
                dack <= 1'b0;
            end
        end
    end

    assign addr_bus = mar;
    assign ram_cs   = dack;
    assign ram_rws  = 1'b0; // Always read from RAM in this workflow

endmodule
