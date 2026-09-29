---
name: refactor-code
description: "Refactor existing code without changing its observable behavior, one small verifiable unit at a time. Use whenever the user asks to refactor, restructure, clean up, simplify, extract, inline, rename, deduplicate, reorganize, or decouple a file, class, or function; asks to reduce duplication or improve readability of existing code; or asks to make a change that must not alter behavior or the public API. Also use when a refactor request bundles several changes at once, when a change risks breaking call sites, or when the user wants the refactor done in reviewable steps — even if they do not say 'refactor' or name a component."
---

# Refactor code

Refactor the target code **without changing observable behavior**, in small units that are each independently executable and verifiable. This is a behavior-preserving transformation, not a rewrite and not a feature change.

The skill exists to make refactoring *reproducible*: the same request should produce the same unit plan, the same budget, and the same gate result every time. Judgment is confined to choosing the units; everything checkable is checked by a script.

## Workflow

1. **Ground the refactor in the code and the docs.** Read the target and every call site before editing. Read `.github/copilot-instructions.md` for conventions and `docs/swdd.md` for the class contracts. If the docs are silent on a behavior, keep the current behavior and flag the ambiguity — do not guess.
2. **Plan the units.** Write a unit plan to `.refactor-gate/plan.json` (copy `assets/unit-plan.example.json`). Each unit is `target → transformation → expected behavior`, with the files it touches and an estimated line count. Order units so each is independently verifiable: rename/move first, then extract, then inline/simplify/deduplicate, then restructure.
3. **Validate the plan before touching code.**
   ```bash
   python3 .github/skills/refactor-code/scripts/validate_plan.py .refactor-gate/plan.json
   ```
   Exit 1 means a unit is too big, missing an expected behavior, or not verifiable — fix the plan, not the code. Do not start editing until this passes.
4. **Apply one unit at a time, gated.** For each unit:
   ```bash
   python3 .github/skills/refactor-code/scripts/unit_gate.py snapshot
   # ...apply only this unit...
   python3 .github/skills/refactor-code/scripts/unit_gate.py all --allow <files in this unit>
   ```
   `all` runs three checks: **check** (diff stayed inside the budget and the allowed files), **signatures** (no public header signature moved), **build** (compiles with `-Wall -Wextra`, no warnings). Exit 1 means the unit failed — fix or revert it before starting the next. Never stack units and verify once at the end.
5. **Report per unit.** State the unit's smell → transformation → gate result. After the last unit, summarize what changed and list anything left for a follow-up.
6. **Close out.** Work through `references/refactor-checklist.md` for the judgment items the gate cannot check (behavior preservation, scope, honesty). Call out explicitly any behavior that could not be preserved.

## Unit of work

A **unit** is the smallest change that is independently executable and verifiable: one named transformation on one target, or one mechanical sweep of that same transformation across that target's call sites.

Budget (defaults, enforced by the gate): one target, one smell, ≤ 50 changed lines, ≤ 5 files, builds alone. Raise the limits only for a genuinely mechanical sweep, and say so in the plan. See `references/unit-sizing.md` for the full rationale, ordering, and stop conditions.

**Stop conditions** — do not continue past a unit when the build fails or warns, a public signature moved without the goal allowing it, behavior cannot be confirmed unchanged, or the next unit needs a decision the docs do not make. Reverting one unit is cheap; untangling three stacked units is not.

## Rules

1. **Preserve behavior.** Public signatures, return types, output format, and error handling stay identical unless the goal explicitly says otherwise.
2. **Stay in scope.** Touch only the target and its direct call sites. No unrelated reformatting or renames.
3. **Follow project conventions.** Match existing naming and layout; one class per header/source pair.
4. **Work in units.** One unit at a time, gated per unit. Never batch.
5. **No new dependencies.** Standard library only.
6. **Compile clean.** `-Wall -Wextra`, no warnings.
7. **Don't invent requirements.** Keep current behavior when the docs are silent; flag the ambiguity.
8. **Separate behavior changes from refactors.** If a requested change alters behavior (a bug fix, a threshold change), it is not a refactor — surface it and confirm before applying.

## Output

- The edited files, one unit at a time.
- A per-unit summary: smell → transformation → gate result.
- Any behavior that could not be preserved, called out explicitly.

## Bundled resources

- `scripts/unit_gate.py` — the deterministic gate. `snapshot` records the pre-unit state; `check` enforces the budget and scope; `signatures` detects public API drift; `build` compiles (CMake if present, else `g++ -fsyntax-only`); `all` runs all three. Exit 0 = pass, 1 = gate failure, 2 = usage error. `--json` for machine-readable output.
- `scripts/validate_plan.py` — validates a unit plan before any code is touched. Exit 0 = valid, 1 = invalid, 2 = usage error.
- `scripts/test_unit_gate.py`, `scripts/test_validate_plan.py` — unit tests for the scripts (`cd scripts && python3 test_unit_gate.py`). Rerun after changing a script.
- `references/unit-sizing.md` — what a unit is, the budget, the per-unit gate, ordering, and stop conditions.
- `references/refactor-checklist.md` — the judgment checklist for closing out a unit.
- `assets/unit-plan.example.json` — a valid unit plan to copy.
- `evals/evals.json` — test prompts for measuring the skill.

## Constraints

- Do not change observable behavior. If the request requires a behavior change, surface it as a separate, confirmed change.
- Do not batch units. The gate is per unit.
- Do not hand-edit around a gate failure; fix the unit or revert it.
- Do not add dependencies, a test framework, or files outside the target's scope.