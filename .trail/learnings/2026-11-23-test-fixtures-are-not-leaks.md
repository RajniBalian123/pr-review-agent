# Test fixtures are not leaks

**Date:** 2026-11-23

## What was decided

Findings in test fixtures, examples, and documentation are excluded at
verification time. A fake API key in a test is not a leak.

## What was tried and ruled out

- Excluding test files at check time: then the check never sees them, and a
  real secret that happens to sit in a test helper is missed silently.
  Flagging first and excluding at verification keeps the decision visible —
  the dropped finding is listed in the report with its reason.
- Matching on the word "fake" or "test" in the value: brittle. A value named
  `sk-test-...` in production code would be missed. Path-based exclusion is
  the rule; the value never decides.

## Watch out for

- A fixture directory that lives outside `tests/` needs the same exclusion
  by path. Add it to the exclusion list explicitly, don't rely on naming.
