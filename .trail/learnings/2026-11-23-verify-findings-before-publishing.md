# Verify findings before publishing

**Date:** 2026-11-23

## What was decided

A review finding is posted only after a second pass confirms the cited line,
the context, and the absence of an exclusion. Unverified findings are dropped,
not posted with a caveat.

## What was tried and ruled out

- Posting everything with a confidence score: reviewers still had to read
  every "maybe" finding, so the noise stayed. A caveat costs the same
  attention as a finding.
- Verifying by re-running the whole review: expensive, and it re-introduces
  the same failure. Verification is a narrow re-check of the cited line and
  the exclusion rules, not a second review.

## Watch out for

- A finding whose cited line moved after a rebase is stale even if the bug is
  real. Drop it and let the next review of the new head re-find it.
- Severity comes from verified impact, not from the pattern that flagged it.
