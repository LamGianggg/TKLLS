"""
Module: verilogdb_sampler.py
Chức năng: Kéo chọn lọc và chuẩn hóa tập mẫu phần cứng đa dạng họ mạch từ
VerilogDB gốc (Rohan-code/Verilog_DB_read trên HuggingFace - arXiv:2507.13369)
để phục vụ chưng cất Teacher CoT + Verilog IEEE 1364-2001.
"""

import os
import re
import ssl
import sys
import json
import time
import urllib.request
import urllib.error
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")
DEFAULT_CACHE_PATH = os.path.join(PROJECT_ROOT, "training", "verilogdb_selected_candidates.json")
FULL_POOL_PATH = os.path.join(PROJECT_ROOT, "training", "verilogdb_full_clean_pool.json")
RAW_PARQUET_DIR = os.path.join(PROJECT_ROOT, "knowledge_base", "raw_verilogdb")
TEACHER_OUT_PATH = os.path.join(PROJECT_ROOT, "training", "dataset_teacher_distilled.json")

if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from spec_analyzer import SpecAnalyzer

HF_DATASET_API = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=Rohan-code/Verilog_DB_read&config=default&split=train&offset={offset}&length={length}"
)
PARQUET_FILES = [
    ("train-00000-of-00003.parquet", "https://huggingface.co/datasets/Rohan-code/Verilog_DB_read/resolve/main/data/train-00000-of-00003.parquet", 120_000_000),
    ("train-00001-of-00003.parquet", "https://huggingface.co/datasets/Rohan-code/Verilog_DB_read/resolve/main/data/train-00001-of-00003.parquet", 90_000_000),
    ("train-00002-of-00003.parquet", "https://huggingface.co/datasets/Rohan-code/Verilog_DB_read/resolve/main/data/train-00002-of-00003.parquet", 80_000_000),
]

VERILOG_KEYWORDS = {
    "module", "endmodule", "input", "output", "inout", "wire", "reg", "always",
    "assign", "case", "casex", "casez", "endcase", "default", "begin", "end",
    "if", "else", "for", "while", "repeat", "forever", "parameter", "localparam",
    "integer", "real", "time", "genvar", "generate", "endgenerate", "function",
    "endfunction", "task", "endtask", "posedge", "negedge", "and", "or", "xor",
    "not", "nand", "nor", "xnor", "buf", "logic", "bit", "signed", "unsigned",
}

EXCLUDED_PORT_WORDS = {
    "port", "port_name", "name", "ten_chan", "ten_cong", "mo_ta", "input", "output",
    "dau_vao", "dau_ra", "tin_hieu", "khi", "neu", "gia_tri", "truong_hop", "so",
    "chu_so", "buoc", "chu_ky", "chu_ky_sau", "thoi_gian", "muc", "che_do",
    "note", "luu_y", "chu_y", "wire", "reg", "logic", "ra", "vao",
}

SV_ONLY_PATTERN = re.compile(r"\b(always_ff|always_comb|always_latch|interface|typedef|struct|enum|modport)\b")
MODULE_IDENT_RE = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
PORT_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")


def fetch_hf_rows(offset, length=100, retries=3):
    """Tải một lô dòng dữ liệu từ HuggingFace Datasets Server API."""
    url = HF_DATASET_API.format(offset=offset, length=length)
    ctx = ssl._create_unverified_context()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Spec2RTL-VerilogDB-Sampler/1.0"})
            with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as ex:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"  [WARN] Lỗi tải offset={offset}: {ex}")
                return None
    return None


