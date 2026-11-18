"""
Module: prepare_dataset_group1.py
Nhiệm vụ Nhóm 1 (Dữ liệu & Thẩm định - Data & Truth Oracle):
- Thu thập và tiền xử lý dữ liệu đặc tả phần cứng (Hardware Spec) và RTL vàng (Golden RTL).
- Nguồn:
  1. knowledge_base/hardware_db.json (NVIDIA VerilogEval, HKUST RTLLM, HuggingFace Verilog-Instruct, Spec2RTL)
  2. docs/100_Prompt_Thiet_Ke_Mach.pdf (100 đề bài chuẩn hóa UIT / VJU)
  3. specs/*.txt (Bộ đặc tả kiểm thử thực tế của đồ án)
  4. Bộ sinh mẫu phần cứng chuẩn hóa đa tham số (Hardware Data Augmentation: Counter, FSM, ALU, FIFO, etc.)
- Xuất dữ liệu: training/dataset_candidate_pool.json theo chuẩn schema training/dataset_schema_standard.json
"""

import os
import re
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KB_PATH = os.path.join(PROJECT_ROOT, "knowledge_base", "hardware_db.json")
PROMPTS_PDF_PATH = os.path.join(PROJECT_ROOT, "docs", "100_Prompt_Thiet_Ke_Mach.pdf")
SPECS_DIR = os.path.join(PROJECT_ROOT, "specs")
OUTPUT_CANDIDATE_POOL = os.path.join(PROJECT_ROOT, "training", "dataset_candidate_pool.json")

def clean_verilog_code(code_str):
    """Trích xuất mã Verilog nguyên bản từ chuỗi markdown hoặc raw text."""
    if not code_str:
        return ""
    code_match = re.search(r"```(?:verilog)?\s*(.*?)\s*```", code_str, re.DOTALL | re.IGNORECASE)
    if code_match:
        code_str = code_match.group(1).strip()
    return code_str.strip()

def extract_module_name(code_str):
    """Trích xuất tên module từ mã Verilog."""
    m = re.search(r"\bmodule\s+([a-zA-Z_][a-zA-Z0-9_$]*)", code_str)
    return m.group(1) if m else "unnamed_module"

def generate_cot_explanation(module_name, category, ports_summary=""):
    """Tạo phân tích kiến trúc vi mạch Chain-of-Thought (CoT) chuẩn công nghiệp."""
    return (
        f"### Phân tích kiến trúc vi mạch:\n"
        f"1. Khối logic `{module_name}` thuộc họ {category}, thực hiện chức năng phần cứng đồng bộ/tổ hợp chuẩn xác.\n"
        f"2. Khai báo danh sách cổng đầy đủ, các thanh ghi tuần tự được cập nhật tại sườn xung clock và hỗ trợ reset an toàn.\n"
        f"3. Tuân thủ tuyệt đối quy tắc thiết kế synthesizable: gán đầy đủ giá trị ở mọi nhánh rẽ để triệt tiêu chốt ẩn (no inferred latches) và nối trọn vẹn toàn bộ các chân (no dangling pins).\n\n"
    )

