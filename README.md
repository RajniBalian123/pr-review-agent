# PR Review Agent — Demo

An automated pull-request reviewer, rebuilt from scratch with synthetic
data. When a PR opens, it reads the change in an isolated copy of the code,
looks for real bugs, double-checks each one, and posts only the findings it
trusts.

This is a personal demo project. It captures the pattern — phased review,
verification before publication, replays, and a learnings trail — without any
client code, client data, or proprietary material.

## The problem

Human review is the bottleneck and the safety net at once. An automated
reviewer helps only if it earns trust: every false positive costs a reviewer's
attention, and every missed bug costs more. The design that earns trust is
not "find more things" — it is "post only what you verified."

## How it works

```
PR diff (unified diff)
  -> parse: files, hunks, added lines with file + line numbers
  -> review phases: correctness, security, tests — each a separate pass
  -> findings: each cites file, line, and the exact code
  -> verify: re-check every finding against the diff before publishing
       - the cited line must still be there
       - test fixtures and examples are excluded (a fake key in a test is not a leak)
       - a new function with a test in the same diff is not "untested"
  -> publish gate: only verified findings reach the report
  -> report: markdown findings, as PR comments would be
```

## Run it

```bash
python -m src.run_demo
```

Pure standard library, no dependencies. It reviews the synthetic diff in
`data/sample_diff.diff`, verifies every finding, and writes the publishable
report to `out/review.md`. Try the clean diff (no findings) and the replay:

```bash
python -m src.run_demo --diff data/sample_diff_clean.diff
python -m src.run_demo --replay strict
```

Run the checks:

```bash
python -m unittest discover -s tests -v
```

## What this proves

- **Verification before publication.** A finding is not posted because a
  check flagged it; it is posted because a second pass confirmed the cited
  line, the context, and the absence of an exclusion. Unverified findings
  are dropped, not posted with a caveat.
- **Phases, not one big prompt.** Correctness, security, and tests are
  separate passes with separate rules. A phase can be added, removed, or
  re-run without touching the others.
- **Replays.** The same diff can be re-reviewed under a different profile
  (e.g. `strict`), and the results compared — the same way a new model
  version is evaluated against old PRs before it reviews live ones.
- **Learnings trail.** Every review session can save what it learned —
  what was decided, what was tried and ruled out, what to watch for — as a
  short markdown file next to the code (`.trail/learnings/`). The next
  session starts from those instead of digging again.

## Layout

- `src/review.py` — the engine: diff parsing, review phases, verification,
  publish gate, report.
- `src/run_demo.py` — the demo runner, with `--diff` and `--replay`.
- `data/` — a synthetic diff with planted bugs, and a clean diff.
- `docs/design.md` — the full design: sandboxing, phases, verification,
  publication, observability, replays, learnings.
- `.trail/learnings/` — sample learnings in the trail format.
- `tests/` — checks for detection, verification, the publish gate, and replay.

## What production adds

Real sandboxing (each review in its own throwaway container), a model
behind the phases instead of rules, a job queue and dashboard, Postgres for
runs and findings, prompt versioning with tracing, and GitHub publication of
the findings as review comments. None of those are claimed here — the demo is
the review-and-verify mechanism, local only.
