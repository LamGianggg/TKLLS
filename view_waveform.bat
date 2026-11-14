@echo off
chcp 65001 > nul
echo ===============================================================================
echo     Spec2RTL ^& Prompt2Silicon: 1-Click Graphical Waveform Launcher
echo ===============================================================================
echo.
echo [1/2] Khoi dong ModelSim Waveform GUI cho module: harness_gray_counter_4bit...

cd /d "D:\altera\13.0sp1\BTVN\Do_An_3\sim"

if exist "D:\altera\13.0sp1\modelsim_ase\win32aloem\vsim.exe" (
    start "" "D:\altera\13.0sp1\modelsim_ase\win32aloem\vsim.exe" -novopt work.harness_gray_counter_4bit -do "add wave -r /*; run -all; wave zoom full;"
    echo -> [OK] Da mo cua so song truc quan trong ModelSim GUI!
) else (
    echo -> [Luu y] Khong tim thay ModelSim GUI, dang mo Waveform HTML truc tiep tren trinh duyet...
    start "" "D:\altera\13.0sp1\BTVN\Do_An_3\sim\waveform.html"
)

echo.
echo [2/2] Da khoi tao thanh cong! Ban co the quan sat bieu do xung song tren man hinh.
echo ===============================================================================
