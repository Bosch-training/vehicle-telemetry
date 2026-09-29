# Refactor safety checklist

Work through this before declaring a unit done. The gate script covers the
mechanical items; the rest need judgment.

## Behavior preservation

- [ ] Public signatures, return types, and access levels are unchanged (or the
      goal explicitly allowed the change).
- [ ] Return values are identical for the same inputs, including edge inputs
      (empty, zero, negative, boundary).
- [ ] Error handling is unchanged: same exceptions, same error codes, same
      messages, same ordering of checks.
- [ ] Side effects are unchanged: same output, same mutation order, same
      logging.
- [ ] Default arguments and overload resolution are unchanged.
- [ ] `const`-ness and reference/value semantics are unchanged.

## Scope

- [ ] Only the target and its direct call sites changed.
- [ ] No unrelated reformatting, import reordering, or whitespace churn.
- [ ] No renames outside the target.
- [ ] The diff is readable in one sitting.

## Project conventions

- [ ] Naming matches the existing style (PascalCase classes, camelCase methods).
- [ ] One class per header/source pair is preserved.
- [ ] No new dependencies — standard library only.
- [ ] Builds with `-Wall -Wextra` and no warnings.

## Verification

- [ ] The gate ran and passed (`unit_gate.py all`).
- [ ] Call sites still compile.
- [ ] If tests exist, they pass unchanged.
- [ ] The expected behavior stated in the plan was actually observed.

## Honesty

- [ ] Any behavior that could not be preserved is called out explicitly.
- [ ] Any ambiguity in the docs is flagged, not silently resolved.
- [ ] Nothing was verified "by inspection" that could have been verified by
      building.