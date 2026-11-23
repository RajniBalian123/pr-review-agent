# Replay before promoting a reviewer

**Date:** 2026-11-23

## What was decided

A new reviewer version (new model, stricter profile, new phase) must replay
old diffs and do at least as well as the old reviewer before it touches a
live PR. Replays save results without publishing them.

## What was tried and ruled out

- Promoting on a small live trial: a bad reviewer version posts noise to
  real PRs, and reviewers stop trusting the tool after one bad week. The
  replay set is the gate; the live trial comes after.
- Comparing only finding counts: a reviewer that finds more things is not
  better if the extras are false positives. Compare verified findings and
  dropped findings separately.

## Watch out for

- Replays must use the diff as it was reviewed, not the merged result.
  Reviewing the final code answers a different question than reviewing the
  change.