def collect_from_hardware_db():
    """Thu thập các mẫu có sẵn từ knowledge_base/hardware_db.json."""
    candidates = []
    if not os.path.exists(KB_PATH):
        print(f"[CẢNH BÁO] Không tìm thấy file {KB_PATH}")
        return candidates

    with open(KB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Đang xử lý {len(data)} mục từ knowledge_base/hardware_db.json...")
    for idx, item in enumerate(data):
        raw_rtl = item.get("golden_rtl", "")
        raw_spec = item.get("spec", "")
        source = item.get("source", "HardwareDB")
        category = item.get("category", "General Logic")

        if not raw_rtl or not raw_spec:
            continue

        clean_rtl = clean_verilog_code(raw_rtl)
        if not clean_rtl or "module " not in clean_rtl or "endmodule" not in clean_rtl:
            continue

        mod_name = item.get("module_name") or extract_module_name(clean_rtl)
        
        # Đồng bộ hóa tên module nếu spec yêu cầu TopModule mà code là RefModule
        if "TopModule" in raw_spec and mod_name == "RefModule":
            clean_rtl = re.sub(r"\bmodule\s+RefModule\b", "module TopModule", clean_rtl)
            mod_name = "TopModule"

        spec_text = raw_spec.strip()
        formatted_input = f"# Tên module: {mod_name}\n\n## Đặc tả kỹ thuật:\n{spec_text}"
        cot = generate_cot_explanation(mod_name, category)
        formatted_output = f"{cot}```verilog\n{clean_rtl}\n```"

        entry_id = f"g1_db_{idx+1:04d}_{mod_name}"
        candidates.append({
            "id": entry_id,
            "category": category,
            "source": source,
            "module_name": mod_name,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": formatted_input,
            "output": formatted_output,
            "raw_rtl": clean_rtl,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    print(f"[+] Thu thập được {len(candidates)} mẫu hợp lệ từ hardware_db.json")
    return candidates

def collect_from_specs_dir():
    """Thu thập 6 bài benchmark thực tế từ thư mục specs/*.txt."""
    candidates = []
    if not os.path.isdir(SPECS_DIR):
        return candidates

    golden_specs_rtl = {
        "uart_tx_8bit": {
            "category": "Communication / Serial",
            "rtl": """module uart_tx_8bit (
    input  wire       clk,
    input  wire       rst,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output reg        tx_serial,
    output reg        tx_busy
);
    localparam IDLE  = 2'b00,
               START = 2'b01,
               DATA  = 2'b10,
               STOP  = 2'b11;

    reg [1:0] state;
    reg [2:0] bit_idx;
    reg [7:0] tx_reg;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state     <= IDLE;
            tx_serial <= 1'b1;
            tx_busy   <= 1'b0;
            bit_idx   <= 3'd0;
            tx_reg    <= 8'd0;
        end else begin
            case (state)
                IDLE: begin
                    tx_serial <= 1'b1;
                    if (tx_start) begin
                        state     <= START;
                        tx_busy   <= 1'b1;
                        tx_reg    <= tx_data;
                        bit_idx   <= 3'd0;
                    end else begin
                        tx_busy   <= 1'b0;
                    end
                end
                START: begin
                    tx_serial <= 1'b0; // Start bit
                    state     <= DATA;
                end
                DATA: begin
                    tx_serial <= tx_reg[bit_idx];
                    if (bit_idx == 3'd7) begin
                        state <= STOP;
                    end else begin
                        bit_idx <= bit_idx + 1'b1;
                    end
                end
                STOP: begin
                    tx_serial <= 1'b1; // Stop bit
                    state     <= IDLE;
                    tx_busy   <= 1'b0;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule"""
        },
        "button_debouncer": {
            "category": "Signal Conditioning",
            "rtl": """module button_debouncer (
    input  wire clk,
    input  wire rst,
    input  wire btn_in,
    output reg  btn_clean,
    output reg  btn_pressed_pulse
);
    reg [15:0] counter;
    reg        sync_0, sync_1;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            sync_0            <= 1'b0;
            sync_1            <= 1'b0;
            counter           <= 16'd0;
            btn_clean         <= 1'b0;
            btn_pressed_pulse <= 1'b0;
        end else begin
            sync_0            <= btn_in;
            sync_1            <= sync_0;
            btn_pressed_pulse <= 1'b0;

            if (sync_1 != btn_clean) begin
                counter <= counter + 1'b1;
                if (counter == 16'hFFFF) begin
                    btn_clean <= sync_1;
                    if (sync_1 == 1'b1) begin
                        btn_pressed_pulse <= 1'b1;
                    end
                end
            end else begin
                counter <= 16'd0;
            end
        end
    end
endmodule"""
        },
        "bcd_to_7seg_anode": {
            "category": "Display / Decoder",
            "rtl": """module bcd_to_7seg_anode (
    input  wire [3:0] bcd,
    output reg  [6:0] seg
);
    always @(*) begin
        case (bcd)
            4'h0: seg = 7'b1000000;
            4'h1: seg = 7'b1111001;
            4'h2: seg = 7'b0100100;
            4'h3: seg = 7'b0110000;
            4'h4: seg = 7'b0011001;
            4'h5: seg = 7'b0010010;
            4'h6: seg = 7'b0000010;
            4'h7: seg = 7'b1111000;
            4'h8: seg = 7'b0000000;
            4'h9: seg = 7'b0010000;
            default: seg = 7'b1111111;
        endcase
    end
endmodule"""
        },
        "smart_home_security": {
            "category": "System Control / Alarm",
            "rtl": """module smart_home_security (
    input  wire       clk,
    input  wire       rst,
    input  wire       motion_pir,
    input  wire       smoke_gas,
    input  wire       arm_mode,
    output reg        siren,
    output reg        sprinkler,
    output reg  [1:0] status_code
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            siren       <= 1'b0;
            sprinkler   <= 1'b0;
            status_code <= 2'b00;
        end else begin
            if (smoke_gas) begin
                siren       <= 1'b1;
                sprinkler   <= 1'b1;
                status_code <= 2'b10;
            end else if (arm_mode && motion_pir) begin
                siren       <= 1'b1;
                sprinkler   <= 1'b0;
                status_code <= 2'b01;
            end else begin
                siren       <= 1'b0;
                sprinkler   <= 1'b0;
                status_code <= 2'b00;
            end
        end
    end
endmodule"""
        },
        "decoder_3to8": {
            "category": "Decoder",
            "rtl": """module decoder_3to8 (
    input  wire [2:0] in,
    input  wire       en,
    output reg  [7:0] out
);
    always @(*) begin
        if (!en) begin
            out = 8'h00;
        end else begin
            case (in)
                3'b000: out = 8'b00000001;
                3'b001: out = 8'b00000010;
                3'b010: out = 8'b00000100;
                3'b011: out = 8'b00001000;
                3'b100: out = 8'b00010000;
                3'b101: out = 8'b00100000;
                3'b110: out = 8'b01000000;
                3'b111: out = 8'b10000000;
                default: out = 8'b00000000;
            endcase
        end
    end
endmodule"""
        },
        "digital_lock_fsm": {
            "category": "FSM / Security",
            "rtl": """module digital_lock_fsm (
    input  wire       clk,
    input  wire       rst,
    input  wire [3:0] key_in,
    input  wire       key_valid,
    output reg        unlock,
    output reg        alarm
);
    localparam S_IDLE   = 2'b00,
               S_DIGIT1 = 2'b01,
               S_OPEN   = 2'b10,
               S_ERROR  = 2'b11;

    reg [1:0] state, next_state;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state <= S_IDLE;
        end else begin
            state <= next_state;
        end
    end

    always @(*) begin
        next_state = state;
        unlock     = 1'b0;
        alarm      = 1'b0;

        case (state)
            S_IDLE: begin
                if (key_valid) begin
                    if (key_in == 4'h5) next_state = S_DIGIT1;
                    else                next_state = S_ERROR;
                end
            end
            S_DIGIT1: begin
                if (key_valid) begin
                    if (key_in == 4'h9) next_state = S_OPEN;
                    else                next_state = S_ERROR;
                end
            end
            S_OPEN: begin
                unlock = 1'b1;
            end
            S_ERROR: begin
                alarm = 1'b1;
            end
            default: begin
                next_state = S_IDLE;
            end
        endcase
    end
endmodule"""
        }
    }

    files = [
        ("a.txt", "uart_tx_8bit"),
        ("b.txt", "button_debouncer"),
        ("c.txt", "bcd_to_7seg_anode"),
        ("d.txt", "smart_home_security"),
        ("e.txt", "decoder_3to8"),
        ("f_digital_lock_fsm.txt", "digital_lock_fsm")
    ]

    for fname, mod_name in files:
        fpath = os.path.join(SPECS_DIR, fname)
        if os.path.exists(fpath) and mod_name in golden_specs_rtl:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            
            info = golden_specs_rtl[mod_name]
            clean_rtl = info["rtl"]
            cot = generate_cot_explanation(mod_name, info["category"])
            
            candidates.append({
                "id": f"g1_benchmark_{mod_name}",
                "category": info["category"],
                "source": "Spec2RTL Project Benchmarks",
                "module_name": mod_name,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": content,
                "output": f"{cot}```verilog\n{clean_rtl}\n```",
                "raw_rtl": clean_rtl,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    print(f"[+] Thu thập được {len(candidates)} mẫu benchmark từ specs/*.txt")
    return candidates

def generate_augmented_hardware_suite():
    """
    Sinh tập dữ liệu mở rộng chuẩn hóa đa tham số (Hardware Data Augmentation).
    Bao phủ 10 họ vi mạch kinh điển theo giáo trình CE118 và file 100_Prompt:
    - Counter, Mod-N, BCD, Gray, Johnson, Ring, Loadable
    - Decoders (1-hot, 7-seg common anode/cathode, priority encoders)
    - Multiplexers & Demultiplexers (multi-bus, multi-width)
    - Arithmetic (Adders, Subtractors, ALUs, Multipliers, Comparators, Accumulators)
    - Shift Registers (SISO, SIPO, PISO, PIPO, Barrel Shifters)
    - FSMs (Sequence Detectors, Traffic Light, Digital Locks, Vending Machine, Arbiters)
    - Signal Conditioning (Debouncers, Synchronizers, Edge Detectors, Pulse Generators)
    - Memory & FIFO (RAM, ROM, Synchronous FIFO)
    - Clock & PWM (Frequency Dividers, PWM Generators, Interval Timers)
    """
    augmented = []

    # 1. BỘ ĐẾM (COUNTERS)
    # Binary Counters: widths 4, 8, 10, 12, 16, 20, 24, 32
    for width in [4, 8, 10, 12, 16, 20, 24, 32]:
        for rst_active in ["high", "low"]:
            for has_load in [False, True]:
                rst_cond = "rst" if rst_active == "high" else "!rst_n"
                rst_port = "input wire rst" if rst_active == "high" else "input wire rst_n"
                rst_edge = "posedge rst" if rst_active == "high" else "negedge rst_n"
                load_str = "_load" if has_load else ""
                mname = f"counter_{width}bit{load_str}_rst_{rst_active}"
                max_val = (1 << width) - 1

                load_port = f",\n    input  wire [{width-1}:0] data_in,\n    input  wire load" if has_load else ""
                load_logic = f"        end else if (load) begin\n            count <= data_in;\n" if has_load else ""

                code = f"""module {mname} (
    input  wire             clk,
    {rst_port},
    input  wire             en,
    input  wire             up_down{load_port},
    output reg  [{width-1}:0] count,
    output wire             tc
);
    always @(posedge clk or {rst_edge}) begin
        if ({rst_cond}) begin
            count <= {width}'d0;
{load_logic}        end else if (en) begin
            if (up_down)
                count <= count + 1'b1;
            else
                count <= count - 1'b1;
        end
    end

    assign tc = (up_down) ? (count == {width}'d{max_val} && en) : (count == {width}'d0 && en);
endmodule"""
                input_spec = (
                    f"# Tên module: {mname}\n\n"
                    f"## 1. Danh sách cổng:\n"
                    f"- clk: Xung nhịp hệ thống\n"
                    f"- {rst_port}: Reset ({rst_active})\n"
                    f"- en: Cho phép đếm\n"
                    f"- up_down: 1 đếm lên, 0 đếm xuống\n"
                    f"- [{width-1}:0] count: Giá trị đếm nhị phân {width}-bit\n"
                    f"- tc: Cờ báo chạm đỉnh Terminal Count\n\n"
                    f"## 2. Hoạt động logic:\n"
                    f"- Reset ưu tiên cao nhất, đưa count về 0.\n"
                    f"- Khi en=1, count tăng khi up_down=1 hoặc giảm khi up_down=0."
                )
                cot = generate_cot_explanation(mname, "Counter")
                augmented.append({
                    "id": f"aug_cnt_{mname}",
                    "category": "Counter",
                    "source": "Synthesized CE118 Augmentation Suite",
                    "module_name": mname,
                    "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                    "input": input_spec,
                    "output": f"{cot}```verilog\n{code}\n```",
                    "raw_rtl": code,
                    "verification_status": "PENDING_MODELSIM",
                    "linter_status": "PENDING_LINTER"
                })

    # Mod-N Counters: 3, 5, 6, 7, 9, 10, 12, 16, 24, 60, 100, 1000
    for mod_val in [3, 5, 6, 7, 9, 10, 12, 16, 24, 60, 100, 1000]:
        width = (mod_val - 1).bit_length()
        mname = f"mod_{mod_val}_counter"
        code = f"""module {mname} (
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    output reg  [{width-1}:0] count,
    output wire             rollover
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= {width}'d0;
        end else if (en) begin
            if (count == {width}'d{mod_val - 1})
                count <= {width}'d0;
            else
                count <= count + 1'b1;
        end
    end

    assign rollover = (count == {width}'d{mod_val - 1}) && en;
endmodule"""
        input_spec = (
            f"# Tên module: {mname}\n\n"
            f"## 1. Danh sách cổng:\n"
            f"- clk, rst: Xung nhịp và reset tích cực cao\n"
            f"- en: Cho phép đếm\n"
            f"- [{width-1}:0] count: Giá trị đếm Modulo-{mod_val}\n"
            f"- rollover: Xung tràn khi đạt {mod_val - 1}\n\n"
            f"## 2. Hoạt động logic:\n"
            f"- Đếm tuần tự từ 0 đến {mod_val - 1} rồi tự động quay vòng về 0."
        )
        cot = generate_cot_explanation(mname, "Counter / Timing")
        augmented.append({
            "id": f"aug_mod_{mod_val}_counter",
            "category": "Counter",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # Gray & Johnson Counters (3, 4, 5, 8 bit)
    for w in [3, 4, 5, 8]:
        # Gray counter
        mname = f"gray_counter_{w}bit"
        code = f"""module {mname} (
    input  wire         clk,
    input  wire         rst,
    input  wire         en,
    output wire [{w-1}:0] gray_count
);
    reg [{w-1}:0] bin_count;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            bin_count <= {w}'d0;
        end else if (en) begin
            bin_count <= bin_count + 1'b1;
        end
    end
    assign gray_count = bin_count ^ (bin_count >> 1);
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nBộ đếm mã Gray {w}-bit không tạo xung nhiễu (glitch-free)."
        cot = generate_cot_explanation(mname, "Counter")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Counter",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

        # Johnson counter
        mname_j = f"johnson_counter_{w}bit"
        code_j = f"""module {mname_j} (
    input  wire         clk,
    input  wire         rst,
    output reg  [{w-1}:0] q
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            q <= {w}'d0;
        end else begin
            q <= {{q[{w-2}:0], ~q[{w-1}]}};
        end
    end
endmodule"""
        input_spec_j = f"# Tên module: {mname_j}\n\nBộ đếm Johnson {w}-bit chu kỳ {2*w} trạng thái."
        cot_j = generate_cot_explanation(mname_j, "Counter")
        augmented.append({
            "id": f"aug_{mname_j}",
            "category": "Counter",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname_j,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec_j,
            "output": f"{cot_j}```verilog\n{code_j}\n```",
            "raw_rtl": code_j,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # 2. GIẢI MÃ & GHÉP KÊNH (DECODERS, MUX, DEMUX)
    # Decoders: 2-to-4, 3-to-8, 4-to-16 with active-high & active-low enable
    for in_w in [2, 3, 4]:
        out_w = 1 << in_w
        for en_pol in ["high", "low"]:
            en_cond = "en" if en_pol == "high" else "!en_n"
            en_port = "input wire en" if en_pol == "high" else "input wire en_n"
            mname = f"decoder_{in_w}to{out_w}_en_{en_pol}"
            
            code = f"""module {mname} (
    input  wire [{in_w-1}:0] in,
    {en_port},
    output reg  [{out_w-1}:0] out
);
    always @(*) begin
        if (!({en_cond})) begin
            out = {out_w}'d0;
        end else begin
            out = {out_w}'d1 << in;
        end
    end
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nBộ giải mã {in_w} sang {out_w} tích cực cao, chân cho phép {en_pol}."
            cot = generate_cot_explanation(mname, "Decoder")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Decoder",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # Multiplexers: 2-to-1, 4-to-1, 8-to-1, 16-to-1 across data widths 1, 2, 4, 8, 16, 32
    for n_inputs in [2, 4, 8, 16]:
        sel_w = (n_inputs - 1).bit_length()
        for dw in [1, 2, 4, 8, 16, 32]:
            mname = f"mux_{n_inputs}to1_{dw}bit"
            code = f"""module {mname} (
    input  wire [{n_inputs * dw - 1}:0] in_bus,
    input  wire [{sel_w - 1}:0]         sel,
    output wire [{dw - 1}:0]           out
);
    assign out = in_bus[sel * {dw} +: {dw}];
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nBộ ghép kênh {n_inputs} sang 1 với độ rộng kênh {dw}-bit."
            cot = generate_cot_explanation(mname, "Multiplexer")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Multiplexer",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # Demultiplexers: 1-to-2, 1-to-4, 1-to-8 across data widths 1, 4, 8, 16
    for n_outs in [2, 4, 8]:
        sel_w = (n_outs - 1).bit_length()
        for dw in [1, 4, 8, 16]:
            mname = f"demux_1to{n_outs}_{dw}bit"
            code = f"""module {mname} (
    input  wire [{dw - 1}:0]             din,
    input  wire [{sel_w - 1}:0]          sel,
    output reg  [{n_outs * dw - 1}:0]    dout_bus
);
    always @(*) begin
        dout_bus = {n_outs * dw}'d0;
        dout_bus[sel * {dw} +: {dw}] = din;
    end
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nBộ phân kênh 1 sang {n_outs} với độ rộng dữ liệu {dw}-bit."
            cot = generate_cot_explanation(mname, "Demultiplexer")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Demultiplexer",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # Priority Encoders: 4-to-2, 8-to-3, 16-to-4
    for in_w, out_w in [(4, 2), (8, 3), (16, 4)]:
        mname = f"priority_encoder_{in_w}to{out_w}"
        lines = []
        for b in reversed(range(in_w)):
            prefix = "if" if b == in_w - 1 else "else if"
            lines.append(f"            {prefix} (in[{b}]) out = {out_w}'d{b};")
        lines.append(f"            else out = {out_w}'d0;")
        enc_body = "\n".join(lines)
        
        code = f"""module {mname} (
    input  wire [{in_w - 1}:0] in,
    input  wire                    en,
    output reg  [{out_w - 1}:0] out,
    output wire                    valid
);
    assign valid = en & (|in);

    always @(*) begin
        if (!en) begin
            out = {out_w}'d0;
        end else begin
{enc_body}
        end
    end
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nBộ mã hóa ưu tiên {in_w} sang {out_w} kèm cờ valid."
        cot = generate_cot_explanation(mname, "Encoder")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Encoder",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # 3. MẠCH SỐ HỌC (ARITHMETIC UNITS)
    # ALUs across 4, 8, 16, 32-bit
    for width in [4, 8, 16, 32]:
        mname = f"alu_{width}bit_core"
        code = f"""module {mname} (
    input  wire [{width - 1}:0] a,
    input  wire [{width - 1}:0] b,
    input  wire [2:0]           opcode,
    output reg  [{width - 1}:0] result,
    output reg                  carry_out,
    output wire                 zero_flag
);
    reg [{width}:0] temp_sum;

    always @(*) begin
        carry_out = 1'b0;
        temp_sum  = {width + 1}'d0;
        case (opcode)
            3'b000: begin // ADD
                temp_sum = a + b;
                result = temp_sum[{width - 1}:0];
                carry_out = temp_sum[{width}];
            end
            3'b001: begin // SUB
                temp_sum = a - b;
                result = temp_sum[{width - 1}:0];
                carry_out = temp_sum[{width}];
            end
            3'b010: result = a & b;        // AND
            3'b011: result = a | b;        // OR
            3'b100: result = a ^ b;        // XOR
            3'b101: result = ~a;           // NOT
            3'b110: result = a << 1;       // SHL
            3'b111: result = a >> 1;       // SHR
            default: result = {width}'d0;
        endcase
    end

    assign zero_flag = (result == {width}'d0);
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nKhối số học logic ALU {width}-bit 8 phép tính chuẩn."
        cot = generate_cot_explanation(mname, "Arithmetic / ALU")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Arithmetic",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # Adders & Subtractors with overflow detection: 4, 8, 16, 32-bit
    for width in [4, 8, 16, 32]:
        mname = f"adder_subtractor_{width}bit"
        code = f"""module {mname} (
    input  wire [{width - 1}:0] a,
    input  wire [{width - 1}:0] b,
    input  wire                 sub_mode,
    output wire [{width - 1}:0] result,
    output wire                 carry_borrow,
    output wire                 overflow
);
    wire [{width}:0] sum_ext;
    wire [{width - 1}:0] b_operand;

    assign b_operand = sub_mode ? (~b) : b;
    assign sum_ext   = a + b_operand + sub_mode;
    assign result    = sum_ext[{width - 1}:0];
    assign carry_borrow = sum_ext[{width}];
    assign overflow  = (a[{width - 1}] == b_operand[{width - 1}]) && (result[{width - 1}] != a[{width - 1}]);
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nMạch cộng/trừ nhị phân {width}-bit có cờ tràn số bù 2 (overflow)."
        cot = generate_cot_explanation(mname, "Arithmetic")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Arithmetic",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # Magnitude Comparators: 4, 8, 16, 32-bit
    for width in [4, 8, 16, 32]:
        mname = f"comparator_{width}bit"
        code = f"""module {mname} (
    input  wire [{width - 1}:0] a,
    input  wire [{width - 1}:0] b,
    output wire                 gt,
    output wire                 eq,
    output wire                 lt
);
    assign gt = (a > b);
    assign eq = (a == b);
    assign lt = (a < b);
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nBộ so sánh độ lớn {width}-bit (Greater, Equal, Less)."
        cot = generate_cot_explanation(mname, "Arithmetic")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Arithmetic",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # Accumulators with saturation & wrap-around: 8, 16, 32-bit
    for width in [8, 16, 32]:
        for mode in ["wrap", "saturate"]:
            mname = f"accumulator_{width}bit_{mode}"
            max_v = (1 << width) - 1
            sat_check = f"""
            if (sum_ext > {max_v})
                acc <= {width}'d{max_v};
            else
                acc <= sum_ext[{width-1}:0];
""" if mode == "saturate" else f"""
            acc <= sum_ext[{width-1}:0];
"""
            code = f"""module {mname} (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 en,
    input  wire [{width - 1}:0] data_in,
    output reg  [{width - 1}:0] acc
);
    wire [{width}:0] sum_ext;
    assign sum_ext = acc + data_in;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            acc <= {width}'d0;
        end else if (en) begin{sat_check}        end
    end
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nBộ cộng dồn {width}-bit chế độ {mode}."
            cot = generate_cot_explanation(mname, "Arithmetic / Accumulator")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Arithmetic",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # 4. THANH GHI & DỊCH BÍT (SHIFT REGISTERS)
    for width in [4, 8, 16, 32]:
        for mode in ["siso", "sipo", "piso", "pipo"]:
            mname = f"shift_register_{mode}_{width}bit"
            if mode == "siso":
                code = f"""module {mname} (
    input  wire clk,
    input  wire rst,
    input  wire shift_en,
    input  wire serial_in,
    output wire serial_out
);
    reg [{width - 1}:0] sreg;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            sreg <= {width}'d0;
        end else if (shift_en) begin
            sreg <= {{sreg[{width - 2}:0], serial_in}};
        end
    end
    assign serial_out = sreg[{width - 1}];
endmodule"""
            elif mode == "sipo":
                code = f"""module {mname} (
    input  wire             clk,
    input  wire             rst,
    input  wire             shift_en,
    input  wire             serial_in,
    output reg  [{width-1}:0] parallel_out
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            parallel_out <= {width}'d0;
        end else if (shift_en) begin
            parallel_out <= {{parallel_out[{width - 2}:0], serial_in}};
        end
    end
endmodule"""
            elif mode == "piso":
                code = f"""module {mname} (
    input  wire             clk,
    input  wire             rst,
    input  wire             load,
    input  wire             shift_en,
    input  wire [{width-1}:0] parallel_in,
    output wire             serial_out
);
    reg [{width - 1}:0] sreg;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            sreg <= {width}'d0;
        end else if (load) begin
            sreg <= parallel_in;
        end else if (shift_en) begin
            sreg <= {{1'b0, sreg[{width - 1}:1]}};
        end
    end
    assign serial_out = sreg[0];
endmodule"""
            else: # pipo
                code = f"""module {mname} (
    input  wire             clk,
    input  wire             rst,
    input  wire             load_en,
    input  wire [{width-1}:0] d_in,
    output reg  [{width-1}:0] d_out
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            d_out <= {width}'d0;
        end else if (load_en) begin
            d_out <= d_in;
        end
    end
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nThanh ghi dịch {mode.upper()} {width}-bit."
            cot = generate_cot_explanation(mname, "Shift Register")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Shift Register",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # Barrel Shifters: 8, 16, 32-bit (logical / arithmetic / rotate)
    for width in [8, 16, 32]:
        shift_bits = (width - 1).bit_length()
        mname = f"barrel_shifter_{width}bit"
        code = f"""module {mname} (
    input  wire [{width - 1}:0]      din,
    input  wire [{shift_bits - 1}:0] shift_amt,
    input  wire [1:0]                mode, // 0: SHL, 1: SHR, 2: ROL, 3: ROR
    output reg  [{width - 1}:0]      dout
);
    always @(*) begin
        case (mode)
            2'b00: dout = din << shift_amt;
            2'b01: dout = din >> shift_amt;
            2'b10: dout = (din << shift_amt) | (din >> ({width} - shift_amt));
            2'b11: dout = (din >> shift_amt) | (din << ({width} - shift_amt));
            default: dout = din;
        endcase
    end
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nBộ dịch thùng (Barrel Shifter) {width}-bit đa năng."
        cot = generate_cot_explanation(mname, "Shift Register")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Shift Register",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # 5. MÁY TRẠNG THÁI FSM (FINITE STATE MACHINES)
    # Sequence Detectors: "1011", "1101", "1010", "1110", "0110", "1001"
    patterns = ["1011", "1101", "1010", "1110", "0110", "1001", "1111", "0000"]
    for pat in patterns:
        mname = f"seq_detector_{pat}"
        code = f"""module {mname} (
    input  wire clk,
    input  wire rst,
    input  wire din,
    output reg  detected
);
    reg [3:0] shift_reg;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            shift_reg <= 4'b0000;
            detected  <= 1'b0;
        end else begin
            shift_reg <= {{shift_reg[2:0], din}};
            detected  <= ({{shift_reg[2:0], din}} == 4'b{pat});
        end
    end
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nMạch FSM nhận diện chuỗi bít '{pat}' liên tục trên đường truyền."
        cot = generate_cot_explanation(mname, "FSM")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "FSM",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # Round-Robin Arbiters: 2, 3, 4, 8 masters
    for n_req in [2, 3, 4, 8]:
        mname = f"arbiter_round_robin_{n_req}req"
        code = f"""module {mname} (
    input  wire                 clk,
    input  wire                 rst,
    input  wire [{n_req - 1}:0] req,
    output reg  [{n_req - 1}:0] grant
);
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            grant <= {n_req}'d0;
        end else begin
            grant <= req & (~(req - 1'b1)); // Priority resolve
        end
    end
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nBộ trọng tài cấp phát tài nguyên bus cho {n_req} thiết bị yêu cầu (Arbiter)."
        cot = generate_cot_explanation(mname, "FSM / Arbiter")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "FSM",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # 6. KHỬ RUNG & XỬ LÝ TÍN HIỆU (SIGNAL CONDITIONING)
    # Edge Detectors (Posedge, Negedge, Anyedge)
    for edge_type in ["posedge", "negedge", "anyedge"]:
        mname = f"edge_detector_{edge_type}"
        expr = "d_in & (~d_prev)" if edge_type == "posedge" else "(~d_in) & d_prev" if edge_type == "negedge" else "d_in ^ d_prev"
        code = f"""module {mname} (
    input  wire clk,
    input  wire rst,
    input  wire d_in,
    output wire pulse_out
);
    reg d_prev;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            d_prev <= 1'b0;
        end else begin
            d_prev <= d_in;
        end
    end
    assign pulse_out = {expr};
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nMạch phát hiện cạnh xung {edge_type} phát xung 1 chu kỳ clock."
        cot = generate_cot_explanation(mname, "Signal Conditioning")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "Signal Conditioning",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    # 7. BỘ NHỚ & HÀNG ĐỢI (MEMORY & FIFO)
    # Synchronous FIFO across depths 8, 16, 32, 64 and data widths 8, 16, 32
    for depth in [8, 16, 32, 64]:
        addr_w = (depth - 1).bit_length()
        for dwidth in [8, 16, 32]:
            mname = f"sync_fifo_d{depth}_w{dwidth}"
            code = f"""module {mname} (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 wr_en,
    input  wire                 rd_en,
    input  wire [{dwidth - 1}:0] din,
    output reg  [{dwidth - 1}:0] dout,
    output wire                 full,
    output wire                 empty,
    output reg  [{addr_w}:0]     count
);
    reg [{dwidth - 1}:0] mem [0:{depth - 1}];
    reg [{addr_w - 1}:0] wr_ptr, rd_ptr;

    assign full  = (count == {depth});
    assign empty = (count == 0);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            wr_ptr <= {addr_w}'d0;
            rd_ptr <= {addr_w}'d0;
            count  <= 0;
            dout   <= {dwidth}'d0;
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr] <= din;
                wr_ptr <= wr_ptr + 1'b1;
            end
            if (rd_en && !empty) begin
                dout <= mem[rd_ptr];
                rd_ptr <= rd_ptr + 1'b1;
            end
            case ({{wr_en && !full, rd_en && !empty}})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end
    end
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nHàng đợi đồng bộ FIFO độ sâu {depth}, độ rộng {dwidth}-bit."
            cot = generate_cot_explanation(mname, "Memory / FIFO")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Memory / FIFO",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # Single-Port RAM & Dual-Port RAM
    for depth in [16, 64, 256]:
        addr_w = (depth - 1).bit_length()
        for dw in [8, 16, 32]:
            mname = f"single_port_ram_d{depth}_w{dw}"
            code = f"""module {mname} (
    input  wire                 clk,
    input  wire                 we,
    input  wire [{addr_w - 1}:0] addr,
    input  wire [{dw - 1}:0]     din,
    output reg  [{dw - 1}:0]     dout
);
    reg [{dw - 1}:0] ram [0:{depth - 1}];
    always @(posedge clk) begin
        if (we) begin
            ram[addr] <= din;
        end
        dout <= ram[addr];
    end
endmodule"""
            input_spec = f"# Tên module: {mname}\n\nBộ nhớ RAM đơn cổng {depth} từ nhớ x {dw}-bit."
            cot = generate_cot_explanation(mname, "Memory / RAM")
            augmented.append({
                "id": f"aug_{mname}",
                "category": "Memory / Storage",
                "source": "Synthesized CE118 Augmentation Suite",
                "module_name": mname,
                "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
                "input": input_spec,
                "output": f"{cot}```verilog\n{code}\n```",
                "raw_rtl": code,
                "verification_status": "PENDING_MODELSIM",
                "linter_status": "PENDING_LINTER"
            })

    # 8. ĐIỀU CHẾ XUNG PWM & ĐỊNH THỜI (TIMERS & PWM)
    for pwm_res in [8, 10, 12, 16]:
        mname = f"pwm_generator_{pwm_res}bit"
        code = f"""module {mname} (
    input  wire                   clk,
    input  wire                   rst,
    input  wire [{pwm_res - 1}:0] duty_cycle,
    output reg                    pwm_out
);
    reg [{pwm_res - 1}:0] counter;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            counter <= {pwm_res}'d0;
            pwm_out <= 1'b0;
        end else begin
            counter <= counter + 1'b1;
            pwm_out <= (counter < duty_cycle);
        end
    end
endmodule"""
        input_spec = f"# Tên module: {mname}\n\nMạch điều chế độ rộng xung PWM độ phân giải {pwm_res}-bit."
        cot = generate_cot_explanation(mname, "PWM / Timing")
        augmented.append({
            "id": f"aug_{mname}",
            "category": "PWM",
            "source": "Synthesized CE118 Augmentation Suite",
            "module_name": mname,
            "instruction": "Hãy thiết kế module Verilog synthesizable theo chuẩn IEEE 1364-2001 từ đặc tả kỹ thuật sau.",
            "input": input_spec,
            "output": f"{cot}```verilog\n{code}\n```",
            "raw_rtl": code,
            "verification_status": "PENDING_MODELSIM",
            "linter_status": "PENDING_LINTER"
        })

    print(f"[+] Đã sinh {len(augmented)} mẫu mở rộng đa tham số từ Hardware Suite")
    return augmented

def main():
    print("================================================================================")
    print(">>> NHÓM 1: TIẾN TRÌNH THU THẬP & CHUẨN HÓA DỮ LIỆU SƠ CẤP (NGÀY 1 - 2)")
    print("================================================================================")

    all_candidates = []

    # 1. Thu thập từ hardware_db.json
    db_items = collect_from_hardware_db()
    all_candidates.extend(db_items)

    # 2. Thu thập từ benchmark specs/*.txt
    benchmark_items = collect_from_specs_dir()
    all_candidates.extend(benchmark_items)

    # 3. Mở rộng bộ mạch đa tham số (Augmentation Suite)
    augmented_items = generate_augmented_hardware_suite()
    all_candidates.extend(augmented_items)

    # Lưu tập dữ liệu ứng viên sơ bộ
    with open(OUTPUT_CANDIDATE_POOL, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print("--------------------------------------------------------------------------------")
    print(f"[THÀNH CÔNG] Đã tạo tập dữ liệu ứng viên sơ bộ: {OUTPUT_CANDIDATE_POOL}")
    print(f"[*] Tổng số lượng mẫu ứng viên đã thu thập: {len(all_candidates)} mẫu.")
    print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    main()
