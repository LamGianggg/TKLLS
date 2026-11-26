"""
Module: benchmark_70_rag.py
Danh gia kha nang truy xuat tri thuc phan cung cho nhom 70% khoi ha tang pho thong
bang bo 28 truy van ngon ngu tu nhien (14 tieng Viet + 14 tieng Anh) co tinh ne tu khoa
va ten module, so sanh 3 che do chinh: `keyword` vs `bm25` vs `hybrid` (kem `vector` ablation).

Chi so do luong (Top-K = 3):
- Recall@1: Ty le truy van co ket qua dung ngay tai vi tri #1.
- Recall@3: Ty le truy van co ket qua dung nam trong Top-3.
- MRR (Mean Reciprocal Rank): Trung binh nghich dao hang (1/rank trong Top-3, 0 neu truot).
"""

import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")

if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from knowledge_matcher import KnowledgeMatcher, xoa_dau_tieng_viet


# Bo 28 truy van nhom 70% khoi ha tang pho thong (co tinh ne ten module / tu khoa truc tiep)
BENCHMARK_70_QUERIES = [
    {
        "id": "Q01",
        "family": "UART TX",
        "lang": "vi",
        "query": (
            "Mach truyen du lieu noi tiep bat dong bo 8 bit, tu dong goi bit khoi dau "
            "muc thap, 8 bit du lieu LSB truoc va bit dung muc cao ma khong can day xung nhip chung."
        ),
        "targets": ["uart_tx_8bit", "distill_pdf_051_uart_tx_8bit"],
    },
    {
        "id": "Q02",
        "family": "UART RX",
        "lang": "en",
        "query": (
            "Asynchronous serial receiver that samples an incoming single-wire bit stream, "
            "detects the falling start edge, reconstructs an 8-bit byte, and raises a valid strobe."
        ),
        "targets": ["uart_rx_8bit", "distill_pdf_052_uart_rx_8bit", "fsm_serial", "fsm_serialdata"],
    },
    {
        "id": "Q03",
        "family": "SPI Master",
        "lang": "vi",
        "query": (
            "Bo dieu khien truyen thong dong bo bon day phia chu dong phat xung clock, "
            "keo tin hieu chon chip xuong thap va trao doi song cong tung byte voi ngoai vi."
        ),
        "targets": ["spi_master_basic", "distill_pdf_054_spi_master_basic", "SPI_AD"],
    },
    {
        "id": "Q04",
        "family": "SPI Slave",
        "lang": "en",
        "query": (
            "Four-wire synchronous peripheral responder driven by an external clock and active-low "
            "chip select, shifting incoming bits from master while returning a preloaded byte."
        ),
        "targets": ["spi_slave_controller", "distill_pdf_053_spi_slave_controller"],
    },
    {
        "id": "Q05",
        "family": "I2C Bus",
        "lang": "en",
        "query": (
            "Two-wire bidirectional serial bus interface core with clock and data lines "
            "handling start/stop signaling and byte-level acknowledge handshake."
        ),
        "targets": ["instruct60k_body", "body"],
    },
    {
        "id": "Q06",
        "family": "Synchronous FIFO",
        "lang": "vi",
        "query": (
            "Bo nho dem hang doi vao truoc ra truoc dung chung mot mien xung nhip dong bo, "
            "co con tro doc ghi va hai co bao day hoac rong."
        ),
        "targets": [
            "fifo_syn_8x8",
            "fifo_syn",
            "distill_pdf_025_fifo_syn_8x8",
            "distill_extra_fifo_syn",
            "axi_protocol_converter_v2_1_b2s_simple_fifo",
        ],
    },
    {
        "id": "Q07",
        "family": "Asynchronous FIFO",
        "lang": "en",
        "query": (
            "Dual-clock elastic data queue bridging independent write and read clock domains "
            "safely with dual-port storage and empty/full status flags."
        ),
        "targets": [
            "asyn_fifo",
            "hkust_rtllm_asyn_fifo",
            "dual_port_RAM",
            "cvdp_agentic_async_fifo_compute_ram_application_0001",
            "cvdp_agentic_async_fifo_compute_ram_application_0006",
        ],
    },
    {
        "id": "Q08",
        "family": "Gray Counter",
        "lang": "vi",
        "query": (
            "Bo dem tuan tu 4 bit sao cho hai trang thai lien tiep chi doi dung mot bit duy nhat "
            "nham loai bo hien tuong gai logic khi truyen qua mien xung nhip khac."
        ),
        "targets": ["gray_counter_4bit", "distill_pdf_004_gray_counter_4bit"],
    },
    {
        "id": "Q09",
        "family": "BCD Counter",
        "lang": "vi",
        "query": (
            "Mach dem thap phan hai chu so tu 00 den 59 phuc vu hien thi giay dong ho so, "
            "tu quay ve 0 khi cham nguong 59."
        ),
        "targets": ["bcd_counter_59", "distill_pdf_003_bcd_counter_59", "countbcd", "bcd_ctr"],
    },
    {
        "id": "Q10",
        "family": "Up-Down Counter",
        "lang": "en",
        "query": (
            "Synchronous register that either increments by one or decrements by one "
            "on every clock edge depending on a direction control input."
        ),
        "targets": [
            "up_down_counter",
            "hkust_rtllm_up_down_counter",
            "binary_counter_4bit",
            "distill_pdf_001_binary_counter_4bit",
        ],
    },
    {
        "id": "Q11",
        "family": "Traffic Light FSM",
        "lang": "vi",
        "query": (
            "Bo dieu khien cot den ba mau tai giao lo tu luan phien pha dung, cho va di "
            "theo thoi gian dinh san kem nut xin qua duong cho khach bo hanh."
        ),
        "targets": [
            "traffic_light",
            "traffic_light_controller",
            "traffic_light_fsm",
            "hkust_rtllm_traffic_light",
            "distill_pdf_082_traffic_light_controller",
            "distill_extra_traffic_light_fsm",
        ],
    },
    {
        "id": "Q12",
        "family": "Vending Machine FSM",
        "lang": "vi",
        "query": (
            "May tu dong nha do uong sau khi nguoi dung nap du tong tien xu menh gia nho va lon, "
            "dong thoi tra lai tien du neu nap vuot muc."
        ),
        "targets": [
            "vending_machine",
            "local_vending_machine",
            "distill_pdf_081_vending_machine",
            "ticket_vending_fsm",
        ],
    },
    {
        "id": "Q13",
        "family": "Digital Lock FSM",
        "lang": "en",
        "query": (
            "Electronic security keypad controller verifying a multi-digit PIN sequence, "
            "opening the door on match and raising an alarm after consecutive wrong attempts."
        ),
        "targets": [
            "digital_lock_fsm",
            "digital_safe_lock",
            "distill_pdf_043_digital_safe_lock",
            "distill_extra_digital_lock_fsm",
        ],
    },
    {
        "id": "Q14",
        "family": "ALU",
        "lang": "en",
        "query": (
            "Combinational arithmetic and logic execution core taking two operands and an opcode "
            "to compute addition, subtraction, bitwise logic, shifts, and status flags."
        ),
        "targets": [
            "alu",
            "alu_4bit",
            "alu_8bit",
            "alu_core",
            "pdp1_alu",
            "hkust_rtllm_alu",
            "distill_pdf_016_alu_4bit",
            "distill_pdf_017_alu_8bit",
        ],
    },
    {
        "id": "Q15",
        "family": "Multiplier",
        "lang": "vi",
        "query": (
            "Mach tinh tich hai so nguyen nhi phan khong dau 8 bit cho ra ket qua rong 16 bit "
            "dung thuat toan dich va cong hoac ma hoa Booth."
        ),
        "targets": [
            "multiplier_8bit",
            "multi_8bit",
            "multi_booth_8bit",
            "multi_pipe_8bit",
            "multiplier_4bit",
            "multi_16bit",
        ],
    },
    {
        "id": "Q16",
        "family": "Divider",
        "lang": "en",
        "query": (
            "Integer division circuit computing quotient and remainder from dividend and divisor "
            "inputs using shift-and-subtract iterations."
        ),
        "targets": ["div_16bit", "radix2_div", "hkust_rtllm_div_16bit", "hkust_rtllm_radix2_div"],
    },
    {
        "id": "Q17",
        "family": "PWM Generator",
        "lang": "vi",
        "query": (
            "Mach dieu che do rong xung so sanh bo dem chu ky voi nguong ty le thoi gian muc cao "
            "de dieu khien toc do dong co hoac do sang den LED."
        ),
        "targets": [
            "pwm_generator_8bit",
            "pwm_fixed_1khz",
            "servo_motor_pwm",
            "breathing_led_pwm",
        ],
    },
    {
        "id": "Q18",
        "family": "Decoder 3-to-8",
        "lang": "vi",
        "query": (
            "Mach to hop chuyen ma chon 3 duong vao thanh dung mot trong tam ngo ra "
            "kich hoat muc cao khi co tin hieu cho phep."
        ),
        "targets": ["decoder_3to8", "distill_pdf_036_decoder_3to8", "decoder_2to4"],
    },
    {
        "id": "Q19",
        "family": "BCD to 7-Segment",
        "lang": "en",
        "query": (
            "Combinational display driver translating a 4-bit decimal digit into seven LED "
            "segment control lines for common-anode or common-cathode digits."
        ),
        "targets": [
            "bcd_to_7seg_anode",
            "bcd_to_7seg_cathode",
            "distill_pdf_038_bcd_to_7seg_anode",
            "distill_pdf_039_bcd_to_7seg_cathode",
        ],
    },
    {
        "id": "Q20",
        "family": "Priority Encoder",
        "lang": "en",
        "query": (
            "Circuit encoding 8 parallel interrupt request lines into the 3-bit binary index "
            "of the highest-ranked active requester."
        ),
        "targets": [
            "priority_encoder_8to3",
            "distill_pdf_037_priority_encoder_8to3",
            "fixed_priority_arbiter",
            "fixed_priority_bus_arbiter",
            "fp_convert_altpriority_encoder_3e8",
            "fp_convert_altpriority_encoder_6e8",
        ],
    },
    {
        "id": "Q21",
        "family": "Universal Shift Register",
        "lang": "vi",
        "query": (
            "Thanh ghi 4 bit da che do cho phep giu nguyen du lieu, nap song song ca tu, "
            "hoac truot tung vi tri bit ve hai phia MSB va LSB theo tin hieu chon."
        ),
        "targets": [
            "universal_shift_reg_4bit",
            "shift_reg_universal",
            "distill_pdf_021_universal_shift_reg_4bit",
            "distill_extra_shift_reg_universal",
        ],
    },
    {
        "id": "Q22",
        "family": "SIPO Shift Register",
        "lang": "en",
        "query": (
            "Sequential register converting a single-bit serial input stream into an 8-bit "
            "parallel output word over eight clock cycles."
        ),
        "targets": [
            "sipo_shift_reg_8bit",
            "serial2parallel",
            "distill_pdf_022_sipo_shift_reg_8bit",
            "hkust_rtllm_serial2parallel",
        ],
    },
    {
        "id": "Q23",
        "family": "Button Debouncer",
        "lang": "vi",
        "query": (
            "Mach loc chong doi tiep diem co hoc bi nay nhieu nhieu lan truoc khi on dinh "
            "de tao tin hieu sach sau thoi gian cho xac nhan."
        ),
        "targets": ["button_debouncer", "distill_pdf_071_button_debouncer"],
    },
    {
        "id": "Q24",
        "family": "Watchdog Timer",
        "lang": "en",
        "query": (
            "Hardware supervision countdown monitor that forces a system reset pulse "
            "whenever software fails to refresh or kick it before timeout."
        ),
        "targets": ["watchdog_timer_fsm", "distill_pdf_049_watchdog_timer_fsm"],
    },
    {
        "id": "Q25",
        "family": "Frequency Divider",
        "lang": "vi",
        "query": (
            "Mach ha tan so xung nhip 50MHz xuong 1Hz voi chu ky nhiem vu can bang 50% "
            "de tao nhip chuan 1 giay."
        ),
        "targets": [
            "freq_divider_1hz",
            "freq_div",
            "freq_divbyeven",
            "freq_divbyodd",
            "freq_divbyfrac",
        ],
    },
    {
        "id": "Q26",
        "family": "Edge / Pulse Detector",
        "lang": "en",
        "query": (
            "Sequential circuit comparing current and delayed input samples to emit a "
            "single-cycle strobe on rising or falling signal transitions."
        ),
        "targets": [
            "edge_detect",
            "pos_edge_detector",
            "neg_edge_detector",
            "dual_edge_detector",
            "pulse_detect",
            "pulse_detector",
        ],
    },
    {
        "id": "Q27",
        "family": "CDC Synchronizer",
        "lang": "vi",
        "query": (
            "Cap chot D noi tiep hai tang giup dua tin hieu tu mien xung nhip khac vao mien dich "
            "an toan, han che hien tuong gia on dinh."
        ),
        "targets": [
            "dual_flop_sync",
            "distill_pdf_059_dual_flop_sync",
            "single_bit_cdc_synchronizer",
            "synchronizer",
        ],
    },
    {
        "id": "Q28",
        "family": "CRC-8 Generator",
        "lang": "en",
        "query": (
            "Polynomial remainder calculator computing an 8-bit cyclic redundancy check code "
            "over incoming data bytes for frame integrity verification."
        ),
        "targets": ["crc8_generator", "distill_pdf_055_crc8_generator"],
    },
]


