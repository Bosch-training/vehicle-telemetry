#!/usr/bin/env python3
"""Deterministic gate for behavior-preserving refactors.

The gate makes "one small, verifiable unit at a time" checkable instead of a
matter of judgment. It snapshots the tree before a unit, then after the unit it
reports exactly what changed, whether the change fits the unit budget, whether
public header signatures moved, and whether the tree still compiles.

Subcommands:
    snapshot    Record the current state of source files (hashes + signatures).
    check       Compare the tree to the snapshot and enforce the unit budget.
    signatures  Compare public header signatures to the snapshot.
    build       Compile the tree (CMake if present, else g++ -fsyntax-only).
    all         check + signatures + build in one pass.

Usage:
    python3 unit_gate.py snapshot [--root DIR] [--snapshot DIR]
    python3 unit_gate.py check    [--root DIR] [--snapshot DIR]
                                  [--max-files N] [--max-lines N]
                                  [--allow PATH ...] [--json]
    python3 unit_gate.py signatures [--root DIR] [--snapshot DIR] [--json]
    python3 unit_gate.py build    [--root DIR] [--build-dir DIR] [--json]
    python3 unit_gate.py all      [--root DIR] [--snapshot DIR] [--json]

Exit codes: 0 = pass, 1 = gate failure, 2 = usage error.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_INCLUDE = ("*.h", "*.hpp", "*.hh", "*.cpp", "*.cc", "*.cxx", "CMakeLists.txt")
EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "build", "out", "dist", "node_modules",
    "__pycache__", ".cache", ".refactor-gate", "cmake-build-debug",
    "cmake-build-release", ".venv", "venv",
}
DEFAULT_SNAPSHOT = ".refactor-gate/snapshot"
DEFAULT_BUILD_DIR = ".refactor-gate/build"
DEFAULT_MAX_FILES = 5
DEFAULT_MAX_LINES = 50

# A declaration line: has a parameter list and ends in ';'. Deliberately loose
# so it catches signature drift without needing a real C++ parser.
_SIG_RE = re.compile(r"^[^#/].*\([^;{]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?;\s*$")
_SIG_SKIP = re.compile(r"^\s*(?:using|typedef|return|#)")


class Gate:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)


def _iter_sources(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for name in sorted(filenames):
            if any(Path(name).match(pat) for pat in DEFAULT_INCLUDE):
                yield Path(dirpath) / name


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def extract_signatures(path: Path) -> list[str]:
    """Normalized public declarations in a header, for API-drift detection."""
    try:
        text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return []
    sigs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or _SIG_SKIP.match(line):
            continue
        if _SIG_RE.match(line):
            sigs.append(re.sub(r"\s+", " ", line))
    return sorted(set(sigs))


def cmd_snapshot(args) -> int:
    root = Path(args.root).resolve()
    snap = (root / args.snapshot).resolve()
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True)
    files_dir = snap / "files"
    manifest = {"root": str(root), "files": {}}
    for path in _iter_sources(root):
        rel = _rel(root, path)
        entry = {"sha256": _sha256(path)}
        if path.suffix in {".h", ".hpp", ".hh"}:
            entry["signatures"] = extract_signatures(path)
        manifest["files"][rel] = entry
        # Keep a copy so the post-unit check can compute real line deltas.
        dest = files_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    (snap / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"snapshot: {len(manifest['files'])} files -> {snap}")
    return 0


def _load_manifest(root: Path, snapshot: str) -> dict:
    path = (root / snapshot / "manifest.json").resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"no snapshot at {path}; run `unit_gate.py snapshot` before the unit"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _line_delta(old: str, new: str) -> tuple[int, int]:
    added = removed = 0
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def _diff_tree(root: Path, manifest: dict) -> dict:
    old_files = manifest["files"]
    current = {_rel(root, p): p for p in _iter_sources(root)}
    changed, added, deleted = [], [], []
    for rel, entry in sorted(old_files.items()):
        path = current.get(rel)
        if path is None:
            deleted.append(rel)
            continue
        if _sha256(path) != entry["sha256"]:
            changed.append(rel)
    for rel in sorted(current):
        if rel not in old_files:
            added.append(rel)
    return {"changed": changed, "added": added, "deleted": deleted}


def cmd_check(args) -> int:
    root = Path(args.root).resolve()
    gate = Gate()
    try:
        manifest = _load_manifest(root, args.snapshot)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    delta = _diff_tree(root, manifest)
    touched = delta["changed"] + delta["added"] + delta["deleted"]

    # Line counts need the pre-unit text; the snapshot stores hashes only, so
    # count against the snapshot copy when it exists, else report file-level.
    snap_dir = (root / args.snapshot).resolve()
    total_lines = 0
    per_file = {}
    for rel in delta["changed"] + delta["added"]:
        new_path = root / rel
        old_path = snap_dir / rel
        old_text = old_path.read_text(encoding="utf-8", errors="replace") if old_path.exists() else ""
        new_text = new_path.read_text(encoding="utf-8", errors="replace")
        a, r = _line_delta(old_text, new_text)
        per_file[rel] = {"added": a, "removed": r}
        total_lines += a + r

    if not touched:
        gate.note("no source changes since snapshot")

    if len(touched) > args.max_files:
        gate.fail(
            f"unit budget: {len(touched)} files changed (max {args.max_files}) — "
            "split into smaller units"
        )
    if total_lines > args.max_lines:
        gate.fail(
            f"unit budget: {total_lines} changed lines (max {args.max_lines}) — "
            "split into smaller units"
        )
    if args.allow:
        allowed = {Path(p).as_posix().lstrip("./") for p in args.allow}
        for rel in touched:
            if rel not in allowed:
                gate.fail(f"out of scope: {rel} changed but not in --allow")

    result = {
        "changed": delta["changed"],
        "added": delta["added"],
        "deleted": delta["deleted"],
        "files_touched": len(touched),
        "lines_changed": total_lines,
        "per_file": per_file,
        "budget": {"max_files": args.max_files, "max_lines": args.max_lines},
        "failures": gate.failures,
        "notes": gate.notes,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"files touched: {len(touched)} (max {args.max_files})")
        print(f"lines changed: {total_lines} (max {args.max_lines})")
        for rel in touched:
            d = per_file.get(rel, {})
            tag = "deleted" if rel in delta["deleted"] else ("added" if rel in delta["added"] else "modified")
            print(f"  {tag:8} {rel}  +{d.get('added', 0)} -{d.get('removed', 0)}")
        for n in gate.notes:
            print(f"note: {n}")
        for f in gate.failures:
            print(f"FAIL: {f}")
    return 1 if gate.failures else 0


def cmd_signatures(args) -> int:
    root = Path(args.root).resolve()
    try:
        manifest = _load_manifest(root, args.snapshot)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    removed, added = [], []
    for rel, entry in sorted(manifest["files"].items()):
        if "signatures" not in entry:
            continue
        path = root / rel
        if not path.exists():
            removed.append({"file": rel, "signature": "<file deleted>"})
            continue
        old = set(entry["signatures"])
        new = set(extract_signatures(path))
        for sig in sorted(old - new):
            removed.append({"file": rel, "signature": sig})
        for sig in sorted(new - old):
            added.append({"file": rel, "signature": sig})

    result = {"removed": removed, "added": added}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if not removed and not added:
            print("signatures: unchanged")
        for item in removed:
            print(f"REMOVED {item['file']}: {item['signature']}")
        for item in added:
            print(f"ADDED   {item['file']}: {item['signature']}")
    # A removed or changed public signature is a behavior change unless the
    # goal explicitly allowed it; the skill decides, the gate only reports.
    return 1 if removed else 0


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    except FileNotFoundError:
        return 127, f"tool not found: {cmd[0]}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _syntax_only(root: Path, result: dict, args) -> int:
    """Compile each translation unit with -fsyntax-only. Used when CMake is
    absent or unavailable, so the gate still catches compile errors."""
    cpp = [p for p in _iter_sources(root) if p.suffix in {".cpp", ".cc", ".cxx"}]
    if not cpp:
        result["mode"] = "unavailable"
        result["output"] = "no CMakeLists.txt and no translation units to compile"
        return _emit_build(args, result)
    compiler = shutil.which("g++") or shutil.which("clang++")
    if compiler is None:
        result["mode"] = "unavailable"
        result["output"] = "no C++ compiler on PATH"
        return _emit_build(args, result)
    result["mode"] = "syntax-only"
    includes = [str(root), str(root / "src")]
    chunks = []
    for path in cpp:
        cmd = [compiler, "-std=c++17", "-fsyntax-only", "-Wall", "-Wextra"]
        for inc in includes:
            cmd += ["-I", inc]
        cmd.append(str(path))
        _, out = _run(cmd, root)
        chunks.append(out)
    result["output"] = "\n".join(chunks)
    result["warnings"] = result["output"].count("warning:")
    result["errors"] = result["output"].count("error:")
    return _emit_build(args, result)


def cmd_build(args) -> int:
    root = Path(args.root).resolve()
    build_dir = (root / args.build_dir).resolve()
    result = {"mode": None, "warnings": 0, "errors": 0, "ok": False, "output": ""}

    if (root / "CMakeLists.txt").exists() and shutil.which("cmake") is not None:
        result["mode"] = "cmake"
        rc, out = _run(
            ["cmake", "-S", ".", "-B", str(build_dir), "-DCMAKE_CXX_FLAGS=-Wall -Wextra"],
            root,
        )
        if rc != 0:
            result["output"] = out
            result["errors"] = out.count("error:")
            return _emit_build(args, result)
        rc, out = _run(["cmake", "--build", str(build_dir)], root)
        result["output"] = out
        result["warnings"] = out.count("warning:")
        result["errors"] = out.count("error:")
        return _emit_build(args, result)

    if (root / "CMakeLists.txt").exists():
        # CMake project but no cmake binary: fall back to syntax-only so the
        # gate still verifies compilation instead of crashing.
        rc = _syntax_only(root, result, args)
        if result["mode"] == "syntax-only":
            result["output"] = "note: cmake not on PATH; used -fsyntax-only\n" + result["output"]
        return rc

    return _syntax_only(root, result, args)


def _emit_build(args, result: dict) -> int:
    result["ok"] = result["mode"] != "unavailable" and result["errors"] == 0 and result["warnings"] == 0
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"build mode: {result['mode']}")
        print(f"warnings: {result['warnings']}  errors: {result['errors']}")
        if result["mode"] == "unavailable":
            print(f"note: {result['output']}")
        elif not result["ok"]:
            print(result["output"])
    if result["mode"] == "unavailable":
        return 0  # not a failure; the skill falls back to manual verification
    return 0 if result["ok"] else 1


def cmd_all(args) -> int:
    rc_check = cmd_check(args)
    rc_sig = cmd_signatures(args)
    rc_build = cmd_build(args)
    return 1 if (rc_check or rc_sig or rc_build) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--root", default=".", help="project root (default: .)")
        p.add_argument("--snapshot", default=DEFAULT_SNAPSHOT, help="snapshot dir, relative to root")
        p.add_argument("--json", action="store_true", help="machine-readable output")

    p_snap = sub.add_parser("snapshot", help="record the pre-unit state")
    common(p_snap)
    p_snap.set_defaults(func=cmd_snapshot)

    p_check = sub.add_parser("check", help="diff against snapshot and enforce budget")
    common(p_check)
    p_check.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    p_check.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    p_check.add_argument("--allow", action="append", default=[], help="path allowed to change (repeatable)")
    p_check.set_defaults(func=cmd_check)

    p_sig = sub.add_parser("signatures", help="detect public API drift")
    common(p_sig)
    p_sig.set_defaults(func=cmd_signatures)

    p_build = sub.add_parser("build", help="compile the tree")
    common(p_build)
    p_build.add_argument("--build-dir", default=DEFAULT_BUILD_DIR)
    p_build.set_defaults(func=cmd_build)

    p_all = sub.add_parser("all", help="check + signatures + build")
    common(p_all)
    p_all.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    p_all.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    p_all.add_argument("--allow", action="append", default=[])
    p_all.add_argument("--build-dir", default=DEFAULT_BUILD_DIR)
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())