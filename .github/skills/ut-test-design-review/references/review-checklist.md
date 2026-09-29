# Review checklist

Work through this after `review_design.py` has run. The script finds structural gaps; these checks find the semantic ones — cases that exist but would not catch a defect. For each item, record a finding only when you can point at the row(s) and the requirement it fails to verify.

## 1. Coverage

- For each Functional Requirement and Verification Criterion, name the case that would fail if the requirement were violated. If you cannot name one, that is a High finding.
- A case "covers" a requirement only if its Expected Output is specific enough to fail. "averageSpeed is computed" does not cover FR2; "averageSpeed == 55.3 within 1e-9" does.
- Check that the requirement's *whole* claim is covered, not just its easiest part. FR2 has three parts (count, average, low-battery list) — three separate cases, or one case asserting all three.
- Requirements that are not unit-testable (FR5, VC1, VC5) should be flagged as verified elsewhere, not silently ignored.

## 2. Boundaries

- Every threshold needs cases on both sides and exactly at the boundary. For the low-battery threshold: below, equal, above. A design with only "below" cannot detect `<` versus `<=`.
- Numeric limits: 0 and 100 for battery, 0 for speed, `INT_MIN`/`INT_MAX` for ids and thresholds, ±90/±180 for GPS.
- Collection limits: empty, single-element, and full-size fleets. Empty is the one that catches division-by-zero.
- String limits: empty and very long values, for both the builder and the renderer.

## 3. Discriminating power

- For each case, ask: what implementation bug would this case catch? If the answer is "none", the case is decoration.
- Watch for cases whose Expected Output restates the Input ("input speed -10, expected speed -10") without asserting the behavior the requirement demands.
- Watch for cases that assert only "no crash" or "does not throw" — those pass for almost any implementation.
- A case that asserts a value is present but not that it is correct (e.g. "output contains a number") is weak; flag it.

## 4. Interactions

- Are there cases where two or more fields are invalid at once, to catch cross-field coupling?
- Are there cases that exercise the full path (builder → repository → service → renderer) rather than each unit in isolation?
- Does the design test the singleton's identity across call sites, not just twice in one expression?

## 5. Traceability

- Every case should trace to a requirement, SWDD section, or an explicit "exploratory" note. Cases with no reference and no rationale are candidates for removal.
- Every requirement should trace to at least one case. Build the matrix both ways.
- `Comments` should carry the SWDD/FR reference; empty comments on a non-obvious case is a Low finding.

## 6. Ambiguity and open questions

- Treat `Comments` that say "open question", "implementation-defined", "needs a test seam", or "assumes" as unresolved. Each is a Medium finding until the SWDD decides the behavior.
- A case whose Expected Output offers alternatives ("stored as-is or clamped") cannot fail and therefore cannot verify anything — High finding.
- Test seams that do not exist in the SWDD (e.g. constructing a repository with zero vehicles) are not implementable as written; flag them and propose the seam or a different approach.

## 7. Hygiene

- IDs unique, correctly prefixed, and matching the Testcase Type.
- `Actual Output` blank at design time; `Automated` = No unless a test is confirmed.
- No near-duplicate cases that differ only in wording.
- The CSV parses to exactly 9 fields per row (run the design skill's `validate_csv.py` if unsure).
