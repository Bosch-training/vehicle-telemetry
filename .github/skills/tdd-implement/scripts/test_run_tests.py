#!/usr/bin/env python3
"""Unit tests for run_tests.py (parsing and source discovery)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import run_tests


class ParseOutputTests(unittest.TestCase):
    def test_parses_pass_fail_and_total(self) -> None:
        text = (
            "[PASS] VB-POS-001 Full fluent chain\n"
            "[FAIL] TS-EDGE-003 Threshold equals a seeded battery value\n"
            "    CHECK FAILED at tests/x.cpp:12: a == b\n"
            "TOTAL 2 PASSED 1 FAILED 1\n"
        )
        parsed = run_tests.parse_output(text)
        self.assertEqual(parsed["total"], 2)
        self.assertEqual(parsed["passed"], ["VB-POS-001"])
        self.assertEqual(parsed["failed"], ["TS-EDGE-003"])

    def test_empty_output(self) -> None:
        parsed = run_tests.parse_output("")
        self.assertIsNone(parsed["total"])
        self.assertEqual(parsed["passed"], [])
        self.assertEqual(parsed["failed"], [])


class FindSourcesTests(unittest.TestCase):
    def test_excludes_main_and_finds_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "main.cpp").write_text("int main(){return 0;}")
            (root / "src" / "VehicleBuilder.cpp").write_text("")
            (root / "tests" / "test_vehicle_builder.cpp").write_text("")
            sources, tests = run_tests.find_sources(root)
            self.assertEqual([p.name for p in sources], ["VehicleBuilder.cpp"])
            self.assertEqual([p.name for p in tests], ["test_vehicle_builder.cpp"])


if __name__ == "__main__":
    unittest.main()