---
name: ut-test-design
description: "Design exhaustive C++ unit-test cases for the Vehicle Telemetry Visualization project (VehicleBuilder, VehicleRepository, TelemetryService, DashboardRenderer) and write them as a validated CSV test-case matrix under docs/ut-design/. Also owns the review-driven fix loop: turn review findings into recorded decisions and apply them to the CSV. Use whenever the user mentions unit test design, test case matrix, test plan CSV, test cases for a component, happy-path/negative/edge/exhaustive coverage, asks to regenerate, fix, or validate the ut-design CSV, or asks to fix, apply, or close out review findings or comments on the test design, even if they do not say 'skill' or name a component."
---

# UT test design

Produce a test-case design, not test code, as a validated CSV matrix. The skill owns the case source and generation workflow; do not rely on prompt text or hand-authored CSV. Reviewers open the output in spreadsheets, so a single unescaped comma can shift columns and invalidate the matrix.

## Workflow

1. **Ground the cases in the docs and implementation.** Read `docs/requirements.md` and `docs/swdd.md` (sections 5.x for class contracts, 7 for error handling, 12 for resolved design decisions). If `src/` exists, read the headers/sources of the components in scope. Expected outputs must use real signatures and observable behavior (for example, `getById` returns `std::optional<Vehicle>`). Do not invent validation rules. Where the docs and implementation are silent or disagree, make the case concrete and record the ambiguity in `Comments` — then resolve it through the review loop rather than leaving it hedged.
2. **Pick scope.** All four components unless the user names some. Default output is one consolidated file, `docs/ut-design/unit-test-design.csv`; use one file per component (`docs/ut-design/<Component>.csv`) only if asked.
3. **Design cases for every component in all four categories.** Do not skip a category because it seems unlikely to fail.
   - **Positive** - typical inputs and normal usage.
   - **Negative** - invalid or out-of-range input (negative speed, battery outside 0-100, invalid GPS, unknown id, negative or oversized threshold).
   - **Edge** - boundaries (battery 0/100, speed 0, empty/single-vehicle fleet, first/last id, `INT_MIN`/`INT_MAX`, threshold exactly equal to a battery value).
   - **Exhaustive** - interacting combinations (several invalid fields at once, several vehicles at the threshold, mixed field widths in the table, repeated `getInstance()` calls).
4. **Generate the CSV with the bundled generator.** Keep the checked-in case matrix as the source data and run:
   ```bash
   python3 .github/skills/ut-test-design/scripts/generate_csv.py
   ```
   The generator writes all 9 fields with `csv.writer(f, lineterminator="\n")` and validates the result. Never join fields with commas, hand-quote cells, or create a second prompt/file that duplicates this workflow.
5. **Validate and auto-fix (mandatory):**
   ```bash
   python3 .github/skills/ut-test-design/scripts/validate_csv.py docs/ut-design
   ```
   The script re-reads the file with a strict parser and repairs what it safely can: rejoins rows split by unquoted commas, normalizes Type/Automated values, header case, BOM, CRLF, trailing newline, embedded newlines, and prefixes cells that spreadsheets would evaluate as formulas (`=`, `@`, `+x`, `-x`). It then re-verifies the written file. IDs must use the documented `VB`, `VR`, `TS`, or `DR` component prefixes, and the ID category must agree with `Testcase Type`; these are validation errors, not warnings. If it prints `fixed:` lines for realigned rows, spot-check those rows. If it exits 1 with `error:` lines (bad header, duplicate ID, empty required field, invalid ID, category mismatch, unknown type), the file is left untouched; correct the generating script and rerun. Use `--check-only` to report without modifying.
6. **Report** row counts per component and category, plus open questions raised in `Comments`.
7. **Close the review loop (when a review exists).** If `docs/ut-design/review-findings.csv` exists, do not hand-edit the CSV to silence findings. Instead run the loop below, which turns each finding into a decision and applies it through the generator.

## Review loop

The design and the review are two halves of one loop. The review finds gaps; the loop fixes them by recording a decision and re-applying it, so the CSV stays reproducible and the reasoning stays traceable.

