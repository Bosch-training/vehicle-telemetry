#!/usr/bin/env python3
"""Unit tests for review_design.py. Run: cd scripts && python3 test_review_design.py"""
from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_design as rd  # noqa: E402


def make_csv(rows: list[list[str]]) -> Path:
    fd = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    writer = csv.writer(fd, lineterminator="\n")
    writer.writerow(rd.HEADER)
    writer.writerows(rows)
    fd.close()
    return Path(fd.name)


def row(cid: str, name: str, desc: str, inp: str, typ: str, expected: str,
        actual: str = "", auto: str = "No", comments: str = "") -> list[str]:
    return [cid, name, desc, inp, typ, expected, actual, auto, comments]


class ReadRowsTest(unittest.TestCase):
    def test_reads_valid_rows(self) -> None:
        path = make_csv([row("VB-POS-001", "n", "d", "i", "Positive", "e")])
        rows = rd.read_rows(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][rd.ID], "VB-POS-001")

    def test_rejects_wrong_header(self) -> None:
        fd = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
        fd.write("a,b,c\n1,2,3\n")
        fd.close()
        with self.assertRaises(ValueError):
            rd.read_rows(Path(fd.name))

    def test_rejects_wrong_column_count(self) -> None:
        path = make_csv([["VB-POS-001", "n", "d", "i", "Positive", "e", "", "No"]])
        with self.assertRaises(ValueError):
            rd.read_rows(path)


class ConsistencyTest(unittest.TestCase):
    def test_flags_id_type_mismatch(self) -> None:
        rows = [row("VB-NEG-001", "n", "d", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        rd.check_consistency(rows, findings)
        self.assertTrue(any(f.category == "Consistency" for f in findings))

    def test_flags_duplicate_id(self) -> None:
        rows = [row("VB-POS-001", "n", "d", "i", "Positive", "e"),
                row("VB-POS-001", "n2", "d2", "i2", "Positive", "e2")]
        findings: list[rd.Finding] = []
        rd.check_consistency(rows, findings)
        self.assertTrue(any(f.category == "Duplicate" for f in findings))

    def test_flags_empty_required_field(self) -> None:
        rows = [row("VB-POS-001", "", "d", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        rd.check_consistency(rows, findings)
        self.assertTrue(any("empty" in f.finding for f in findings))

    def test_clean_row_has_no_findings(self) -> None:
        rows = [row("VB-POS-001", "n", "d", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        rd.check_consistency(rows, findings)
        self.assertEqual(findings, [])


class CategoryBalanceTest(unittest.TestCase):
    def test_flags_missing_component(self) -> None:
        rows = [row("VB-POS-001", "n", "d", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        balance = rd.check_category_balance(rows, findings)
        self.assertEqual(balance["VR"]["Positive"], 0)
        self.assertTrue(any(f.component == "VR" and f.severity == "High" for f in findings))

    def test_flags_missing_type(self) -> None:
        rows = [row("VB-POS-001", "n", "d", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        rd.check_category_balance(rows, findings)
        self.assertTrue(any(f.component == "VB" and f.severity == "Medium" for f in findings))


class CoverageTest(unittest.TestCase):
    def test_flags_uncovered_requirement(self) -> None:
        rows = [row("VB-POS-001", "n", "d", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        coverage = rd.check_coverage(rows, findings)
        self.assertEqual(coverage["FR2"], [])
        self.assertTrue(any(f.reference == "FR2" and f.severity == "High" for f in findings))

    def test_positive_only_coverage_is_medium(self) -> None:
        rows = [row("TS-POS-001", "average speed", "mean of speeds", "i", "Positive", "e")]
        findings: list[rd.Finding] = []
        rd.check_coverage(rows, findings)
        self.assertTrue(any(f.reference == "FR2" and f.severity == "Medium" for f in findings))

    def test_build_requirement_flagged_as_low(self) -> None:
        findings: list[rd.Finding] = []
        rd.check_coverage([], findings)
        self.assertTrue(any(f.reference == "FR5" and f.severity == "Low" for f in findings))


class AmbiguityTest(unittest.TestCase):
    def test_flags_open_question(self) -> None:
        rows = [row("VB-NEG-001", "n", "d", "i", "Negative", "e", comments="Open question: no validation")]
        findings: list[rd.Finding] = []
        questions = rd.check_ambiguity(rows, findings)
        self.assertEqual(len(questions), 1)
        self.assertTrue(any(f.category == "Ambiguity" for f in findings))

    def test_flags_non_committal_expected(self) -> None:
        rows = [row("VB-NEG-001", "n", "d", "i", "Negative", "stored as-is or clamped if implemented")]
        findings: list[rd.Finding] = []
        rd.check_ambiguity(rows, findings)
        self.assertTrue(any(f.category == "Observability" and f.severity == "High" for f in findings))

    def test_clean_case_has_no_findings(self) -> None:
        rows = [row("VB-POS-001", "n", "d", "i", "Positive", "speed == 10.0")]
        findings: list[rd.Finding] = []
        rd.check_ambiguity(rows, findings)
        self.assertEqual(findings, [])


class OutputTest(unittest.TestCase):
    def test_findings_csv_round_trips(self) -> None:
        findings = [rd.Finding("High", "Coverage Gap", "TS", "FR2", "f", "e", "r")]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "review-findings.csv"
            rd.write_findings(path, findings)
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
        self.assertEqual(rows[0], rd.FINDING_HEADER)
        self.assertEqual(rows[1][0], "REV-001")
        self.assertEqual(len(rows[1]), len(rd.FINDING_HEADER))

    def test_report_contains_sections(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "review-report.md"
            rd.write_report(path, [], [], {r["id"]: [] for r in rd.REQUIREMENTS},
                            {c: {t: 0 for t in rd.TYPES} for c in rd.COMPONENTS}, [])
            text = path.read_text(encoding="utf-8")
        for section in ("## Summary", "## Coverage matrix", "## Category balance",
                        "## Findings by severity", "## Open questions"):
            self.assertIn(section, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
