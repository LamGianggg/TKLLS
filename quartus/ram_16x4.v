//==============================================================================
// Module: ram_16x4
// Description: Synchronous 16x4 Static RAM
// CS=1, RWS=1 -> Write; CS=1, RWS=0 -> Read
//==============================================================================
module ram_16x4 (
    input  wire       clk,
    input  wire       cs,
    input  wire       rws,
    input  wire [1:0] addr,
    input  wire [3:0] din,
    output wire [3:0] dout
);

    reg [3:0] mem [0:3];

    // Synchronous write
    always @(posedge clk) begin
        if (cs && rws) begin
            mem[addr] <= din;
        end
    end

    // Transparent read when enabled
    assign dout = (cs && !rws) ? mem[addr] : 4'b0000;

endmodule
