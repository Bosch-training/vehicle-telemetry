#!/usr/bin/env python3
"""Tests for validate_csv.py. Run: python3 test_validate_csv.py"""
import csv
import io
import tempfile
import unittest
from pathlib import Path

import validate_csv as v

HDR = ",".join(v.HEADER)
GOOD = "VB-POS-001,Name,Desc,input,Positive,out,,No,note"


def run(body: str, apply: bool = True, raw: bytes | None = None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.csv"
        p.write_bytes(raw if raw is not None else (HDR + "\n" + body).encode())
        status, rep = v.process(p, apply)
        rows = list(csv.reader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))
        return status, rep, rows


class ValidateCsv(unittest.TestCase):
    def test_clean_file_untouched(self):
        status, rep, _ = run(GOOD + "\n")
        self.assertEqual(status, "OK")
        self.assertFalse(rep.fixes)

    def test_unquoted_commas_in_description_expected_and_comments(self):
        line = 'VB-EXH-001,Name,Verify speed, battery, and GPS,"withGps(1, 2)",Exhaustive,stored as-is, or clamped,,No,open item, see SWDD'
        status, rep, rows = run(line + "\n")
        self.assertEqual(status, "FIXED", rep.errors)
        self.assertEqual(len(rows[1]), 9)
        self.assertEqual(rows[1][2], "Verify speed, battery, and GPS")
        self.assertEqual(rows[1][3], "withGps(1, 2)")
        self.assertEqual(rows[1][5], "stored as-is, or clamped")
        self.assertEqual(rows[1][8], "open item, see SWDD")

    def test_normalizes_type_yesno_bom_crlf_and_missing_trailing_newline(self):
        raw = b"\xef\xbb\xbf" + (HDR + "\r\nVB-POS-001,N,D,i,positive,o,,YES,c").encode()
        status, rep, rows = run("", raw=raw)
        self.assertEqual(status, "FIXED")
        self.assertEqual(rows[1][4], "Positive")
        self.assertEqual(rows[1][7], "Yes")

    def test_formula_guard(self):
        status, _, rows = run("VB-NEG-001,N,D,=SUM(A1),Negative,-x is bad,,No,\n")
        self.assertEqual(status, "FIXED")
        self.assertEqual(rows[1][3], "'=SUM(A1)")
        self.assertEqual(rows[1][5], "'-x is bad")

    def test_unfixable_errors_leave_file_untouched(self):
        body = "VB-POS-001,N,D,i,Bogus,o,,No,c\n" + GOOD + "\n" + GOOD + "\n"
        status, rep, rows = run(body)
        self.assertEqual(status, "FAILED")
        self.assertTrue(any("Bogus" in e for e in rep.errors))
        self.assertTrue(any("duplicate" in e for e in rep.errors))

    def test_rejects_unknown_component_prefix(self):
        status, rep, _ = run("XX-POS-001,N,D,i,Positive,o,,No,c\n")
        self.assertEqual(status, "FAILED")
        self.assertTrue(any("required prefixes" in e for e in rep.errors))

    def test_rejects_id_type_mismatch(self):
        status, rep, _ = run("VB-NEG-001,N,D,i,Positive,o,,No,c\n")
        self.assertEqual(status, "FAILED")
        self.assertTrue(any("implies Negative" in e for e in rep.errors))

    def test_bad_header_fails(self):
        status, rep, _ = run("", raw=b"a,b,c\n1,2,3\n")
        self.assertEqual(status, "FAILED")

    def test_check_only_does_not_write(self):
        status, _, rows = run("VB-POS-001,N,D,i,positive,o,,No,c\n", apply=False)
        self.assertEqual(status, "NEEDS_FIX")
        self.assertEqual(rows[1][4], "positive")

    def test_embedded_newline_collapsed(self):
        status, _, rows = run('VB-POS-001,N,"line one\nline two",i,Positive,o,,No,c\n')
        self.assertEqual(status, "FIXED")
        self.assertEqual(rows[1][2], "line one line two")


if __name__ == "__main__":
    unittest.main()
