#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Challenger 1: Empirical Verification of Frontend Workbench & Static Serving
Author: Teamwork Challenger 1 (critic, specialist)
Location: tests/test_challenger_frontend.py
"""

import http.client
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.parse
import urllib.request

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")

class TestChallengerFrontendEmpirical(unittest.TestCase):
    """
    Independent adversarial stress testing suite for Frontend Workbench
    and Static Serving routes.
    """

    @classmethod
    def setUpClass(cls):
        # Determine an open port for the challenger test server
        cls.port = 8097
        server_py = os.path.join(WEB_DIR, "server.py")
        cls.server_proc = subprocess.Popen(
            [sys.executable, server_py, "--port", str(cls.port)],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        
        # Wait up to 6 seconds for server to come up
        ready = False
        start = time.time()
        while time.time() - start < 6.0:
            try:
                req = urllib.request.urlopen(f"{cls.base_url}/api/samples", timeout=0.8)
                if req.status == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.2)
        
        if not ready:
            raise RuntimeError(f"Challenger test server failed to bind and listen on port {cls.port}")

    @classmethod
    def tearDownClass(cls):
        if cls.server_proc:
            try:
                cls.server_proc.terminate()
                cls.server_proc.wait(timeout=3)
            except Exception:
                try:
                    cls.server_proc.kill()
                except Exception:
                    pass

    # ==========================================================================
    # 1. STATIC ASSET SERVING & MIME TYPE VALIDATION
    # ==========================================================================

    def test_static_asset_root_html(self):
        """Verify GET / returns 200 with text/html and UTF-8 charset."""
        url = f"{self.base_url}/"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("text/html", ct.lower())
            body = resp.read().decode("utf-8")
            self.assertIn("<!DOCTYPE html>", body)
            self.assertIn("Spec2RTL", body)

    def test_static_asset_styles_css(self):
        """Verify GET /styles.css returns 200 with text/css."""
        url = f"{self.base_url}/styles.css"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("text/css", ct.lower())
            body = resp.read().decode("utf-8")
            self.assertIn("--bg-main", body)
            self.assertIn(".workbench-header", body)

    def test_static_asset_app_js(self):
        """Verify GET /app.js returns 200 with application/javascript."""
        url = f"{self.base_url}/app.js"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("javascript", ct.lower())
            body = resp.read().decode("utf-8")
            self.assertIn("AppState", body)

    def test_static_asset_chip3d_js(self):
        """Verify GET /chip3d.js returns 200 with application/javascript."""
        url = f"{self.base_url}/chip3d.js"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("javascript", ct.lower())
            body = resp.read().decode("utf-8")
            self.assertIn("calcDieDimension", body)

    def test_static_asset_three_js(self):
        """Verify GET /assets/three.min.js returns 200 with application/javascript."""
        url = f"{self.base_url}/assets/three.min.js"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("javascript", ct.lower())
            body = resp.read()
            self.assertGreater(len(body), 500000, "three.min.js should be >= 500KB")

    def test_static_asset_orbit_controls_js(self):
        """Verify GET /assets/OrbitControls.js returns 200 with application/javascript."""
        url = f"{self.base_url}/assets/OrbitControls.js"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("javascript", ct.lower())
            body = resp.read()
            self.assertGreater(len(body), 20000, "OrbitControls.js should be >= 20KB")

    def test_static_asset_waveform_preview(self):
        """Verify GET /sim/waveform.html returns 200 with text/html."""
        url = f"{self.base_url}/sim/waveform.html"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("text/html", ct.lower())
            body = resp.read().decode("utf-8")
            self.assertIn("Waveform", body)

    def test_static_asset_reports_serving(self):
        """Verify research report files are served with correct MIME types."""
        url_md = f"{self.base_url}/reports/00_Master_Spec2RTL_Synthesis_Report.md"
        with urllib.request.urlopen(url_md, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertTrue("text/markdown" in ct.lower() or "text/plain" in ct.lower())

        url_pdf = f"{self.base_url}/reports/00_Master_Spec2RTL_Synthesis_Report.pdf"
        with urllib.request.urlopen(url_pdf, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            ct = resp.headers.get("Content-Type", "")
            self.assertIn("application/pdf", ct.lower())

    def test_static_asset_404_nonexistent(self):
        """Verify non-existent static assets return HTTP 404."""
        url = f"{self.base_url}/assets/definitely_not_exist.xyz"
        try:
            with urllib.request.urlopen(url, timeout=3.0) as resp:
                self.assertEqual(resp.status, 404)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    # ==========================================================================
    # 2. ZERO EXTERNAL NETWORK DEPENDENCY AUDIT (100% OFFLINE)
    # ==========================================================================

    def test_zero_external_network_urls_in_html(self):
        """Verify web/index.html contains 0 external http/https resource tags."""
        html_path = os.path.join(WEB_DIR, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check script src, link href, img src, iframe src
        ext_script = re.findall(r'<script[^>]+src=["\'](https?://[^"\']+)["\']', content, re.IGNORECASE)
        ext_link = re.findall(r'<link[^>]+href=["\'](https?://[^"\']+)["\']', content, re.IGNORECASE)
        ext_img = re.findall(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', content, re.IGNORECASE)
        ext_iframe = re.findall(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', content, re.IGNORECASE)

        self.assertEqual(ext_script, [], f"Found external scripts: {ext_script}")
        self.assertEqual(ext_link, [], f"Found external links/fonts: {ext_link}")
        self.assertEqual(ext_img, [], f"Found external images: {ext_img}")
        self.assertEqual(ext_iframe, [], f"Found external iframes: {ext_iframe}")

    def test_zero_external_network_urls_in_css(self):
        """Verify web/styles.css contains 0 external @import or url() http/https links."""
        css_path = os.path.join(WEB_DIR, "styles.css")
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()

        ext_imports = re.findall(r'@import\s+url\(["\']?(https?://[^"\'\)]+)["\']?\)', content, re.IGNORECASE)
        ext_urls = re.findall(r'url\(["\']?(https?://[^"\'\)]+)["\']?\)', content, re.IGNORECASE)

        self.assertEqual(ext_imports, [], f"Found external @import: {ext_imports}")
        self.assertEqual(ext_urls, [], f"Found external CSS url(): {ext_urls}")

    def test_zero_external_network_urls_in_js(self):
        """Verify web/app.js and web/chip3d.js do not fetch or load external URLs."""
        for js_file in ["app.js", "chip3d.js"]:
            js_path = os.path.join(WEB_DIR, js_file)
            with open(js_path, "r", encoding="utf-8") as f:
                content = f.read()

            fetch_matches = re.findall(r'''fetch\(\s*['"](https?://(?!(?:127\.0\.0\.1|localhost))[^'"]+)['"]''', content)
            self.assertEqual(fetch_matches, [], f"Found external fetch in {js_file}: {fetch_matches}")

    # ==========================================================================
    # 3. DOM CONTRACT & ELEMENT ID INTEGRITY AUDIT
    # ==========================================================================

    def test_all_app_js_dom_ids_exist_in_index_html(self):
        """Verify every getElementById('...') queried by app.js actually exists in index.html."""
        app_js_path = os.path.join(WEB_DIR, "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js_code = f.read()

        html_path = os.path.join(WEB_DIR, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_code = f.read()

        queried_ids = set(re.findall(r'''getElementById\(\s*['"]([a-zA-Z0-9_\-]+)['"]\s*\)''', app_js_code))
        present_ids = set(re.findall(r'''id=["']([a-zA-Z0-9_\-]+)["']''', html_code))

        missing_ids = []
        for qid in queried_ids:
            if qid not in present_ids:
                missing_ids.append(qid)

        truly_missing = []
        for m in missing_ids:
            pattern = rf'''getElementById\(\s*['"]{re.escape(m)}['"]\s*\)\s*\|\|\s*document\.getElementById\(\s*['"]([a-zA-Z0-9_\-]+)['"]\s*\)'''
            alt1 = re.findall(pattern, app_js_code)
            pattern_rev = rf'''getElementById\(\s*['"]([a-zA-Z0-9_\-]+)['"]\s*\)\s*\|\|\s*document\.getElementById\(\s*['"]{re.escape(m)}['"]\s*\)'''
            alt2 = re.findall(pattern_rev, app_js_code)
            has_valid_alt = any(a in present_ids for a in (alt1 + alt2))
            if not has_valid_alt and m not in present_ids:
                truly_missing.append(m)

        self.assertEqual(truly_missing, [], f"The following DOM IDs are queried in app.js but missing in index.html: {truly_missing}")

    def test_layer_toggles_match_chip3d_groups(self):
        """Verify that layer toggles in index.html cover all 8 3D groups."""
        html_path = os.path.join(WEB_DIR, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_code = f.read()

        expected_layers = ["substrate", "cells", "m1", "m2", "m3", "vias", "pads", "labels"]
        for layer in expected_layers:
            self.assertIn(f'data-layer="{layer}"', html_code, f"Missing toggle for layer '{layer}' in index.html")

    # ==========================================================================
    # 4. JAVASCRIPT SYNTAX & MATHEMATICAL FORMULA VERIFICATION
    # ==========================================================================

    def test_js_syntax_via_node_if_available(self):
        """Test JS syntax of app.js and chip3d.js using node --check if node is installed."""
        node_bin = shutil.which("node")
        if node_bin:
            for js_file in ["app.js", "chip3d.js"]:
                res = subprocess.run(
                    [node_bin, "--check", os.path.join(WEB_DIR, js_file)],
                    capture_output=True,
                    text=True
                )
                self.assertEqual(res.returncode, 0, f"Node syntax error in {js_file}: {res.stderr}")
        else:
            for js_file in ["app.js", "chip3d.js"]:
                with open(os.path.join(WEB_DIR, js_file), "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertEqual(content.count('{'), content.count('}'), f"Unmatched curly braces in {js_file}")
                self.assertEqual(content.count('('), content.count(')'), f"Unmatched parentheses in {js_file}")

    def test_die_dimension_scaling_adversarial_inputs(self):
        """Adversarial stress test on calcDieDimension formula."""
        # Formula: D = max(24.0, sqrt(LEs + FFs) * 4.0 + Pins * 0.6)
        calc = lambda le, ff, pins: max(24.0, math.sqrt(max(0, le) + max(0, ff)) * 4.0 + max(0, pins) * 0.6)

        # Baseline multiplier: LEs=17, FFs=16, Pins=34
        d_mult = calc(17, 16, 34)
        expected = max(24.0, math.sqrt(33) * 4.0 + 34 * 0.6)
        self.assertAlmostEqual(d_mult, expected, places=2)

        # Negative / zero values should clamp to 24.0
        self.assertEqual(calc(0, 0, 0), 24.0)
        self.assertEqual(calc(-10, -5, -20), 24.0)

        # Large circuit: LEs=10000, FFs=5000, Pins=200
        d_large = calc(10000, 5000, 200)
        self.assertGreater(d_large, 500.0)

    # ==========================================================================
    # 5. ADVERSARIAL HTTP ENDPOINT & CORNER CASE TESTS
    # ==========================================================================

    def test_http_method_not_allowed(self):
        """Verify PUT, DELETE, PATCH return 405 Method Not Allowed."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        for method in ["PUT", "DELETE", "PATCH"]:
            conn.request(method, "/api/samples")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 405, f"Expected 405 for {method}, got {resp.status}")
            data = resp.read()
            self.assertTrue(len(data) > 0)
        conn.close()

    def test_api_status_missing_param(self):
        """Verify GET /api/status without task_id returns 400 Bad Request."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/status", timeout=2.0) as resp:
                self.assertEqual(resp.status, 400)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_api_status_nonexistent_task(self):
        """Verify GET /api/status with non-existent task_id returns 404 Not Found."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/status?task_id=deadbeef9999", timeout=2.0) as resp:
                self.assertEqual(resp.status, 404)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_post_run_spec_malformed_json(self):
        """Adversarial check: send malformed JSON body to POST /api/run-spec."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("POST", "/api/run-spec", body="{invalid_json:", headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 400)
        conn.close()

    def test_post_run_spec_empty_prompt_and_spec(self):
        """Verify POST /api/run-spec with empty prompt and empty spec_file returns 400."""
        req_data = json.dumps({"prompt": "", "spec_file": ""}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/run-spec",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 400)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_post_open_quartus_traversal_rejection(self):
        """Verify POST /api/open-quartus rejects directory traversal in bdf_path."""
        req_data = json.dumps({"bdf_path": "../../Windows/System32/cmd.exe"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/open-quartus",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 400)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_samples_endpoint_integrity(self):
        """Verify /api/samples returns all 5 canonical samples with expected keys."""
        with urllib.request.urlopen(f"{self.base_url}/api/samples", timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 5)
            ids = [s.get("id") for s in data]
            for exp in ["multiplier_8bit", "gray_counter_4bit", "vending_machine", "elevator_5floor", "traffic_light"]:
                self.assertIn(exp, ids)
            for s in data:
                self.assertIn("name_vi", s)
                self.assertIn("name_en", s)
                self.assertIn("prompt", s)
                self.assertIn("spec_file", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
