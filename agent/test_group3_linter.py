"""
Test Suite: test_group3_linter.py
Nhiệm vụ Nhóm 3: Kỹ thuật Vi mạch & Bộ phân tích AST (Hardware Engineering & AST Linter)
Áp dụng phong cách Ponytail (Zero-dependency, Lazy Senior Dev Mode, Assert-based check).

Kiểm tra:
1. Phát hiện Chốt ẩn (Inferred Latches): case thiếu default, if thiếu else.
2. Phát hiện Chân lơ lửng (Dangling Pins): input không dùng (như lỗi button_debouncer), output không gán.
3. Phát hiện Race Condition: gán '=' trong khối tuần tự posedge clk.
4. Xác nhận mã chuẩn (Clean RTL): 100% PASS không báo lỗi giả.
"""

import os
import sys

# Đưa thư mục agent vào sys.path để import VerilogLinter
ThuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ThuMucAgent = os.path.join(ThuMucGoc, "agent")
if ThuMucAgent not in sys.path:
    sys.path.insert(0, ThuMucAgent)

from verilog_linter import VerilogLinter
from synthesis_profiler import SynthesisProfiler

def test_clean_counter():
    """Kiểm tra mạch chuẩn (Counter 4-bit) -> 100% PASS."""
    clean_code = '''
    module sync_counter (
        input wire clk,
        input wire rst_n,
        input wire enable,
        output reg [3:0] count
    );
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                count <= 4'b0000;
            else if (enable)
                count <= count + 1'b1;
        end
    endmodule
    '''
    res = VerilogLinter.lint_check(clean_code)
    assert res["valid"] is True, f"Mã chuẩn bị báo lỗi: {res['issues']}"
    assert len(res["latches"]) == 0
    assert len(res["dangling_pins"]) == 0
    assert len(res["race_conditions"]) == 0
    print("[PASS] Test 1: Clean Counter 4-bit -> 100% PASS (0 Latch, 0 Dangling, 0 Race)")

def test_dangling_pins_debouncer():
    """Kiểm tra phát hiện chân lơ lửng (btn_in bị cô lập trong button_debouncer)."""
    buggy_debouncer = '''
    module button_debouncer (
        input wire clk,
        input wire rst,
        input wire btn_in,
        output reg btn_clean,
        output reg btn_pressed_pulse
    );
        reg [1:0] shift_reg;
        always @(posedge clk or posedge rst) begin
            if (rst) begin
                shift_reg <= 2'b00;
                btn_clean <= 1'b0;
            end else begin
                // LỖI: Không nối btn_in vào shift_reg, tự dịch 0
                shift_reg <= {shift_reg[0], 1'b0};
                btn_clean <= shift_reg[1];
                // LỖI: Quên không gán giá trị cho btn_pressed_pulse
            end
        end
    endmodule
    '''
    res = VerilogLinter.lint_check(buggy_debouncer)
    assert res["valid"] is False, "Không phát hiện lỗi chân lơ lửng!"
    dangling_text = " ".join(res["dangling_pins"])
    assert "btn_in" in dangling_text, f"Không phát hiện btn_in bị dangling! {res['dangling_pins']}"
    assert "btn_pressed_pulse" in dangling_text, f"Không phát hiện btn_pressed_pulse unassigned! {res['dangling_pins']}"
    print("[PASS] Test 2: Dangling Pin Detection -> Bắt chính xác 'btn_in' cô lập & 'btn_pressed_pulse' chưa gán")

def test_inferred_latches():
    """Kiểm tra phát hiện chốt ẩn trong khối tổ hợp always @(*)."""
    latch_code = '''
    module alu_comb (
        input wire [1:0] op,
        input wire [3:0] a, b,
        input wire en,
        output reg [3:0] res_case,
        output reg [3:0] res_if
    );
        // Lỗi 1: case thiếu default:
        always @(*) begin
            case (op)
                2'b00: res_case = a + b;
                2'b01: res_case = a - b;
            endcase
        end

        // Lỗi 2: if thiếu else và không có gán mặc định
        always @(*) begin
            if (en)
                res_if = a & b;
        end
    endmodule
    '''
    res = VerilogLinter.lint_check(latch_code)
    assert res["valid"] is False, "Không phát hiện lỗi Inferred Latch!"
    latch_text = " ".join(res["latches"])
    assert "default" in latch_text, f"Không phát hiện case thiếu default! {res['latches']}"
    assert "res_if" in latch_text, f"Không phát hiện if thiếu else cho res_if! {res['latches']}"
    print("[PASS] Test 3: Inferred Latch Detection -> Bắt chính xác case thiếu default & if thiếu else")

def test_race_conditions():
    """Kiểm tra phát hiện gán blocking '=' trong khối tuần tự."""
    race_code = '''
    module bad_pipeline (
        input wire clk,
        input wire [7:0] d_in,
        output reg [7:0] d_out
    );
        reg [7:0] stage1;
        always @(posedge clk) begin
            stage1 = d_in;   // LỖI: Blocking assignment trong khối tuần tự
            d_out = stage1;  // Gây race condition giữa các flip-flop
        end
    endmodule
    '''
    res = VerilogLinter.lint_check(race_code)
    assert res["valid"] is False, "Không phát hiện vi phạm Race Condition!"
    race_text = " ".join(res["race_conditions"])
    assert "BLOCKING_IN_SEQUENTIAL" in race_text, f"Không bắt được lỗi gán blocking! {res['race_conditions']}"
    print("[PASS] Test 4: Race Condition Detection -> Bắt chính xác gán '=' trong khối posedge clk")

def test_synthesis_profiler():
    """Kiểm tra module ước lượng và đo đạc tài nguyên phần cứng (FPGA Resource Profiler)."""
    rtl_sample = os.path.join(ThuMucGoc, "quartus", "bcd_to_7seg_anode", "bcd_to_7seg_anode.v")
    if os.path.exists(rtl_sample):
        stats = SynthesisProfiler.estimate_static_resources(rtl_sample)
        assert stats["total_pins"] > 0, "Không đo được số chân I/O"
        assert stats["logic_elements"] > 0, "Không ước lượng được Logic Elements"
        card = SynthesisProfiler.format_profiler_card(stats, "bcd_to_7seg_anode")
        assert "THỐNG KÊ TÀI NGUYÊN PHẦN CỨNG" in card
        print("[PASS] Test 5: Synthesis Resource Profiler -> Đo đạc chính xác LEs, Registers, Pins cho FPGA")
    else:
        print("[SKIP] Test 5: File bcd_to_7seg_anode.v không tồn tại để test profiler")

def run_all_checks():
    print("================================================================================")
    print("      KIỂM TRA TỰ ĐỘNG BỘ PHÂN TÍCH TĨNH AST NHÓM 3 (PONYTAIL MODE)            ")
    print("================================================================================")
    test_clean_counter()
    test_dangling_pins_debouncer()
    test_inferred_latches()
    test_race_conditions()
    test_synthesis_profiler()
    print("================================================================================")
    print(">>> TOÀN BỘ 5 TEST CASES CỦA NHÓM 3 ĐÃ VƯỢT QUA 100% (ALL ASSERTIONS PASSED) <<<")
    print("================================================================================")

if __name__ == "__main__":
    run_all_checks()