def _item_matches_targets(item, targets):
    """Kiem tra muc tra ve co khop voi tap muc tieu ground-truth hay khong."""
    if not item:
        return False
    target_set = {t.lower() for t in targets}
    mod = str(item.get("module_name") or "").strip().lower()
    candidates = {
        str(item.get("id") or "").strip().lower(),
        str(item.get("name") or "").strip().lower(),
        mod,
    }
    if mod.startswith("verified_"):
        candidates.add(mod[9:])
    return bool(candidates & target_set)


def _format_candidate_name(item):
    """Lay ten gon cua ung vien de hien thi trong bang ket qua."""
    if not item:
        return "-"
    mod = str(item.get("module_name") or "").strip()
    name = str(item.get("name") or "").strip()
    if mod.lower() in ("", "refmodule", "topmodule"):
        return name or str(item.get("id") or "-")
    return mod


def _check_no_module_name_leakage(queries):
    """Xac nhan khong co ten module muc tieu nao xuat hien nguyen ven trong cau truy van."""
    leaks = []
    for q in queries:
        q_norm = xoa_dau_tieng_viet(q["query"])
        for t in q["targets"]:
            t_norm = t.lower()
            if len(t_norm) >= 4 and t_norm in q_norm:
                leaks.append((q["id"], t))
    return leaks


