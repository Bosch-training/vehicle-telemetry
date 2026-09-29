# Unit sizing

A refactor is unpredictable when a single pass bundles several changes and is
verified once at the end: when the build breaks, you cannot tell which change
broke it, and when behavior drifts, you cannot tell which change caused it. The
unit is the fix — the smallest change that is independently executable and
verifiable.

## Definition

A **unit** is exactly one of:

- one named transformation (extract, inline, rename, deduplicate, reorder, …)
  applied to one target, or
- one mechanical sweep of that *same* transformation across the call sites of
  that one target.

Two transformations on one target is two units. One transformation on two
targets is two units. "Tidy up the builder" is not a unit — it is a plan.

## Budget

A unit must satisfy all of:

| Constraint | Default | Why |
|---|---|---|
| Targets | 1 (one class or one function) | keeps the diff readable in one sitting |
| Smells addressed | 1 | a bundle cannot be verified as a single behavior claim |
| Changed lines | ≤ 50 | beyond this, review stops being a check and becomes a skim |
| Files touched | ≤ 5 | a wide diff usually means the unit is really a plan |
| Builds alone | yes | the tree must stay in a working state after every unit |

The line and file limits are defaults, not laws. Raise them only when the
transformation is genuinely mechanical (a rename sweep) and say so in the plan.
Lower them when the target is subtle.

## The per-unit gate

For each unit, in order:

1. **State** the unit: target, transformation, expected behavior.
2. **Snapshot** the tree (`unit_gate.py snapshot`).
3. **Apply** only that unit.
4. **Gate** — run `unit_gate.py all`:
   - `check` — did the diff stay inside the budget and the allowed files?
   - `signatures` — did any public header signature move?
   - `build` — does it still compile with `-Wall -Wextra` and no warnings?
5. **Report** the unit's result, then proceed to the next unit.

The gate is per unit, not per session. Batching units to "save time" and
verifying once at the end reintroduces exactly the unpredictability the unit
exists to remove.

## Stop conditions

Do not continue past a unit when:

- the build fails or a warning appears — fix or revert the unit first;
- a public signature was removed or changed and the goal did not allow it —
  revert and flag it;
- behavior cannot be confirmed unchanged — revert and flag it;
- the next unit depends on a decision the docs do not make — stop and ask.

Reverting a unit is cheap; untangling three stacked units is not.

## Ordering

Order units so each one is independently verifiable and later units build on
earlier ones:

1. **Rename / move** first — mechanical, no behavior risk, makes later diffs
   readable.
2. **Extract** next — creates the seams later units need.
3. **Inline / simplify / deduplicate** after extraction.
4. **Reorder / restructure** last — the riskiest, done on already-clean code.

If a unit cannot be verified on its own, it is not a unit — split it until it
can be.