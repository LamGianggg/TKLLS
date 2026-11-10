//==============================================================================
// Module: ai_fsm
// Description: AI Accelerator Finite State Machine Controller
// Coordinates DREQ/DACK handshake, MAC execution, and completion interrupts
//==============================================================================
module ai_fsm (
    input  wire clk,
    input  wire clr,
    input  wire start_ai,
    input  wire dack,
    input  wire v_done,
    output reg  dreq,
    output reg  load_w,
    output reg  load_x,
    output reg  acc_en,
    output reg  relu_en,
    output reg  load_len,
    output reg  dec_vc,
    output reg  ai_done,
    output reg  intr
);

    localparam T0 = 3'b000; // Idle
    localparam T1 = 3'b001; // Req W
    localparam T2 = 3'b010; // Latch W / Prep X
    localparam T3 = 3'b011; // Req X
    localparam T4 = 3'b100; // Latch X / MAC Calc
    localparam T5 = 3'b101; // Vector Done Check
    localparam T6 = 3'b110; // ReLU & Done

    reg [2:0] state, next_state;

    // State register
    always @(posedge clk or posedge clr) begin
        if (clr)
            state <= T0;
        else
            state <= next_state;
    end

    // Next state and output logic
    always @(*) begin
        next_state = state;
        dreq       = 1'b0;
        load_w     = 1'b0;
        load_x     = 1'b0;
        acc_en     = 1'b0;
        relu_en    = 1'b0;
        load_len   = 1'b0;
        dec_vc     = 1'b0;
        ai_done    = 1'b0;
        intr       = 1'b0;

        case (state)
            T0: begin
                if (start_ai) begin
                    load_len   = 1'b1;
                    next_state = T1;
                end
            end

            T1: begin
                dreq = 1'b1;
                if (dack) begin
                    load_w     = 1'b1;
                    next_state = T2;
                end
            end

            T2: begin
                next_state = T3;
            end

            T3: begin
                dreq = 1'b1;
                if (dack) begin
                    load_x     = 1'b1;
                    next_state = T4;
                end
            end

            T4: begin
                acc_en     = 1'b1;
                dec_vc     = 1'b1;
                next_state = T5;
            end

            T5: begin
                if (v_done)
                    next_state = T6;
                else
                    next_state = T1;
            end

            T6: begin
                relu_en = 1'b1;
                ai_done = 1'b1;
                intr    = 1'b1;
                // Stay in T6 until cleared/reset
            end

            default: next_state = T0;
        endcase
    end

endmodule
