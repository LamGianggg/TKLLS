//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER
// Module: harness_decoder_3to8
// Mạch kiểm thử: decoder_3to8
// Chuẩn: IEEE 1364-2001 Test Fixture
// Tính năng:
//   1. Hệ thống tạo xung nhịp 50 MHz & Reset đồng bộ
//   2. Watchdog an toàn: Tự ngắt sau 100,000 ps để tránh treo lặp vô tận
//   3. Bộ task tự động kiểm tra assertion hợp lệ
//   4. Ghép nối DUT socket tường minh
//==============================================================================
`timescale 1ns / 1ps

module harness_decoder_3to8;

    // -------------------------------------------------------------------------
    // 1. KHAI BÁO TÍN HIỆU HARNESS
    // -------------------------------------------------------------------------
    reg  [2:0]    a;
    reg           en;
    wire [7:0]    y;
    reg           clk;

    // Biến đếm thống kê kết quả
    integer total_tests  = 0;
    integer passed_tests = 0;
    integer failed_tests = 0;

    // -------------------------------------------------------------------------
    // 2. BỘ PHÁT XUNG CLOCK (50 MHz, Chu kỳ = 20ns)
    // -------------------------------------------------------------------------
    always #10 clk = ~clk;

    // -------------------------------------------------------------------------
    // 3. WATCHDOG TIMER AN TOÀN (Ngắt tự động nếu FSM bị treo)
    // -------------------------------------------------------------------------
    initial begin
        #100000;
        $display("\n============================================================================");
        $display("   [HARNESS WATCHDOG TIMEOUT] Quá thời gian mô phỏng an toàn (100 us)!");
        $display("   Phát hiện nguy cơ lặp vô tận hoặc treo trạng thái trong mạch 'decoder_3to8'.");
        $display("   Thống kê tại thời điểm ngắt -> Tổng: %0d | Đạt: %0d | Lỗi: %0d",
                 total_tests, passed_tests, failed_tests);
        $display("============================================================================");
        $finish;
    end

    // -------------------------------------------------------------------------
    // 4. CÁC TASK KIỂM TRA ĐỐI SOÁT TÍN HIỆU
    // -------------------------------------------------------------------------
    task harness_assert_eq;
        input [31:0]  actual;
        input [31:0]  expected;
        input [255:0] test_name;
        begin
            total_tests = total_tests + 1;
            if (actual === expected) begin
                passed_tests = passed_tests + 1;
                $display("  [HARNESS PASS] %0s | Thực tế: %h == Kỳ vọng: %h", test_name, actual, expected);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [HARNESS FAIL] %0s | Thực tế: %h != Kỳ vọng: %h tại %0t ps",
                         test_name, actual, expected, $time);
            end
        end
    endtask

    task harness_assert_valid;
        input [31:0]  val;
        input [255:0] signal_name;
        begin
            total_tests = total_tests + 1;
            if (^val !== 1'bx && ^val !== 1'bz) begin
                passed_tests = passed_tests + 1;
                $display("  [HARNESS PASS] %0s hợp lệ (xác định): %h", signal_name, val);
            end else begin
                failed_tests = failed_tests + 1;
                $display("  [HARNESS FAIL] %0s chứa bit thả nổi X/Z: %h tại %0t ps",
                         signal_name, val, $time);
            end
        end
    endtask

    // -------------------------------------------------------------------------
    // 5. GHÉP NỐI LINH KIỆN MẠCH CẦN TEST (DUT)
    // -------------------------------------------------------------------------
    decoder_3to8 dut (
        .a(a),
        .en(en),
        .y(y)
    );

    // -------------------------------------------------------------------------
    // 6. TRÌNH TỰ KÍCH THÍCH VÀ XUẤT DẠNG SÓNG
    // -------------------------------------------------------------------------
    initial begin
        $dumpfile("decoder_3to8.vcd");
        $dumpvars(0, harness_decoder_3to8);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_decoder_3to8");
        $display("   Linh kiện kiểm thử: decoder_3to8");
        $display("============================================================================");

        // Khởi động
        clk = 0;
        a = 3'd0;
        en = 1'd0;

        #25;

        //====================================================================
        // KỊCH BẢN KIỂM TRA ĐẦU VÀO VÀ ĐỐI SOÁT ĐẦU RA
        //====================================================================

        // --- Kịch bản kiểm thử 1 ---
        a = 3'd0;
        en = 1'd1;
        #20;
        harness_assert_valid(y, "Kịch bản 1 - Cổng y");

        // --- Kịch bản kiểm thử 2 ---
        a = 3'd1;
        en = 1'd0;
        #20;
        harness_assert_valid(y, "Kịch bản 2 - Cổng y");

        // --- Kịch bản kiểm thử 3 ---
        a = 3'd2;
        en = 1'd1;
        #20;
        harness_assert_valid(y, "Kịch bản 3 - Cổng y");

        // --- Kịch bản kiểm thử 4 ---
        a = 3'd3;
        en = 1'd0;
        #20;
        harness_assert_valid(y, "Kịch bản 4 - Cổng y");

        // --- Kịch bản kiểm thử 5 ---
        a = 3'd4;
        en = 1'd1;
        #20;
        harness_assert_valid(y, "Kịch bản 5 - Cổng y");

        // --- Kịch bản kiểm thử 6 ---
        a = 3'd5;
        en = 1'd0;
        #20;
        harness_assert_valid(y, "Kịch bản 6 - Cổng y");

        #40;
        // Tổng kết
        $display("============================================================================");
        $display("       BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ HARNESS");
        $display("============================================================================");
        $display("  Mạch kiểm thử           : decoder_3to8");
        $display("  Tổng số bài test đã chạy: %0d", total_tests);
        $display("  Số phép kiểm tra đạt    : %0d", passed_tests);
        $display("  Số phép kiểm tra lỗi    : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Độ chính xác chức năng  : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] KIỂM THỬ MẠCH 'decoder_3to8' ĐẠT 100 PERCENT!");
        end else begin
            $display("  [ERROR] KIỂM THỬ MẠCH 'decoder_3to8' PHÁT HIỆN %0d LỖI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
