# Implementation checklist

The gate (`run_tests.py`) and traceability check (`check_traceability.py`) cover
the mechanical facts. This checklist covers the judgment calls they cannot make.
Work through it before declaring the implementation done.

## Before writing code

- [ ] Read the design CSV and confirmed the case count per component.
- [ ] Read SWDD 5.x for the exact signatures and SWDD 12 / `review-decisions.json`
      for the resolved boundary behaviors.
- [ ] Identified the cases the design marks as deferred (no test seam) so they are
      recorded as `TC-SKIP`, not silently dropped.

## Tests

- [ ] One test file per component under `tests/`, plus `TestHarness.h`.
- [ ] Every `TEST_CASE` uses its design ID as the first argument, exactly as written.
- [ ] Every designed case is either implemented or has a `// TC-SKIP: <ID> <reason>`.
- [ ] No test exists that the design does not list.
- [ ] Tests assert the design's expected output, not a weaker proxy (a case that
      cannot fail verifies nothing).

## Production code

- [ ] `src/` matches SWDD 5.x: `Vehicle.h`, `VehicleBuilder`, `VehicleRepository`,
      `TelemetryService`, `DashboardRenderer`, `main.cpp`.
- [ ] Public signatures match the SWDD; no invented methods.
- [ ] Resolved decisions honored: verbatim builder storage, strict `<` threshold,
      2-decimal renderer precision, widened Name column, header-only empty table,
      omitted empty warning list, `0`/`0.00` zero-vehicle summary, literal `nan`.
- [ ] One class per header/source pair; PascalCase classes, camelCase methods.
- [ ] Standard library only; no third-party framework or dependency.

## Green gate

- [ ] `run_tests.py` exits 0: warning-free `-Wall -Wextra` build and all tests pass.
- [ ] `check_traceability.py` exits 0: design and suite agree.
- [ ] `update_results.py` recorded the outcomes in the design CSV.

## Honesty

- [ ] No expected output was changed to make a test pass.
- [ ] No case was deleted, weakened, or skipped to reach green.
- [ ] Any behavior the SWDD does not define was raised, not guessed.
- [ ] Skipped cases are reported with their reasons, not hidden.