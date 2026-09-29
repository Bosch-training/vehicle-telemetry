#!/usr/bin/env python3
"""Unit tests for validate_plan.py. Run: cd scripts && python3 test_validate_plan.py"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "validate_plan.py"


def run(plan: dict, *args):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path), *args],
            capture_output=True, text=True,
        )


def unit(**overrides):
    base = {
        "id": "U1",
        "target": "VehicleBuilder::withSpeed",
        "transformation": "extract-method",
        "expected_behavior": "withSpeed(60) sets speed to 60 and returns *this",
        "verify": ["build", "call sites compile"],
        "files": ["src/VehicleBuilder.cpp"],
        "estimated_lines": 20,
    }
    base.update(overrides)
    return base


class ValidatePlanTest(unittest.TestCase):
    def test_valid_plan_passes(self):
        proc = run({"units": [unit()]})
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("plan valid", proc.stdout)

    def test_empty_units_fails(self):
        proc = run({"units": []})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("non-empty", proc.stdout)

    def test_missing_required_field_fails(self):
        bad = unit()
        del bad["expected_behavior"]
        proc = run({"units": [bad]})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("expected_behavior", proc.stdout)

    def test_duplicate_ids_fail(self):
        proc = run({"units": [unit(), unit()]})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("duplicate unit id", proc.stdout)

    def test_too_many_files_fails(self):
        proc = run({"units": [unit(files=[f"src/f{i}.cpp" for i in range(6)])]})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("split the unit", proc.stdout)

    def test_too_many_lines_fails(self):
        proc = run({"units": [unit(estimated_lines=80)]})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("split the unit", proc.stdout)

    def test_vague_expected_behavior_warns(self):
        proc = run({"units": [unit(expected_behavior="unchanged")]})
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("warning", proc.stdout)

    def test_unknown_transformation_warns(self):
        proc = run({"units": [unit(transformation="frobnicate")]})
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("not in the known set", proc.stdout)

    def test_empty_verify_fails(self):
        proc = run({"units": [unit(verify=[])]})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("must be verifiable", proc.stdout)

    def test_invalid_json_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text("{not json", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                capture_output=True, text=True,
            )
        self.assertEqual(proc.returncode, 2)

    def test_json_output_is_parseable(self):
        proc = run({"units": [unit()]}, "--json")
        data = json.loads(proc.stdout)
        self.assertEqual(data["units"], 1)
        self.assertEqual(data["errors"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)