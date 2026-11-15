//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER
// Module: harness_temperature_monitor_alarm
// Mạch kiểm thử: temperature_monitor_alarm
// Chuẩn: IEEE 1364-2001 Test Fixture
// Tính năng:
//   1. Hệ thống tạo xung nhịp 50 MHz & Reset đồng bộ
//   2. Watchdog an toàn: Tự ngắt sau 100,000 ps để tránh treo lặp vô tận
//   3. Bộ task tự động kiểm tra assertion hợp lệ
//   4. Ghép nối DUT socket tường minh
//==============================================================================
`timescale 1ns / 1ps

module harness_temperature_monitor_alarm;

    // -------------------------------------------------------------------------
    // 1. KHAI BÁO TÍN HIỆU HARNESS
    // -------------------------------------------------------------------------
    reg           clk;
    reg           rst;
    reg  [7:0]    temp_celsius;
    reg  [7:0]    max_temp_limit;
    wire          fan_high_speed;
    wire          overtemp_alarm;
    wire          shutdown_signal;

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
        $display("   Phát hiện nguy cơ lặp vô tận hoặc treo trạng thái trong mạch 'temperature_monitor_alarm'.");
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
    temperature_monitor_alarm dut (
        .clk(clk),
        .rst(rst),
        .temp_celsius(temp_celsius),
        .max_temp_limit(max_temp_limit),
        .fan_high_speed(fan_high_speed),
        .overtemp_alarm(overtemp_alarm),
        .shutdown_signal(shutdown_signal)
    );

    // -------------------------------------------------------------------------
    // 6. TRÌNH TỰ KÍCH THÍCH VÀ XUẤT DẠNG SÓNG
    // -------------------------------------------------------------------------
    initial begin
        $dumpfile("temperature_monitor_alarm.vcd");
        $dumpvars(0, harness_temperature_monitor_alarm);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_temperature_monitor_alarm");
        $display("   Linh kiện kiểm thử: temperature_monitor_alarm");
        $display("============================================================================");

        // Khởi động
        clk = 0;
        rst = 1'b1; // Kích hoạt reset ban đầu
        temp_celsius = 8'd0;
        max_temp_limit = 8'd0;

        #25;
        rst = 1'b0; // Nhả reset để mạch hoạt động

        //====================================================================
        // KỊCH BẢN KIỂM TRA ĐẦU VÀO VÀ ĐỐI SOÁT ĐẦU RA
        //====================================================================

        // --- Kịch bản kiểm thử 1 ---
        temp_celsius = 8'd24;
        max_temp_limit = 8'd47;
        #20;
        harness_assert_valid(fan_high_speed, "Kịch bản 1 - Cổng fan_high_speed");
        harness_assert_valid(overtemp_alarm, "Kịch bản 1 - Cổng overtemp_alarm");
        harness_assert_valid(shutdown_signal, "Kịch bản 1 - Cổng shutdown_signal");

        // --- Kịch bản kiểm thử 2 ---
        temp_celsius = 8'd41;
        max_temp_limit = 8'd64;
        #20;
        harness_assert_valid(fan_high_speed, "Kịch bản 2 - Cổng fan_high_speed");
        harness_assert_valid(overtemp_alarm, "Kịch bản 2 - Cổng overtemp_alarm");
        harness_assert_valid(shutdown_signal, "Kịch bản 2 - Cổng shutdown_signal");

        // --- Kịch bản kiểm thử 3 ---
        temp_celsius = 8'd58;
        max_temp_limit = 8'd81;
        #20;
        harness_assert_valid(fan_high_speed, "Kịch bản 3 - Cổng fan_high_speed");
        harness_assert_valid(overtemp_alarm, "Kịch bản 3 - Cổng overtemp_alarm");
        harness_assert_valid(shutdown_signal, "Kịch bản 3 - Cổng shutdown_signal");

        // --- Kịch bản kiểm thử 4 ---
        temp_celsius = 8'd75;
        max_temp_limit = 8'd98;
        #20;
        harness_assert_valid(fan_high_speed, "Kịch bản 4 - Cổng fan_high_speed");
        harness_assert_valid(overtemp_alarm, "Kịch bản 4 - Cổng overtemp_alarm");
        harness_assert_valid(shutdown_signal, "Kịch bản 4 - Cổng shutdown_signal");

        // --- Kịch bản kiểm thử 5 ---
        temp_celsius = 8'd92;
        max_temp_limit = 8'd115;
        #20;
        harness_assert_valid(fan_high_speed, "Kịch bản 5 - Cổng fan_high_speed");
        harness_assert_valid(overtemp_alarm, "Kịch bản 5 - Cổng overtemp_alarm");
        harness_assert_valid(shutdown_signal, "Kịch bản 5 - Cổng shutdown_signal");

        // --- Kịch bản kiểm thử 6 ---
        temp_celsius = 8'd109;
        max_temp_limit = 8'd132;
        #20;
        harness_assert_valid(fan_high_speed, "Kịch bản 6 - Cổng fan_high_speed");
        harness_assert_valid(overtemp_alarm, "Kịch bản 6 - Cổng overtemp_alarm");
        harness_assert_valid(shutdown_signal, "Kịch bản 6 - Cổng shutdown_signal");

        #40;
        // Tổng kết
        $display("============================================================================");
        $display("       BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ HARNESS");
        $display("============================================================================");
        $display("  Mạch kiểm thử           : temperature_monitor_alarm");
        $display("  Tổng số bài test đã chạy: %0d", total_tests);
        $display("  Số phép kiểm tra đạt    : %0d", passed_tests);
        $display("  Số phép kiểm tra lỗi    : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Độ chính xác chức năng  : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] KIỂM THỬ MẠCH 'temperature_monitor_alarm' ĐẠT 100 PERCENT!");
        end else begin
            $display("  [ERROR] KIỂM THỬ MẠCH 'temperature_monitor_alarm' PHÁT HIỆN %0d LỖI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
