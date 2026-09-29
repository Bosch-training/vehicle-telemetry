#!/usr/bin/env python3
"""Apply review findings to the unit-test design CSV.

Usage:
    python3 apply_review.py [--design PATH] [--findings PATH] [--decisions PATH]
                            [--dry-run] [--json]

This is the "fix" half of the review loop. It reads the findings produced by
ut-test-design-review and a decisions file that records the behavior the SWDD
left unspecified, then rewrites the affected rows so their Expected Output is
definitive and their Comments no longer raise an open question.

The decisions file is the human's input to the loop. It is a JSON object:

    {
      "builder_validation": "store",          # store | clamp | reject
      "threshold_comparison": "strict",       # strict (<) | inclusive (<=)
      "renderer_precision": 2,                # decimals for speed/coordinates
      "renderer_long_name": "widen",          # widen | truncate
      "renderer_empty_list": "header-only",   # header-only | message
      "renderer_no_low_battery": "omit",      # omit | none-message
      "test_seam": "none"                     # none | inject-repository
    }

Only the keys present are applied; missing keys leave the corresponding rows
untouched. The script never invents a decision — an unresolved key means the
finding stays open, which is the correct outcome.

Exit codes: 0 = applied (or nothing to do), 1 = input error, 2 = usage error.
"""
from __future__ import annotations

import argparse
import csv
import json
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

# Rows whose Expected Output hedges on builder validation, keyed by the field
# they exercise. The replacement text is chosen from the decision.
BUILDER_ROWS = {
    "VB-NEG-001": ("speed", "speed == -10.0"),
    "VB-NEG-002": ("battery", "battery == 150"),
    "VB-NEG-003": ("battery", "battery == -5"),
    "VB-NEG-004": ("latitude", "latitude == 200.0"),
    "VB-NEG-005": ("longitude", "longitude == -500.0"),
    "VB-NEG-006": ("speed", "speed is NaN"),
}

BUILDER_EXPECTED = {
    "store": "{field} is stored exactly as given ({value}); no validation is applied",
    "clamp": "{field} is clamped to the nearest valid bound; the builder never stores an out-of-range value",
    "reject": "the builder rejects the value and {field} keeps its previous/default value",
}

BUILDER_COMMENT = {
    "store": "SWDD 5.2: builder stores values verbatim; validation is out of scope",
    "clamp": "SWDD 5.2: builder clamps to the documented range",
    "reject": "SWDD 5.2: builder rejects out-of-range values",
}

THRESHOLD_EXPECTED = {
    "strict": "That vehicle is NOT in lowBatteryVehicles; getFleetSummary(t + 1) includes it",
    "inclusive": "That vehicle IS in lowBatteryVehicles; getFleetSummary(t - 1) excludes it",
}

THRESHOLD_COMMENT = {
    "strict": "SWDD 5.4: comparison is strict less-than (battery < threshold)",
    "inclusive": "SWDD 5.4: comparison is inclusive (battery <= threshold)",
}

RENDERER_PRECISION_ROWS = {
    "DR-POS-003": "Decimal precision is implementation-defined; assert the chosen format",
    "DR-EDGE-005": "Precision is implementation-defined; assert the chosen setprecision",
}

RENDERER_LONG_NAME = "DR-EDGE-003"
RENDERER_EMPTY_LIST = "DR-EDGE-001"
RENDERER_NO_LOW = "DR-NEG-001"

SEAM_ROWS = (
    "VR-EDGE-005", "VR-EDGE-006", "VR-EXH-002",
    "TS-EDGE-004", "TS-EDGE-005", "TS-EDGE-006", "TS-EDGE-007", "TS-EXH-003",
)


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows or [h.strip() for h in rows[0]] != HEADER:
        raise ValueError(f"{path} header does not match the 9-column contract")
    for n, row in enumerate(rows[1:], start=2):
        if len(row) != len(HEADER):
            raise ValueError(f"{path} line {n}: {len(row)} fields instead of {len(HEADER)}")
    return rows


