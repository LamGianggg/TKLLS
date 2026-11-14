//==============================================================================
// Module: mac_unit
// Description: 8-bit Multiply-Accumulate (MAC) Unit
// Computes Acc = Acc + (W * X)
//==============================================================================
module mac_unit (
    input  wire       clk,
    input  wire       clr,
    input  wire       acc_en,
    input  wire [3:0] w_in,
    input  wire [3:0] x_in,
    output reg  [7:0] mac_out
);

    wire [7:0] product;
    assign product = w_in * x_in;

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            mac_out <= 8'h00;
        end else if (acc_en) begin
            mac_out <= mac_out + product;
        end
    end

endmodule