def evaluate_modes(matcher, queries=BENCHMARK_70_QUERIES, modes=("keyword", "bm25", "hybrid", "vector"), top_k=3):
    """Chay benchmark Recall@1, Recall@3, MRR va do tre tren danh sach truy van."""
    summary = {}
    per_query = {q["id"]: {} for q in queries}

    for mode in modes:
        r1_hits = 0
        r3_hits = 0
        rr_sum = 0.0
        t0 = time.perf_counter()

        for q in queries:
            best, match_type, conf, top_results = matcher.search_by_mode(
                q["query"], mode=mode, top_k=top_k
            )
            hit_rank = 0
            for rank_idx, cand in enumerate(top_results[:top_k], 1):
                if _item_matches_targets(cand, q["targets"]):
                    hit_rank = rank_idx
                    break

            if hit_rank == 1:
                r1_hits += 1
            if 1 <= hit_rank <= top_k:
                r3_hits += 1
                rr_sum += 1.0 / hit_rank

            per_query[q["id"]][mode] = {
                "rank": hit_rank,
                "rr": round(1.0 / hit_rank, 4) if hit_rank else 0.0,
                "top1": _format_candidate_name(best),
                "top3": [_format_candidate_name(c) for c in top_results[:top_k]],
                "match_type": match_type,
                "confidence": conf,
            }

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        n = len(queries)
        summary[mode] = {
            "n": n,
            "r1_hits": r1_hits,
            "r3_hits": r3_hits,
            "recall_at_1": round(r1_hits / n, 4) if n else 0.0,
            "recall_at_3": round(r3_hits / n, 4) if n else 0.0,
            "mrr": round(rr_sum / n, 4) if n else 0.0,
            "total_ms": round(elapsed_ms, 2),
            "avg_ms": round(elapsed_ms / n, 2) if n else 0.0,
        }

    return summary, per_query


