---
name: tdd-implement
description: "Implement the production C++ code for the Vehicle Telemetry Visualization project from the approved test design, then drive the suite to green. Use whenever the user asks to implement, write, or build the code, turn the test design into working code, make the tests pass, run the test suite, or fix failing tests until everything is green — even if they do not say 'skill' or name a component. This is the green phase of TDD: it starts after tdd-test-design and must never change the approved test design to make a test pass."
---

# TDD implement

Turn the approved test design into working code, then fix the code until every test is green. This is the **green phase** of TDD: `tdd-test-design` produced the cases, this skill writes the tests, implements the production code, and closes the loop.

The design CSV is the contract. Implement exactly the cases it lists — no more, no fewer — and never edit a case's expected result to make it pass. If a case cannot pass without changing the design, that is a design change, not an implementation fix.

## Hard constraints (do not violate)

- **Do not change the test design to make a test pass.** No editing `docs/ut-design/unit-test-design.csv` expected outputs, no deleting or weakening a case, no marking a case skipped just because it is hard. A failing case is a signal about the code (or, rarely, the design) — resolve it honestly.
- **Do not invent requirements.** Implement what `docs/swdd.md` and the design specify. If a case needs behavior the docs do not define, stop and raise it (see Stop conditions).
- **Standard library only.** No third-party test framework, no new dependencies. Use the bundled header-only harness.
- **Compile clean.** `-Wall -Wextra`, no warnings. A warning fails the gate.
- **One class per header/source pair**, PascalCase classes, camelCase methods, matching the existing conventions in `.github/copilot-instructions.md`.

## Workflow

1. **Ground in the design and the docs.** Read `docs/ut-design/unit-test-design.csv` (the approved cases), `docs/requirements.md`, `docs/swdd.md` (5.x class contracts, 7 error handling, 12 resolved decisions), and `.github/copilot-instructions.md`. The CSV rows are the work items; the SWDD gives the signatures and the resolved behaviors. If `docs/ut-design/review-decisions.json` exists, it records the decisions the design depends on — honor them.
2. **Write the tests first (red).** Create `tests/` with one test file per component (`test_vehicle_builder.cpp`, `test_vehicle_repository.cpp`, `test_telemetry_service.cpp`, `test_dashboard_renderer.cpp`). Copy the bundled harness to `tests/TestHarness.h` and give every case its design ID as the first `TEST_CASE` argument:
   ```cpp
   TEST_CASE("VB-POS-001", "Full fluent chain sets all fields") { /* ... */ }
   ```
   Cases the design marks as deferred (for example `VR-EDGE-005`, "no test seam") are recorded with a `// TC-SKIP: <ID> <reason>` comment instead of a test body — do not invent a seam the SWDD does not define. Run the gate now and expect **red**: the production code does not exist yet.
3. **Implement the production code (green).** Create `src/` per SWDD 5.x: `Vehicle.h`, `VehicleBuilder.h/.cpp`, `VehicleRepository.h/.cpp`, `TelemetryService.h/.cpp`, `DashboardRenderer.h/.cpp`, `main.cpp`. Keep the patterns explicit and visible — this is a teaching artifact.
4. **Run the green gate.**
   ```bash
   python3 .github/skills/tdd-implement/scripts/run_tests.py
   ```
   Exit 0 means the build is warning-free and every test passed. Anything else is a failure to fix.
5. **Fix the code until green.** For each `[FAIL]` line, map the case ID back to its design row, read the expected output, and fix the **production code**. Re-run the gate. Repeat until it exits 0. See the fix loop below.
6. **Check traceability.**
   ```bash
   python3 .github/skills/tdd-implement/scripts/check_traceability.py
   ```
   Every designed case must be implemented or explicitly skipped, and no test may exist that the design does not list. Exit 0 means the design and the suite agree.
7. **Record the results.** Write the outcomes back into the design CSV so it stays the living record:
   ```bash
   python3 .github/skills/tdd-implement/scripts/update_results.py
   ```
   Passing cases get `Actual Output = Pass` and `Automated = Yes`; skipped cases get the reason and `No`.
