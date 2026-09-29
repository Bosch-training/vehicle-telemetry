#!/usr/bin/env python3
"""Green gate for the tdd-implement skill.

Compiles the production sources (src/, minus main.cpp) together with the test
sources (tests/) using g++ with -Wall -Wextra, then runs the resulting test
binary and parses the harness output.

The gate is green only when BOTH hold:
  * the build produced no warnings and no errors, and
  * every test case passed.

Usage:
    python3 run_tests.py [--root DIR] [--build-only] [--json]

Exit codes: 0 = green, 1 = build failure or failing tests, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WARNING_RE = re.compile(r"\bwarning:")
ERROR_RE = re.compile(r"\berror:")
SUMMARY_RE = re.compile(r"^TOTAL\s+(\d+)\s+PASSED\s+(\d+)\s+FAILED\s+(\d+)\s*$")
RESULT_RE = re.compile(r"^\[(PASS|FAIL)\]\s+(\S+)\s*(.*)$")


def find_sources(root: Path) -> tuple[list[Path], list[Path]]:
    src_dir = root / "src"
    tests_dir = root / "tests"
    sources = sorted(p for p in src_dir.glob("*.cpp") if p.name != "main.cpp")
    tests = sorted(tests_dir.glob("*.cpp"))
    return sources, tests


def compile_all(root: Path, out_bin: Path) -> tuple[int, str]:
    sources, tests = find_sources(root)
    if not tests:
        return 2, f"no test sources found under {root / 'tests'}"
    cmd = [
        "g++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-I",
        str(root / "src"),
        "-I",
        str(root / "tests"),
        *[str(p) for p in sources],
        *[str(p) for p in tests],
        "-o",
        str(out_bin),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stderr


def parse_output(text: str) -> dict:
    passed: list[str] = []
    failed: list[str] = []
    total = None
    for line in text.splitlines():
        m = RESULT_RE.match(line.strip())
        if m:
            (passed if m.group(1) == "PASS" else failed).append(m.group(2))
            continue
        s = SUMMARY_RE.match(line.strip())
        if s:
            total = int(s.group(1))
    return {"total": total, "passed": passed, "failed": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and run the C++ test suite.")
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--build-only", action="store_true", help="compile without running")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "src").is_dir():
        print(f"error: {root / 'src'} does not exist", file=sys.stderr)
        return 2
    if shutil.which("g++") is None:
        print("error: g++ not found on PATH", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        out_bin = Path(tmp) / "run_tests"
        rc, stderr = compile_all(root, out_bin)

        warnings = [ln for ln in stderr.splitlines() if WARNING_RE.search(ln)]
        errors = [ln for ln in stderr.splitlines() if ERROR_RE.search(ln)]

        if rc != 0:
            result = {
                "status": "build-failed",
                "warnings": warnings,
                "errors": errors,
                "stderr": stderr,
            }
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("BUILD FAILED")
                for ln in errors or stderr.splitlines():
                    print(f"  {ln}")
            return 1

        if warnings:
            result = {"status": "warnings", "warnings": warnings}
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("BUILD HAS WARNINGS (-Wall -Wextra must be clean)")
                for ln in warnings:
                    print(f"  {ln}")
            return 1

        if args.build_only:
            result = {"status": "build-ok", "warnings": []}
            print(json.dumps(result, indent=2) if args.json else "BUILD OK (no warnings)")
            return 0

        proc = subprocess.run([str(out_bin)], capture_output=True, text=True)
        parsed = parse_output(proc.stdout)
        green = proc.returncode == 0 and not parsed["failed"]

        result = {
            "status": "green" if green else "red",
            "total": parsed["total"],
            "passed": parsed["passed"],
            "failed": parsed["failed"],
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for cid in parsed["passed"]:
                print(f"[PASS] {cid}")
            for cid in parsed["failed"]:
                print(f"[FAIL] {cid}")
            print(
                f"TOTAL {parsed['total']} PASSED {len(parsed['passed'])} "
                f"FAILED {len(parsed['failed'])}"
            )
            print("GREEN" if green else "RED")
        return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())