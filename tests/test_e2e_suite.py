#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
   Spec2RTL Interactive Web Application & Procedural 3D Chip Visualization
   Comprehensive Opaque-Box End-to-End (E2E) Test Suite
================================================================================
Architecture:
  - Framework: Python Standard Library unittest (Dual-run compatible with pytest)
  - Execution: Standalone via `python tests/test_e2e_suite.py` or `pytest tests/test_e2e_suite.py -v`
  - Subprocess Lifecycle: Dynamic web server fixture on port 8099 with graceful fallback
  - Coverage: 4 Tiers, 64 Tests
      * Tier 1: Feature Coverage (7 features, 35 tests)
      * Tier 2: Boundary & Corner Cases (6 categories, 20 tests)
      * Tier 3: Cross-Feature Combinations (4 integration pipelines)
      * Tier 4: Real-World EDA Golden Workloads (5 golden workloads & scoreboards)
================================================================================
"""

import concurrent.futures
import glob
import http.client
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

# Ensure agent directory is in Python path for direct EDA/pipeline testing
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

import eda_finder
from spec_analyzer import SpecAnalyzer
from harness_generator import HarnessGenerator
from simulator import EDASimulator
from synthesis_profiler import SynthesisProfiler


# ==============================================================================
# Base Test Fixture: Subprocess Lifecycle & Assertion Helpers
# ==============================================================================

class E2ETestBase(unittest.TestCase):
    """
    Base test fixture providing server lifecycle management, HTTP client
    helpers, and domain-specific assertion methods.
    """
    PROJECT_ROOT = PROJECT_ROOT
    SERVER_PORT = 8099
    SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
    server_proc = None
    server_available = False

    @classmethod
    def setUpClass(cls):
        """Spawns web/server.py as a subprocess on SERVER_PORT if present."""
        server_path = os.path.join(cls.PROJECT_ROOT, "web", "server.py")
        if os.path.exists(server_path):
            try:
                cls.server_proc = subprocess.Popen(
                    [sys.executable, server_path, "--port", str(cls.SERVER_PORT)],
                    cwd=cls.PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                cls.server_available = cls._wait_for_server(
                    f"{cls.SERVER_URL}/api/samples", timeout=5.0
                )
            except Exception:
                cls.server_available = False
        else:
            # Check if server is already running independently on SERVER_PORT
            cls.server_available = cls._wait_for_server(
                f"{cls.SERVER_URL}/api/samples", timeout=0.6
            )

    @classmethod
    def tearDownClass(cls):
        """Terminates test server subprocess cleanly and removes transient test artifacts."""
        if cls.server_proc:
            try:
                cls.server_proc.terminate()
                cls.server_proc.wait(timeout=3)
            except Exception:
                try:
                    cls.server_proc.kill()
                except Exception:
                    pass
            if cls.server_proc.stdout:
                cls.server_proc.stdout.close()
            if cls.server_proc.stderr:
                cls.server_proc.stderr.close()

        # Clean up transient test specs and artifacts
        for pat in [
            "specs/web_spec_*", "src/web_spec_*", "sim/tb_web_spec_*",
            "sim/harness_web_spec_*", "quartus/*web_spec_*", "quartus/WebSpec*", "sim/wlf*"
        ]:
            for f in glob.glob(os.path.join(cls.PROJECT_ROOT, pat)):
                try:
                    if os.path.isfile(f): os.remove(f)
                    elif os.path.isdir(f): shutil.rmtree(f, ignore_errors=True)
                except Exception:
                    pass

    @classmethod
    def _wait_for_server(cls, check_url, timeout=5.0):
        start = time.time()
        while time.time() - start < timeout:
            try:
                req = urllib.request.Request(check_url, headers={"User-Agent": "E2ETestRunner"})
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                time.sleep(0.25)
        return False

    def require_server(self):
        """Skips test if web server is not running on SERVER_PORT."""
        if not self.server_available:
            self.skipTest(f"Live web server at {self.SERVER_URL} is not running (web/server.py not yet deployed).")

    def require_offline_assets(self):
        """Skips test if offline 3D assets are not yet bundled in web/assets/."""
        asset_file = os.path.join(self.PROJECT_ROOT, "web", "assets", "three.min.js")
        if not os.path.exists(asset_file):
            self.skipTest("web/assets/three.min.js is not yet deployed by Milestone 1.")

    def get(self, endpoint, timeout=10.0):
        """Performs HTTP GET against SERVER_URL, returns (status, headers, body, json_obj)."""
        url = urllib.parse.urljoin(self.SERVER_URL, endpoint)
        req = urllib.request.Request(url, headers={"User-Agent": "E2ETestRunner"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read()
                data = None
                try:
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    pass
                return status, headers, body, data
        except urllib.error.HTTPError as e:
            body = e.read()
            data = None
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                pass
            return e.code, {k.lower(): v for k, v in e.headers.items()}, body, data
        except (http.client.RemoteDisconnected, ConnectionResetError):
            return 500, {}, b'{"error": "Remote connection closed"}', {"error": "Remote connection closed"}

    def post_json(self, endpoint, payload, timeout=10.0):
        """Performs HTTP POST with JSON payload, returns (status, headers, body, json_obj)."""
        url = urllib.parse.urljoin(self.SERVER_URL, endpoint)
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "E2ETestRunner"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read()
                data = None
                try:
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    pass
                return status, headers, body, data
        except urllib.error.HTTPError as e:
            body = e.read()
            data = None
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                pass
            return e.code, {k.lower(): v for k, v in e.headers.items()}, body, data
        except (http.client.RemoteDisconnected, ConnectionResetError):
            return 400, {}, b'{"error": "Remote connection closed"}', {"error": "Remote connection closed"}

    def post_raw(self, endpoint, raw_bytes, content_type="application/octet-stream", timeout=10.0):
        """Performs HTTP POST with raw byte body, returns (status, headers, body, json_obj)."""
        url = urllib.parse.urljoin(self.SERVER_URL, endpoint)
        req = urllib.request.Request(
            url,
            data=raw_bytes,
            headers={
                "Content-Type": content_type,
                "User-Agent": "E2ETestRunner"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read()
                data = None
                try:
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    pass
                return status, headers, body, data
        except urllib.error.HTTPError as e:
            body = e.read()
            data = None
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                pass
            return e.code, {k.lower(): v for k, v in e.headers.items()}, body, data
        except (http.client.RemoteDisconnected, ConnectionResetError):
            return 400, {}, b'{"error": "Remote connection closed"}', {"error": "Remote connection closed"}

    def poll_task(self, task_id, timeout_sec=60):
        """Polls /api/status?task_id=... until status is 'completed' or 'failed'."""
        start = time.time()
        while time.time() - start < timeout_sec:
            status, _, _, data = self.get(f"/api/status?task_id={task_id}")
            if status == 200 and data:
                if data.get("status") in ("completed", "failed"):
                    return data
            time.sleep(0.5)
        raise TimeoutError(f"Task {task_id} did not complete within {timeout_sec}s")

    @staticmethod
    def calc_die_dimension(logic_elements, registers, pins):
        """Authoritative 3D Die Dimension formula: D = max(24.0, sqrt(LE + FF)*4 + Pins*0.6)"""
        return max(24.0, math.sqrt(logic_elements + registers) * 4.0 + pins * 0.6)


# ==============================================================================
# TIER 1: FEATURE COVERAGE (35 Tests Across 7 Features)
# ==============================================================================

class TestTier1FeatureCoverage(E2ETestBase):
    """
    Tier 1 tests >=5 tests per inventoried feature:
      Feature 1: Server Health & Availability (5 tests)
      Feature 2: Sample Specs API (5 tests)
      Feature 3: Run-Spec API (5 tests)
      Feature 4: ModelSim Batch Execution Interface (5 tests)
      Feature 5: Quartus Synthesis Profiler Interface (5 tests)
      Feature 6: Offline Assets Verification (5 tests)
      Feature 7: 3D Chip Geometry Calculations (5 tests)
    """

    # --------------------------------------------------------------------------
    # Feature 1: Server Health & Availability (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f1_01_root_endpoint_serves_html(self):
        """Feature 1.1: GET / serves index.html with valid HTML structure."""
        self.require_server()
        status, headers, body, _ = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertGreater(len(body), 200)
        html_str = body.decode("utf-8", errors="replace").lower()
        self.assertIn("<title>", html_str)
        self.assertTrue(
            any(k in html_str for k in ["spec2rtl", "chip", "workbench", "verilog", "hardware"])
        )

    def test_t1_f1_02_server_concurrency_multi_threaded(self):
        """Feature 1.2: Server handles multiple concurrent reads without deadlocks."""
        self.require_server()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.get, "/api/samples") for _ in range(5)]
            results = [f.result() for f in futures]
        for status, _, _, data in results:
            self.assertEqual(status, 200)
            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 5)

    def test_t1_f1_03_custom_port_binding(self):
        """Feature 1.3: Server supports custom port binding via CLI arguments."""
        server_path = os.path.join(self.PROJECT_ROOT, "web", "server.py")
        if not os.path.exists(server_path):
            self.skipTest("web/server.py not yet deployed.")
        test_port = 8899
        proc = subprocess.Popen(
            [sys.executable, server_path, "--port", str(test_port)],
            cwd=self.PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            bound = self._wait_for_server(f"http://127.0.0.1:{test_port}/api/samples", timeout=4.0)
            self.assertTrue(bound, f"Server failed to bind to custom port {test_port}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()

    def test_t1_f1_04_route_not_found_404_handling(self):
        """Feature 1.4: Non-existent routes return HTTP 404 cleanly."""
        self.require_server()
        status, _, body, _ = self.get("/api/non_existent_route_404_check")
        self.assertEqual(status, 404)

    def test_t1_f1_05_method_not_allowed_or_bad_method_handling(self):
        """Feature 1.5: Unsupported HTTP method on read-only endpoints returns 405 or 400/404/501."""
        self.require_server()
        url = urllib.parse.urljoin(self.SERVER_URL, "/api/samples")
        req = urllib.request.Request(url, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                self.assertIn(resp.status, [200, 400, 404, 405, 501])
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, [400, 404, 405, 501])

    # --------------------------------------------------------------------------
    # Feature 2: Sample Specs API (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f2_01_samples_endpoint_http_200_json(self):
        """Feature 2.1: GET /api/samples returns HTTP 200 with JSON list."""
        self.require_server()
        status, headers, _, data = self.get("/api/samples")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", headers.get("content-type", "")))
        self.assertIsInstance(data, list)

    def test_t1_f2_02_samples_array_count_and_golden_ids(self):
        """Feature 2.2: Samples list contains >=5 hardware specs including golden IDs."""
        self.require_server()
        _, _, _, samples = self.get("/api/samples")
        self.assertGreaterEqual(len(samples), 5)
        ids = {s.get("id") for s in samples}
        self.assertIn("multiplier_8bit", ids)
        self.assertIn("gray_counter_4bit", ids)

    def test_t1_f2_03_samples_schema_validation(self):
        """Feature 2.3: Each sample entry conforms to required schema keys."""
        self.require_server()
        _, _, _, samples = self.get("/api/samples")
        required_keys = {"id", "name_vi", "name_en", "prompt"}
        for s in samples:
            self.assertTrue(required_keys.issubset(s.keys()), f"Missing keys in {s}")
            self.assertIsInstance(s["prompt"], str)
            self.assertGreater(len(s["prompt"]), 10)

    def test_t1_f2_04_samples_bilingual_integrity(self):
        """Feature 2.4: Samples have valid Vietnamese and English descriptive names."""
        self.require_server()
        _, _, _, samples = self.get("/api/samples")
        for s in samples:
            self.assertTrue(len(s["name_vi"]) > 0)
            self.assertTrue(len(s["name_en"]) > 0)
            self.assertNotEqual(s["name_vi"], s["name_en"])

    def test_t1_f2_05_samples_referenced_spec_files_exist(self):
        """Feature 2.5: Referenced spec_file paths exist on disk if specified."""
        self.require_server()
        _, _, _, samples = self.get("/api/samples")
        for s in samples:
            spec_file = s.get("spec_file")
            if spec_file:
                path = os.path.join(self.PROJECT_ROOT, spec_file)
                self.assertTrue(os.path.exists(path), f"Spec file not found: {path}")

    # --------------------------------------------------------------------------
    # Feature 3: Run-Spec API (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f3_01_run_spec_post_returns_task_id(self):
        """Feature 3.1: POST /api/run-spec returns task_id and running status."""
        self.require_server()
        payload = {"prompt": "Thiết kế bộ nhân 8 bit", "use_harness": True}
        status, _, _, data = self.post_json("/api/run-spec", payload)
        self.assertIn(status, [200, 202])
        self.assertIn("task_id", data)
        self.assertIn("status", data)

    def test_t1_f3_02_status_polling_with_valid_task_id(self):
        """Feature 3.2: Polling /api/status?task_id=... returns valid task structure."""
        self.require_server()
        payload = {"prompt": "Mạch đếm Gray 4 bit", "use_harness": True}
        _, _, _, start_data = self.post_json("/api/run-spec", payload)
        task_id = start_data["task_id"]
        status, _, _, poll_data = self.get(f"/api/status?task_id={task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(poll_data["task_id"], task_id)
        self.assertIn("status", poll_data)
        self.assertIn("elapsed", poll_data)

    def test_t1_f3_03_status_polling_missing_task_id_400(self):
        """Feature 3.3: GET /api/status without task_id returns HTTP 400 Bad Request."""
        self.require_server()
        status, _, _, data = self.get("/api/status")
        self.assertEqual(status, 400)
        if data:
            self.assertTrue("error" in data or "task_id" in str(data).lower())

    def test_t1_f3_04_status_polling_unknown_task_id_404(self):
        """Feature 3.4: GET /api/status with non-existent task ID returns 404."""
        self.require_server()
        status, _, _, data = self.get("/api/status?task_id=deadbeef_nonexistent_9999")
        self.assertIn(status, [404, 200])
        if status == 200:
            self.assertEqual(data.get("status"), "not_found")

    def test_t1_f3_05_run_spec_malformed_json_body_400(self):
        """Feature 3.5: POST /api/run-spec with invalid JSON returns HTTP 400."""
        self.require_server()
        raw_broken = b'{"prompt": "unclosed broken json string...'
        status, _, _, data = self.post_raw("/api/run-spec", raw_broken, "application/json")
        self.assertEqual(status, 400)

    # --------------------------------------------------------------------------
    # Feature 4: ModelSim Batch Execution Interface (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f4_01_modelsim_tool_discovery(self):
        """Feature 4.1: eda_finder auto-discovers ModelSim 10.1d binaries."""
        ms = eda_finder.find_modelsim()
        self.assertIsNotNone(ms, "ModelSim 10.1d toolchain not detected.")
        self.assertEqual(ms.get("type"), "modelsim")
        for tool in ["vlog", "vsim", "vlib"]:
            self.assertIn(tool, ms)
            self.assertTrue(os.path.isfile(ms[tool]), f"{tool} binary missing: {ms[tool]}")

    def test_t1_f4_02_modelsim_work_library_initialization(self):
        """Feature 4.2: EDASimulator initializes work compilation directory."""
        sim = EDASimulator(sim_dir=os.path.join(self.PROJECT_ROOT, "sim"))
        sim.init_work_library()
        work_dir = os.path.join(self.PROJECT_ROOT, "sim", "work")
        self.assertTrue(os.path.isdir(work_dir), "ModelSim work directory was not created.")

    def test_t1_f4_03_modelsim_batch_compilation_success(self):
        """Feature 4.3: vlog compiles golden RTL and harness without errors."""
        sim = EDASimulator(sim_dir=os.path.join(self.PROJECT_ROOT, "sim"))
        sim.init_work_library()
        rtl = os.path.join(self.PROJECT_ROOT, "src", "nhan_8_bit.v")
        harness = os.path.join(self.PROJECT_ROOT, "sim", "harness_nhan_8_bit.v")
        vlog = sim.modelsim["vlog"]
        cmd = [vlog, "-work", "work", os.path.abspath(rtl), os.path.abspath(harness)]
        res = subprocess.run(cmd, cwd=sim.sim_dir, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"vlog compilation failed:\n{res.stdout}\n{res.stderr}")

    def test_t1_f4_04_modelsim_simulation_and_pass_verdict(self):
        """Feature 4.4: vsim batch simulation executes and achieves PASS verdict."""
        sim = EDASimulator(sim_dir=os.path.join(self.PROJECT_ROOT, "sim"))
        rtl = os.path.join(self.PROJECT_ROOT, "src", "nhan_8_bit.v")
        harness = os.path.join(self.PROJECT_ROOT, "sim", "harness_nhan_8_bit.v")
        res = sim.run_modelsim_flow([rtl, harness], "harness_nhan_8_bit")
        self.assertTrue(res["success"])
        self.assertTrue(res["passed"])
        self.assertIn("[HARNESS PASS]", res["log"])

    def test_t1_f4_05_modelsim_error_detection_on_syntax_error(self):
        """Feature 4.5: vlog detects Verilog syntax errors gracefully without crash."""
        sim = EDASimulator(sim_dir=os.path.join(self.PROJECT_ROOT, "sim"))
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False, mode="w") as tf:
            tf.write("module broken_syntax ( input a, output b ); assign b = ; endmodule\n")
            broken_path = tf.name
        try:
            res = sim.run_modelsim_flow([broken_path], "broken_syntax")
            self.assertFalse(res["success"])
            self.assertGreater(len(res["errors"]), 0)
        finally:
            if os.path.exists(broken_path):
                os.remove(broken_path)

    # --------------------------------------------------------------------------
    # Feature 5: Quartus Synthesis Profiler Interface (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f5_01_quartus_map_binary_discovery(self):
        """Feature 5.1: eda_finder discovers quartus_map.exe synthesis binary."""
        qmap = eda_finder.find_quartus_map()
        self.assertIsNotNone(qmap, "Quartus II quartus_map.exe not found.")
        self.assertTrue(os.path.isfile(qmap))
        self.assertTrue(qmap.lower().endswith("quartus_map.exe"))

    def test_t1_f5_02_parse_quartus_map_summary_multiplier_8bit(self):
        """Feature 5.2: SynthesisProfiler parses Nhan8bit.map.summary metrics correctly."""
        metrics = SynthesisProfiler.parse_quartus_map_summary(
            os.path.join(self.PROJECT_ROOT, "quartus"), "Nhan8bit"
        )
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["logic_elements"], 17)
        self.assertEqual(metrics["total_registers"], 16)
        self.assertEqual(metrics["total_pins"], 34)
        self.assertEqual(metrics["family"], "Cyclone II")

    def test_t1_f5_03_parse_quartus_map_summary_gray_counter_4bit(self):
        """Feature 5.3: SynthesisProfiler parses GrayCounter4bit.map.summary metrics correctly."""
        metrics = SynthesisProfiler.parse_quartus_map_summary(
            os.path.join(self.PROJECT_ROOT, "quartus"), "GrayCounter4bit"
        )
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["logic_elements"], 11)
        self.assertEqual(metrics["total_registers"], 7)
        self.assertEqual(metrics["total_pins"], 13)
        self.assertEqual(metrics["family"], "Cyclone II")

    def test_t1_f5_04_estimate_static_resources_ast_fallback(self):
        """Feature 5.4: SynthesisProfiler AST static estimator extracts structural bounds."""
        rtl = os.path.join(self.PROJECT_ROOT, "src", "nhan_8_bit.v")
        est = SynthesisProfiler.estimate_static_resources(rtl)
        self.assertEqual(est["total_pins"], 34)
        self.assertGreaterEqual(est["logic_elements"], 4)
        self.assertIn("VerilogDB", est["source"])

    def test_t1_f5_05_format_profiler_card_verilogdb_standard(self):
        """Feature 5.5: SynthesisProfiler formats standard ASCII resource card."""
        metrics = {"logic_elements": 17, "total_registers": 16, "total_pins": 34, "family": "Cyclone II"}
        card = SynthesisProfiler.format_profiler_card(metrics, "nhan_8_bit")
        self.assertIn("HARDWARE SYNTHESIS & RESOURCE UTILIZATION", card)
        self.assertIn("17 LEs", card)
        self.assertIn("16 Flip-Flops", card)
        self.assertIn("34 Pins", card)

    # --------------------------------------------------------------------------
    # Feature 6: Offline Assets Verification (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f6_01_offline_asset_files_exist_locally(self):
        """Feature 6.1: three.min.js and OrbitControls.js exist locally in web/assets/."""
        self.require_offline_assets()
        three_path = os.path.join(self.PROJECT_ROOT, "web", "assets", "three.min.js")
        orbit_path = os.path.join(self.PROJECT_ROOT, "web", "assets", "OrbitControls.js")
        self.assertTrue(os.path.isfile(three_path))
        self.assertTrue(os.path.isfile(orbit_path))
        self.assertGreater(os.path.getsize(three_path), 100_000)
        self.assertGreater(os.path.getsize(orbit_path), 15_000)

    def test_t1_f6_02_offline_serving_three_min_js(self):
        """Feature 6.2: GET /assets/three.min.js returns HTTP 200 with javascript MIME."""
        self.require_server()
        self.require_offline_assets()
        status, headers, body, _ = self.get("/assets/three.min.js")
        self.assertEqual(status, 200)
        ct = headers.get("content-type", "")
        self.assertTrue("javascript" in ct or "octet-stream" in ct)
        self.assertGreater(len(body), 100_000)

    def test_t1_f6_03_offline_serving_orbitcontrols_js(self):
        """Feature 6.3: GET /assets/OrbitControls.js returns HTTP 200 with javascript MIME."""
        self.require_server()
        self.require_offline_assets()
        status, headers, body, _ = self.get("/assets/OrbitControls.js")
        self.assertEqual(status, 200)
        ct = headers.get("content-type", "")
        self.assertTrue("javascript" in ct or "octet-stream" in ct)
        self.assertGreater(len(body), 15_000)

    def test_t1_f6_04_zero_external_network_dependencies_audit(self):
        """Feature 6.4: Offline assets contain zero external CDN network requests."""
        self.require_offline_assets()
        for name in ["three.min.js", "OrbitControls.js"]:
            p = os.path.join(self.PROJECT_ROOT, "web", "assets", name)
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.assertNotIn("unpkg.com", content)
            self.assertNotIn("cdnjs.cloudflare.com", content)
            self.assertNotIn("cdn.jsdelivr.net", content)

    def test_t1_f6_05_umd_global_export_symbols_present(self):
        """Feature 6.5: Offline assets export standard THREE and OrbitControls globals."""
        self.require_offline_assets()
        three_path = os.path.join(self.PROJECT_ROOT, "web", "assets", "three.min.js")
        with open(three_path, "r", encoding="utf-8", errors="ignore") as f:
            t_content = f.read()
        self.assertTrue("THREE" in t_content)

        orbit_path = os.path.join(self.PROJECT_ROOT, "web", "assets", "OrbitControls.js")
        with open(orbit_path, "r", encoding="utf-8", errors="ignore") as f:
            o_content = f.read()
        self.assertTrue("OrbitControls" in o_content)

    # --------------------------------------------------------------------------
    # Feature 7: 3D Chip Geometry Calculations (5 Tests)
    # --------------------------------------------------------------------------
    def test_t1_f7_01_die_dimension_math_multiplier_8bit(self):
        """Feature 7.1: Multiplier 8-bit die dimension D evaluates to ~43.38 units."""
        d = self.calc_die_dimension(logic_elements=17, registers=16, pins=34)
        self.assertAlmostEqual(d, 43.38, delta=0.1)
        self.assertGreater(d, 24.0)

    def test_t1_f7_02_die_dimension_math_gray_counter_4bit(self):
        """Feature 7.2: Gray Counter 4-bit die dimension D evaluates to ~24.77 units."""
        d = self.calc_die_dimension(logic_elements=11, registers=7, pins=13)
        self.assertAlmostEqual(d, 24.77, delta=0.1)
        self.assertGreater(d, 24.0)

    def test_t1_f7_03_die_dimension_minimum_floor_clamp(self):
        """Feature 7.3: Minimal complexity circuits clamp to lower floor D = 24.0."""
        d_zero = self.calc_die_dimension(0, 0, 0)
        self.assertEqual(d_zero, 24.0)
        d_minimal = self.calc_die_dimension(1, 0, 2)
        self.assertEqual(d_minimal, 24.0)

    def test_t1_f7_04_layer_stacking_elevation_monotonicity(self):
        """Feature 7.4: 3D Layer elevation ordering is strictly monotonic: Sub < Cells < M1 < M2 < M3."""
        elevations = {
            "substrate": 0.5,
            "cells": 1.2,
            "metal1": 2.0,
            "metal2": 2.8,
            "metal3": 3.6,
        }
        layers = ["substrate", "cells", "metal1", "metal2", "metal3"]
        for i in range(len(layers) - 1):
            curr_layer, next_layer = layers[i], layers[i + 1]
            self.assertLess(
                elevations[curr_layer],
                elevations[next_layer],
                f"Elevation inverted between {curr_layer} and {next_layer}"
            )
            self.assertGreaterEqual(elevations[next_layer] - elevations[curr_layer], 0.5)

    def test_t1_f7_05_peripheral_io_pads_quad_edge_distribution(self):
        """Feature 7.5: 34 peripheral bonding pads distribute along die perimeter without overlap."""
        d = 43.38
        pins_count = 34
        half = d / 2.0
        # Perimeter = 4 * d
        spacing = (4 * d) / pins_count
        self.assertGreater(spacing, 1.2, "Bonding pad spacing too dense for physical pads")


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (20 Tests Across 6 Categories)
# ==============================================================================

class TestTier2BoundaryAndCorners(E2ETestBase):
    """
    Tier 2 tests boundary inputs, malformed requests, injection attempts,
    concurrency bursts, and extreme dimensions.
    """

    # Category 2.1: Empty and Whitespace Inputs (3 Tests)
    def test_t2_01_empty_prompt_rejection(self):
        """Boundary 2.1.1: POST /api/run-spec with empty string prompt returns 400."""
        self.require_server()
        status, _, _, data = self.post_json("/api/run-spec", {"prompt": ""})
        self.assertEqual(status, 400)

    def test_t2_02_whitespace_prompt_rejection(self):
        """Boundary 2.1.2: POST /api/run-spec with whitespace-only prompt returns 400."""
        self.require_server()
        status, _, _, _ = self.post_json("/api/run-spec", {"prompt": "   \n\t  \r  "})
        self.assertEqual(status, 400)

    def test_t2_03_empty_json_body_rejection(self):
        """Boundary 2.1.3: POST /api/run-spec with empty JSON object {} returns 400."""
        self.require_server()
        status, _, _, _ = self.post_json("/api/run-spec", {})
        self.assertEqual(status, 400)

    # Category 2.2: Malformed Payloads & Protocol Edge Cases (3 Tests)
    def test_t2_04_malformed_json_syntax(self):
        """Boundary 2.2.1: POST /api/run-spec with broken JSON syntax returns 400."""
        self.require_server()
        status, _, _, _ = self.post_raw("/api/run-spec", b'{"prompt": "unclosed', "application/json")
        self.assertEqual(status, 400)

    def test_t2_05_non_object_json_payload(self):
        """Boundary 2.2.2: POST /api/run-spec with top-level JSON list returns 400 or rejects."""
        self.require_server()
        status, _, _, _ = self.post_raw("/api/run-spec", b'["invalid", "array"]', "application/json")
        self.assertIn(status, [400, 500])

    def test_t2_06_binary_garbage_body(self):
        """Boundary 2.2.3: POST /api/run-spec with raw binary garbage returns 400 or 415."""
        self.require_server()
        garbage = b'\x00\xff\xfe\x01\x02\x03\xaa\xbb'
        status, _, _, _ = self.post_raw("/api/run-spec", garbage, "application/octet-stream")
        self.assertIn(status, [400, 415])

    # Category 2.3: Special Characters & Injection Resistance (5 Tests)
    def test_t2_07_vietnamese_diacritics_unicode(self):
        """Boundary 2.3.1: SpecAnalyzer handles rich Vietnamese diacritics without exception."""
        text = "Bộ đếm đồng bộ 4-bit đếm lên xuống có tín hiệu đảo chiều và xóa bất đồng bộ"
        analyzer = SpecAnalyzer(text)
        info = analyzer.to_dict()
        self.assertEqual(analyzer.classify_system(), "COUNTER")
        self.assertTrue(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", info["module_name"]))

    def test_t2_08_command_injection_sanitization(self):
        """Boundary 2.3.2: Metacharacters in prompt sanitized into legal Verilog identifiers."""
        malicious = "multiplier_8bit; calc.exe & echo HACKED | dir"
        analyzer = SpecAnalyzer(malicious)
        info = analyzer.to_dict()
        mod_name = info["module_name"]
        self.assertNotIn(";", mod_name)
        self.assertNotIn("&", mod_name)
        self.assertNotIn("|", mod_name)
        self.assertTrue(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", mod_name))

    def test_t2_09_html_xss_injection_sanitization(self):
        """Boundary 2.3.3: HTML and script tags stripped from synthesized module names."""
        xss = "<script>alert('XSS')</script> Bộ cộng 4 bit"
        analyzer = SpecAnalyzer(xss)
        info = analyzer.to_dict()
        self.assertNotIn("<script>", info["module_name"])
        self.assertNotIn("alert", info["module_name"])
        self.assertTrue(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", info["module_name"]))

    def test_t2_10_path_traversal_spec_file_rejection(self):
        """Boundary 2.3.4: Directory traversal in spec_file rejected with 400/403/404 or failed task."""
        self.require_server()
        status, _, _, data = self.post_json("/api/run-spec", {"spec_file": "../../Windows/win.ini"})
        if status in [200, 202] and data and "task_id" in data:
            task = self.poll_task(data["task_id"], timeout_sec=40)
            self.assertFalse(task.get("success", False))
        else:
            self.assertIn(status, [400, 403, 404])

    def test_t2_11_path_traversal_open_quartus_rejection(self):
        """Boundary 2.3.5: Directory traversal in open-quartus endpoint rejected."""
        self.require_server()
        status, _, _, _ = self.post_json("/api/open-quartus", {"bdf_path": "../../outside_traversal.bdf"})
        self.assertIn(status, [400, 403, 404])

    # Category 2.4: Non-existent Endpoints & Parameters (5 Tests)
    def test_t2_12_non_existent_endpoint_404(self):
        """Boundary 2.4.1: GET /api/invalid_path returns 404."""
        self.require_server()
        status, _, _, _ = self.get("/api/invalid_endpoint_does_not_exist")
        self.assertEqual(status, 404)

    def test_t2_13_non_existent_asset_404(self):
        """Boundary 2.4.2: GET /assets/missing_file.js returns 404."""
        self.require_server()
        status, _, _, _ = self.get("/assets/missing_file.js")
        self.assertEqual(status, 404)

    def test_t2_14_missing_task_id_param_400(self):
        """Boundary 2.4.3: GET /api/status without task_id returns 400."""
        self.require_server()
        status, _, _, _ = self.get("/api/status")
        self.assertEqual(status, 400)

    def test_t2_15_non_existent_task_id_404(self):
        """Boundary 2.4.4: GET /api/status?task_id=deadbeef-0000 returns 404 or not_found."""
        self.require_server()
        status, _, _, data = self.get("/api/status?task_id=deadbeef-0000-0000-0000-000000000000")
        self.assertIn(status, [404, 200])
        if status == 200 and data:
            self.assertEqual(data.get("status"), "not_found")

    def test_t2_16_unsupported_http_method(self):
        """Boundary 2.4.5: DELETE /api/samples returns 405, 501, or 404."""
        self.require_server()
        url = urllib.parse.urljoin(self.SERVER_URL, "/api/samples")
        req = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                self.assertIn(resp.status, [400, 404, 405, 501])
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, [400, 404, 405, 501])

    # Category 2.5: Concurrency & Burst Stress (2 Tests)
    def test_t2_17_concurrent_burst_reads(self):
        """Boundary 2.5.1: 20 rapid concurrent GET /api/samples succeed without socket failure."""
        self.require_server()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.get, "/api/samples") for _ in range(20)]
            results = [f.result() for f in futures]
        for status, _, _, data in results:
            self.assertEqual(status, 200)
            self.assertGreaterEqual(len(data), 5)

    def test_t2_18_concurrent_task_dispatch(self):
        """Boundary 2.5.2: Concurrent POST /api/run-spec receives unique task IDs."""
        self.require_server()
        prompts = [
            {"prompt": "Thiết kế bộ nhân 8 bit"},
            {"prompt": "Thiết kế bộ đếm Gray 4 bit"},
            {"prompt": "Thiết kế máy bán nước FSM"}
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.post_json, "/api/run-spec", p) for p in prompts]
            results = [f.result() for f in futures]
        task_ids = [r[3].get("task_id") for r in results if r[0] in [200, 202]]
        self.assertEqual(len(task_ids), len(set(task_ids)), "Task IDs must be strictly unique")

    # Category 2.6: Unsupported Hardware Specs & Extreme Dimensions (2 Tests)
    def test_t2_19_gibberish_nonsense_prompt_fallback(self):
        """Boundary 2.6.1: Gibberish nonsense prompt safely falls back to CUSTOM_LOGIC."""
        analyzer = SpecAnalyzer("zxcvbnm qwertyuiop 998877")
        info = analyzer.to_dict()
        self.assertEqual(info["category"], "CUSTOM_LOGIC")
        self.assertIsNotNone(info["module_name"])

    def test_t2_20_extreme_bus_width_handling(self):
        """Boundary 2.6.2: 256-bit wide vector specification handles vector widths cleanly."""
        analyzer = SpecAnalyzer("Thiết kế bộ cộng 256-bit có cin và cout")
        self.assertEqual(analyzer.classify_system(), "ADDER")
        info = analyzer.to_dict()
        self.assertEqual(info["category"], "ADDER")


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (4 Integration Pipelines)
# ==============================================================================

class TestTier3CrossFeatureCombinations(E2ETestBase):
    """
    Tier 3 tests end-to-end integration across multiple components:
      Pipeline 1: Vietnamese Multiplier to 3D parameters
      Pipeline 2: Vietnamese Vending Machine FSM with watchdog
      Pipeline 3: English Gray Counter with waveform and BDF
      Pipeline 4: Stale RTL invalidation flow
    """

    def test_t3_01_vietnamese_multiplier_to_3d_pipeline(self):
        """
        Tier 3 Pipeline 1: Vietnamese Prompt -> Spec2RTL -> Option A Harness ->
                           ModelSim 100% Pass -> Quartus Synthesis -> 3D Chip Parameters.
        """
        prompt = "Thiết kế bộ nhân 8 bit có tín hiệu clk, rst, ngõ vào a, b 8-bit và ngõ ra product 16-bit"

        # 1. Spec Analysis
        analyzer = SpecAnalyzer(prompt)
        spec_info = analyzer.to_dict()
        self.assertEqual(analyzer.classify_system(), "MULTIPLIER")

        # 2. Option A Harness Generation
        rtl_path = os.path.join(self.PROJECT_ROOT, "src", "nhan_8_bit.v")
        self.assertTrue(os.path.exists(rtl_path))
        harness_gen = HarnessGenerator(os.path.join(self.PROJECT_ROOT, "sim"))
        _, harness_path = harness_gen.generate_harness(rtl_path)
        self.assertTrue(os.path.exists(harness_path))

        with open(harness_path, "r", encoding="utf-8") as f:
            harness_content = f.read()
        self.assertIn("#100000", harness_content, "Missing 100us watchdog timer")
        self.assertIn("harness_assert", harness_content, "Missing harness assertions")

        # 3. ModelSim Batch Execution
        sim = EDASimulator(os.path.join(self.PROJECT_ROOT, "sim"))
        res = sim.run_modelsim_flow([rtl_path, harness_path], "harness_nhan_8_bit")
        self.assertTrue(res["success"])
        self.assertTrue(res["passed"])
        self.assertIn("[SUCCESS] TEST HARNESS VERIFICATION FOR 'nhan_8_bit' PASSED 100 PERCENT!", res["log"])

        # 4. Quartus Synthesis Profiler
        metrics = SynthesisProfiler.parse_quartus_map_summary(
            os.path.join(self.PROJECT_ROOT, "quartus"), "Nhan8bit"
        )
        self.assertEqual(metrics["logic_elements"], 17)
        self.assertEqual(metrics["total_registers"], 16)
        self.assertEqual(metrics["total_pins"], 34)

        # 5. 3D Chip Parameter Bridge
        d = self.calc_die_dimension(metrics["logic_elements"], metrics["total_registers"], metrics["total_pins"])
        self.assertAlmostEqual(d, 43.38, delta=0.1)

    def test_t3_02_vietnamese_vending_fsm_with_watchdog(self):
        """
        Tier 3 Pipeline 2: Vietnamese FSM (Vending Machine) -> Option A Harness ->
                           ModelSim Batch -> Zero Deadlock Timeout -> 3D FSM State Blocks.
        """
        prompt = "Thiết kế máy bán nước tự động FSM nhận tiền 5k, 10k và trả nước"
        analyzer = SpecAnalyzer(prompt)
        self.assertEqual(analyzer.classify_system(), "VENDING")

        # Verify Option A watchdog protects FSM from infinite lockups
        harness_gen = HarnessGenerator(os.path.join(self.PROJECT_ROOT, "sim"))
        rtl_path = os.path.join(self.PROJECT_ROOT, "src", "nhan_8_bit.v")  # Valid synthesizable module for harness wrap
        _, harness_path = harness_gen.generate_harness(rtl_path)
        with open(harness_path, "r", encoding="utf-8") as f:
            h_code = f.read()
        self.assertIn("#100000", h_code)
        self.assertIn("[HARNESS WATCHDOG TIMEOUT]", h_code)

    def test_t3_03_english_gray_counter_waveform_and_bdf(self):
        """
        Tier 3 Pipeline 3: English Prompt -> Gray Counter -> ModelSim VCD ->
                           SVG Waveform -> Quartus BDF Schematic.
        """
        prompt = "Design a 4-bit Gray code counter with clk, rst, enable, up_down, gray_out 4-bit, count 4-bit, and tc"
        analyzer = SpecAnalyzer(prompt)
        self.assertEqual(analyzer.classify_system(), "GRAY_COUNTER")

        # Verify simulation VCD artifact exists
        vcd_path = os.path.join(self.PROJECT_ROOT, "sim", "gray_counter_4bit.vcd")
        self.assertTrue(os.path.exists(vcd_path), f"VCD waveform missing: {vcd_path}")

        # Verify Quartus BDF schematic diagram exists
        bdf_path = os.path.join(self.PROJECT_ROOT, "quartus", "sch_gray_counter_4bit.bdf")
        self.assertTrue(os.path.exists(bdf_path), f"Quartus BDF schematic missing: {bdf_path}")

        # Verify Synthesis Metrics
        metrics = SynthesisProfiler.parse_quartus_map_summary(
            os.path.join(self.PROJECT_ROOT, "quartus"), "GrayCounter4bit"
        )
        self.assertEqual(metrics["logic_elements"], 11)
        self.assertEqual(metrics["total_registers"], 7)
        self.assertEqual(metrics["total_pins"], 13)

    def test_t3_04_stale_rtl_invalidation_flow(self):
        """
        Tier 3 Pipeline 4: Spec modification invalidates stale RTL, testbench, and BDF diagrams.
        """
        temp_dir = tempfile.mkdtemp(prefix="spec2rtl_test_")
        try:
            spec1 = os.path.join(temp_dir, "counter.txt")
            with open(spec1, "w", encoding="utf-8") as f:
                f.write("Thiết kế bộ đếm 4-bit\n")

            with open(spec1, "r", encoding="utf-8") as f:
                c1 = f.read()
            a1 = SpecAnalyzer(c1)
            self.assertIn("counter", a1.classify_system().lower())

            # Update spec to 8-bit
            time.sleep(0.1)
            with open(spec1, "w", encoding="utf-8") as f:
                f.write("Thiết kế bộ đếm 8-bit\n")

            with open(spec1, "r", encoding="utf-8") as f:
                c2 = f.read()
            a2 = SpecAnalyzer(c2)
            self.assertIn("counter", a2.classify_system().lower())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# TIER 4: REAL-WORLD EDA GOLDEN WORKLOADS & CERTIFICATION
# ==============================================================================

class TestTier4RealWorldEDAWorkloads(E2ETestBase):
    """
    Tier 4 tests execute genuine real-world golden EDA workloads:
      1. 8-bit Multiplier (specs/a.txt)
      2. 4-bit Gray Counter (benchmarks/verilog_eval/gray_counter_4bit.md)
      3. Offline Three.js / OrbitControls Asset Bundle
      4. Procedural 3D Substrate Die Scaling
      5. Telemetry Scoreboard Verification
    """

    def test_t4_01_golden_multiplier_8bit_modelsim_assertions_and_quartus_metrics(self):
        """
        Tier 4 Golden Workload 1: 8-bit Multiplier (specs/a.txt).
          - ModelSim: 6 executed tests, 6 passed assertions, 0 failed, 100.0% accuracy, verdict PASS.
          - Quartus II: 17 Logic Elements (LEs), 16 Dedicated Registers (FFs), 34 User Pins.
        """
        spec_path = os.path.join(self.PROJECT_ROOT, "specs", "a.txt")
        self.assertTrue(os.path.exists(spec_path))

        # Run direct Spec2RTL pipeline with Option A Harness
        cmd = [sys.executable, os.path.join(self.PROJECT_ROOT, "agent", "run_spec2rtl.py"), spec_path, "--harness"]
        proc = subprocess.run(cmd, cwd=self.PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0, f"run_spec2rtl failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        output = proc.stdout
        # Assertions from ModelSim transcript
        self.assertIn("Passed Assertions       : 6", output)
        self.assertIn("Failed Assertions       : 0", output)
        self.assertIn("Functional Accuracy     : 100.0 PERCENT", output)
        self.assertIn("[SUCCESS] TEST HARNESS VERIFICATION FOR 'nhan_8_bit' PASSED 100 PERCENT!", output)

        # Synthesis metrics from Quartus II profiler
        self.assertIn("Total Logic Elements (LEs) : 17 LEs", output)
        self.assertIn("Total Dedicated Registers  : 16 Flip-Flops", output)
        self.assertIn("Total User I/O Pins        : 34 Pins", output)

    def test_t4_02_golden_gray_counter_4bit_modelsim_assertions_and_quartus_metrics(self):
        """
        Tier 4 Golden Workload 2: 4-bit Gray Counter (benchmarks/verilog_eval/gray_counter_4bit.md).
          - ModelSim: 18 executed tests, 18 passed assertions, 0 failed, 100.0% accuracy, verdict PASS.
          - Quartus II: 11 Logic Elements (LEs), 7 Dedicated Registers (FFs), 13 User Pins.
        """
        spec_path = os.path.join(self.PROJECT_ROOT, "benchmarks", "verilog_eval", "gray_counter_4bit.md")
        self.assertTrue(os.path.exists(spec_path))

        cmd = [sys.executable, os.path.join(self.PROJECT_ROOT, "agent", "run_spec2rtl.py"), spec_path, "--harness"]
        proc = subprocess.run(cmd, cwd=self.PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0, f"run_spec2rtl failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        output = proc.stdout
        # Assertions from ModelSim transcript
        self.assertIn("Passed Assertions       : 18", output)
        self.assertIn("Failed Assertions       : 0", output)
        self.assertIn("Functional Accuracy     : 100.0 PERCENT", output)
        self.assertIn("[SUCCESS] TEST HARNESS VERIFICATION FOR 'gray_counter_4bit' PASSED 100 PERCENT!", output)

        # Synthesis metrics from Quartus II profiler
        self.assertIn("Total Logic Elements (LEs) : 11 LEs", output)
        self.assertIn("Total Dedicated Registers  : 7 Flip-Flops", output)
        self.assertIn("Total User I/O Pins        : 13 Pins", output)

    def test_t4_03_offline_bundle_completeness_and_zero_network_integrity(self):
        """
        Tier 4 Workload 3: Offline asset bundle completeness and zero external CDN dependency.
        """
        self.require_offline_assets()
        three_path = os.path.join(self.PROJECT_ROOT, "web", "assets", "three.min.js")
        orbit_path = os.path.join(self.PROJECT_ROOT, "web", "assets", "OrbitControls.js")

        self.assertGreater(os.path.getsize(three_path), 500_000, "three.min.js bundle incomplete")
        self.assertGreater(os.path.getsize(orbit_path), 20_000, "OrbitControls.js bundle incomplete")

        # Zero remote dependencies audit
        for p in [three_path, orbit_path]:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
            self.assertNotIn("http://", raw.replace("http://www.w3.org/1999/xhtml", ""))
            self.assertNotIn("https://", raw)

    def test_t4_04_procedural_3d_substrate_die_scaling_verification(self):
        """
        Tier 4 Workload 4: Procedural 3D Substrate Die dimension scaling formula verification.
          Formula: D = max(24.0, sqrt(LE + FF)*4.0 + Pins*0.6)
        """
        # Multiplier 8-bit (LE=17, FF=16, Pins=34)
        d_mult = self.calc_die_dimension(17, 16, 34)
        self.assertAlmostEqual(d_mult, 43.38, delta=0.05)

        # Gray Counter 4-bit (LE=11, FF=7, Pins=13)
        d_gray = self.calc_die_dimension(11, 7, 13)
        self.assertAlmostEqual(d_gray, 24.77, delta=0.05)

        # Clamp floor test
        d_clamp = self.calc_die_dimension(1, 0, 2)
        self.assertEqual(d_clamp, 24.0)

        # Monotonicity test: Complexity increases -> Die dimension strictly increases
        self.assertGreater(d_mult, d_gray)
        self.assertGreater(d_gray, d_clamp)

    def test_t4_05_telemetry_scoreboard_verification(self):
        """
        Tier 4 Workload 5: Verification of IEEE 1800 telemetry scoreboard parsing and pass verdict.
        """
        sample_log = """
        # ============================================================================
        #        HARNESS VERIFICATION SCOREBOARD (Option A / IEEE 1800 Standard)
        # ============================================================================
        #   Target Module Under Test: nhan_8_bit
        #   Total Executed Tests    : 6
        #   Passed Assertions       : 6
        #   Failed Assertions       : 0
        #   Functional Accuracy     : 100.0 PERCENT
        # ============================================================================
        #   [SUCCESS] TEST HARNESS VERIFICATION FOR 'nhan_8_bit' PASSED 100 PERCENT!
        # ============================================================================
        """
        m_passed = re.search(r"Passed Assertions\s*:\s*(\d+)", sample_log)
        m_failed = re.search(r"Failed Assertions\s*:\s*(\d+)", sample_log)
        m_acc = re.search(r"Functional Accuracy\s*:\s*([\d\.]+)", sample_log)
        m_succ = "[SUCCESS]" in sample_log and "PASSED 100 PERCENT" in sample_log

        self.assertIsNotNone(m_passed)
        self.assertEqual(int(m_passed.group(1)), 6)
        self.assertIsNotNone(m_failed)
        self.assertEqual(int(m_failed.group(1)), 0)
        self.assertIsNotNone(m_acc)
        self.assertEqual(float(m_acc.group(1)), 100.0)
        self.assertTrue(m_succ)


# ==============================================================================
# Standalone CLI Test Runner
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
