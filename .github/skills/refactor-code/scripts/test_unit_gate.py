#!/usr/bin/env python3
"""Unit tests for unit_gate.py. Run: cd scripts && python3 test_unit_gate.py"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / "unit_gate.py"


def run(*args, cwd):
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=str(cwd), capture_output=True, text=True,
    )


class UnitGateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "Vehicle.h").write_text(
            "#pragma once\nclass Vehicle {\npublic:\n    int id;\n    int getId() const;\n};\n",
            encoding="utf-8",
        )
        (self.root / "src" / "Vehicle.cpp").write_text(
            '#include "Vehicle.h"\nint Vehicle::getId() const { return id; }\n',
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_snapshot_then_no_change_passes(self):
        self.assertEqual(run("snapshot", cwd=self.root).returncode, 0)
        proc = run("check", cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("files touched: 0", proc.stdout)

    def test_small_change_within_budget_passes(self):
        run("snapshot", cwd=self.root)
        (self.root / "src" / "Vehicle.cpp").write_text(
            '#include "Vehicle.h"\nint Vehicle::getId() const { return this->id; }\n',
            encoding="utf-8",
        )
        proc = run("check", cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("files touched: 1", proc.stdout)

    def test_too_many_files_fails(self):
        run("snapshot", cwd=self.root)
        for i in range(6):
            (self.root / "src" / f"Extra{i}.h").write_text("int x;\n", encoding="utf-8")
        proc = run("check", "--max-files", "5", cwd=self.root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unit budget", proc.stdout)

    def test_too_many_lines_fails(self):
        run("snapshot", cwd=self.root)
        body = "\n".join(f"int v{i};" for i in range(80))
        (self.root / "src" / "Vehicle.cpp").write_text(body + "\n", encoding="utf-8")
        proc = run("check", "--max-lines", "50", cwd=self.root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("changed lines", proc.stdout)

    def test_allow_list_flags_out_of_scope(self):
        run("snapshot", cwd=self.root)
        (self.root / "src" / "Vehicle.cpp").write_text("int changed;\n", encoding="utf-8")
        proc = run("check", "--allow", "src/Vehicle.h", cwd=self.root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("out of scope", proc.stdout)

    def test_signature_removal_detected(self):
        run("snapshot", cwd=self.root)
        (self.root / "src" / "Vehicle.h").write_text(
            "#pragma once\nclass Vehicle {\npublic:\n    int id;\n};\n",
            encoding="utf-8",
        )
        proc = run("signatures", cwd=self.root)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("REMOVED", proc.stdout)
        self.assertIn("getId", proc.stdout)

    def test_signature_addition_reported_but_passes(self):
        run("snapshot", cwd=self.root)
        (self.root / "src" / "Vehicle.h").write_text(
            "#pragma once\nclass Vehicle {\npublic:\n    int id;\n    int getId() const;\n    int getSpeed() const;\n};\n",
            encoding="utf-8",
        )
        proc = run("signatures", cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("ADDED", proc.stdout)

    def test_check_without_snapshot_is_usage_error(self):
        proc = run("check", cwd=self.root)
        self.assertEqual(proc.returncode, 2)

    def test_json_output_is_parseable(self):
        run("snapshot", cwd=self.root)
        (self.root / "src" / "Vehicle.cpp").write_text("int x;\n", encoding="utf-8")
        proc = run("check", "--json", cwd=self.root)
        data = json.loads(proc.stdout)
        self.assertEqual(data["files_touched"], 1)
        self.assertIn("budget", data)

    def test_build_unavailable_is_not_a_failure(self):
        # No CMakeLists.txt and no translation units -> graceful pass.
        empty = self.root / "empty"
        empty.mkdir()
        proc = run("build", cwd=empty)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("unavailable", proc.stdout)

    def test_cmake_project_without_cmake_falls_back_to_syntax_only(self):
        # A CMakeLists.txt with no cmake binary must not crash; it should fall
        # back to -fsyntax-only and still report a result.
        (self.root / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(x CXX)\n", encoding="utf-8"
        )
        proc = run("build", cwd=self.root)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn(proc.returncode, (0, 1))
        self.assertIn("build mode:", proc.stdout)

    def test_build_detects_compile_error(self):
        (self.root / "src" / "Broken.cpp").write_text(
            "int main() { this is not c++; }\n", encoding="utf-8"
        )
        proc = run("build", cwd=self.root)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("errors:", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)