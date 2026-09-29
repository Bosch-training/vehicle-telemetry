---
name: ut-test-design-review
description: "Review a unit-test design CSV for the Vehicle Telemetry Visualization project against docs/requirements.md and docs/swdd.md, and report coverage gaps, category imbalances, traceability holes, and ambiguities as a findings CSV plus a markdown report. Use whenever the user asks to review, audit, critique, or gap-check the test design or test cases, asks whether the CSV covers all requirements, wants a requirement-to-test traceability matrix, asks if the test design is complete or missing cases, or asks to verify test coverage against the requirements — even if they do not say 'skill' or name a component. This skill only reports; to apply the findings, use the ut-test-design skill's review loop."
---

# UT test design review

Review an existing test-case design against the requirements it is supposed to satisfy. The deliverable is a review — a findings CSV and a markdown report — not a rewritten test design. The design CSV is the input; leave it untouched unless the user explicitly asks you to apply fixes.

The review answers one question: **if every case in this CSV passed, which requirements would still be unverified?** Everything else (category balance, traceability, ambiguity) exists to make that answer trustworthy.

## Workflow

1. **Ground the review in the source documents.** Read `docs/requirements.md` (Functional Requirements, Verification Criteria) and `docs/swdd.md` (sections 5.x class contracts, 7 error handling, 9 traceability, 10 verification mapping). Read the design CSV under `docs/ut-design/` (default `unit-test-design.csv`; if the user names a component file, review that one). Never review the CSV in isolation — a case can look thorough and still miss a requirement.
2. **Run the mechanical review.** The bundled script does the objective work — parsing, coverage matrix, category balance, ID/type consistency, duplicates, ambiguity markers:
   ```bash
   python3 .github/skills/ut-test-design-review/scripts/review_design.py
   ```
   It writes `docs/ut-design/review-findings.csv` and `docs/ut-design/review-report.md` and prints a summary. Use `--design <path>` to review a single component file, `--out-dir <dir>` to redirect output, and `--json` for a machine-readable summary on stdout. Exit 0 means the review ran (findings may exist); exit 1 means an input could not be read; exit 3 means findings at or above `--fail-on` remain. Pass `--fail-on high` when driving the fix loop in the `ut-test-design` skill, so a non-zero exit signals that High findings are still open.
3. **Add the judgment findings the script cannot make.** Read `references/review-checklist.md` and work through it against the actual CSV rows. The script finds structural gaps; the checklist finds semantic ones — a case that exists but asserts nothing observable, a boundary that is tested at the wrong side, a requirement covered only by a case that would pass even if the feature were broken. Append these to the findings CSV and report.
4. **Report.** Summarize: coverage of each requirement, per-component category balance, the highest-severity findings, and the open questions the design itself raises. Propose concrete new cases for each gap (ID, type, input, expected output) but do not add them to the design CSV unless asked.

## Closing the loop

This skill only finds gaps. Fixing them is the `ut-test-design` skill's **Review loop**: record the decision the SWDD left open in `docs/ut-design/review-decisions.json`, run `apply_review.py`, validate, then re-run this review with `--fail-on high`. The loop converges when only findings that no decision can close remain (build/doc criteria, genuinely missing cases). Do not hand-edit the design CSV to silence a finding — that breaks reproducibility and hides the underlying ambiguity.

## What counts as a finding

A finding is a specific, actionable gap with evidence — the requirement or SWDD section it relates to, the row(s) that should have covered it, and what is missing. "Coverage could be better" is not a finding. "FR2 (low-battery list) has no case that exercises a threshold between two seeded battery values, so an off-by-one in the comparison would pass every existing case" is.

Severity reflects the risk of shipping a defect that the design would not catch:

- **High** — a requirement or verification criterion with no covering case, a component or category with no cases, a case whose expected output is not observable, or an ID/type/duplicate defect that breaks the matrix.
- **Medium** — a boundary tested on only one side, a requirement covered only indirectly, an ambiguity that leaves the expected result undecidable, or a missing interaction case.
- **Low** — traceability or hygiene issues: empty `Comments`, non-blank `Actual Output` at design time, `Automated` set to `Yes` without a confirmed test, near-duplicate case names, or a criterion that no unit case can cover (build- and documentation-level criteria such as FR5, VC1, VC5).

## Review quality rules

- Judge coverage against the requirement text, not against the case names. A case named "average speed" that only checks the field is non-zero does not cover FR2's "match manual calculation".
- Every requirement and verification criterion needs at least one case that would fail if the requirement were violated. Presence of a case is not coverage; discriminating power is.
- Check both sides of every boundary. A threshold case that only tests below the threshold cannot detect a `<` versus `<=` error.
- Treat the design's own `Comments` as claims to verify, not facts. If a row says "needs a test seam", confirm the seam is actually reachable; if it says "implementation-defined", that is an unresolved ambiguity, not a covered case.
- Do not invent requirements. If the docs are silent, the finding is "requirement unspecified", not "case missing".
- Do not modify the design CSV, implement C++ tests, or run the C++ suite. The review is read-only with respect to the design.

## Output contract

`review-findings.csv` — header exactly:

`Finding ID, Severity, Category, Component, Reference, Finding, Evidence, Recommendation`

| Column | Rule |
|---|---|
| Finding ID | Unique, `REV-<nnn>`. |
| Severity | `High`, `Medium`, or `Low`. |
| Category | `Coverage Gap`, `Category Balance`, `Traceability`, `Consistency`, `Duplicate`, `Ambiguity`, or `Observability`. |
| Component | `VB`, `VR`, `TS`, `DR`, `ALL`, or `-`. |
| Reference | Requirement/SWDD reference (e.g. `FR2`, `VC3`, `SWDD 5.4`) or `-`. |
| Finding | One sentence stating the gap. |
| Evidence | The row IDs or document lines that show it. |
| Recommendation | The concrete case(s) to add, or the decision to make. |

`review-report.md` — sections: Summary, Coverage matrix (requirement → covering case IDs), Category balance, Findings by severity, Open questions, Proposed cases.

## Bundled scripts

- `scripts/review_design.py` — mechanical review described above. Exit 0 = review completed, 1 = input error, 2 = usage error, 3 = findings at or above `--fail-on` remain.
- `scripts/test_review_design.py` — unit tests for the reviewer (`cd scripts && python3 test_review_design.py`); rerun after changing the reviewer, especially the coverage or severity logic.

## Reference files

- `references/review-checklist.md` — the semantic checklist to work through after the script runs.
