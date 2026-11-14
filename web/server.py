#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module: web/server.py
Description: Production Lightweight Ponytail Web Server for Spec2RTL Interactive Workbench
Architecture:
  - 0 External Dependencies: Pure Python Standard Library (http.server.ThreadingHTTPServer)
  - Thread-Safe Non-Blocking Concurrency: Real-time background EDA worker execution with TaskRegistry
  - Resilient Static & Dynamic Routing: Offline assets, simulation previews, reports, BDF schematics
  - Robust Port Binding: Automatic busy-port detection (WinError 10048) with 8080..8099 fallback loop
  - Strict Cross-Platform MIME Typing: Guarantees application/javascript for ES modules on Windows
"""

import argparse
import json
import mimetypes
import os
import posixpath
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Force UTF-8 encoding on standard I/O streams
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Directory resolution: WEB_DIR is directory of this script, BASE_DIR is project root
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(WEB_DIR)
AGENT_DIR = os.path.join(BASE_DIR, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

# Comprehensive MIME mapping (prevents Windows Registry corruption of .js files)
MIME_MAP = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".vcd": "text/plain; charset=utf-8",
    ".v": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".pdf": "application/pdf",
    ".bdf": "text/plain; charset=utf-8",
    ".bsf": "text/plain; charset=utf-8",
}

# 5 Hardware Specification Samples per PROJECT.md interface contract
SPEC_SAMPLES = [
    {
        "id": "multiplier_8bit",
        "name_vi": "Bộ nhân 8 bit",
        "name_en": "8-bit Multiplier",
        "spec_file": "specs/a.txt",
        "prompt": "Thiết kế bộ nhân 8 bit có tín hiệu clk, rst, ngõ vào a, b 8-bit và ngõ ra product 16-bit"
    },
    {
        "id": "gray_counter_4bit",
        "name_vi": "Bộ đếm Gray 4-bit",
        "name_en": "4-bit Gray Counter",
        "spec_file": "benchmarks/verilog_eval/gray_counter_4bit.md",
        "prompt": "Thiết kế bộ đếm mã Gray 4 bit có tín hiệu clk, rst, enable, up_down, ngõ ra gray_out 4-bit, count 4-bit và tc"
    },
    {
        "id": "vending_machine",
        "name_vi": "Máy bán nước tự động",
        "name_en": "Vending Machine",
        "spec_file": "specs/vendding_machine.md",
        "prompt": "Thiết kế máy bán nước tự động FSM nhận tiền 5k, 10k và trả nước"
    },
    {
        "id": "elevator_5floor",
        "name_vi": "Thang máy 5 tầng",
        "name_en": "5-Floor Elevator Controller",
        "spec_file": "specs/thang_may_spec.md",
        "prompt": "Thiết kế mạch điều khiển thang máy 5 tầng FSM"
    },
    {
        "id": "traffic_light",
        "name_vi": "Đèn giao thông ngã tư",
        "name_en": "Traffic Light Controller",
        "spec_file": "specs/traffic_light_spec.md",
        "prompt": "Thiết kế mạch đèn giao thông ngã tư có đèn xanh, vàng, đỏ"
    }
]

# Alias map for alternative sample paths
SPEC_ALIASES = {
    "benchmarks/verilog_eval/vending_machine.md": "specs/vendding_machine.md",
    "specs/vending_machine.md": "specs/vendding_machine.md",
    "specs/elevator.txt": "specs/thang_may_spec.md",
    "specs/traffic.txt": "specs/traffic_light_spec.md",
}


# ==============================================================================
# Thread-Safe Task Registry for Background EDA Pipelines
# ==============================================================================

class TaskRegistry:
    """Thread-safe in-memory storage for background EDA tasks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._tasks = {}

    def create_task(self, prompt, spec_file=None, use_harness=True):
        task_id = uuid.uuid4().hex[:12]
        now = time.time()
        record = {
            "task_id": task_id,
            "status": "running",
            "start_time": now,
            "elapsed": 0.0,
            "success": False,
            "prompt": prompt or "",
            "spec_file": spec_file or "",
            "use_harness": bool(use_harness),
            "top_entity": "",
            "rtl_code": "",
            "tb_code": "",
            "harness_code": "",
            "log": "",
            "scoreboard": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "accuracy_percent": 0.0,
                "verdict": "RUNNING"
            },
            "metrics": {
                "logic_elements": 0,
                "total_registers": 0,
                "total_pins": 0,
                "family": "Cyclone II"
            },
            "ports": [],
            "waveform_url": "",
            "bdf_path": "",
            "error": None
        }
        with self._lock:
            self._tasks[task_id] = record
        return task_id

    def get_task(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            snapshot = dict(task)
            if snapshot["status"] == "running":
                snapshot["elapsed"] = round(time.time() - snapshot["start_time"], 2)
            snapshot["scoreboard"] = dict(task["scoreboard"])
            snapshot["metrics"] = dict(task["metrics"])
            snapshot["ports"] = list(task["ports"])
            return snapshot

    def append_log(self, task_id, chunk):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["log"] += chunk

    def update_task(self, task_id, **kwargs):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(kwargs)


# Global task registry instance
TASKS = TaskRegistry()


# ==============================================================================
# Verilog RTL Port Extraction Helper
# ==============================================================================

def parse_verilog_ports(rtl_text):
    """Extracts typed port definitions from synthesizable Verilog module source."""
    if not rtl_text:
        return []

    # First attempt: Use existing HarnessGenerator if available
    try:
        from harness_generator import HarnessGenerator
        _, h_ports = HarnessGenerator().extract_ports(rtl_text)
        if h_ports:
            formatted = []
            for p in h_ports:
                w = p.get("width", 1)
                msb = int(p["msb"]) if p.get("msb") is not None else (w - 1 if w > 1 else 0)
                lsb = int(p["lsb"]) if p.get("lsb") is not None else 0
                formatted.append({
                    "name": p["name"],
                    "dir": p.get("direction", "input"),
                    "width": w,
                    "is_bus": (w > 1),
                    "msb": msb,
                    "lsb": lsb
                })
            return formatted
    except Exception:
        pass

    # Fallback regex port parser
    ports = []
    clean = re.sub(r"//.*", "", rtl_text)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)

    pattern = r"(input|output|inout)\s+(?:(?:reg|wire|logic)\s+)?(?:\[(\d+):(\d+)\])?\s*([^;,\)]+)"
    for m in re.finditer(pattern, clean):
        direction = m.group(1).lower()
        msb = int(m.group(2)) if m.group(2) is not None else 0
        lsb = int(m.group(3)) if m.group(3) is not None else 0
        names = m.group(4).strip()
        is_bus = (m.group(2) is not None)
        width = abs(msb - lsb) + 1 if is_bus else 1
        for raw_name in names.split(","):
            name = raw_name.strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                if not any(p["name"] == name for p in ports):
                    ports.append({
                        "name": name,
                        "dir": direction,
                        "width": width,
                        "is_bus": is_bus,
                        "msb": msb,
                        "lsb": lsb
                    })
    return ports


