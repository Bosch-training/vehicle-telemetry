#!/usr/bin/env python3
"""Validate a refactor unit plan before any code is touched.

A unit plan is the machine-checkable form of "one small, verifiable unit at a
time". Validating it up front catches the two failure modes that make refactors
unpredictable: units that are too big to verify, and units whose expected
behavior is not stated (so nothing can be checked afterwards).

Usage:
    python3 validate_plan.py PLAN.json [--max-files N] [--max-lines N] [--json]

Exit codes: 0 = valid, 1 = invalid, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TRANSFORMATIONS = {
    "extract-method", "extract-function", "extract-class", "inline",
    "rename", "deduplicate", "reorder", "move", "encapsulate",
    "replace-conditional", "introduce-parameter-object", "split-function",
    "remove-dead-code", "simplify", "other",
}
REQUIRED_UNIT_FIELDS = ("id", "target", "transformation", "expected_behavior", "verify")
DEFAULT_MAX_FILES = 5
DEFAULT_MAX_LINES = 50


def validate(plan: dict, max_files: int, max_lines: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(plan, dict):
        return ["plan must be a JSON object"], warnings
    units = plan.get("units")
    if not isinstance(units, list) or not units:
        return ["plan.units must be a non-empty array"], warnings

    seen_ids: set[str] = set()
    for i, unit in enumerate(units):
        where = f"units[{i}]"
        if not isinstance(unit, dict):
            errors.append(f"{where}: must be an object")
            continue
        for field in REQUIRED_UNIT_FIELDS:
            value = unit.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"{where}: missing required field '{field}'")
        uid = unit.get("id")
        if isinstance(uid, str):
            if uid in seen_ids:
                errors.append(f"{where}: duplicate unit id '{uid}'")
            seen_ids.add(uid)
            where = f"unit {uid}"

        transform = unit.get("transformation")
        if isinstance(transform, str) and transform not in TRANSFORMATIONS:
            warnings.append(
                f"{where}: transformation '{transform}' is not in the known set "
                f"({', '.join(sorted(TRANSFORMATIONS))})"
            )

        files = unit.get("files")
        if files is not None:
            if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
                errors.append(f"{where}: 'files' must be an array of paths")
            elif len(files) > max_files:
                errors.append(
                    f"{where}: touches {len(files)} files (max {max_files}) — split the unit"
                )

        est = unit.get("estimated_lines")
        if est is not None:
            if not isinstance(est, int) or est < 0:
                errors.append(f"{where}: 'estimated_lines' must be a non-negative integer")
            elif est > max_lines:
                errors.append(
                    f"{where}: estimated {est} lines (max {max_lines}) — split the unit"
                )

        behavior = unit.get("expected_behavior")
        if isinstance(behavior, str) and behavior.strip().lower() in {
            "unchanged", "same", "no change", "n/a", "tbd", "unknown",
        }:
            warnings.append(
                f"{where}: expected_behavior is '{behavior.strip()}' — state the concrete "
                "observable behavior that must hold, not just 'unchanged'"
            )

        verify = unit.get("verify")
        if isinstance(verify, list) and not verify:
            errors.append(f"{where}: 'verify' is empty — a unit must be verifiable")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", help="path to the unit plan JSON")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.plan)
    if not path.exists():
        print(f"error: no such plan: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate(plan, args.max_files, args.max_lines)
    result = {"plan": str(path), "units": len(plan.get("units", [])), "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"units: {result['units']}")
        for w in warnings:
            print(f"warning: {w}")
        for e in errors:
            print(f"error: {e}")
        if not errors:
            print("plan valid")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())