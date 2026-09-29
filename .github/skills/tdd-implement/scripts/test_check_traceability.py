#!/usr/bin/env python3
"""Unit tests for check_traceability.py (design parsing and test scanning)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_traceability as ct


class ReadDesignIdsTests(unittest.TestCase):
    def test_reads_ids_skipping_header_and_blanks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "design.csv"
            path.write_text(
                "Testcase ID,Testcase Name\n"
                "VB-POS-001,Full chain\n"
                ",blank id row\n"
                "TS-EDGE-003,Threshold\n",
                encoding="utf-8",
            )
            self.assertEqual(ct.read_design_ids(path), ["VB-POS-001", "TS-EDGE-003"])


class ScanTestsTests(unittest.TestCase):
    def test_finds_implemented_and_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp)
            (tests / "test_a.cpp").write_text(
                'TEST_CASE("VB-POS-001", "Full chain") {}\n'
                "// TC-SKIP: VR-EDGE-005 no test seam\n",
                encoding="utf-8",
            )
            implemented, skipped = ct.scan_tests(tests)
            self.assertEqual(implemented, {"VB-POS-001"})
            self.assertEqual(skipped, {"VR-EDGE-005"})


if __name__ == "__main__":
    unittest.main()