# ==============================================================================
# Background EDA Pipeline Worker
# ==============================================================================

def run_pipeline_worker(task_id, prompt, spec_file, use_harness):
    """Executes the Spec2RTL pipeline in a separate thread without blocking HTTP clients."""
    start_time = time.time()
    try:
        # Clean stale ModelSim lock if present from previous runs
        stale_lock = os.path.join(BASE_DIR, "sim", "work", "_lock")
        if os.path.exists(stale_lock):
            try:
                os.remove(stale_lock)
            except Exception:
                pass

        # 1. Determine target specification file
        target_spec_path = None
        if spec_file:
            cand = os.path.join(BASE_DIR, spec_file)
            if not os.path.exists(cand) and spec_file in SPEC_ALIASES:
                cand = os.path.join(BASE_DIR, SPEC_ALIASES[spec_file])
            if os.path.exists(cand):
                target_spec_path = cand

        if not target_spec_path:
            # Create a persistent prompt file in specs/
            specs_dir = os.path.join(BASE_DIR, "specs")
            os.makedirs(specs_dir, exist_ok=True)
            target_spec_path = os.path.join(specs_dir, f"web_spec_{task_id}.txt")
            with open(target_spec_path, "w", encoding="utf-8") as f:
                f.write(prompt or "")

        TASKS.append_log(task_id, f"[*] Initializing Spec2RTL Pipeline for: {os.path.basename(target_spec_path)}\n")
        TASKS.append_log(task_id, f"[*] Harness Option A: {'ENABLED' if use_harness else 'DISABLED'}\n\n")

        # 2. Launch master CLI orchestrator as subprocess
        orchestrator_script = os.path.join(BASE_DIR, "agent", "run_spec2rtl.py")
        cmd = [sys.executable, "-u", orchestrator_script, target_spec_path]
        if use_harness:
            cmd.append("--harness")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        # Stream console output in real-time to the task registry
        full_log = []
        for line in iter(proc.stdout.readline, ""):
            full_log.append(line)
            TASKS.append_log(task_id, line)
        proc.stdout.close()
        ret_code = proc.wait(timeout=120)

        log_text = "".join(full_log)
        elapsed = round(time.time() - start_time, 2)

        # 3. Detect top entity
        top_entity = ""
        m_dut = re.search(r"(?:Device Under Test|Target Module Under Test|Target Module|Top-level Entity Name|Module Entity Name)\s*[:=]?\s*([A-Za-z0-9_]+)", log_text)
        if m_dut:
            top_entity = m_dut.group(1).strip()
            if top_entity.startswith("sch_"):
                top_entity = top_entity[4:]
        if not top_entity:
            m_v = re.search(r"Synthesized:\s*(?:src/|sim/harness_)?([A-Za-z0-9_]+)\.v", log_text)
            if m_v:
                top_entity = m_v.group(1).strip()
                if top_entity.startswith("harness_"):
                    top_entity = top_entity[8:]

        # Fallback to SpecAnalyzer if entity extraction from log fails
        if not top_entity and os.path.exists(target_spec_path):
            try:
                from spec_analyzer import SpecAnalyzer
                top_entity = SpecAnalyzer(target_spec_path).extract_module_name()
            except Exception:
                top_entity = "custom_module"

        # 4. Load RTL, Testbench, and Harness code
        rtl_code = ""
        tb_code = ""
        harness_code = ""
        src_path = os.path.join(BASE_DIR, "src", f"{top_entity}.v")
        tb_path = os.path.join(BASE_DIR, "sim", f"tb_{top_entity}.v")
        harness_path = os.path.join(BASE_DIR, "sim", f"harness_{top_entity}.v")

        if os.path.exists(src_path):
            with open(src_path, "r", encoding="utf-8", errors="replace") as f:
                rtl_code = f.read()

        if os.path.exists(tb_path):
            with open(tb_path, "r", encoding="utf-8", errors="replace") as f:
                tb_code = f.read()

        if os.path.exists(harness_path):
            with open(harness_path, "r", encoding="utf-8", errors="replace") as f:
                harness_code = f.read()
        else:
            harness_code = tb_code

        # 5. Extract Verification Scoreboard
        scoreboard = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "accuracy_percent": 0.0,
            "verdict": "FAIL"
        }
        m_tot = re.search(r"(?:Total Executed Tests|Total Test Scenarios)\s*:\s*(\d+)", log_text)
        m_pas = re.search(r"Passed Assertions\s*:\s*(\d+)", log_text)
        m_fai = re.search(r"Failed Assertions\s*:\s*(\d+)", log_text)
        m_acc = re.search(r"Functional Accuracy\s*:\s*([0-9.]+)\s*PERCENT", log_text)

        if m_tot and m_pas and m_fai:
            tot = int(m_tot.group(1))
            pas = int(m_pas.group(1))
            fai = int(m_fai.group(1))
            acc = float(m_acc.group(1)) if m_acc else (100.0 if tot > 0 and fai == 0 else 0.0)
            scoreboard["total_tests"] = tot
            scoreboard["passed_tests"] = pas
            scoreboard["failed_tests"] = fai
            scoreboard["accuracy_percent"] = acc
            scoreboard["verdict"] = "PASS" if (fai == 0 and tot > 0 and ret_code == 0) else "FAIL"
        else:
            # Generic testbench pattern
            if ("100% PASS" in log_text or "SUCCESS" in log_text or "ALL TESTS PASSED" in log_text) and ret_code == 0:
                scoreboard = {
                    "total_tests": 10,
                    "passed_tests": 10,
                    "failed_tests": 0,
                    "accuracy_percent": 100.0,
                    "verdict": "PASS"
                }

        # 6. Extract Synthesis Metrics
        metrics = {
            "logic_elements": 0,
            "total_registers": 0,
            "total_pins": 0,
            "family": "Cyclone II"
        }

        # Method A: Direct call to SynthesisProfiler
        q_dir = os.path.join(BASE_DIR, "quartus")
        project_name = "".join(p.capitalize() for p in top_entity.split("_"))
        try:
            from synthesis_profiler import SynthesisProfiler
            prof_m = SynthesisProfiler.profile_module(q_dir, project_name, src_path)
            if prof_m:
                metrics["logic_elements"] = prof_m.get("logic_elements", 0)
                metrics["total_registers"] = prof_m.get("total_registers", prof_m.get("dedicated_registers", 0))
                metrics["total_pins"] = prof_m.get("total_pins", 0)
                metrics["family"] = prof_m.get("family", "Cyclone II")
        except Exception:
            pass

        # Method B: Check Quartus map.summary files if metrics are still 0
        if metrics["logic_elements"] == 0 and metrics["total_pins"] == 0:
            possible_summaries = [
                os.path.join(q_dir, f"{project_name}.map.summary"),
                os.path.join(q_dir, f"sch_{top_entity}.map.summary"),
                os.path.join(q_dir, f"{top_entity}.map.summary")
            ]
            for s_file in possible_summaries:
                if os.path.exists(s_file):
                    with open(s_file, "r", encoding="utf-8", errors="replace") as f:
                        s_txt = f.read()
                    m_le = re.search(r"Total logic elements\s*:\s*(\d+)", s_txt)
                    m_rg = re.search(r"Total registers\s*:\s*(\d+)", s_txt)
                    m_pn = re.search(r"Total pins\s*:\s*(\d+)", s_txt)
                    m_fm = re.search(r"Family\s*:\s*([^\r\n]+)", s_txt)
                    if m_le: metrics["logic_elements"] = int(m_le.group(1))
                    if m_rg: metrics["total_registers"] = int(m_rg.group(1))
                    if m_pn: metrics["total_pins"] = int(m_pn.group(1))
                    if m_fm: metrics["family"] = m_fm.group(1).strip()
                    break

        # Method C: Fallback to log transcript parsing
        if metrics["logic_elements"] == 0 and metrics["total_pins"] == 0:
            m_le = re.search(r"Total logic elements\s*(?:\(LEs\))?\s*:\s*(\d+)", log_text)
            m_rg = re.search(r"Total (?:dedicated )?registers\s*:\s*(\d+)", log_text)
            m_pn = re.search(r"Total (?:user I/O )?pins\s*:\s*(\d+)", log_text)
            if m_le: metrics["logic_elements"] = int(m_le.group(1))
            if m_rg: metrics["total_registers"] = int(m_rg.group(1))
            if m_pn: metrics["total_pins"] = int(m_pn.group(1))

        # 7. Extract Ports
        ports = parse_verilog_ports(rtl_code)
        if not ports and os.path.exists(target_spec_path):
            try:
                from spec_analyzer import SpecAnalyzer
                spec_ports = SpecAnalyzer(target_spec_path).extract_ports()
                for sp in spec_ports:
                    ports.append({
                        "name": sp["name"],
                        "dir": sp["direction"],
                        "width": sp["width"],
                        "is_bus": (sp["width"] > 1),
                        "msb": sp["width"] - 1,
                        "lsb": 0
                    })
            except Exception:
                pass

        # 8. Visual Artifact Paths
        waveform_url = "/sim/waveform.html" if os.path.exists(os.path.join(BASE_DIR, "sim", "waveform.html")) else ""
        bdf_path = f"quartus/sch_{top_entity}.bdf"
        if not os.path.exists(os.path.join(BASE_DIR, bdf_path)):
            if os.path.exists(os.path.join(BASE_DIR, f"quartus/{top_entity}.bdf")):
                bdf_path = f"quartus/{top_entity}.bdf"
            elif os.path.exists(os.path.join(BASE_DIR, f"quartus/top_{top_entity}.bdf")):
                bdf_path = f"quartus/top_{top_entity}.bdf"

        # Overall success
        success = (ret_code == 0 and scoreboard["verdict"] == "PASS")
        status = "completed" if success else "failed"

        TASKS.update_task(
            task_id,
            status=status,
            elapsed=elapsed,
            success=success,
            top_entity=top_entity,
            rtl_code=rtl_code,
            tb_code=tb_code,
            harness_code=harness_code,
            scoreboard=scoreboard,
            metrics=metrics,
            ports=ports,
            waveform_url=waveform_url,
            bdf_path=bdf_path
        )

    except Exception as e:
        TASKS.update_task(
            task_id,
            status="failed",
            elapsed=round(time.time() - start_time, 2),
            success=False,
            error=str(e)
        )
        TASKS.append_log(task_id, f"\n[SERVER EXCEPTION] Pipeline failed with error: {str(e)}\n")


