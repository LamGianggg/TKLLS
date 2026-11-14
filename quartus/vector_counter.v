//==============================================================================
// Module: vector_counter
// Description: Vector Length Counter
// Decrements vector length and flags v_done when complete
//==============================================================================
module vector_counter (
    input  wire       clk,
    input  wire       clr,
    input  wire       load_len,
    input  wire       dec_en,
    input  wire [3:0] len_in,
    output reg  [3:0] count,
    output wire       v_done
);

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            count <= 4'h0;
        end else if (load_len) begin
            count <= len_in;
        end else if (dec_en && (count > 4'h0)) begin
            count <= count - 1'b1;
        end
    end

    assign v_done = (count == 4'h0);

endmodule
