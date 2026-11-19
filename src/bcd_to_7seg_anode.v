//==============================================================================
// Module: bcd_to_7seg_anode
// Description: Parameterized n-to-2^n Binary Decoder
//==============================================================================
module bcd_to_7seg_anode (
    input  wire [3:0] bcd,
    output reg  [6:0] seg
);

    always @(*) begin
        seg = (1'b1 << bcd);
    end

endmodule