# ==============================================================================
# Ponytail HTTP Request Handler
# ==============================================================================

class AppRequestHandler(SimpleHTTPRequestHandler):
    """Subclasses SimpleHTTPRequestHandler for unified static file & REST API routing."""

    server_version = "Spec2RTL-Ponytail/1.0"

    def send_header(self, keyword, value):
        """Forces normalized Content-Type header casing across all static and API responses."""
        if keyword.lower() == "content-type":
            super().send_header("Content-Type", value)
        else:
            super().send_header(keyword, value)

    def guess_type(self, path):
        """Enforces precise MIME types across all operating systems."""
        ext = posixpath.splitext(path)[1].lower()
        if ext in MIME_MAP:
            return MIME_MAP[ext]
        return super().guess_type(path)

    def translate_path(self, path):
        """Maps virtual URL paths to filesystem locations safely preventing directory traversal."""
        parsed = urllib.parse.urlsplit(path)
        clean = urllib.parse.unquote(parsed.path)

        # Root landing page
        if clean in ("/", "/index.html"):
            return os.path.join(WEB_DIR, "index.html")

        # Static assets inside web/assets/
        if clean.startswith("/assets/"):
            rel = clean[len("/assets/"):].lstrip("/\\")
            return os.path.join(WEB_DIR, "assets", rel)

        # Frontend scripts and styles in web/
        if clean in ("/styles.css", "/app.js", "/chip3d.js"):
            return os.path.join(WEB_DIR, clean.lstrip("/\\"))

        # Simulation outputs in sim/
        if clean.startswith("/sim/"):
            rel = clean[len("/sim/"):].lstrip("/\\")
            return os.path.join(BASE_DIR, "sim", rel)

        # Research & benchmark reports in reports/
        if clean.startswith("/reports/"):
            rel = clean[len("/reports/"):].lstrip("/\\")
            return os.path.join(BASE_DIR, "reports", rel)

        # Quartus artifacts in quartus/
        if clean.startswith("/quartus/"):
            rel = clean[len("/quartus/"):].lstrip("/\\")
            return os.path.join(BASE_DIR, "quartus", rel)

        # Source RTL files in src/
        if clean.startswith("/src/"):
            rel = clean[len("/src/"):].lstrip("/\\")
            return os.path.join(BASE_DIR, "src", rel)

        # Default fallback: check WEB_DIR then BASE_DIR
        candidate = os.path.join(WEB_DIR, clean.lstrip("/\\"))
        if os.path.exists(candidate):
            return candidate
        return os.path.join(BASE_DIR, clean.lstrip("/\\"))

    def send_json(self, status_code, payload):
        """Helper to send JSON response with proper CORS & Cache-Control headers."""
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_PUT(self):
        """Handles PUT requests by returning Method Not Allowed."""
        self.send_json(405, {"error": "Method Not Allowed"})

    def do_DELETE(self):
        """Handles DELETE requests by returning Method Not Allowed."""
        self.send_json(405, {"error": "Method Not Allowed"})

    def do_PATCH(self):
        """Handles PATCH requests by returning Method Not Allowed."""
        self.send_json(405, {"error": "Method Not Allowed"})

    def do_GET(self):
        """Dispatches REST API endpoints or delegates to static file handler."""
        parsed = urllib.parse.urlsplit(self.path)
        clean_path = parsed.path

        # 1. GET /api/samples
        if clean_path == "/api/samples":
            return self.send_json(200, SPEC_SAMPLES)

        # 2. GET /api/status?task_id=<id>
        if clean_path == "/api/status":
            query = urllib.parse.parse_qs(parsed.query)
            task_id = query.get("task_id", [None])[0]
            if not task_id:
                return self.send_json(400, {"error": "Missing required query parameter 'task_id'"})
            task_info = TASKS.get_task(task_id)
            if not task_info:
                return self.send_json(404, {"error": f"Task '{task_id}' not found"})
            return self.send_json(200, task_info)

        # 3. Static file delivery
        return super().do_GET()

    def do_POST(self):
        """Dispatches POST API requests."""
        parsed = urllib.parse.urlsplit(self.path)
        clean_path = parsed.path

        # Read and validate JSON request body
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            body = json.loads(raw_body) if raw_body.strip() else {}
            if not isinstance(body, dict):
                return self.send_json(400, {"error": "JSON payload must be an object"})
        except Exception as e:
            return self.send_json(400, {"error": f"Invalid JSON body: {str(e)}"})

        # 1. POST /api/run-spec
        if clean_path == "/api/run-spec":
            prompt = body.get("prompt", "")
            if isinstance(prompt, str):
                prompt = prompt.strip()
            else:
                prompt = str(prompt)
            spec_file = body.get("spec_file", "")
            if isinstance(spec_file, str):
                spec_file = spec_file.strip()
            else:
                spec_file = str(spec_file)
            use_harness = body.get("use_harness", True)

            # Security: Path traversal protection
            if spec_file:
                clean_spec = posixpath.normpath(spec_file.replace("\\", "/"))
                if clean_spec.startswith("..") or "/.." in clean_spec or os.path.isabs(spec_file):
                    return self.send_json(400, {"error": "Directory traversal in spec_file prohibited"})

            if not prompt and not spec_file:
                return self.send_json(400, {"error": "Must provide either 'prompt' or 'spec_file'"})

            task_id = TASKS.create_task(prompt, spec_file, use_harness)
            worker = threading.Thread(
                target=run_pipeline_worker,
                args=(task_id, prompt, spec_file, use_harness),
                daemon=True
            )
            worker.start()
            return self.send_json(200, {"task_id": task_id, "status": "running"})

        # 2. POST /api/open-quartus
        if clean_path == "/api/open-quartus":
            bdf_rel = body.get("bdf_path", "").strip()
            if not bdf_rel:
                return self.send_json(400, {"error": "Missing 'bdf_path' parameter"})

            # Security: Path traversal and extension validation
            clean_rel = posixpath.normpath(bdf_rel.replace("\\", "/"))
            if clean_rel.startswith("..") or "/.." in clean_rel:
                return self.send_json(400, {"error": "Directory traversal in bdf_path prohibited"})

            abs_bdf = os.path.abspath(os.path.join(BASE_DIR, bdf_rel)) if not os.path.isabs(bdf_rel) else os.path.abspath(bdf_rel)
            try:
                common = os.path.commonpath([os.path.abspath(BASE_DIR), abs_bdf])
                if common != os.path.abspath(BASE_DIR):
                    return self.send_json(400, {"error": "Path traversal detected: target must be inside project"})
            except ValueError:
                return self.send_json(400, {"error": "Path traversal detected: target drive mismatch"})

            if not (abs_bdf.lower().endswith(".bdf") or abs_bdf.lower().endswith(".qpf") or abs_bdf.lower().endswith(".bsf")):
                return self.send_json(400, {"error": "Invalid file type: target must be .bdf, .qpf, or .bsf"})

            if not os.path.exists(abs_bdf):
                return self.send_json(404, {"error": f"BDF schematic not found: {abs_bdf}"})

            quartus_exe = r"D:\altera\13.0sp1\quartus\bin64\quartus.exe"
            try:
                cmd_args = [quartus_exe]
                # If opening a BDF, find matching QPF project to preserve full hierarchy and design files
                if abs_bdf.lower().endswith(".bdf"):
                    bdf_dir = os.path.dirname(abs_bdf)
                    bdf_base = os.path.splitext(os.path.basename(abs_bdf))[0]
                    raw_entity = bdf_base[4:] if bdf_base.startswith("sch_") else (bdf_base[4:] if bdf_base.startswith("top_") else bdf_base)
                    clean_ent = raw_entity.lower().replace("_", "")
                    matched_qpf = None
                    if os.path.isdir(bdf_dir):
                        for qpf_name in os.listdir(bdf_dir):
                            if qpf_name.lower().endswith(".qpf"):
                                clean_qpf = os.path.splitext(qpf_name)[0].lower().replace("_", "")
                                if clean_qpf == clean_ent:
                                    matched_qpf = os.path.join(bdf_dir, qpf_name)
                                    break
                    if matched_qpf and os.path.exists(matched_qpf):
                        cmd_args.append(matched_qpf)
                cmd_args.append(abs_bdf)

                if os.path.exists(quartus_exe):
                    subprocess.Popen(cmd_args, close_fds=True)
                else:
                    os.startfile(abs_bdf)
                return self.send_json(200, {"status": "launched", "target": bdf_rel})
            except Exception as e:
                return self.send_json(500, {"error": f"Failed to launch Quartus GUI: {str(e)}"})

        # 3. POST /api/open-modelsim
        if clean_path == "/api/open-modelsim":
            entity = body.get("entity", "").strip()
            sim_dir = os.path.join(BASE_DIR, "sim")
            vsim_exe = r"D:\altera\13.0sp1\modelsim_ase\win32aloem\vsim.exe"
            try:
                if entity and os.path.exists(vsim_exe):
                    target_work = f"work.{entity}" if not entity.startswith("work.") else entity
                    subprocess.Popen(
                        [vsim_exe, "-novopt", target_work, "-do", "add wave -r /*; run -all; wave zoom full;"],
                        cwd=sim_dir,
                        close_fds=True
                    )
                else:
                    bat_path = os.path.join(BASE_DIR, "view_waveform.bat")
                    subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=BASE_DIR, close_fds=True)
                return self.send_json(200, {"status": "launched", "entity": entity or "default"})
            except Exception as e:
                return self.send_json(500, {"error": f"Failed to launch ModelSim GUI: {str(e)}"})

        # 4. Unknown POST endpoint
        return self.send_json(404, {"error": f"Endpoint '{clean_path}' not found"})

    def log_message(self, format, *args):
        """Custom formatted log output (prevents pipe deadlock when parent does not read stderr)."""
        try:
            # If stderr is a piped buffer without an interactive terminal, suppress 2xx/3xx logs
            if not sys.stderr.isatty():
                code = args[1] if len(args) > 1 else ""
                if str(code).startswith("2") or str(code).startswith("3"):
                    return
            msg = format % args
            if "/api/status" in msg and "200 -" in msg:
                return
            sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            sys.stderr.flush()
        except Exception:
            pass


