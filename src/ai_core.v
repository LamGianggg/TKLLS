//==============================================================================
// Module: ai_core
// Description: Top-Level AI Accelerator Core
// Connects AI FSM controller and Datapath
//==============================================================================
module ai_core (
    input  wire       clk,
    input  wire       clr,
    input  wire       start_ai,
    input  wire       dack,
    input  wire [3:0] data_in,
    input  wire [3:0] vec_len,
    output wire       dreq,
    output wire       ai_done,
    output wire       system_intr,
    output wire [7:0] result_out
);

    wire load_w;
    wire load_x;
    wire acc_en;
    wire relu_en;
    wire load_len;
    wire dec_vc;
    wire v_done;

    ai_fsm u_fsm (
        .clk(clk),
        .clr(clr),
        .start_ai(start_ai),
        .dack(dack),
        .v_done(v_done),
        .dreq(dreq),
        .load_w(load_w),
        .load_x(load_x),
        .acc_en(acc_en),
        .relu_en(relu_en),
        .load_len(load_len),
        .dec_vc(dec_vc),
        .ai_done(ai_done),
        .intr(system_intr)
    );

    ai_datapath u_dp (
        .clk(clk),
        .clr(clr),
        .data_in(data_in),
        .vec_len(vec_len),
        .load_w(load_w),
        .load_x(load_x),
        .acc_en(acc_en),
        .relu_en(relu_en),
        .load_len(load_len),
        .dec_vc(dec_vc),
        .v_done(v_done),
        .result_out(result_out)
    );

endmodule
