@echo off
chcp 65001 > nul
echo ===============================================================================
echo     Spec2RTL ^& Prompt2Silicon: 1-Click Graphical Waveform Launcher
echo ===============================================================================
echo.
echo [1/2] Khoi dong ModelSim Waveform GUI cho module: tb_khoa_ma_so_dien_tu_4_chu_so_bao_mat...

cd /d "D:\altera\13.0sp1\BTVN\Do_An_3\sim"

if exist "D:\altera\13.0sp1\modelsim_ase\win32aloem\vsim.exe" (
    start "" "D:\altera\13.0sp1\modelsim_ase\win32aloem\vsim.exe" -novopt work.tb_khoa_ma_so_dien_tu_4_chu_so_bao_mat -do "add wave -r /*; run -all; wave zoom full;"
    echo -> [OK] Da mo cua so song truc quan trong ModelSim GUI!
) else (
    echo -> [Luu y] Khong tim thay ModelSim GUI!
    echo -> Ban co the mo file quartus/Waveform.vwf truc tiep trong Quartus II Waveform Editor.
)

echo.
echo [2/2] Da khoi tao thanh cong! Ban co the quan sat bieu do xung song tren man hinh.
echo ===============================================================================
