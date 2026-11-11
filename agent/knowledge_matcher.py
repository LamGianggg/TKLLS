"""
Module: knowledge_matcher.py
Description: Semantic Hardware Knowledge Matcher and In-Context Exemplar Retriever.
Enables Spec2RTL to autonomously search, recognize, and retrieve reference architectures,
ports, golden RTL, and testbenches from 308+ benchmark designs (VerilogEval, RTLLM, VeriPrefer).
"""

import os
import re
import json
import unicodedata
from collections import Counter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "knowledge_base", "hardware_db.json")
REFL_PATH = os.path.join(BASE_DIR, "knowledge_base", "reflection_db.json")

def remove_vietnamese_accents(text):
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return text.lower()

def tokenize(text):
    clean = remove_vietnamese_accents(text)
    tokens = re.findall(r"[a-z0-9_]+", clean)
    stop_words = {"va", "thi", "la", "cac", "cho", "co", "the", "duoc", "mot", "trong",
                  "the", "a", "an", "and", "or", "to", "of", "in", "with", "is", "for",
                  "module", "thiet", "ke", "mach", "he", "thong", "dong", "bo"}
    return [t for t in tokens if len(t) > 1 and t not in stop_words]

# Concept definitions mapping keywords & phrases to canonical hardware types
HARDWARE_CONCEPTS = {
    "vending_machine": {
        "triggers": ["ban nuoc", "vending", "lon nuoc", "15000", "5000", "10000", "thoi tien", "nhan tien"],
        "target_names": ["vending_machine"],
        "target_category": "Control / FSM"
    },
    "traffic_light": {
        "triggers": ["den giao thong", "traffic light", "den do", "den xanh", "nga tu", "di bo"],
        "target_names": ["traffic_light"],
        "target_category": "Control / FSM"
    },
    "elevator": {
        "triggers": ["thang may", "elevator", "tang", "cua thang may", "elevator controller"],
        "target_names": ["fsm", "sequence_detector"],
        "target_category": "Control / FSM"
    },
    "up_down_counter": {
        "triggers": ["dem len xuong", "up down counter", "up down", "len xuong"],
        "target_names": ["up_down_counter"],
        "target_category": "Counter"
    },
    "counter": {
        "triggers": ["bo dem", "mach dem", "counter", "dem 4 bit", "dem 8 bit", "dem 1 bit", "johnson", "ring counter"],
        "target_names": ["counter_12", "JC_counter", "ring_counter", "up_down_counter"],
        "target_category": "Counter"
    },
    "asyn_fifo": {
        "triggers": ["asyn fifo", "bat dong bo fifo", "fifo bat dong bo", "asynchronous fifo"],
        "target_names": ["asyn_fifo"],
        "target_category": "Memory / Storage"
    },
    "fifo": {
        "triggers": ["fifo", "hang doi", "first in first out", "bo dem fifo"],
        "target_names": ["asyn_fifo"],
        "target_category": "Memory / Storage"
    },
    "multi_booth_8bit": {
        "triggers": ["booth multiplier", "nhan booth", "booth", "nhan 8 bit"],
        "target_names": ["multi_booth_8bit", "multi_8bit", "multi_16bit"],
        "target_category": "Arithmetic"
    },
    "multiplier": {
        "triggers": ["bo nhan", "mach nhan", "multiplier", "phep nhan"],
        "target_names": ["multi_8bit", "multi_16bit", "multi_booth_8bit", "multi_pipe_4bit", "multi_pipe_8bit", "float_multi"],
        "target_category": "Arithmetic"
    },
    "adder_bcd": {
        "triggers": ["adder bcd", "cong bcd", "bcd adder"],
        "target_names": ["adder_bcd"],
        "target_category": "Arithmetic"
    },
    "adder": {
        "triggers": ["bo cong", "mach cong", "adder", "full adder", "half adder", "cong 8 bit", "cong 16 bit", "cong 32 bit"],
        "target_names": ["adder_8bit", "adder_16bit", "adder_32bit", "adder_bcd", "adder_pipe_64bit"],
        "target_category": "Arithmetic"
    },
    "divider": {
        "triggers": ["bo chia", "mach chia", "divider", "radix2 div", "chia 16 bit"],
        "target_names": ["div_16bit", "radix2_div"],
        "target_category": "Arithmetic"
    },
    "comparator": {
        "triggers": ["bo so sanh", "mach so sanh", "comparator"],
        "target_names": ["comparator_3bit", "comparator_4bit"],
        "target_category": "Arithmetic"
    },
    "alu": {
        "triggers": ["alu", "arithmetic logic unit", "khoi alu"],
        "target_names": ["alu"],
        "target_category": "Arithmetic"
    },
    "top_soc": {
        "triggers": ["soc", "ai accelerator", "cpu controller", "dma 8237", "ai core"],
        "target_names": ["top_soc"],
        "target_category": "SoC / Processor"
    },
    "barrel_shifter": {
        "triggers": ["barrel shifter", "dich bit", "shifter", "dich trai", "dich phai"],
        "target_names": ["barrel_shifter", "right_shifter", "LFSR"],
        "target_category": "Memory / Storage"
    },
    "frequency_divider": {
        "triggers": ["chia tan", "chia tan so", "freq div", "frequency divider"],
        "target_names": ["freq_div", "freq_divbyeven", "freq_divbyodd", "freq_divbyfrac"],
        "target_category": "Clock & Timing"
    }
}