def main():
    leaks = _check_no_module_name_leakage(BENCHMARK_70_QUERIES)
    matcher = KnowledgeMatcher()
    backend_info = matcher.get_vector_backend_info()

    modes = ("keyword", "bm25", "hybrid", "vector")
    summary, per_query = evaluate_modes(matcher, BENCHMARK_70_QUERIES, modes=modes, top_k=3)

    print("=" * 92)
    print("   BENCHMARK TRUY XUAT NHOM 70% HA TANG PHO THONG (28 TRUY VAN NE TU KHOA / TEN MODULE)")
    print(
        f"   Corpus: {backend_info['corpus_size']} mau "
        f"(DB={len(matcher.DanhSachMau)}, Teacher={len(matcher.TeacherMau)}) | "
        f"Vector Backend: {backend_info['backend']} {backend_info['vector_shape']}"
    )
    print(f"   Kiem tra ro ri ten module trong truy van: {len(leaks)} ro ri")
    print("=" * 92)

    print(f"\n| {'Che do (Mode)':<14} | {'Recall@1':<18} | {'Recall@3':<18} | {'MRR@3':<10} | {'Avg ms/q':<10} |")
    print("-" * 86)
    for mode in modes:
        s = summary[mode]
        r1_str = f"{s['r1_hits']}/{s['n']} ({s['recall_at_1']*100:.1f}%)"
        r3_str = f"{s['r3_hits']}/{s['n']} ({s['recall_at_3']*100:.1f}%)"
        print(f"| {mode:<14} | {r1_str:<18} | {r3_str:<18} | {s['mrr']:<10.4f} | {s['avg_ms']:<10.2f} |")

    # Breakdown theo ngon ngu VI vs EN
    vi_queries = [q for q in BENCHMARK_70_QUERIES if q["lang"] == "vi"]
    en_queries = [q for q in BENCHMARK_70_QUERIES if q["lang"] == "en"]
    print("\n--- PHAN TICH THEO NGON NGU (14 VI / 14 EN) ---")
    for lang_label, subset in [("Tieng Viet (14)", vi_queries), ("Tieng Anh  (14)", en_queries)]:
        parts = []
        for mode in ("keyword", "bm25", "hybrid", "vector"):
            r1 = sum(1 for q in subset if per_query[q["id"]][mode]["rank"] == 1)
            r3 = sum(1 for q in subset if 1 <= per_query[q["id"]][mode]["rank"] <= 3)
            mrr = sum(per_query[q["id"]][mode]["rr"] for q in subset) / len(subset)
            parts.append(f"{mode}: R@1={r1}/{len(subset)} R@3={r3}/{len(subset)} MRR={mrr:.3f}")
        print(f"  {lang_label}: " + " | ".join(parts))

    print("\n--- CHI TIET TUNG TRUY VAN (RANK: 1..3, 0 = MISS) ---")
    print(f"| {'ID':<4} | {'Lang':<4} | {'Family':<24} | {'kw':<3} | {'bm25':<4} | {'hyb':<3} | {'vec':<3} | {'Hybrid Top-1':<28} |")
    print("-" * 92)
    for q in BENCHMARK_70_QUERIES:
        row = per_query[q["id"]]
        kw_r = row["keyword"]["rank"]
        bm_r = row["bm25"]["rank"]
        hy_r = row["hybrid"]["rank"]
        ve_r = row["vector"]["rank"]
        top1 = row["hybrid"]["top1"][:28]
        print(
            f"| {q['id']:<4} | {q['lang']:<4} | {q['family']:<24} | "
            f"{kw_r:<3} | {bm_r:<4} | {hy_r:<3} | {ve_r:<3} | {top1:<28} |"
        )

    return summary, per_query, backend_info


if __name__ == "__main__":
    main()
