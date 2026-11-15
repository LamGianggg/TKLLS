//==============================================================================
// VERILOG HARDWARE TEST HARNESS WRAPPER
// Module: harness_memory_address_decoder
// Mạch kiểm thử: memory_address_decoder
// Chuẩn: IEEE 1364-2001 Test Fixture
// Tính năng:
//   1. Hệ thống tạo xung nhịp 50 MHz & Reset đồng bộ
//   2. Watchdog an toàn: Tự ngắt sau 100,000 ps để tránh treo lặp vô tận
//   3. Bộ task tự động kiểm tra assertion hợp lệ
//   4. Ghép nối DUT socket tường minh
//==============================================================================
`timescale 1ns / 1ps

module harness_memory_address_decoder;

    // -------------------------------------------------------------------------
    // 1. KHAI BÁO TÍN HIỆU HARNESS
    // -------------------------------------------------------------------------
    reg  [15:0]   addr;
    reg           mem_en;
    wire          cs_ram;
    wire          cs_rom;
    wire          cs_io;
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
        $display("   Phát hiện nguy cơ lặp vô tận hoặc treo trạng thái trong mạch 'memory_address_decoder'.");
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
    memory_address_decoder dut (
        .addr(addr),
        .mem_en(mem_en),
        .cs_ram(cs_ram),
        .cs_rom(cs_rom),
        .cs_io(cs_io)
    );

    // -------------------------------------------------------------------------
    // 6. TRÌNH TỰ KÍCH THÍCH VÀ XUẤT DẠNG SÓNG
    // -------------------------------------------------------------------------
    initial begin
        $dumpfile("memory_address_decoder.vcd");
        $dumpvars(0, harness_memory_address_decoder);

        $display("============================================================================");
        $display("   VERILOG TEST HARNESS (OPTION A): harness_memory_address_decoder");
        $display("   Linh kiện kiểm thử: memory_address_decoder");
        $display("============================================================================");

        // Khởi động
        clk = 0;
        addr = 16'd0;
        mem_en = 1'd0;

        #25;

        //====================================================================
        // KỊCH BẢN KIỂM TRA ĐẦU VÀO VÀ ĐỐI SOÁT ĐẦU RA
        //====================================================================

        // --- Kịch bản kiểm thử 1 ---
        addr = 16'd24;
        mem_en = 1'd1;
        #20;
        harness_assert_valid(cs_ram, "Kịch bản 1 - Cổng cs_ram");
        harness_assert_valid(cs_rom, "Kịch bản 1 - Cổng cs_rom");
        harness_assert_valid(cs_io, "Kịch bản 1 - Cổng cs_io");

        // --- Kịch bản kiểm thử 2 ---
        addr = 16'd41;
        mem_en = 1'd0;
        #20;
        harness_assert_valid(cs_ram, "Kịch bản 2 - Cổng cs_ram");
        harness_assert_valid(cs_rom, "Kịch bản 2 - Cổng cs_rom");
        harness_assert_valid(cs_io, "Kịch bản 2 - Cổng cs_io");

        // --- Kịch bản kiểm thử 3 ---
        addr = 16'd58;
        mem_en = 1'd1;
        #20;
        harness_assert_valid(cs_ram, "Kịch bản 3 - Cổng cs_ram");
        harness_assert_valid(cs_rom, "Kịch bản 3 - Cổng cs_rom");
        harness_assert_valid(cs_io, "Kịch bản 3 - Cổng cs_io");

        // --- Kịch bản kiểm thử 4 ---
        addr = 16'd75;
        mem_en = 1'd0;
        #20;
        harness_assert_valid(cs_ram, "Kịch bản 4 - Cổng cs_ram");
        harness_assert_valid(cs_rom, "Kịch bản 4 - Cổng cs_rom");
        harness_assert_valid(cs_io, "Kịch bản 4 - Cổng cs_io");

        // --- Kịch bản kiểm thử 5 ---
        addr = 16'd92;
        mem_en = 1'd1;
        #20;
        harness_assert_valid(cs_ram, "Kịch bản 5 - Cổng cs_ram");
        harness_assert_valid(cs_rom, "Kịch bản 5 - Cổng cs_rom");
        harness_assert_valid(cs_io, "Kịch bản 5 - Cổng cs_io");

        // --- Kịch bản kiểm thử 6 ---
        addr = 16'd109;
        mem_en = 1'd0;
        #20;
        harness_assert_valid(cs_ram, "Kịch bản 6 - Cổng cs_ram");
        harness_assert_valid(cs_rom, "Kịch bản 6 - Cổng cs_rom");
        harness_assert_valid(cs_io, "Kịch bản 6 - Cổng cs_io");

        #40;
        // Tổng kết
        $display("============================================================================");
        $display("       BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ HARNESS");
        $display("============================================================================");
        $display("  Mạch kiểm thử           : memory_address_decoder");
        $display("  Tổng số bài test đã chạy: %0d", total_tests);
        $display("  Số phép kiểm tra đạt    : %0d", passed_tests);
        $display("  Số phép kiểm tra lỗi    : %0d", failed_tests);
        if (total_tests > 0) begin
            $display("  Độ chính xác chức năng  : %0.1f PERCENT", (passed_tests * 100.0) / total_tests);
        end
        $display("============================================================================");

        if (failed_tests == 0 && passed_tests == total_tests && total_tests > 0) begin
            $display("  [SUCCESS] KIỂM THỬ MẠCH 'memory_address_decoder' ĐẠT 100 PERCENT!");
        end else begin
            $display("  [ERROR] KIỂM THỬ MẠCH 'memory_address_decoder' PHÁT HIỆN %0d LỖI!", failed_tests);
        end
        $display("============================================================================");
        $finish;
    end

endmodule
