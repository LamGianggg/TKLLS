@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:MENU
cls
echo ===============================================================================
echo        DEMO ĐỒ ÁN 3: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH SPEC2RTL
echo   Dựa trên NVIDIA Research (arXiv:2506.13905) & CityU HK VeriPrefer (arXiv:2504.15804)
echo   Kho tri thức phần cứng tích hợp: 539 thiết kế chuẩn công nghiệp
echo ===============================================================================
echo.
echo   [1] Demo Máy Bán Nước Tự Động (Chạy Pipeline + Tự động mở ModelSim Waveform GUI)
echo   [2] Demo Hệ Thống SoC AI Accelerator (CPU + RAM + DMA + AI MAC Unit)
echo   [3] Demo 3 Bộ Benchmark Chuẩn Quốc Tế (NVIDIA VerilogEval, HKUST RTLLM, CityU VeriPrefer)
echo   [4] Demo Khả Năng RAG & Tự Sinh Mạch Bất Kỳ (Dynamic Spec2RTL từ Prompt tự do)
echo   [5] Xem Dạng Sóng Trực Quan Tương Tác trên Trình Duyệt Web (waveform.html)
echo   [6] Mở Sơ Đồ Nguyên Lý Khối BDF trong Quartus II (top_vending_machine.bdf)
echo   [0] Thoát
echo.
echo ===============================================================================
set /p opt="👉 Vui lòng chọn kịch bản muốn demo cho Thầy [0-6, mặc định: 1]: "

if "%opt%"=="" set opt=1
if "%opt%"=="1" goto DEMO_VENDING
if "%opt%"=="2" goto DEMO_SOC
if "%opt%"=="3" goto DEMO_BENCHMARK
if "%opt%"=="4" goto DEMO_DYNAMIC
if "%opt%"=="5" goto OPEN_HTML
if "%opt%"=="6" goto OPEN_BDF
if "%opt%"=="0" goto EXIT
goto MENU

:DEMO_VENDING
cls
echo [DEMO 1] Đang thực thi Spec2RTL: Máy bán nước tự động (kèm cửa sổ sóng ModelSim GUI)...
python agent\run_spec2rtl.py specs\vendding_machine.md --gui
echo.
pause
goto MENU

:DEMO_SOC
cls
echo [DEMO 2] Đang thực thi Spec2RTL: SoC AI Accelerator Core...
python agent\run_spec2rtl.py specs\soc_ai_spec.md --gui
echo.
pause
goto MENU

:DEMO_BENCHMARK
cls
echo [DEMO 3] Đang thực thi đo đạc tài nguyên trên cả 3 bộ Benchmark quốc tế...
python agent\run_spec2rtl.py benchmark
echo.
pause
goto MENU

:DEMO_DYNAMIC
cls
echo [DEMO 4] Nhập đường dẫn file đặc tả tự do trong specs/ (hoặc ấn Enter để chạy specs/a.txt):
set /p spec_file="Đường dẫn file: "
if "!spec_file!"=="" set spec_file=specs\a.txt
python agent\run_spec2rtl.py "!spec_file!" --gui
echo.
pause
goto MENU

:OPEN_HTML
cls
echo Đang mở dạng sóng trực quan HTML5 trên trình duyệt...
if exist "sim\waveform.html" (
    start "" "sim\waveform.html"
) else (
    echo Chưa có file sim\waveform.html. Vui lòng chạy kịch bản [1] trước!
)
pause
goto MENU

:OPEN_BDF
cls
echo Đang mở sơ đồ nguyên lý mạch BDF...
if exist "quartus\top_vending_machine.bdf" (
    start "" "quartus\top_vending_machine.bdf"
) else (
    echo Chưa có file quartus\top_vending_machine.bdf. Vui lòng chạy kịch bản [1] trước!
)
pause
goto MENU

:EXIT
echo Tạm biệt! Chúc bạn có buổi báo cáo và demo thành công rực rỡ với Thầy!
timeout /t 2 > nul
exit /b 0