class KnowledgeMatcher:
    def __init__(self, db_path=DB_PATH, refl_path=REFL_PATH):
        self.db_path = db_path
        self.refl_path = refl_path
        self.entries = []
        self.reflection_rules = []
        self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8", errors="replace") as f:
                self.entries = json.load(f)
        if os.path.exists(self.refl_path):
            with open(self.refl_path, "r", encoding="utf-8", errors="replace") as f:
                self.reflection_rules = json.load(f)

    def search(self, spec_text, top_k=3):
        """Searches the knowledge base for designs matching the input specification.
        Returns:
            best_match: dict or None
            match_type: 'EXACT' | 'SIMILAR' | 'CUSTOM'
            confidence: float (0.0 - 1.0)
            exemplars: list of top matching unique entries
        """
        if not self.entries:
            return None, "CUSTOM", 0.0, []

        spec_norm = remove_vietnamese_accents(spec_text)
        query_tokens = tokenize(spec_text)
        query_set = set(query_tokens)

        # Detect active concepts
        matched_concepts = []
        for c_id, c_data in HARDWARE_CONCEPTS.items():
            for trig in c_data["triggers"]:
                if trig in spec_norm:
                    matched_concepts.append(c_data)
                    break

        scored = []
        seen_names = set()

        for item in self.entries:
            score = 0.0
            item_name = item.get("name", "").lower()
            item_mod = item.get("module_name", "").lower()
            item_desc = item.get("spec", "").lower()
            item_cat = item.get("category", "")
            item_kws = [k.lower() for k in item.get("keywords", [])]

            # 1. Concept direct hit
            for c_data in matched_concepts:
                if item_name in c_data["target_names"] or item_mod in c_data["target_names"]:
                    score += 1.5
                elif item_cat == c_data.get("target_category"):
                    score += 0.4

            # 2. Token overlap on name and keywords
            for q_tok in query_tokens:
                if q_tok == item_name or q_tok == item_mod:
                    score += 0.8
                elif q_tok in item_name or item_name in q_tok:
                    score += 0.35
                if any(q_tok in kw for kw in item_kws):
                    score += 0.2

            # 3. Text overlap with target spec
            target_tokens = set(tokenize(item_name + " " + " ".join(item_kws)))
            intersection = query_set.intersection(target_tokens)
            if target_tokens:
                score += (len(intersection) / float(len(target_tokens))) * 0.5

            if score > 0.25:
                confidence = min(1.0, score / 3.0)
                scored.append((score, confidence, item))

        # Sort by actual raw score first (highest relevance first)
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return None, "CUSTOM", 0.0, []

        # Deduplicate exemplars by module_name
        unique_exemplars = []
        for raw_s, conf, item in scored:
            m_name = item.get("module_name", item.get("name"))
            if m_name not in seen_names:
                seen_names.add(m_name)
                unique_exemplars.append(item)
            if len(unique_exemplars) >= top_k:
                break

        best_score, best_conf, best_item = scored[0]

        if best_conf >= 0.70:
            match_type = "EXACT"
        elif best_conf >= 0.35:
            match_type = "SIMILAR"
        else:
            match_type = "CUSTOM"

        return best_item, match_type, round(best_conf, 3), unique_exemplars

    def get_reflection_guidance(self, error_message):
        """Looks up VeriPrefer reflection rules based on an EDA error message."""
        recs = []
        for rule in self.reflection_rules:
            pattern = rule.get("pattern", "")
            if re.search(pattern, error_message, re.IGNORECASE):
                recs.append({
                    "error_type": rule.get("error_type"),
                    "diagnosis": rule.get("diagnosis"),
                    "remedy": rule.get("remedy")
                })
        return recs

if __name__ == "__main__":
    matcher = KnowledgeMatcher()
    print("=" * 75)
    print("   TESTING HARDWARE KNOWLEDGE MATCHER (RAG BENCHMARK)")
    print("=" * 75)
    queries = [
        "Thiết kế máy bán nước tự động nhận 5k và 10k, lon nước giá 15k",
        "Thiết kế hệ thống đèn giao thông ngã tư với đèn đỏ, xanh, vàng và nút cho người đi bộ",
        "Mạch đếm lên xuống (up down counter) 4 bit đồng bộ",
        "Thiết kế bộ nhớ đệm bất đồng bộ FIFO (Asynchronous FIFO)",
        "Thiết kế mạch nhân 8 bit Booth multiplier",
        "Thiết kế bộ cộng BCD (BCD Adder)",
        "Hệ thống SoC AI Accelerator tích hợp CPU, DMA, AI Core và RAM"
    ]
    for q in queries:
        match, m_type, conf, ex = matcher.search(q)
        print(f"\n[Query]: {q}")
        print(f" -> Result: [{m_type}] Confidence: {conf*100:.1f}%")
        if match:
            print(f" -> Matched: {match['id']} ({match['name']}) | Source: {match['source']} | Cat: {match['category']}")
        print(f" -> Top {len(ex)} Unique Exemplars: {', '.join([e['name'] for e in ex])}")
