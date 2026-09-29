#!/usr/bin/env python3
"""Tests for apply_review.py. Run: cd scripts && python3 test_apply_review.py"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "apply_review.py"

HEADER = [
    "Testcase ID", "Testcase Name", "Test Description", "Input", "Testcase Type",
    "Expected Output", "Actual Output", "Automated (Yes/No)", "Comments",
]


def make_design(rows: list[list[str]]) -> Path:
    fd = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    writer = csv.writer(fd, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    fd.close()
    return Path(fd.name)


def row(cid: str, expected: str, comments: str = "") -> list[str]:
    return [cid, "n", "d", "i", "Negative", expected, "", "No", comments]


def run(design: Path, decisions: dict) -> tuple[int, list[list[str]]]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fd:
        json.dump(decisions, fd)
        decisions_path = Path(fd.name)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--design", str(design), "--decisions", str(decisions_path)],
        capture_output=True, text=True,
    )
    with design.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return result.returncode, rows


class ApplyReviewTest(unittest.TestCase):
    def test_builder_store_makes_expected_definitive(self) -> None:
        design = make_design([row("VB-NEG-001", "speed == -10.0 (stored as-is) or clamped/rejected if implemented")])
        code, rows = run(design, {"builder_validation": "store"})
        self.assertEqual(code, 0)
        self.assertIn("stored exactly as given", rows[1][5])
        self.assertNotIn("or clamped", rows[1][5])

    def test_builder_clamp_and_reject_differ(self) -> None:
        for decision, needle in (("clamp", "clamped"), ("reject", "rejects")):
            design = make_design([row("VB-NEG-002", "battery == 150 (stored as-is) or clamped to 100/rejected if implemented")])
            _, rows = run(design, {"builder_validation": decision})
            self.assertIn(needle, rows[1][5])

    def test_threshold_strict_vs_inclusive(self) -> None:
        design = make_design([row("TS-EDGE-003", "That vehicle is NOT in lowBatteryVehicles; getFleetSummary(t + 1) includes it")])
        _, rows = run(design, {"threshold_comparison": "inclusive"})
        self.assertIn("IS in lowBatteryVehicles", rows[1][5])
        self.assertIn("<=", rows[1][8])

    def test_missing_decision_leaves_row_untouched(self) -> None:
        original = "speed == -10.0 (stored as-is) or clamped/rejected if implemented"
        design = make_design([row("VB-NEG-001", original)])
        code, rows = run(design, {"threshold_comparison": "strict"})
        self.assertEqual(code, 0)
        self.assertEqual(rows[1][5], original)

    def test_unknown_keys_are_ignored(self) -> None:
        design = make_design([row("VB-NEG-001", "x")])
        code, rows = run(design, {"not_a_real_key": "whatever"})
        self.assertEqual(code, 0)
        self.assertEqual(rows[1][5], "x")

    def test_missing_decisions_file_errors(self) -> None:
        design = make_design([row("VB-NEG-001", "x")])
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--design", str(design), "--decisions", "/nonexistent.json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)

    def test_output_stays_nine_columns(self) -> None:
        design = make_design([row("VB-NEG-001", "a, b, c"), row("TS-EDGE-003", "x")])
        _, rows = run(design, {"builder_validation": "store", "threshold_comparison": "strict"})
        self.assertTrue(all(len(r) == 9 for r in rows))

    def test_second_run_is_a_no_op(self) -> None:
        design = make_design([row("VB-NEG-001", "speed == -10.0 (stored as-is) or clamped/rejected if implemented")])
        run(design, {"builder_validation": "store"})
        first = design.read_text(encoding="utf-8")
        code, _ = run(design, {"builder_validation": "store"})
        self.assertEqual(code, 0)
        self.assertEqual(design.read_text(encoding="utf-8"), first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