def load_existing_module_names():
    """Thu thập tên các module đã có trong dataset_teacher_distilled.json để tránh trùng."""
    seen = set()
    if os.path.exists(TEACHER_OUT_PATH):
        try:
            with open(TEACHER_OUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                m = (item.get("module_name") or "").strip().lower()
                if m:
                    seen.add(m)
        except Exception:
            pass
    return seen


def validate_and_format_row(row, seen_modules):
    """Kiểm tra chất lượng mẫu VerilogDB và chuyển sang định dạng đặc tả Spec2RTL."""
    cls = (row.get("classification") or "").strip()
    if not cls or cls == "None":
        return None

    mod_name = (row.get("module_name") or "").strip()
    if not MODULE_IDENT_RE.match(mod_name):
        return None
    if mod_name in VERILOG_KEYWORDS or mod_name in seen_modules:
        return None

    token_count = row.get("token_count")
    if not isinstance(token_count, int) or token_count < 40 or token_count >= 1500:
        return None

    desc = re.sub(r"\s+", " ", (row.get("description") or "").strip())
    if len(desc) < 40 or len(desc) > 1200:
        return None

    # Loại bỏ mô tả là wrapper gọi submodule ngoài hoặc không rõ chức năng
    desc_low = desc.lower()
    if any(bad in desc_low for bad in ["wrapper around", "instantiates external", "testbench", "tb_"]):
        return None

    ports = row.get("ports")
    if not isinstance(ports, list) or len(ports) < 2 or len(ports) > 14:
        return None

    clean_ports = []
    seen_port_names = set()
    for p in ports:
        if not isinstance(p, dict):
            return None
        pname = (p.get("name") or "").strip()
        pdir = (p.get("direction") or "").strip().lower()
        pwidth = p.get("bit_width")

        if pdir not in ("input", "output"):
            return None
        if not PORT_IDENT_RE.match(pname):
            return None
        if pname.lower() in VERILOG_KEYWORDS or pname.lower() in EXCLUDED_PORT_WORDS or pname.lower() in seen_port_names:
            return None
        if not isinstance(pwidth, int) or pwidth < 1 or pwidth > 64:
            return None

        seen_port_names.add(pname.lower())
        clean_ports.append({"name": pname, "direction": pdir, "bit_width": pwidth})

    inputs = [p for p in clean_ports if p["direction"] == "input"]
    outputs = [p for p in clean_ports if p["direction"] == "output"]
    if not inputs or not outputs:
        return None

    vcode = (row.get("verilog_code") or "").strip()
    if vcode:
        if SV_ONLY_PATTERN.search(vcode):
            return None
        if f"module {mod_name}" not in re.sub(r"\s+", " ", vcode):
            return None
        # Tránh trường hợp metadata bit_width=1 nhưng code khai báo vector [msb:lsb]
        for p in clean_ports:
            if p["bit_width"] == 1:
                bus_pat = re.search(
                    rf"\b(?:input|output)\s+(?:wire\s+|reg\s+)?\[\s*\d+\s*:\s*\d+\s*\]\s*[^;\n]*\b{re.escape(p['name'])}\b",
                    vcode,
                )
                if bus_pat:
                    return None

    # Định dạng đặc tả chuẩn Spec2RTL để SpecAnalyzer đọc chính xác 100%
    lines = [
        f"# VerilogDB {cls} | Module: {mod_name}",
        "## 1. Đầu vào (Inputs):",
    ]
    for p in inputs:
        w = p["bit_width"]
        if w > 1:
            lines.append(f"  • [{w - 1}:0] {p['name']}: input ({w}-bit)")
        else:
            lines.append(f"  • {p['name']}: input (1-bit)")

    lines.append("## 2. Đầu ra (Outputs):")
    for p in outputs:
        w = p["bit_width"]
        if w > 1:
            lines.append(f"  • [{w - 1}:0] {p['name']}: output ({w}-bit)")
        else:
            lines.append(f"  • {p['name']}: output (1-bit)")

    lines.append("## 3. Hoạt động / Logic mong muốn (VerilogDB arXiv:2507.13369):")
    lines.append(f"  • {desc}")
    spec_text = "\n".join(lines)

    # Kiểm chứng chéo ngay với SpecAnalyzer (Domain Guard + Port Extraction)
    analyzer = SpecAnalyzer(spec_text)
    is_unsup, _, _ = analyzer.check_unsupported_domain()
    if is_unsup or analyzer.is_30_percent_architecture():
        return None
    if analyzer.extract_module_name() != mod_name:
        return None

    extracted_ports = analyzer.extract_ports()
    extracted_map = {ep["name"].lower(): (ep["direction"], ep["width"]) for ep in extracted_ports}
    for p in clean_ports:
        got = extracted_map.get(p["name"].lower())
        if got != (p["direction"], p["bit_width"]):
            return None

    return {
        "id": f"distill_vdb_{mod_name}",
        "module_name": mod_name,
        "category": cls,
        "origin": f"VerilogDB ({cls})",
        "token_count": token_count,
        "spec_text": spec_text,
    }


def round_robin_select(by_category, target_count):
    """Chọn cân bằng round-robin qua tất cả các họ mạch; target_count <= 0 trả về toàn bộ theo thứ tự round-robin."""
    selected = []
    cat_keys = sorted(by_category.keys(), key=lambda k: len(by_category[k]))
    idx_map = {k: 0 for k in cat_keys}
    limit = target_count if target_count > 0 else sum(len(v) for v in by_category.values())

    while len(selected) < limit:
        progressed = False
        for k in cat_keys:
            if idx_map[k] < len(by_category[k]):
                selected.append(by_category[k][idx_map[k]])
                idx_map[k] += 1
                progressed = True
                if len(selected) >= limit:
                    break
        if not progressed:
            break
    return selected


def download_parquet_files(raw_dir=RAW_PARQUET_DIR, force_download=False):
    """Tải 3 file .parquet (~287 MB) từ HuggingFace vào thư mục gitignored."""
    os.makedirs(raw_dir, exist_ok=True)
    ctx = ssl._create_unverified_context()
    paths = []
    for fname, url, min_bytes in PARQUET_FILES:
        dst = os.path.join(raw_dir, fname)
        if not force_download and os.path.exists(dst) and os.path.getsize(dst) >= min_bytes:
            print(f"  [CACHE] Đã có sẵn {fname} ({os.path.getsize(dst) / (1024**2):.2f} MB)")
            paths.append(dst)
            continue
        tmp_dst = dst + ".tmp"
        print(f"  [TẢI] Đang tải {fname} từ HuggingFace...", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Spec2RTL-VerilogDB-Sampler/1.0"})
        with urllib.request.urlopen(req, timeout=180, context=ctx) as resp, open(tmp_dst, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        os.replace(tmp_dst, dst)
        print(f"  [XONG] {fname}: {os.path.getsize(dst) / (1024**2):.2f} MB", flush=True)
        paths.append(dst)
    return paths


def scan_full_parquet_pool(seen_modules, force_download=False):
    """Đọc toàn bộ 40,755 dòng từ 3 file .parquet, lọc sạch và lưu toàn bộ pool đạt chuẩn."""
    import pyarrow.parquet as pq

    parquet_paths = download_parquet_files(force_download=force_download)
    local_seen = set(seen_modules)
    by_category = {}
    stats = {
        "total_rows": 0,
        "has_classification": 0,
        "has_description": 0,
        "valid_clean": 0,
    }

    for ppath in parquet_paths:
        table = pq.read_table(ppath, columns=["module_name", "ports", "verilog_code", "token_count", "description", "classification"])
        rows = table.to_pylist()
        print(f"  [QUÉT] {os.path.basename(ppath)}: {len(rows)} dòng...", flush=True)
        for row in rows:
            stats["total_rows"] += 1
            cls = (row.get("classification") or "").strip()
            if cls and cls != "None":
                stats["has_classification"] += 1
            desc = (row.get("description") or "").strip()
            if len(desc) >= 40:
                stats["has_description"] += 1
            item = validate_and_format_row(row, local_seen)
            if item:
                local_seen.add(item["module_name"].lower())
                by_category.setdefault(item["category"], []).append(item)
                stats["valid_clean"] += 1

    all_clean = []
    for k in sorted(by_category.keys()):
        all_clean.extend(by_category[k])

    os.makedirs(os.path.dirname(FULL_POOL_PATH), exist_ok=True)
    with open(FULL_POOL_PATH, "w", encoding="utf-8") as f:
        json.dump(all_clean, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 72)
    print(f"THỐNG KÊ TOÀN BỘ VERILOGDB ({stats['total_rows']} MẪU GỐC)")
    print("=" * 72)
    print(f"  - Tổng số dòng gốc           : {stats['total_rows']}")
    print(f"  - Có nhãn classification     : {stats['has_classification']}")
    print(f"  - Có description (>= 40 ký tự): {stats['has_description']}")
    print(f"  - Đạt toàn bộ bộ lọc sạch    : {stats['valid_clean']} mẫu ({len(by_category)} họ mạch)")
    print("  - Chi tiết theo từng họ vi mạch:")
    for k, items in sorted(by_category.items(), key=lambda x: -len(x[1])):
        print(f"      * {k}: {len(items)}")
    print("=" * 72)
    return by_category


def sample_verilogdb_prompts(target_count=200, seen_modules=None, cache_path=DEFAULT_CACHE_PATH, force_refresh=False, source="parquet"):
    """
    Lấy chọn lọc `target_count` bài toán đa dạng classification từ Rohan-code/Verilog_DB_read.
    Mặc định dùng toàn bộ file `.parquet` cục bộ để quét sạch đủ 40,755 dòng; hỗ trợ `source='api'` nhẹ hơn.
    """
    if seen_modules is None:
        seen_modules = set()
    else:
        seen_modules = {m.lower() for m in seen_modules}

    if not force_refresh and target_count > 0 and cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            filtered_cache = [c for c in cached if c["module_name"].lower() not in seen_modules]
            if len(filtered_cache) >= target_count:
                return filtered_cache[:target_count]
        except Exception:
            pass

    if source == "parquet":
        if not force_refresh and os.path.exists(FULL_POOL_PATH):
            with open(FULL_POOL_PATH, "r", encoding="utf-8") as f:
                full_pool = json.load(f)
            by_category = {}
            for item in full_pool:
                if item["module_name"].lower() not in seen_modules:
                    by_category.setdefault(item["category"], []).append(item)
        else:
            by_category = scan_full_parquet_pool(seen_modules, force_download=False)
        selected = round_robin_select(by_category, target_count)
    else:
        print(f"[*] Đang quét chọn lọc {target_count} mẫu đa dạng họ mạch qua HuggingFace REST API...")
        first_page = fetch_hf_rows(0, length=100)
        if not first_page:
            raise RuntimeError("Không thể kết nối HuggingFace Datasets Server API cho Rohan-code/Verilog_DB_read.")

        total_rows = int(first_page.get("num_rows_total", 40755))
        by_category = {}
        local_seen = set(seen_modules)

        def ingest_rows(page_data):
            added = 0
            for r in page_data.get("rows", []):
                row = r.get("row", {})
                item = validate_and_format_row(row, local_seen)
                if item:
                    local_seen.add(item["module_name"].lower())
                    by_category.setdefault(item["category"], []).append(item)
                    added += 1
            return added

        ingest_rows(first_page)
        pool_goal = max(target_count * 2, 400) if target_count > 0 else 40755
        total_valid = sum(len(v) for v in by_category.values())

        stride = 700
        offsets = [
            off for phase in range(0, stride, 100)
            for off in range(phase, total_rows, stride) if off != 0
        ]

        batch_size = 8
        for start in range(0, len(offsets), batch_size):
            if total_valid >= pool_goal and len(by_category) >= 8:
                break
            batch = offsets[start:start + batch_size]
            with ThreadPoolExecutor(max_workers=batch_size) as ex:
                futures = [ex.submit(fetch_hf_rows, off, 100) for off in batch]
                for fut in as_completed(futures):
                    page = fut.result()
                    if page:
                        total_valid += ingest_rows(page)
        selected = round_robin_select(by_category, target_count)

    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(selected, f, ensure_ascii=False, indent=2)

    cat_summary = {}
    for item in selected:
        cat_summary[item["category"]] = cat_summary.get(item["category"], 0) + 1
    print(f"[*] Đã chọn {len(selected)} mẫu VerilogDB chuẩn hóa thuộc {len(cat_summary)} họ mạch:")
    for k, v in sorted(cat_summary.items(), key=lambda x: -x[1]):
        print(f"    - {k}: {v}")

    return selected


def main():
    parser = argparse.ArgumentParser(description="Kéo chọn lọc mẫu đa dạng từ Rohan-code/Verilog_DB_read")
    parser.add_argument("--count", type=int, default=200, help="Số lượng mẫu cần chọn lọc (0 = lấy toàn bộ pool sạch)")
    parser.add_argument("--source", choices=["parquet", "api"], default="parquet", help="Nguồn đọc: parquet (toàn bộ 40,755 mẫu) hoặc api (nhanh qua REST)")
    parser.add_argument("--refresh", action="store_true", help="Bỏ qua cache, tải/quét mới từ HuggingFace")
    args = parser.parse_args()

    existing = load_existing_module_names()
    items = sample_verilogdb_prompts(
        target_count=args.count,
        seen_modules=existing,
        force_refresh=args.refresh,
        source=args.source,
    )
    print(f"[DONE] Đã lưu {len(items)} mẫu vào {DEFAULT_CACHE_PATH}")


if __name__ == "__main__":
    main()
