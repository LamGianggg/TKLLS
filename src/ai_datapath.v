//==============================================================================
// Module: ai_datapath
// Description: AI Accelerator Datapath integrating Reg_W, Reg_X, MAC, ReLU,
// Vector Counter, and Result Register
//==============================================================================
module ai_datapath (
    input  wire       clk,
    input  wire       clr,
    input  wire [3:0] data_in,
    input  wire [3:0] vec_len,
    input  wire       load_w,
    input  wire       load_x,
    input  wire       acc_en,
    input  wire       relu_en,
    input  wire       load_len,
    input  wire       dec_vc,
    output wire       v_done,
    output reg  [7:0] result_out
);

    reg  [3:0] reg_w;
    reg  [3:0] reg_x;
    wire [7:0] mac_out;
    wire [7:0] relu_out;

    // Weight Register
    always @(posedge clk or posedge clr) begin
        if (clr)
            reg_w <= 4'h0;
        else if (load_w)
            reg_w <= data_in;
    end

    // Input X Register
    always @(posedge clk or posedge clr) begin
        if (clr)
            reg_x <= 4'h0;
        else if (load_x)
            reg_x <= data_in;
    end

    // MAC Unit
    mac_unit u_mac (
        .clk(clk),
        .clr(clr),
        .acc_en(acc_en),
        .w_in(reg_w),
        .x_in(reg_x),
        .mac_out(mac_out)
    );

    // ReLU Unit
    relu u_relu (
        .data_in(mac_out),
        .data_out(relu_out)
    );

    // Result Register
    always @(posedge clk or posedge clr) begin
        if (clr)
            result_out <= 8'h00;
        else if (relu_en)
            result_out <= relu_out;
    end

    // Vector Counter
    vector_counter u_vc (
        .clk(clk),
        .clr(clr),
        .load_len(load_len),
        .dec_en(dec_vc),
        .len_in(vec_len),
        .count(),
        .v_done(v_done)
    );

endmodule
