//==============================================================================
// Module: relu
// Description: Rectified Linear Unit (ReLU) Activation
// Returns data_in if MSB == 0 (positive), else 8'h00
//==============================================================================
module relu (
    input  wire [7:0] data_in,
    output wire [7:0] data_out
);

    // For unsigned data, all values are positive or zero
    // If interpreted as signed 2's complement:
    assign data_out = (data_in[7] == 1'b1) ? 8'h00 : data_in;

endmodule