1. **Review.** Run the review skill (or `python3 .github/skills/ut-test-design-review/scripts/review_design.py --fail-on high`). Exit 3 means High findings remain.
2. **Decide.** Read `review-findings.csv`. For each finding, the fix is usually a decision the SWDD left open, not a new case. Record those decisions in `docs/ut-design/review-decisions.json`:
   ```json
   {
     "builder_validation": "store",
     "threshold_comparison": "strict",
     "renderer_precision": 2,
     "renderer_long_name": "widen",
     "renderer_empty_list": "header-only",
     "renderer_no_low_battery": "omit",
     "test_seam": "none"
   }
   ```
   Only include keys you have actually decided. A missing key leaves its finding open, which is the honest outcome — do not guess a behavior the SWDD does not specify.
3. **Apply.** `python3 .github/skills/ut-test-design/scripts/apply_review.py --dry-run` to preview, then without `--dry-run` to write. The script rewrites the affected rows' `Expected Output` and `Comments` from the decisions; it never invents a decision, and re-running it on an already-fixed CSV is a no-op.
4. **Validate.** `python3 .github/skills/ut-test-design/scripts/validate_csv.py docs/ut-design` — the CSV contract still holds after the rewrite.
5. **Re-review.** Run the review again. Repeat from step 2 until `--fail-on high` exits 0. Findings that cannot be closed by a decision (a genuinely missing case, a build-level criterion) are added as new rows or accepted as informational; the loop converges when only those remain.

Do not edit the CSV directly to clear a finding. If a finding cannot be expressed as a decision or a new case, that is a signal the requirement itself is unclear — raise it rather than papering over it.

## Design Quality Rules

- Every component must have Positive, Negative, Edge, and Exhaustive cases.
- IDs must be unique and use `VB`, `VR`, `TS`, or `DR` with a matching category suffix.
- Every case needs concrete input, observable expected behavior, and a useful reason for the case.
- Leave `Actual Output` blank and set `Automated (Yes/No)` to `No` unless an existing test is confirmed.
- Cover interactions, not just isolated setters: threshold boundaries, mixed field widths, repeated singleton access, repository consistency, and invalid values together.
- Flag unspecified behavior rather than making the expected result falsely definitive. The recurring open questions are builder clamping versus storing invalid values, `<` versus `<=` threshold comparison, renderer precision, long-field truncation, and custom-repository test seams. Once the SWDD decides one (see SWDD 12), the expected output must become definitive — a hedged expected output cannot fail and therefore verifies nothing.
- Do not implement C++ tests, modify production code, add a framework, or run the C++ test suite during design generation.

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
| Actual Output | Leave blank at design time; filled in when the test is run. |
| Automated (Yes/No) | `No` at design time unless a test already exists. |
| Comments | Assumptions, open questions, traceability (e.g. "SWDD 5.4"). May be empty. |

## Constraints

- Tests described here rely only on the C++ standard library (e.g. `<cassert>`), with no third-party framework and no files, databases, or network.
- Do not implement or run the C++ tests in this step; the CSV is the deliverable.
- Do not hand-edit an existing CSV to fix formatting. Fix the generator or run `validate_csv.py`, so the result stays reproducible.

## Bundled scripts

- `scripts/validate_csv.py` - validator and auto-fixer described above. Exit 0 = clean or fixed, 1 = unfixable errors, 2 = usage error.
- `scripts/generate_csv.py` - deterministic CSV regeneration using the checked-in case matrix, followed by strict validation.
- `scripts/apply_review.py` - applies review findings to the CSV from `review-decisions.json` (the fix half of the review loop). Exit 0 = applied, 1 = input error, 2 = usage error.
- `scripts/test_validate_csv.py` - unit tests for the validator (`cd scripts && python3 test_validate_csv.py`); rerun after changing the validator, especially when changing the repair heuristics or CSV contract.
- `scripts/test_apply_review.py` - unit tests for the review applier (`cd scripts && python3 test_apply_review.py`); rerun after adding a decision key or changing how a row is rewritten.