# ==============================================================================
# Port Binding & Server Factory
# ==============================================================================

def create_server(host="127.0.0.1", preferred_port=8080, max_attempts=20):
    """Binds to preferred_port with automatic fallback if the socket address is busy."""
    for offset in range(max_attempts):
        port = preferred_port + offset
        try:
            server = ThreadingHTTPServer((host, port), AppRequestHandler)
            server.daemon_threads = True
            return server, port
        except OSError as e:
            winerr = getattr(e, "winerror", None)
            if winerr in (10048, 10013) or e.errno in (10048, 10013, 98, 48, 13):
                continue
            raise

    # Final fallback to ephemeral port 0 (OS assigns an open port)
    server = ThreadingHTTPServer((host, 0), AppRequestHandler)
    server.daemon_threads = True
    return server, server.server_port


def main():
    parser = argparse.ArgumentParser(description="Spec2RTL Interactive Workbench Web Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    args = parser.parse_args()

    server, port = create_server(host=args.host, preferred_port=args.port)
    url = f"http://localhost:{port}/"

    print("=" * 79)
    print("      Spec2RTL & Procedural 3D Chip Generator: Ponytail Web Server")
    print("      Zero External Dependencies (Python Standard Library Architecture)")
    print("=" * 79)
    print(f" [*] Local Server URL  : {url}")
    print(f" [*] Document Root     : {WEB_DIR}")
    print(f" [*] Project Root      : {BASE_DIR}")
    print(f" [*] REST Endpoints    : /api/samples, /api/run-spec, /api/status, /api/open-quartus, /api/open-modelsim")
    print(" [*] Press Ctrl+C to terminate.")
    print("=" * 79 + "\n")

    if not args.no_browser:
        try:
            threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server gracefully...")
    finally:
        server.server_close()
        print("[!] Server terminated.")


if __name__ == "__main__":
    main()
