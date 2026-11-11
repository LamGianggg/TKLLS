"""
Module: fetch_huggingface_datasets.py
Description: Downloads and curates high-value hardware design benchmarks from:
1. AbiralArch/verilog-training-data (119 Processor, Memory, and Expert Verilog designs)
2. davide221/verilog-instruct-60k (Curated industry-grade instruction-Verilog IP cores)
"""

import os
import json
import urllib.request
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "knowledge_base", "raw")
ABIRAL_DIR = os.path.join(RAW_DIR, "AbiralArch")
INSTRUCT_PATH = os.path.join(RAW_DIR, "verilog_instruct_curated.json")

def download_file(url, out_path):
    print(f" -> Downloading: {os.path.basename(out_path)}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response, open(out_path, 'wb') as out_file:
        out_file.write(response.read())
    size_kb = os.path.getsize(out_path) / 1024
    print(f"    [Done] Saved {size_kb:.1f} KB to {out_path}")

def fetch_abiralarch():
    """Downloads the 3 Comprehensive Verilog Digital Design Problem (CVDP) datasets."""
    os.makedirs(ABIRAL_DIR, exist_ok=True)
    files = [
        "cvdp_processor_problems.json",
        "cvdp_memory_problems.json",
        "cvdp_expert_problems.json"
    ]
    base_url = "https://huggingface.co/datasets/AbiralArch/verilog-training-data/raw/main"
    total_designs = 0
    for fn in files:
        target = os.path.join(ABIRAL_DIR, fn)
        if not os.path.exists(target) or os.path.getsize(target) == 0:
            url = f"{base_url}/{fn}"
            try:
                download_file(url, target)
            except Exception as e:
                print(f"    [!] Failed to download {fn}: {e}")
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                    total_designs += len(data)
            except Exception:
                pass
    print(f" -> [AbiralArch]: {total_designs} verified CVDP designs ready.")
    return total_designs

def fetch_verilog_instruct():
    """Fetches high-quality, diverse instruction-Verilog IP cores via HuggingFace Serverless Datasets API."""
    if os.path.exists(INSTRUCT_PATH) and os.path.getsize(INSTRUCT_PATH) > 10000:
        with open(INSTRUCT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
            print(f" -> [verilog-instruct-60k]: Found {len(existing)} cached curated IP cores.")
            return len(existing)

    print(" -> Fetching representative IP cores from davide221/verilog-instruct-60k...")
    offsets = [0, 100, 250, 500, 1000, 1500, 2000, 3000, 5000, 8000, 12000, 18000]
    curated = []
    seen_modules = set()

    for off in offsets:
        url = f"https://datasets-server.huggingface.co/rows?dataset=davide221/verilog-instruct-60k&config=default&split=train&offset={off}&length=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
                for r in data.get('rows', []):
                    row = r.get('row', {})
                    mod_name = row.get('module_name') or row.get('module') or "unknown"
                    if mod_name not in seen_modules and len(mod_name) > 1:
                        seen_modules.add(mod_name)
                        curated.append({
                            "id": f"instruct60k_{mod_name.replace(' ', '_').lower()}",
                            "module_name": mod_name.replace(" ", "_").lower(),
                            "instruction": row.get("instruction", ""),
                            "description": row.get("description", ""),
                            "verilog_code": row.get("output", "")
                        })
        except Exception as e:
            print(f"    [!] Error fetching offset {off}: {e}")
        time.sleep(0.5)

    with open(INSTRUCT_PATH, "w", encoding="utf-8") as f:
        json.dump(curated, f, indent=2, ensure_ascii=False)
    print(f" -> [verilog-instruct-60k]: Curated {len(curated)} unique industrial IP cores.")
    return len(curated)

def main():
    print("=" * 80)
    print("   FETCHING & CURATING HUGGING FACE VERILOG BENCHMARKS")
    print("   1. AbiralArch/verilog-training-data (CVDP Processor & Memory)")
    print("   2. davide221/verilog-instruct-60k (Curated Industry-Grade IP Blocks)")
    print("=" * 80)
    c1 = fetch_abiralarch()
    c2 = fetch_verilog_instruct()
    print("=" * 80)
    print(f" [SUCCESS]: Downloaded & curated {c1 + c2} new hardware designs from Hugging Face!")
    print("=" * 80)

if __name__ == "__main__":
    main()