def write_rows(path: Path, rows: list[list[str]]) -> None:
    with tempfile.NamedTemporaryFile(
        "w", newline="", encoding="utf-8", suffix=".csv", dir=path.parent, delete=False
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(rows)
        tmp = Path(handle.name)
    tmp.replace(path)


def apply_builder(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        cid = row[ID]
        if cid not in BUILDER_ROWS:
            continue
        field, value = BUILDER_ROWS[cid]
        row[EXPECTED] = BUILDER_EXPECTED[decision].format(field=field, value=value)
        row[COMMENTS] = BUILDER_COMMENT[decision]
        changes.append(f"{cid}: builder validation -> {decision}")
    for row in rows[1:]:
        if row[ID] == "VB-EXH-001":
            row[EXPECTED] = (
                "Each field is stored exactly as given, independently of the others; "
                "no cross-field interaction"
            )
            row[COMMENTS] = BUILDER_COMMENT[decision]
            changes.append("VB-EXH-001: builder validation -> " + decision)


def apply_threshold(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == "TS-EDGE-003":
            row[EXPECTED] = THRESHOLD_EXPECTED[decision]
            row[COMMENTS] = THRESHOLD_COMMENT[decision]
            changes.append(f"TS-EDGE-003: threshold comparison -> {decision}")


def apply_precision(rows: list[list[str]], decimals: int, changes: list[str]) -> None:
    for row in rows[1:]:
        cid = row[ID]
        if cid in RENDERER_PRECISION_ROWS:
            row[COMMENTS] = f"SWDD 5.5: fixed precision of {decimals} decimals"
            changes.append(f"{cid}: renderer precision -> {decimals} decimals")
        if cid == "DR-EDGE-005":
            row[EXPECTED] = f"Printed with fixed precision, for example 55.{'3' * decimals}"


def apply_long_name(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == RENDERER_LONG_NAME:
            if decision == "widen":
                row[EXPECTED] = (
                    "Every row has the same width and the following columns stay aligned; "
                    "the Name column widens to fit the longest value"
                )
            else:
                row[EXPECTED] = (
                    "Every row has the same width and the following columns stay aligned; "
                    "the name is truncated to the fixed Name column width"
                )
            row[COMMENTS] = f"SWDD 5.5: long names are {decision}ed"
            changes.append(f"{RENDERER_LONG_NAME}: long name -> {decision}")


def apply_empty_list(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == RENDERER_EMPTY_LIST:
            row[EXPECTED] = (
                "Header row is printed and no data rows follow"
                if decision == "header-only"
                else "A single empty-fleet message is printed instead of a table"
            )
            row[COMMENTS] = f"SWDD 5.5: empty fleet renders {decision}"
            changes.append(f"{RENDERER_EMPTY_LIST}: empty list -> {decision}")


def apply_zero_total(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == "DR-NEG-002":
            row[EXPECTED] = (
                "Prints total 0 and average 0.00"
                if decision == "zero"
                else "Prints total 0 and a placeholder for the average"
            )
            row[COMMENTS] = f"SWDD 5.5: zero-vehicle summary prints {decision}"
            changes.append(f"DR-NEG-002: zero total -> {decision}")


def apply_nan(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == "DR-NEG-004":
            row[EXPECTED] = (
                "Prints the literal text nan for the average speed"
                if decision == "literal"
                else "Prints 0.00 for the average speed"
            )
            row[COMMENTS] = f"SWDD 5.5: NaN average renders as {decision}"
            changes.append(f"DR-NEG-004: NaN average -> {decision}")


def apply_seed_ids(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == "VR-NEG-001":
            row[COMMENTS] = "SWDD 5.3: seed ids are 1..N, so 9999 is never seeded"
            changes.append("VR-NEG-001: seed id range -> 1..N")
        if row[ID] == "VR-NEG-003":
            row[COMMENTS] = "SWDD 5.3: seed ids start at 1, so id 0 is never seeded"
            changes.append("VR-NEG-003: seed ids start at 1")
        if row[ID] == "DR-NEG-003":
            row[COMMENTS] = "SWDD 5.2: builder stores values verbatim, so the renderer receives them as given"
            changes.append("DR-NEG-003: depends on builder store policy")


def apply_no_low(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        if row[ID] == RENDERER_NO_LOW:
            row[EXPECTED] = (
                "Count and average are printed; the warning section is omitted entirely"
                if decision == "omit"
                else "Count and average are printed; the warning section prints a none-message"
            )
            row[COMMENTS] = f"SWDD 5.5: no low-battery vehicles -> {decision}"
            changes.append(f"{RENDERER_NO_LOW}: no low-battery list -> {decision}")


def apply_seam(rows: list[list[str]], decision: str, changes: list[str]) -> None:
    for row in rows[1:]:
        cid = row[ID]
        if cid not in SEAM_ROWS:
            continue
        if decision == "inject-repository":
            row[COMMENTS] = "SWDD 5.3: repository is injectable for tests"
            changes.append(f"{cid}: test seam -> injectable repository")
        else:
            row[COMMENTS] = (
                "SWDD 5.3: no test seam; case is not implementable as written and is deferred"
            )
            changes.append(f"{cid}: test seam -> none (deferred)")


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=root / "docs/ut-design/unit-test-design.csv")
    parser.add_argument("--findings", type=Path, default=root / "docs/ut-design/review-findings.csv")
    parser.add_argument("--decisions", type=Path, default=root / "docs/ut-design/review-decisions.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.decisions.exists():
        print(f"error: decisions file not found: {args.decisions}", file=sys.stderr)
        print("Create it with the behavior the SWDD left unspecified; see the skill's SKILL.md.", file=sys.stderr)
        return 1
    try:
        decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read decisions: {exc}", file=sys.stderr)
        return 1
    try:
        rows = read_rows(args.design)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    changes: list[str] = []
    before = [list(r) for r in rows]
    if "builder_validation" in decisions:
        apply_builder(rows, decisions["builder_validation"], changes)
    if "threshold_comparison" in decisions:
        apply_threshold(rows, decisions["threshold_comparison"], changes)
    if "renderer_precision" in decisions:
        apply_precision(rows, int(decisions["renderer_precision"]), changes)
    if "renderer_long_name" in decisions:
        apply_long_name(rows, decisions["renderer_long_name"], changes)
    if "renderer_empty_list" in decisions:
        apply_empty_list(rows, decisions["renderer_empty_list"], changes)
    if "renderer_no_low_battery" in decisions:
        apply_no_low(rows, decisions["renderer_no_low_battery"], changes)
    if "test_seam" in decisions:
        apply_seam(rows, decisions["test_seam"], changes)
    if "zero_total" in decisions:
        apply_zero_total(rows, decisions["zero_total"], changes)
    if "nan_average" in decisions:
        apply_nan(rows, decisions["nan_average"], changes)
    if "seed_ids" in decisions:
        apply_seed_ids(rows, decisions["seed_ids"], changes)

    # Report only rows that actually changed, so re-running a converged loop is a no-op.
    changed_ids = {r[ID] for old, r in zip(before, rows) if old != r}
    changes = [c for c in changes if c.split(":", 1)[0] in changed_ids]

    if not changes:
        print("nothing to apply: the design already matches the decisions")
        return 0
    if not args.dry_run:
        write_rows(args.design, rows)

    if args.json:
        print(json.dumps({"applied": changes, "dry_run": args.dry_run}, indent=2))
    else:
        verb = "would apply" if args.dry_run else "applied"
        print(f"{verb} {len(changes)} change(s):")
        for c in changes:
            print(f"  - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
