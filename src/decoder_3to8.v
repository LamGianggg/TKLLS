//==============================================================================
// Module: decoder_3to8
// Description: Parameterized n-to-2^n Binary Decoder
//==============================================================================
module decoder_3to8 (
    input  wire [2:0] a,
    input  wire        en,
    output reg  [7:0] y
);

    always @(*) begin
        if (en) y = (1'b1 << a); else y = 8'd0;
    end

endmodule
