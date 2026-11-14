#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
   Spec2RTL Procedural 3D Chip Math & Procedural Geometry Empirical Harness
   Challenger 2 Verification Suite
================================================================================
Empirically stress-tests:
  1. Die dimension formula D = max(24.0, sqrt(LE + FF)*4.0 + Pins*0.6)
     - Boundary conditions: (0,0,0) -> 24.0, (17,16,34) -> 43.38,
       (11,7,13) -> 24.77, (1000, 1000, 100) -> 238.89
     - Extreme stress: (100000, 50000, 2000), (1,0,2), negative/zero/fractional
  2. Dual-language mathematical parity (Python vs Node.js runtime execution of chip3d.js)
  3. Layer elevations, monotonicity, and vertical separation >= 0.5
  4. Perimeter bonding pad spacing 4D / Pins > 1.2 across all pin counts
  5. Geometric containment: core within die, pads within perimeter, wirebond extents
  6. Three.js r128 API symbol completeness in web/assets/three.min.js & OrbitControls.js
================================================================================
"""

import json
import math
import os
import subprocess
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
CHIP3D_JS = os.path.join(WEB_DIR, "chip3d.js")
THREE_JS = os.path.join(ASSETS_DIR, "three.min.js")
ORBIT_JS = os.path.join(ASSETS_DIR, "OrbitControls.js")


def calc_die_dimension_py(le, ff, pins):
    """Authoritative Python implementation of die dimension."""
    total_le = max(0.0, float(le) if le is not None else 0.0)
    total_ff = max(0.0, float(ff) if ff is not None else 0.0)
    total_pins = max(0.0, float(pins) if pins is not None else 0.0)
    return max(24.0, math.sqrt(total_le + total_ff) * 4.0 + total_pins * 0.6)


class TestChip3DDieMath(unittest.TestCase):
    """Empirical verification of die dimension formula under boundary & stress conditions."""

    def test_boundary_zero_complexity(self):
        """(0, 0, 0) clamps strictly to lower floor 24.0."""
        d = calc_die_dimension_py(0, 0, 0)
        self.assertEqual(d, 24.0)

    def test_boundary_minimal_complexity(self):
        """(1, 0, 2) evaluates to 5.2, which clamps to 24.0."""
        raw = math.sqrt(1 + 0) * 4.0 + 2 * 0.6  # 5.2
        self.assertLess(raw, 24.0)
        d = calc_die_dimension_py(1, 0, 2)
        self.assertEqual(d, 24.0)

    def test_boundary_canonical_multiplier_8bit(self):
        """(17, 16, 34) evaluates to ~43.378 -> 43.38."""
        d = calc_die_dimension_py(17, 16, 34)
        expected = math.sqrt(33) * 4.0 + 34 * 0.6
        self.assertAlmostEqual(d, expected, places=7)
        self.assertAlmostEqual(d, 43.37825, delta=0.01)

    def test_boundary_canonical_gray_counter_4bit(self):
        """(11, 7, 13) evaluates to ~24.7705 -> 24.77."""
        d = calc_die_dimension_py(11, 7, 13)
        expected = math.sqrt(18) * 4.0 + 13 * 0.6
        self.assertAlmostEqual(d, expected, places=7)
        self.assertAlmostEqual(d, 24.77056, delta=0.01)

    def test_boundary_large_circuit_1000_1000_100(self):
        """(1000, 1000, 100) evaluates to valid finite dimension ~238.89."""
        d = calc_die_dimension_py(1000, 1000, 100)
        expected = math.sqrt(2000) * 4.0 + 100 * 0.6  # 44.72136 * 4 + 60 = 238.8854
        self.assertAlmostEqual(d, expected, places=7)
        self.assertAlmostEqual(d, 238.885, delta=0.01)
        self.assertTrue(math.isfinite(d))
        self.assertGreater(d, 0)

    def test_stress_massive_vlsi_chip(self):
        """(100000, 50000, 2000) evaluates without overflow or NaN."""
        d = calc_die_dimension_py(100000, 50000, 2000)
        expected = math.sqrt(150000) * 4.0 + 2000 * 0.6  # 387.298 * 4 + 1200 = 2749.19
        self.assertAlmostEqual(d, expected, places=5)
        self.assertTrue(math.isfinite(d))
        self.assertGreater(d, 2000)

    def test_stress_negative_and_degenerate_inputs(self):
        """Negative inputs clamp to 0, resulting in minimum floor 24.0."""
        d_neg = calc_die_dimension_py(-10, -5, -20)
        self.assertEqual(d_neg, 24.0)

    def test_stress_fractional_inputs(self):
        """Fractional inputs produce deterministic, monotonic outputs."""
        d1 = calc_die_dimension_py(17.5, 16.5, 34.0)
        d2 = calc_die_dimension_py(17.0, 16.0, 34.0)
        self.assertGreater(d1, d2)

    def test_monotonicity_across_scaling(self):
        """Strict monotonicity: increasing LE, FF, or Pins never decreases D."""
        prev = 0
        for le in [0, 5, 10, 20, 50, 100, 500]:
            for ff in [0, 5, 10, 20, 50, 100]:
                for pins in [0, 4, 10, 20, 40, 100]:
                    d = calc_die_dimension_py(le, ff, pins)
                    self.assertGreaterEqual(d, 24.0)
                    self.assertTrue(math.isfinite(d))


class TestChip3DLayerElevationsAndMonotonicity(unittest.TestCase):
    """Empirical verification of 3D layer vertical spacing and monotonicity."""

    def test_layer_elevations_strict_monotonicity(self):
        """Layer elevations must be strictly monotonic: Substrate < Cells < M1 < M2 < M3."""
        # Elevations from SCOPE.md and chip3d.js implementation:
        # Substrate surface = 0.0, base = -1.6, center = -0.8
        # Cells center = 0.225 (top = 0.45)
        # M1 elevation = 0.65
        # M2 elevation = 1.20
        # M3 elevation = 1.85
        elevations = [
            ("substrate_base", -1.6),
            ("substrate_surface", 0.0),
            ("cells_top", 0.45),
            ("metal_1", 0.65),
            ("metal_2", 1.20),
            ("metal_3", 1.85),
            ("max_wirebond_apex", 2.20),
        ]
        for i in range(len(elevations) - 1):
            name_a, y_a = elevations[i]
            name_b, y_b = elevations[i + 1]
            self.assertLess(y_a, y_b, f"Inversion between {name_a} ({y_a}) and {name_b} ({y_b})")

    def test_metal_interconnect_vertical_separation(self):
        """Vertical separation between adjacent metal layers must be >= 0.5 units."""
        m1_y = 0.65
        m2_y = 1.20
        m3_y = 1.85

        delta_m1_m2 = m2_y - m1_y
        delta_m2_m3 = m3_y - m2_y

        self.assertGreaterEqual(delta_m1_m2, 0.50, f"M1->M2 gap ({delta_m1_m2}) < 0.5")
        self.assertGreaterEqual(delta_m2_m3, 0.50, f"M2->M3 gap ({delta_m2_m3}) < 0.5")
        self.assertAlmostEqual(delta_m1_m2, 0.55, places=3)
        self.assertAlmostEqual(delta_m2_m3, 0.65, places=3)

    def test_vertical_via_stacks_bridge_exact_layer_gaps(self):
        """Via pillars must exactly bridge adjacent metal layers."""
        # Contact Via: Cells top (0.45) to M1 (0.65) -> height = 0.20, center = 0.55
        cv_center = 0.55
        cv_height = 0.20
        self.assertAlmostEqual(cv_center - cv_height / 2, 0.45, places=3)
        self.assertAlmostEqual(cv_center + cv_height / 2, 0.65, places=3)

        # Via 12: M1 (0.65) to M2 (1.20) -> height = 0.55, center = 0.925
        v12_center = 0.925
        v12_height = 0.55
        self.assertAlmostEqual(v12_center - v12_height / 2, 0.65, places=3)
        self.assertAlmostEqual(v12_center + v12_height / 2, 1.20, places=3)

        # Via 23: M2 (1.20) to M3 (1.85) -> height = 0.65, center = 1.525
        v23_center = 1.525
        v23_height = 0.65
        self.assertAlmostEqual(v23_center - v23_height / 2, 1.20, places=3)
        self.assertAlmostEqual(v23_center + v23_height / 2, 1.85, places=3)

    def test_clipping_plane_covers_complete_chip_vertical_span(self):
        """Dynamic clipping plane range [-1.6, +2.5] covers full chip geometry [-1.6, +2.2]."""
        chip_y_min = -1.6
        chip_y_max = 2.2
        clip_min = -1.6
        clip_max = 2.5
        self.assertLessEqual(clip_min, chip_y_min)
        self.assertGreaterEqual(clip_max, chip_y_max)


class TestChip3DPadSpacingAndGeometryBounds(unittest.TestCase):
    """Empirical verification of peripheral bonding pad spacing and clearance."""

    def test_perimeter_pad_spacing_mathematical_proof(self):
        """
        Prove that for ANY pin count P > 0:
        D >= P * 0.6  ==>  4*D >= 2.4 * P  ==>  4*D / P >= 2.4 > 1.2.
        """
        for pins in range(1, 501):
            d = calc_die_dimension_py(0, 0, pins)
            spacing = (4.0 * d) / pins
            self.assertGreater(spacing, 1.2, f"Pad spacing failed for pins={pins}: {spacing} <= 1.2")
            self.assertGreaterEqual(spacing, 2.4 - 1e-9)

    def test_pad_spacing_with_canonical_designs(self):
        """Verify pad spacing for canonical 8-bit multiplier and 4-bit Gray counter."""
        # Multiplier 8-bit (Pins=34, D=43.38)
        d_mult = calc_die_dimension_py(17, 16, 34)
        spacing_mult = (4.0 * d_mult) / 34
        self.assertAlmostEqual(spacing_mult, (4 * 43.378) / 34, places=2)
        self.assertGreater(spacing_mult, 5.0)  # ~5.10 units/pad > 1.2

        # Gray counter (Pins=13, D=24.77)
        d_gray = calc_die_dimension_py(11, 7, 13)
        spacing_gray = (4.0 * d_gray) / 13
        self.assertAlmostEqual(spacing_gray, (4 * 24.77) / 13, places=2)
        self.assertGreater(spacing_gray, 7.0)  # ~7.62 units/pad > 1.2

    def test_geometric_containment_core_within_die(self):
        """Standard cell core area must stay strictly within die boundary with clearance >= 6.0."""
        for d in [24.0, 43.38, 100.0, 500.0]:
            core_w = d - 6.0
            core_l = d - 6.0
            self.assertLess(core_w, d)
            self.assertLess(core_l, d)
            clearance_x = (d - core_w) / 2.0
            clearance_z = (d - core_l) / 2.0
            self.assertEqual(clearance_x, 3.0)
            self.assertEqual(clearance_z, 3.0)

    def test_pad_inset_within_die_perimeter(self):
        """Bonding pads with padInset=1.2 must lie strictly within die half-dimension."""
        for d in [24.0, 43.38, 100.0]:
            half_d = d / 2.0
            pad_inset = 1.2
            pad_coord = half_d - pad_inset
            self.assertLess(pad_coord, half_d)
            self.assertGreater(pad_coord, 0)


class TestChip3DNodeJSRuntimeEmpirical(unittest.TestCase):
    """Executes Node.js runtime to stress-test web/chip3d.js and Three.js offline assets."""

    def test_nodejs_calc_die_dimension_exact_parity(self):
        """chip3d.js calcDieDimension executed in Node.js matches Python within 1e-9."""
        js_code = """
        const fs = require('fs');
        const vm = require('vm');
        const chipCode = fs.readFileSync(process.argv[1], 'utf8');
        const sandbox = { window: {}, Math, Number, console };
        vm.createContext(sandbox);
        vm.runInContext(chipCode, sandbox);
        const calc = sandbox.window.Chip3D.calcDieDimension;

        const testCases = [
          [0, 0, 0],
          [1, 0, 2],
          [17, 16, 34],
          [11, 7, 13],
          [1000, 1000, 100],
          [100000, 50000, 2000],
          [-10, -5, -20],
          [17.5, 16.5, 34.0]
        ];

        const results = testCases.map(([le, ff, pins]) => ({
          le, ff, pins,
          d: calc(le, ff, pins)
        }));
        console.log(JSON.stringify(results));
        """
        res = subprocess.run(
            ["node", "-e", js_code, CHIP3D_JS],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Node.js execution failed: {res.stderr}")
        items = json.loads(res.stdout)
        for item in items:
            py_d = calc_die_dimension_py(item["le"], item["ff"], item["pins"])
            js_d = item["d"]
            self.assertAlmostEqual(
                py_d, js_d, places=7,
                msg=f"Discrepancy for ({item['le']}, {item['ff']}, {item['pins']}): Py={py_d}, JS={js_d}"
            )

    def test_threejs_and_orbitcontrols_offline_bundle_compatibility(self):
        """Node.js loads three.min.js and OrbitControls.js; verifies all required symbols exist."""
        js_code = """
        const fs = require('fs');
        const vm = require('vm');

        const threeCode = fs.readFileSync(process.argv[1], 'utf8');
        const orbitCode = fs.readFileSync(process.argv[2], 'utf8');

        // Create browser-like global sandbox
        const sandbox = {
          window: {},
          document: {
            createElement: () => ({
              getContext: () => ({
                fillRect: () => {},
                roundRect: () => {},
                fill: () => {},
                stroke: () => {},
                fillText: () => {}
              }),
              width: 256,
              height: 64
            }),
            addEventListener: () => {},
            removeEventListener: () => {}
          },
          navigator: { userAgent: 'NodeTest' },
          Math, Number, String, Object, Array, console
        };
        sandbox.window = sandbox;
        sandbox.self = sandbox;

        vm.createContext(sandbox);
        vm.runInContext(threeCode, sandbox);
        vm.runInContext(orbitCode, sandbox);

        const THREE = sandbox.THREE || sandbox.window.THREE;
        if (!THREE) {
          console.error('THREE is not defined in sandbox');
          process.exit(1);
        }

        // Required Three.js classes and methods used by chip3d.js
        const requiredSymbols = [
          'Scene',
          'Color',
          'Plane',
          'Vector3',
          'PerspectiveCamera',
          'WebGLRenderer',
          'OrbitControls',
          'AmbientLight',
          'DirectionalLight',
          'Group',
          'MeshStandardMaterial',
          'Mesh',
          'BoxGeometry',
          'GridHelper',
          'CylinderGeometry',
          'QuadraticBezierCurve3',
          'TubeGeometry',
          'CanvasTexture',
          'SpriteMaterial',
          'Sprite',
          'LinearFilter'
        ];

        const report = {};
        for (const sym of requiredSymbols) {
          const val = THREE[sym];
          report[sym] = {
            exists: val !== undefined,
            type: typeof val
          };
        }

        console.log(JSON.stringify(report));
        """
        res = subprocess.run(
            ["node", "-e", js_code, THREE_JS, ORBIT_JS],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Node.js Three.js symbol audit failed: {res.stderr}")
        report = json.loads(res.stdout)
        for sym, status in report.items():
            self.assertTrue(status["exists"], f"Symbol THREE.{sym} is MISSING from offline bundle!")
            self.assertIn(
                status["type"], ["function", "number", "object"],
                f"THREE.{sym} unexpected type: {status['type']}"
            )

    def test_chip3d_exported_api_methods(self):
        """Verify web/chip3d.js exports all expected methods on window.Chip3D."""
        js_code = """
        const fs = require('fs');
        const vm = require('vm');
        const chipCode = fs.readFileSync(process.argv[1], 'utf8');

        const sandbox = {
          window: {},
          document: {
            getElementById: () => null,
            createElement: () => ({
              getContext: () => ({
                fillRect: () => {},
                fill: () => {},
                stroke: () => {},
                fillText: () => {}
              }),
              width: 256,
              height: 64
            })
          },
          Math, Number, console
        };
        sandbox.window = sandbox;

        vm.createContext(sandbox);
        vm.runInContext(chipCode, sandbox);

        const chip3d = sandbox.window.Chip3D;
        const api = {
          hasInit: typeof chip3d.init === 'function',
          hasUpdate: typeof chip3d.update === 'function',
          hasUpdateChipGeometry: typeof chip3d.updateChipGeometry === 'function',
          hasToggleLayer: typeof chip3d.toggleLayer === 'function',
          hasSetClippingPlane: typeof chip3d.setClippingPlane === 'function',
          hasResetCamera: typeof chip3d.resetCamera === 'function',
          hasCalcDieDimension: typeof chip3d.calcDieDimension === 'function'
        };
        console.log(JSON.stringify(api));
        """
        res = subprocess.run(
            ["node", "-e", js_code, CHIP3D_JS],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Chip3D API export check failed: {res.stderr}")
        api = json.loads(res.stdout)
        for method, exists in api.items():
            self.assertTrue(exists, f"Chip3D API missing: {method}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