8. **Report.** Per-component pass counts, the skipped cases with their reasons, and any design ambiguity the implementation surfaced.

## The fix loop

The loop is: **run → read the failing case → fix the production code → re-run.** One failure at a time, smallest fix that addresses the case.

- Fix the code, not the test. The test encodes the approved expected output; changing it to pass is the one thing this skill must not do.
- If the test itself is genuinely wrong (it does not match its design row), that is a **design defect** — stop and raise it, do not silently "fix" the test.
- If a failure needs a behavior the SWDD does not specify, that is an **open decision** — stop and raise it so it can be resolved in the design (the `ut-test-design` review loop), not guessed here.
- Do not batch: fix one failing case, re-run, confirm the count moved, then continue.

**Stop conditions** — stop and report rather than continuing when:

- A failure requires a behavior the SWDD and design do not define.
- The only way to pass is to weaken, delete, or re-expect a designed case.
- The build fails for a missing toolchain or environment problem (not a code error).
- Three consecutive iterations do not reduce the failure count — report the blocker instead of thrashing.

## Rules

1. **The design is the contract.** Implement its cases exactly; do not add cases it does not list or drop cases it does.
2. **Fix code, not tests.** Never change an expected result to make a test pass.
3. **Red before green.** Write the tests before the implementation; the first gate run is expected to fail.
4. **Compile clean.** `-Wall -Wextra`, no warnings; a warning fails the gate.
5. **Standard library only.** No third-party framework or dependency.
6. **Follow the SWDD signatures.** Public interfaces match SWDD 5.x; do not invent methods the design does not use.
7. **Honor the resolved decisions.** SWDD 12 and `review-decisions.json` define the boundary behaviors (strict `<` threshold, verbatim builder storage, 2-decimal precision, and so on).
8. **Keep it a teaching artifact.** Explicit patterns, clear names, no cleverness.

## Output

- `tests/` — one test file per component plus `TestHarness.h`, every case tagged with its design ID.
- `src/` — the production code per SWDD 5.x.
- A green gate run (`run_tests.py` exit 0) and a clean traceability run (`check_traceability.py` exit 0).
- The design CSV updated with actual outcomes.
- A report: per-component pass counts, skipped cases and reasons, and any ambiguity raised.

## Bundled resources

- `scripts/run_tests.py` — the green gate. Compiles `src/` (minus `main.cpp`) and `tests/` with `g++ -std=c++17 -Wall -Wextra`, runs the test binary, and parses the harness output. Exit 0 = warning-free build and all tests pass, 1 = build failure or failing tests, 2 = usage error. `--build-only` compiles without running; `--json` for machine-readable output.
- `scripts/check_traceability.py` — verifies every designed case is implemented or explicitly skipped, and that no test exists outside the design. Exit 0 = design and suite agree, 1 = missing or extra cases, 2 = usage error.
- `scripts/update_results.py` — writes outcomes back into the design CSV (`Actual Output`, `Automated`). Exit 0 = updated, 1 = input error, 2 = usage error. `--dry-run` previews.
- `scripts/test_run_tests.py`, `scripts/test_check_traceability.py` — unit tests for the scripts (`cd scripts && python3 test_run_tests.py`). Rerun after changing a script.
- `assets/TestHarness.h` — the header-only test harness to copy into `tests/`. Provides `TEST_CASE`, `CHECK`, `CHECK_EQ`, `CHECK_NEAR`, and a `main` that prints `[PASS]`/`[FAIL]` lines and a `TOTAL n PASSED p FAILED f` summary.
- `references/implementation-checklist.md` — the judgment checklist for closing out the implementation.
- `evals/evals.json` — test prompts for measuring the skill.

## Constraints

- Do not modify the approved test design to make a test pass.
- Do not add a test framework or any third-party dependency.
- Do not implement behavior the SWDD does not specify; raise it instead.
- Do not stop at "it compiles" — the gate must be green and traceability clean.