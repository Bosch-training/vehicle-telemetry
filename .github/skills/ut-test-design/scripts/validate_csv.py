#!/usr/bin/env python3
"""Validate unit-test-design CSV files and auto-repair common defects.

Usage:
    python3 validate_csv.py [PATH ...] [--check-only]

PATH is a CSV file or a directory of CSV files (default: docs/ut-design).
Without --check-only, repairable defects are fixed in place, the file is
re-read from disk to confirm it is clean, and the script exits 0. Defects that
cannot be repaired safely (wrong header, duplicate ids, empty required fields,
unknown testcase type) are reported with line numbers and the file is left
untouched so the rows can be regenerated.

Exit codes: 0 = clean or fixed, 1 = unfixable errors (or defects in --check-only), 2 = usage error.
"""
from __future__ import annotations

import argparse
import codecs
import csv
import io
import os
import re
import sys
import tempfile
from pathlib import Path

HEADER = [
    "Testcase ID",
    "Testcase Name",
    "Test Description",
    "Input",
    "Testcase Type",
    "Expected Output",
    "Actual Output",
    "Automated (Yes/No)",
    "Comments",
]
ID, NAME, DESC, INPUT, TYPE, EXPECTED, ACTUAL, AUTO, COMMENTS = range(9)
NCOLS = len(HEADER)

TYPES = {"positive": "Positive", "negative": "Negative", "edge": "Edge", "exhaustive": "Exhaustive"}
YESNO = {"yes": "Yes", "y": "Yes", "true": "Yes", "no": "No", "n": "No", "false": "No"}
ID_RE = re.compile(r"^(VB|VR|TS|DR)-(POS|NEG|EDGE|EXH)-\d{3,}$")
ID_TYPE = {"POS": "Positive", "NEG": "Negative", "EDGE": "Edge", "EXH": "Exhaustive"}
REQUIRED = (ID, NAME, DESC, INPUT, EXPECTED)


class Report:
    def __init__(self) -> None:
        self.fixes: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.rows = 0


def _read(text: str, strict: bool) -> list[tuple[int, list[str]]]:
    reader = csv.reader(io.StringIO(text, newline=""), strict=strict)
    out, prev = [], 0
    for row in reader:
        out.append((prev + 1, row))
        prev = reader.line_num
    return out


def parse(text: str, rep: Report) -> list[tuple[int, list[str]]]:
    try:
        return _read(text, strict=True)
    except csv.Error as exc:
        rep.fixes.append(f"malformed quoting ({exc}); re-parsed leniently and re-quoted")
        return _read(text, strict=False)


def _anchors(fields: list[str]) -> tuple[int, int] | None:
    """Locate the Type and Automated columns, which have a closed set of values."""
    t = next((i for i in range(4, len(fields)) if fields[i].strip().lower() in TYPES), None)
    if t is None:
        return None
    cands = [i for i in range(t + 2, len(fields)) if fields[i].strip().lower() in YESNO]
    if not cands:
        return None
    # Actual Output is blank at design time, so prefer the Yes/No that follows a blank field.
    a = next((i for i in cands if fields[i - 1].strip() == ""), cands[0])
    return t, a


def _realign(fields: list[str]) -> list[str] | None:
    """Rejoin fields split by unquoted commas, using Type/Automated as anchors.

    Input is assumed to be the field just before Type; extra pieces before it belong to
    Description. Joining with "," restores the original text because the pieces keep their
    surrounding whitespace.
    """
    anchors = _anchors(fields)
    if anchors is None or anchors[0] < 4:
        return None
    t, a = anchors
    return [
        fields[ID],
        fields[NAME],
        ",".join(fields[2 : t - 1]),
        fields[t - 1],
        fields[t],
        ",".join(fields[t + 1 : a - 1]),
        fields[a - 1],
        fields[a],
        ",".join(fields[a + 1 :]),
    ]


def _formula_risk(value: str) -> bool:
    if not value:
        return False
    if value[0] in "=@":
        return True
    return value[0] in "+-" and len(value) > 1 and not (value[1].isdigit() or value[1] == ".")


def _clean(ln: int, fields: list[str], rep: Report, stats: dict[str, int]) -> list[str]:
    out = []
    for col, value in enumerate(fields):
        v = value
        if re.search(r"[\r\n]", v):
            v = re.sub(r"\s*[\r\n]+\s*", " ", v)
            rep.fixes.append(f"line {ln}: collapsed embedded newline in '{HEADER[col]}'")
        if v != v.strip():
            v = v.strip()
            stats["trimmed"] += 1
        if col == TYPE and v.lower() in TYPES and v != TYPES[v.lower()]:
            rep.fixes.append(f"line {ln}: normalized type '{v}' -> '{TYPES[v.lower()]}'")
            v = TYPES[v.lower()]
        if col == AUTO and v.lower() in YESNO and v != YESNO[v.lower()]:
            rep.fixes.append(f"line {ln}: normalized automated '{v}' -> '{YESNO[v.lower()]}'")
            v = YESNO[v.lower()]
        if _formula_risk(v):
            rep.fixes.append(
                f"line {ln}: '{HEADER[col]}' starts with '{v[0]}' (spreadsheets treat it as a formula); prefixed with '"
            )
            v = "'" + v
        out.append(v)
    return out


