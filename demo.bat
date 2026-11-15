@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:MENU
cls
echo ===============================================================================
echo        DEMO ĐỒ ÁN 3: HỆ THỐNG TỰ ĐỘNG HÓA THIẾT KẾ VI MẠCH SPEC2RTL
echo        Luồng thực thi: SPEC -^> GENERATE -^> REVIEW -^> SHIP
echo ===============================================================================
echo.
echo   [1] Chạy Spec a.txt (Khóa Mã Số Điện Tử 4 Chữ Số Bảo Mật)
echo   [2] Chạy Spec b.txt (Đồng Hồ Bấm Giờ 0-9 Giây Kèm LED 7 Đoạn)
echo   [3] Chạy Spec c.txt (Đồng Hồ Bấm Giờ 0-9 Giây Kèm LED 7 Đoạn)
echo   [4] Chạy Spec d.txt (Hệ Thống Cảnh Báo An Ninh & Báo Cháy Nhà Thông Minh)
echo   [5] Chạy Spec Tự Do (Nhập đường dẫn file .txt bất kỳ)
echo   [6] Xem Dạng Sóng Trực Quan Tương Tác trên Web (waveform.html)
echo   [7] Mở Dạng Sóng ModelSim GUI (view_waveform.bat)
echo   [0] Thoát
echo.
echo ===============================================================================
set /p opt="👉 Vui lòng chọn bài toán muốn chạy [0-7, mặc định: 3]: "

if "%opt%"=="" set opt=3
if "%opt%"=="1" goto RUN_A
if "%opt%"=="2" goto RUN_B
if "%opt%"=="3" goto RUN_C
if "%opt%"=="4" goto RUN_D
if "%opt%"=="5" goto RUN_CUSTOM
if "%opt%"=="6" goto OPEN_HTML
if "%opt%"=="7" goto OPEN_GUI
if "%opt%"=="0" goto EXIT
goto MENU

:RUN_A
cls
echo [DEMO 1] Đang thực thi Spec2RTL: specs\a.txt...
python agent\run_spec2rtl.py specs\a.txt --gui
echo.
pause
goto MENU

:RUN_B
cls
echo [DEMO 2] Đang thực thi Spec2RTL: specs\b.txt...
python agent\run_spec2rtl.py specs\b.txt --gui
echo.
pause
goto MENU

:RUN_C
cls
echo [DEMO 3] Đang thực thi Spec2RTL: specs\c.txt...
python agent\run_spec2rtl.py specs\c.txt --gui
echo.
pause
goto MENU

:RUN_D
cls
echo [DEMO 4] Đang thực thi Spec2RTL: specs\d.txt...
python agent\run_spec2rtl.py specs\d.txt --gui
echo.
pause
goto MENU

:RUN_CUSTOM
cls
echo Nhập đường dẫn file .txt trong specs/ (hoặc ấn Enter để chạy specs\c.txt):
set /p spec_file="Đường dẫn file: "
if "!spec_file!"=="" set spec_file=specs\c.txt
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
    echo Chưa có file sim\waveform.html. Vui lòng chạy một spec trước!
)
pause
goto MENU

:OPEN_GUI
cls
echo Đang mở cửa sổ dạng sóng ModelSim GUI...
call view_waveform.bat
pause
goto MENU

:EXIT
echo Tạm biệt! Chúc bạn có buổi báo cáo và demo thành công rực rỡ!
timeout /t 2 > nul
exit /b 0
