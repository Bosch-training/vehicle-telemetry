---
name: tdd-test-design
description: "Design unit-test cases (not test code) for the Vehicle Telemetry Visualization project and write them as a CSV test-case matrix under docs/ut-design/. Use whenever the user asks to design tests, plan test cases, write a test-case matrix or test plan, cover a component with happy-path/negative/edge cases, or asks what to test for VehicleBuilder, VehicleRepository, TelemetryService, or DashboardRenderer — even if they do not say 'skill' or name a component. This skill is TDD-first: it produces the test design only and must never write production or test implementation code."
---

# TDD test design

Produce a **test-case design**, not test code. The deliverable is a CSV matrix that a developer can later turn into tests. This project follows TDD, so the design comes first and the implementation does not exist yet — designing the tests is the whole job.

## Hard constraint (do not violate)

**Never write, generate, or modify implementation code.** This includes:

- No C++ test files (`.cpp`/`.h` test sources), no `assert`/`TEST`/`TEST_CASE` bodies.
- No production code in `src/` — no classes, methods, stubs, or "just a skeleton".
- No test framework setup, no `CMakeLists.txt` test targets, no build/run of a test suite.
- No code blocks that could be pasted in as an implementation.

If the user asks for the tests themselves, stop and say the design must be reviewed and approved first (TDD: red comes after the design, and the developer writes it). The only artifact you produce is the CSV.

## Workflow

1. **Ground the design in the docs.** Read `docs/requirements.md` and `docs/swdd.md` (class contracts, error handling, resolved decisions). If `src/` exists, read the headers to get real signatures. Do not invent validation rules the docs do not state.
2. **Pick scope.** All four components (`VehicleBuilder`, `VehicleRepository`, `TelemetryService`, `DashboardRenderer`) unless the user names some. Default output: `docs/ut-design/unit-test-design.csv`.
3. **Design cases in all four categories for every component in scope:**
   - **Positive** — typical inputs and normal usage.
   - **Negative** — invalid or out-of-range input (negative speed, battery outside 0–100, invalid GPS, unknown id).
   - **Edge** — boundaries (battery 0/100, speed 0, empty/single-vehicle fleet, `INT_MIN`/`INT_MAX`, threshold exactly equal to a value).
   - **Exhaustive** — interacting combinations (several invalid fields at once, several vehicles at a threshold, repeated `getInstance()` calls).
4. **Write the CSV** with the exact header below. Quote any field containing a comma. Leave `Actual Output` blank and `Automated (Yes/No)` as `No` at design time.
5. **Validate.** Re-read the file and confirm: header matches exactly, IDs are unique and use the `VB`/`VR`/`TS`/`DR` prefix with a category suffix matching `Testcase Type`, no empty required fields, no unquoted commas shifting columns.
6. **Report** row counts per component and category, plus any open questions recorded in `Comments`.

## CSV contract

Header, exactly in this order:

`Testcase ID, Testcase Name, Test Description, Input, Testcase Type, Expected Output, Actual Output, Automated (Yes/No), Comments`

| Column | Rule |
|---|---|
| Testcase ID | Unique, `<COMP>-<POS\|NEG\|EDGE\|EXH>-<nnn>`, e.g. `VB-POS-001`. Prefixes: `VB`, `VR`, `TS`, `DR`. |
| Testcase Name | Short label. |
| Test Description | What is verified and why. |
| Input | Concrete values or state, so the case can be implemented without guessing. |
| Testcase Type | `Positive`, `Negative`, `Edge`, or `Exhaustive`. |
| Expected Output | Observable result or behavior. |
| Actual Output | Leave blank at design time. |
| Automated (Yes/No) | `No` at design time. |
| Comments | Assumptions, open questions, traceability (e.g. "SWDD 5.4"). May be empty. |

## Design quality rules

- Every component needs Positive, Negative, Edge, and Exhaustive cases — do not skip a category because it seems unlikely to fail.
- Every case needs concrete input, an observable expected result, and a reason it exists.
- Cover interactions, not just isolated setters: threshold boundaries, mixed field widths, repeated singleton access, repository consistency.
- Flag unspecified behavior in `Comments` rather than making the expected result falsely definitive. A hedged expected output cannot fail and therefore verifies nothing.
- Tests described here rely only on the C++ standard library (e.g. `<cassert>`), with no third-party framework and no files, databases, or network.

## Related skills

- `ut-test-design` — the fuller version of this workflow, with bundled generator/validator scripts and a review-driven fix loop. Prefer it when the user wants scripted generation or to apply review findings.
- `ut-test-design-review` — reviews an existing design CSV for coverage gaps.