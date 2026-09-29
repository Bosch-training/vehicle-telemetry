#!/usr/bin/env python3
"""Mechanically review a unit-test-design CSV against the project requirements.

Usage:
    python3 review_design.py [--design PATH] [--out-dir DIR] [--json]

Reads the design CSV (default: docs/ut-design/unit-test-design.csv) plus
docs/requirements.md and docs/swdd.md, then writes:

    <out-dir>/review-findings.csv   structured findings
    <out-dir>/review-report.md      human-readable report

The script covers the objective checks: requirement coverage, per-component
category balance, ID/type consistency, duplicates, non-committal expected
outputs, and ambiguity markers. Semantic judgment (does a case actually
discriminate?) is left to the reviewer following references/review-checklist.md.

Exit codes: 0 = review completed (findings may exist), 1 = input error, 2 = usage error,
3 = findings at or above --fail-on severity remain.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
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

TYPES = ("Positive", "Negative", "Edge", "Exhaustive")
ID_RE = re.compile(r"^(VB|VR|TS|DR)-(POS|NEG|EDGE|EXH)-\d{3,}$")
ID_TYPE = {"POS": "Positive", "NEG": "Negative", "EDGE": "Edge", "EXH": "Exhaustive"}
COMPONENTS = ("VB", "VR", "TS", "DR")

FINDING_HEADER = [
    "Finding ID",
    "Severity",
    "Category",
    "Component",
    "Reference",
    "Finding",
    "Evidence",
    "Recommendation",
]

# Requirement / verification-criterion coverage specs. `kind` decides how a gap
# is reported: unit cases can be covered by the CSV, build/doc items cannot.
REQUIREMENTS = [
    {
        "id": "FR1",
        "text": "Fleet of 5-8 mock vehicles with the full field set",
        "kind": "unit",
        "components": {"VR", "VB"},
        "pattern": r"seed|mock|fleet|field|range|populat",
    },
    {
        "id": "FR2",
        "text": "Fleet aggregates: count, average speed, low-battery list",
        "kind": "unit",
        "components": {"TS"},
        "pattern": r"average|low[- ]?battery|threshold|count|summary|aggregat",
    },
    {
        "id": "FR3",
        "text": "Fixed-width ASCII table with aligned columns",
        "kind": "unit",
        "components": {"DR"},
        "pattern": r"table|column|align|header|row",
    },
    {
        "id": "FR4",
        "text": "Fleet summary section below the table",
        "kind": "unit",
        "components": {"DR"},
        "pattern": r"summary|low[- ]?battery|warning|below",
    },
    {
        "id": "FR5",
        "text": "Single executable, no external runtime dependencies",
        "kind": "build",
        "components": set(),
        "pattern": "",
    },
    {
        "id": "VC1",
        "text": "Clean compile with -Wall -Wextra, no warnings",
        "kind": "build",
        "components": set(),
        "pattern": "",
    },
    {
        "id": "VC2",
        "text": "Binary output shows a correctly aligned ASCII table",
        "kind": "unit",
        "components": {"DR"},
        "pattern": r"align|table|width|column",
    },
    {
        "id": "VC3",
        "text": "Average speed and low-battery count match manual calculation",
        "kind": "unit",
        "components": {"TS"},
        "pattern": r"average|low[- ]?battery|manual|mean",
    },
    {
        "id": "VC4",
        "text": "getInstance() returns the same instance across calls",
        "kind": "unit",
        "components": {"TS"},
        "pattern": r"singleton|instance|identity|same",
    },
    {
        "id": "VC5",
        "text": "README documents architecture and pattern placement",
        "kind": "doc",
        "components": set(),
        "pattern": "",
    },
]

AMBIGUITY_MARKERS = (
    "open question",
    "implementation-defined",
    "implementation defined",
    "needs a test seam",
    "test-only construction",
    "unspecified",
    "assumes",
    "confirm",
    "depends on",
)

NON_COMMITTAL = (
    "no crash",
    "or clamped",
    "or rejected",
    "if implemented",
    "implementation-defined",
    "or an empty message",
    "or shows a none-message",
)


class Finding:
    def __init__(self, severity: str, category: str, component: str, reference: str,
                 finding: str, evidence: str, recommendation: str) -> None:
        self.severity = severity
        self.category = category
        self.component = component
        self.reference = reference
        self.finding = finding
        self.evidence = evidence
        self.recommendation = recommendation


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ValueError(f"{path} is empty")
    if [h.strip() for h in rows[0]] != HEADER:
        raise ValueError(f"{path} header does not match the 9-column contract")
    out = []
    for n, row in enumerate(rows[1:], start=2):
        if not any(f.strip() for f in row):
            continue
        if len(row) != NCOLS:
            raise ValueError(f"{path} line {n}: {len(row)} fields instead of {NCOLS}")
        out.append([f.strip() for f in row])
    return out


def component_of(case_id: str) -> str:
    return case_id.split("-", 1)[0] if "-" in case_id else "-"


def check_consistency(rows: list[list[str]], findings: list[Finding]) -> None:
    seen: dict[str, int] = {}
    for n, row in enumerate(rows, start=2):
        cid = row[ID]
        for col in (ID, NAME, DESC, INPUT, EXPECTED):
            if not row[col]:
                findings.append(Finding(
                    "High", "Consistency", component_of(cid), "-",
                    f"Required field '{HEADER[col]}' is empty",
                    f"line {n} ({cid or 'no id'})",
                    "Fill the field so the case is implementable and reviewable.",
                ))
        m = ID_RE.match(cid)
        if not m:
            findings.append(Finding(
                "High", "Consistency", component_of(cid), "-",
                f"Testcase ID '{cid}' does not match <VB|VR|TS|DR>-<POS|NEG|EDGE|EXH>-<nnn>",
                f"line {n}",
                "Rename the ID to the documented scheme.",
            ))
        elif ID_TYPE[m.group(2)] != row[TYPE]:
            findings.append(Finding(
                "High", "Consistency", component_of(cid), "-",
                f"ID '{cid}' implies {ID_TYPE[m.group(2)]} but Testcase Type is '{row[TYPE]}'",
                f"line {n}",
                "Align the ID suffix with the Testcase Type.",
            ))
        if cid in seen:
            findings.append(Finding(
                "High", "Duplicate", component_of(cid), "-",
                f"Duplicate Testcase ID '{cid}'",
                f"line {n}, first seen line {seen[cid]}",
                "Give the case a unique ID.",
            ))
        seen.setdefault(cid, n)
        if row[ACTUAL]:
            findings.append(Finding(
                "Low", "Traceability", component_of(cid), "-",
                "Actual Output is filled at design time",
                f"{cid}: '{row[ACTUAL][:60]}'",
                "Leave Actual Output blank until the test is run.",
            ))
        if row[AUTO].lower() == "yes":
            findings.append(Finding(
                "Low", "Traceability", component_of(cid), "-",
                "Automated is 'Yes' but no confirmed test exists in the design",
                f"{cid}",
                "Set Automated to No unless a test is confirmed to exist.",
            ))


def check_category_balance(rows: list[list[str]], findings: list[Finding]) -> dict[str, dict[str, int]]:
    balance: dict[str, dict[str, int]] = {c: {t: 0 for t in TYPES} for c in COMPONENTS}
    for row in rows:
        comp = component_of(row[ID])
        if comp in balance and row[TYPE] in balance[comp]:
            balance[comp][row[TYPE]] += 1
    for comp, counts in balance.items():
        if sum(counts.values()) == 0:
            findings.append(Finding(
                "High", "Category Balance", comp, "-",
                f"Component {comp} has no test cases at all",
                "no rows with this prefix",
                f"Add Positive, Negative, Edge and Exhaustive cases for {comp}.",
            ))
            continue
        for t in TYPES:
            if counts[t] == 0:
                findings.append(Finding(
                    "Medium", "Category Balance", comp, "-",
                    f"Component {comp} has no {t} cases",
                    f"{comp} counts: " + ", ".join(f"{k}={v}" for k, v in counts.items()),
                    f"Add at least one {t} case for {comp}.",
                ))
    return balance


def check_coverage(rows: list[list[str]], findings: list[Finding]) -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {}
    for req in REQUIREMENTS:
        if req["kind"] != "unit":
            coverage[req["id"]] = []
            continue
        rx = re.compile(req["pattern"], re.IGNORECASE)
        matched = []
        for row in rows:
            if component_of(row[ID]) not in req["components"]:
                continue
            haystack = " ".join((row[NAME], row[DESC], row[EXPECTED], row[COMMENTS]))
            if rx.search(haystack):
                matched.append(row[ID])
        coverage[req["id"]] = matched
        if not matched:
            findings.append(Finding(
                "High", "Coverage Gap", "/".join(sorted(req["components"])), req["id"],
                f"{req['id']} ({req['text']}) has no covering case",
                "no row matched the requirement's component and keywords",
                f"Add a case that fails when {req['id']} is violated.",
            ))
        else:
            types = {row[TYPE] for row in rows if row[ID] in matched}
            if types == {"Positive"}:
                findings.append(Finding(
                    "Medium", "Coverage Gap", "/".join(sorted(req["components"])), req["id"],
                    f"{req['id']} is covered only by Positive cases",
                    f"covering cases: {', '.join(matched)}",
                    "Add a Negative or Edge case so a violation is detectable.",
                ))
    # Build- and doc-level criteria cannot be covered by a unit case. Report them as
    # informational so the fix loop can converge on the findings that are actionable.
    for req in REQUIREMENTS:
        if req["kind"] == "build":
            findings.append(Finding(
                "Low", "Coverage Gap", "-", req["id"],
                f"{req['id']} ({req['text']}) is not verifiable by unit cases",
                "build-level criterion",
                "Verify via the CMake build and a clean -Wall -Wextra compile, not the CSV.",
            ))
        elif req["kind"] == "doc":
            findings.append(Finding(
                "Low", "Coverage Gap", "-", req["id"],
                f"{req['id']} ({req['text']}) is a documentation deliverable",
                "doc-level criterion",
                "Verify by reading README.md; no unit case applies.",
            ))
    return coverage


def check_ambiguity(rows: list[list[str]], findings: list[Finding]) -> list[str]:
    open_questions: list[str] = []
    for row in rows:
        cid = row[ID]
        comments = row[COMMENTS].lower()
        expected = row[EXPECTED].lower()
        hit = next((m for m in AMBIGUITY_MARKERS if m in comments), None)
        if hit:
            open_questions.append(f"{cid}: {row[COMMENTS]}")
            findings.append(Finding(
                "Medium", "Ambiguity", component_of(cid), "-",
                f"Case leaves the expected result undecidable ('{hit}')",
                f"{cid}: {row[COMMENTS][:120]}",
                "Resolve the behavior in the SWDD, then make the expected output definitive.",
            ))
        if any(m in expected for m in NON_COMMITTAL):
            findings.append(Finding(
                "High", "Observability", component_of(cid), "-",
                "Expected Output is non-committal, so the case cannot fail",
                f"{cid}: {row[EXPECTED][:120]}",
                "State the single observable result the implementation must produce.",
            ))
    return open_questions


def write_findings(path: Path, findings: list[Finding]) -> None:
    order = {"High": 0, "Medium": 1, "Low": 2}
    findings = sorted(findings, key=lambda f: (order.get(f.severity, 3), f.category, f.component))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(FINDING_HEADER)
        for i, f in enumerate(findings, start=1):
            writer.writerow([
                f"REV-{i:03d}", f.severity, f.category, f.component,
                f.reference, f.finding, f.evidence, f.recommendation,
            ])


def write_report(path: Path, rows: list[list[str]], findings: list[Finding],
                 coverage: dict[str, list[str]], balance: dict[str, dict[str, int]],
                 open_questions: list[str]) -> None:
    by_sev = {s: [f for f in findings if f.severity == s] for s in ("High", "Medium", "Low")}
    buf = io.StringIO()
    buf.write("# Unit test design review\n\n")
    buf.write(f"Cases reviewed: {len(rows)}\n\n")
    buf.write("## Summary\n\n")
    buf.write(f"- High: {len(by_sev['High'])}\n- Medium: {len(by_sev['Medium'])}\n- Low: {len(by_sev['Low'])}\n\n")
    buf.write("## Coverage matrix\n\n")
    buf.write("| Requirement | Description | Covering cases |\n|---|---|---|\n")
    for req in REQUIREMENTS:
        cases = coverage.get(req["id"], [])
        shown = ", ".join(cases) if cases else ("n/a (" + req["kind"] + ")" if req["kind"] != "unit" else "**none**")
        buf.write(f"| {req['id']} | {req['text']} | {shown} |\n")
    buf.write("\n## Category balance\n\n")
    buf.write("| Component | Positive | Negative | Edge | Exhaustive |\n|---|---|---|---|---|\n")
    for comp, counts in balance.items():
        buf.write(f"| {comp} | {counts['Positive']} | {counts['Negative']} | {counts['Edge']} | {counts['Exhaustive']} |\n")
    buf.write("\n## Findings by severity\n\n")
    for sev in ("High", "Medium", "Low"):
        buf.write(f"### {sev}\n\n")
        if not by_sev[sev]:
            buf.write("None.\n\n")
            continue
        for f in by_sev[sev]:
            ref = f" ({f.reference})" if f.reference != "-" else ""
            buf.write(f"- **{f.category}** [{f.component}]{ref}: {f.finding}\n")
            buf.write(f"  - Evidence: {f.evidence}\n")
            buf.write(f"  - Recommendation: {f.recommendation}\n")
        buf.write("\n")
    buf.write("## Open questions\n\n")
    if open_questions:
        for q in open_questions:
            buf.write(f"- {q}\n")
    else:
        buf.write("None raised by the design.\n")
    buf.write("\n## Proposed cases\n\n")
    buf.write("Add cases for each High/Medium coverage gap above, using the existing ID scheme.\n")
    path.write_text(buf.getvalue(), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=root / "docs/ut-design/unit-test-design.csv")
    parser.add_argument("--out-dir", type=Path, default=root / "docs/ut-design")
    parser.add_argument("--json", action="store_true", help="print a machine-readable summary")
    parser.add_argument(
        "--fail-on",
        choices=("none", "high", "medium"),
        default="none",
        help="exit 3 when findings at or above this severity remain (default: none)",
    )
    args = parser.parse_args()

    try:
        rows = read_rows(args.design)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    findings: list[Finding] = []
    check_consistency(rows, findings)
    balance = check_category_balance(rows, findings)
    coverage = check_coverage(rows, findings)
    open_questions = check_ambiguity(rows, findings)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_findings(args.out_dir / "review-findings.csv", findings)
    write_report(args.out_dir / "review-report.md", rows, findings, coverage, balance, open_questions)

    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("High", "Medium", "Low")}
    if args.json:
        print(json.dumps({
            "cases": len(rows),
            "findings": counts,
            "coverage": coverage,
            "balance": balance,
            "open_questions": len(open_questions),
        }, indent=2))
    else:
        print(f"reviewed {len(rows)} cases: {counts['High']} high, {counts['Medium']} medium, {counts['Low']} low")
        print(f"wrote {args.out_dir / 'review-findings.csv'}")
        print(f"wrote {args.out_dir / 'review-report.md'}")

    if args.fail_on == "high" and counts["High"]:
        return 3
    if args.fail_on == "medium" and (counts["High"] or counts["Medium"]):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