def _validate_row(ln: int, row: list[str], rep: Report) -> None:
    for col in REQUIRED:
        if not row[col]:
            rep.errors.append(f"line {ln}: required field '{HEADER[col]}' is empty")
    if row[TYPE] not in TYPES.values():
        rep.errors.append(f"line {ln}: invalid Testcase Type '{row[TYPE]}' (expected Positive/Negative/Edge/Exhaustive)")
    if row[AUTO] not in ("Yes", "No"):
        rep.errors.append(f"line {ln}: invalid Automated value '{row[AUTO]}' (expected Yes or No)")
    m = ID_RE.match(row[ID])
    if row[ID] and not m:
        rep.errors.append(
            f"line {ln}: id '{row[ID]}' does not match one of the required prefixes "
            "VB/VR/TS/DR and <POS|NEG|EDGE|EXH>-<nnn>"
        )
    elif m and ID_TYPE[m.group(2)] != row[TYPE]:
        rep.errors.append(f"line {ln}: id '{row[ID]}' implies {ID_TYPE[m.group(2)]} but type is '{row[TYPE]}'")


def serialize(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    return buf.getvalue()


def process(path: Path, apply: bool) -> tuple[str, Report]:
    rep = Report()
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        rep.errors.append(f"not valid UTF-8: {exc}")
        return "FAILED", rep
    if raw.startswith(codecs.BOM_UTF8):
        rep.fixes.append("removed UTF-8 BOM")

    parsed = parse(text, rep)
    blank = sum(1 for _, r in parsed if all(not f.strip() for f in r))
    if blank:
        rep.fixes.append(f"removed {blank} blank row(s)")
    parsed = [(ln, r) for ln, r in parsed if any(f.strip() for f in r)]
    if not parsed:
        rep.errors.append("file is empty")
        return "FAILED", rep

    header = [h.strip() for h in parsed[0][1]]
    if [h.lower() for h in header] != [h.lower() for h in HEADER]:
        rep.errors.append(f"header mismatch: got {header}, expected {HEADER}")
        return "FAILED", rep
    if parsed[0][1] != HEADER:
        rep.fixes.append("normalized header names/case/whitespace")

    stats = {"trimmed": 0}
    rows: list[list[str]] = []
    line_of: dict[str, int] = {}
    for ln, fields in parsed[1:]:
        aligned = len(fields) == NCOLS and fields[TYPE].strip().lower() in TYPES and fields[AUTO].strip().lower() in YESNO
        if not aligned:
            repaired = _realign(fields)
            if repaired is not None:
                rep.fixes.append(
                    f"line {ln}: {len(fields)} fields instead of {NCOLS} (unquoted comma?); realigned - "
                    "review Description/Expected Output/Comments"
                )
                fields = repaired
            elif len(fields) != NCOLS:
                rep.errors.append(f"line {ln}: {len(fields)} fields instead of {NCOLS} and could not be realigned")
                continue
        row = _clean(ln, fields, rep, stats)
        _validate_row(ln, row, rep)
        if row[ID] in line_of:
            rep.errors.append(f"line {ln}: duplicate Testcase ID '{row[ID]}' (first seen on line {line_of[row[ID]]})")
        line_of.setdefault(row[ID], ln)
        rows.append(row)
    if stats["trimmed"]:
        rep.fixes.append(f"trimmed surrounding whitespace in {stats['trimmed']} field(s)")
    rep.rows = len(rows)
    if not rows:
        rep.warnings.append("no data rows")

    if rep.errors:
        return "FAILED", rep

    canonical = serialize(rows)
    if canonical == text:
        return ("NEEDS_FIX" if rep.fixes else "OK"), rep
    if not rep.fixes:
        rep.fixes.append("normalized quoting, line endings, or trailing newline")
    if not apply:
        return "NEEDS_FIX", rep

    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(canonical)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

    status, verify = process(path, apply=False)
    if status != "OK":
        rep.errors.append("post-write verification failed: " + "; ".join(verify.errors + verify.fixes))
        return "FAILED", rep
    return "FIXED", rep


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            # Only design CSVs live in this directory; review outputs (review-findings.csv)
            # have a different contract and must not be validated against it.
            files.extend(sorted(q for q in p.glob("*.csv") if q.name != "review-findings.csv"))
        elif p.is_file():
            files.append(p)
        else:
            print(f"error: {p} does not exist", file=sys.stderr)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate and auto-fix unit-test-design CSV files.")
    ap.add_argument("paths", nargs="*", default=["docs/ut-design"], help="CSV files or directories")
    ap.add_argument("--check-only", action="store_true", help="report defects without modifying files")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    if not files:
        print("error: no CSV files found", file=sys.stderr)
        return 2

    exit_code = 0
    for f in files:
        status, rep = process(f, apply=not args.check_only)
        print(f"[{status}] {f} ({rep.rows} rows)")
        for label, items in (("fixed" if status == "FIXED" else "defect", rep.fixes), ("warning", rep.warnings), ("error", rep.errors)):
            for item in items:
                print(f"  {label}: {item}")
        if status in ("FAILED", "NEEDS_FIX"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
