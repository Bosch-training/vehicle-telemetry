---
mode: agent
description: "Refactor existing code without changing its observable behavior. Use when asked to clean up, restructure, extract, rename, reduce duplication, or improve readability of a file, class, or function."
---

# Refactor code

Refactor the target code **without changing observable behavior**. This is a behavior-preserving transformation, not a rewrite and not a feature change.

## Inputs

- **Target:** `${input:target}` — file, class, or function to refactor.
- **Goal:** `${input:goal}` — the specific smell or outcome (e.g. "reduce duplication in the builder setters").
- **Constraints:** `${input:constraints}` — anything that must stay fixed (public API, signatures, output format).

## Rules

1. **Preserve behavior.** Public signatures, return types, output format, and error handling stay identical unless the goal explicitly says otherwise.
2. **Stay in scope.** Touch only the target and its direct call sites. Do not refactor unrelated code, reformat whole files, or rename things outside the target.
3. **Follow project conventions.** Match the existing naming, file layout, and style (see `.github/copilot-instructions.md`). One class per header/source pair.
4. **Work in units.** One unit = one named transformation on one target. Never stack units in a single pass. See "Unit of work" below.
5. **No new dependencies.** Standard library only.
6. **Compile clean.** Must build with `-Wall -Wextra` and no warnings.
7. **Don't invent requirements.** If the docs are silent on a behavior, keep the current behavior and flag the ambiguity instead of guessing.

## Unit of work

A **unit** is the smallest change that is independently executable and verifiable. Size it so a reviewer can read the diff in one sitting and confirm behavior is unchanged.

**Definition** — a unit is exactly one of:
- one named transformation (extract method, rename, inline, deduplicate, reorder) applied to one target, or
- one mechanical sweep of the *same* transformation across call sites of that one target.

**Budget** — a unit must satisfy all of:
- one target (one class, or one function) — not several;
- one smell addressed — not a bundle;
- roughly ≤ 50 changed lines; if it exceeds this, split it;
- compiles on its own and leaves the tree in a working state.

**Per-unit loop** — for each unit, in order:
1. State the unit: target + transformation + expected behavior (unchanged).
2. Apply only that unit.
3. **Gate:** build with `-Wall -Wextra`; confirm call sites compile and behavior is unchanged.
4. Report the unit's result, then proceed to the next unit.

**Stop conditions** — do not continue past a unit when:
- the build fails or a warning appears — fix or revert the unit first;
- behavior cannot be confirmed unchanged — revert and flag it;
- the next unit depends on a decision the docs don't make — stop and ask.

Never batch units to "save time" and verify once at the end. The gate is per unit, not per session.

## Steps

1. Read the target and every call site before editing.
2. **Plan the units.** List them as `target → transformation → expected behavior`. If more than one unit, do them one at a time.
3. For each unit: state it, apply it, run the gate (build + behavior check), report it.
4. After the last unit, summarize what changed and why, and list anything left for a follow-up.

## Output

- The edited files.
- A short summary: smell → transformation → verification result.
- Any behavior that could not be preserved, called out explicitly.

---

## Keyword reference (for authoring this prompt)

Use these when filling in or extending the prompt. Grouped by the role they play.

| Role | Keywords |
|------|----------|
| **Intent** | refactor, restructure, clean up, simplify, extract, inline, rename, deduplicate, reorganize, decouple |
| **Invariant** | behavior-preserving, no functional change, same public API, same output, backward compatible, no signature change |
| **Scope** | target file/class/function, call sites, in scope, out of scope, do not touch, minimal diff |
| **Unit sizing** | one unit at a time, smallest verifiable change, one transformation, one target, ≤ 50 lines, split if larger, per-unit gate, stop condition |
| **Quality** | readability, cohesion, single responsibility, reduce duplication, naming, complexity, dead code |
| **Constraints** | C++17, standard library only, no new dependencies, `-Wall -Wextra`, no warnings, one class per file |
| **Verification** | build, compile, call sites still compile, behavior unchanged, tests pass, diff review |
| **Safety** | do not invent requirements, flag ambiguity, keep current behavior, small steps, reviewable |

## Structure (skeleton)

```
1. Role / intent        → "Refactor X without changing behavior"
2. Inputs               → target, goal, constraints
3. Rules                → invariants, scope, conventions, units, deps, build
4. Unit of work         → definition, size budget, per-unit gate, stop conditions
5. Steps                → read → plan units → per unit: state → apply → gate → report
6. Output               → edited files + summary + caveats
7. Keyword reference    → vocabulary for authoring/extending
```