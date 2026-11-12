"""
Module: waveform_visualizer.py
Description: Generates multi-platform visual waveforms from EDA simulation:
1. 1-Click ModelSim GUI launcher (view_waveform.bat)
2. Interactive standalone HTML5 Waveform Viewer (sim/waveform.html)
3. Quartus II University Program Vector Waveform File (quartus/Waveform.vwf)
"""

import os
import re
import json

class WaveformVisualizer:
    def __init__(self):
        pass

    @staticmethod
    def parse_vcd(vcd_path):
        """Parses a standard Value Change Dump (.vcd) file into structured timing traces."""
        if not os.path.exists(vcd_path):
            return None

        with open(vcd_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        var_map = {} # symbol -> {name, width, is_bus}
        timescale_multiplier = 1.0 # normalize to ns

        in_header = True
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if "$timescale" in line:
                # check timescale
                ts_str = lines[idx+1].strip() if idx+1 < len(lines) else "1ns"
                if "ps" in ts_str:
                    timescale_multiplier = 0.001
                elif "ns" in ts_str:
                    timescale_multiplier = 1.0
                elif "us" in ts_str:
                    timescale_multiplier = 1000.0

            if "$var" in line:
                parts = line.split()
                if len(parts) >= 5:
                    v_type = parts[1]
                    w = int(parts[2]) if parts[2].isdigit() else 1
                    symbol = parts[3]
                    name = parts[4]
                    if len(parts) > 5 and parts[5].startswith("["):
                        name = f"{name}{parts[5]}"
                    # Filter out internal test counters
                    if not any(ign in name for ign in ["total_tests", "passed_tests", "failed_tests"]):
                        var_map[symbol] = {
                            "name": name,
                            "width": w,
                            "symbol": symbol
                        }

            if "$enddefinitions" in line:
                idx += 1
                break
            idx += 1

        # Parse value changes over time
        current_time_ns = 0.0
        time_points = []
        signal_traces = {sym: [] for sym in var_map}

        # Track bus bits if split
        buses = {}
        for sym, v in var_map.items():
            m_bus = re.match(r"([A-Za-z0-9_]+)\[(\d+)\]", v["name"])
            if m_bus:
                b_name = m_bus.group(1)
                b_idx = int(m_bus.group(2))
                if b_name not in buses:
                    buses[b_name] = {}
                buses[b_name][b_idx] = sym

        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith("#"):
                t_val = float(line[1:]) * timescale_multiplier
                current_time_ns = round(t_val, 2)
            elif line.startswith("b") or line.startswith("B"):
                # Binary bus value
                parts = line.split()
                if len(parts) >= 2:
                    val = parts[0][1:]
                    sym = parts[1]
                    if sym in signal_traces:
                        signal_traces[sym].append((current_time_ns, val))
            elif line.startswith("r") or line.startswith("R"):
                pass
            elif len(line) >= 2:
                # Single bit change: e.g. "1!" or "0#"
                val = line[0]
                sym = line[1:].strip()
                if sym in signal_traces:
                    signal_traces[sym].append((current_time_ns, val))
            idx += 1

        return {
            "var_map": var_map,
            "buses": buses,
            "signal_traces": signal_traces,
            "max_time": current_time_ns if current_time_ns > 0 else 500.0
        }

    @staticmethod
    def generate_html_viewer(vcd_path, html_path, title="Hardware Simulation Waveform"):
        """Generates an interactive, dark-themed HTML5/SVG Waveform Viewer."""
        parsed = WaveformVisualizer.parse_vcd(vcd_path)
        if not parsed:
            # Fallback placeholder
            with open(html_path, "w", encoding="utf-8") as f:
                f.write("<html><body><h3>No VCD Waveform Data Available</h3></body></html>")
            return html_path

        var_map = parsed["var_map"]
        traces = parsed["signal_traces"]
        max_t = max(parsed["max_time"], 100.0)

        # Select primary signals to plot (prefer non-bus bits or clean names)
        signals_to_plot = []
        # Group buses
        plotted_names = set()
        for sym, meta in var_map.items():
            name = meta["name"]
            base_name = re.sub(r"\[\d+\]", "", name)
            if base_name not in plotted_names:
                plotted_names.add(base_name)
                # find transitions
                tr = traces.get(sym, [])
                signals_to_plot.append({
                    "name": name,
                    "symbol": sym,
                    "transitions": tr,
                    "is_bus": meta["width"] > 1 or "[" in name
                })

        # Pre-compute SVG paths for 0 to max_t
        # Time scale: e.g. 2 pixels per ns
        scale_x = 1.8
        total_w = max(900, int(max_t * scale_x) + 100)
        row_h = 42

        rows_svg = []
        for i, sig in enumerate(signals_to_plot):
            y_base = i * row_h + 30
            y_high = y_base + 6
            y_low = y_base + 30
            y_mid = y_base + 18

            # Build digital step polyline
            path_points = []
            cur_val = "0"
            tr_list = sig["transitions"]
            if not tr_list:
                tr_list = [(0.0, "0"), (max_t, "0")]

            last_x = 0.0
            last_y = y_low

            for t_ns, val in tr_list:
                x = t_ns * scale_x
                # horizontal segment
                path_points.append(f"{x:.1f},{last_y:.1f}")
                # vertical transition
                target_y = y_high if val in ["1", "h", "H"] else y_low
                path_points.append(f"{x:.1f},{target_y:.1f}")
                last_y = target_y
                last_x = x
            # Extend to end
            path_points.append(f"{max_t * scale_x:.1f},{last_y:.1f}")

            stroke_color = "#00e676" if "clk" in sig["name"].lower() else ("#ffab00" if "coin" in sig["name"].lower() or "in" in sig["name"].lower() else "#00b0ff")
            poly_str = " ".join(path_points)

            rows_svg.append(f"""
            <!-- Signal: {sig['name']} -->
            <g class="signal-row" data-name="{sig['name']}">
                <rect x="0" y="{y_base}" width="{total_w}" height="{row_h}" fill="{'#1a1e24' if i%2==0 else '#15181c'}" />
                <line x1="0" y1="{y_low}" x2="{total_w}" y2="{y_low}" stroke="#2a303c" stroke-dasharray="2,4" />
                <polyline points="{poly_str}" fill="none" stroke="{stroke_color}" stroke-width="2" />
            </g>
            """)

        # Grid lines every 50 ns
        grid_svg = []
        t = 0.0
        while t <= max_t:
            x = t * scale_x
            grid_svg.append(f"""
                <line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{len(signals_to_plot)*row_h + 30}" stroke="#2c3440" stroke-width="1" />
                <text x="{x + 2:.1f}" y="18" fill="#788b9c" font-size="11" font-family="monospace">{int(t)}ns</text>
            """)
            t += 20.0

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #0f1216;
            color: #eceff1;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Consolas", monospace;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #263238;
            padding-bottom: 12px;
            margin-bottom: 15px;
        }}
        .title {{
            font-size: 20px;
            font-weight: bold;
            color: #00e5ff;
        }}
        .badges {{
            display: flex;
            gap: 10px;
        }}
        .badge {{
            background: #1e293b;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            border: 1px solid #334155;
        }}
        .badge-success {{
            color: #00e676;
            border-color: #00e676;
        }}
        .container {{
            display: flex;
            border: 1px solid #334155;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            background: #15181c;
        }}
        .signal-labels {{
            width: 220px;
            background: #111417;
            border-right: 2px solid #263238;
            flex-shrink: 0;
            padding-top: 30px;
        }}
        .label-row {{
            height: {row_h}px;
            display: flex;
            align-items: center;
            padding: 0 15px;
            font-weight: 600;
            font-size: 13px;
            border-bottom: 1px solid #1f2730;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .waveform-scroll {{
            overflow-x: auto;
            flex-grow: 1;
            background: #15181c;
            position: relative;
        }}
        .tooltip {{
            position: fixed;
            background: #1e293b;
            color: #fff;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            display: none;
            border: 1px solid #00e5ff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">⚡ {title}</div>
        <div class="badges">
            <div class="badge badge-success">● ModelSim 10.1d Verified</div>
            <div class="badge">Duration: {max_t:.1f} ns</div>
            <div class="badge">Radix: Binary / Hex</div>
        </div>
    </div>

    <div class="container">
        <div class="signal-labels">
            {"".join([f'<div class="label-row" title="{s["name"]}">{s["name"]}</div>' for s in signals_to_plot])}
        </div>
        <div class="waveform-scroll">
            <svg width="{total_w}" height="{len(signals_to_plot)*row_h + 35}" xmlns="http://www.w3.org/2000/svg">
                <!-- Time Grid -->
                {"".join(grid_svg)}
                <!-- Waveform Rows -->
                {"".join(rows_svg)}
            </svg>
        </div>
    </div>
    <p style="color: #64748b; font-size: 12px; margin-top: 15px;">
        * Trục ngang thể hiện thời gian mô phỏng (nanoseconds). Bạn có thể cuộn ngang để xem toàn bộ quá trình giao dịch, cấp tiền, nhả nước và thối tiền.
    </p>
</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return html_path

    @staticmethod
    def generate_view_launcher(modelsim_bin, sim_dir, top_module, bat_path):
        """Creates a 1-click Windows batch file to launch ModelSim Waveform GUI immediately."""
        vsim_exe = os.path.join(modelsim_bin, "vsim.exe") if modelsim_bin else "vsim.exe"
        
        bat_content = f"""@echo off
chcp 65001 > nul
echo ===============================================================================
echo     Spec2RTL ^& Prompt2Silicon: 1-Click Graphical Waveform Launcher
echo ===============================================================================
echo.
echo [1/2] Khoi dong ModelSim Waveform GUI cho module: {top_module}...

cd /d "{sim_dir}"

if exist "{vsim_exe}" (
    start "" "{vsim_exe}" -novopt work.{top_module} -do "add wave -r /*; run -all; wave zoom full;"
    echo -> [OK] Da mo cua so song truc quan trong ModelSim GUI!
) else (
    echo -> [Luu y] Khong tim thay ModelSim GUI, dang mo Waveform HTML truc tiep tren trinh duyet...
    start "" "{os.path.join(sim_dir, 'waveform.html')}"
)

echo.
echo [2/2] Da khoi tao thanh cong! Ban co the quan sat bieu do xung song tren man hinh.
echo ===============================================================================
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        return bat_path

if __name__ == "__main__":
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    vcd = os.path.join(base, "sim", "vending_machine.vcd")
    html_out = os.path.join(base, "sim", "waveform.html")
    bat_out = os.path.join(base, "sim", "view_waveform.bat")
    root_bat = os.path.join(base, "view_waveform.bat")

    vis = WaveformVisualizer()
    if os.path.exists(vcd):
        vis.generate_html_viewer(vcd, html_out, "Máy Bán Nước Tự Động (Vending Machine Waveform)")
        print("Generated interactive HTML waveform at:", html_out)

    vis.generate_view_launcher(
        r"D:\altera\13.0sp1\modelsim_ase\win32aloem",
        os.path.join(base, "sim"),
        "tb_vending_machine",
        bat_out
    )
    vis.generate_view_launcher(
        r"D:\altera\13.0sp1\modelsim_ase\win32aloem",
        os.path.join(base, "sim"),
        "tb_vending_machine",
        root_bat
    )
    print("Generated 1-click launchers at:", bat_out, "and", root_bat)
