# Design: an automated PR reviewer that earns trust

Status: demo of the review-and-verify pattern, with synthetic diffs. It does
not claim a model, sandboxing, a queue, or GitHub publication.

## 1. The flow

```
PR opens
  -> checkout the PR's code in an isolated copy (never the live repo)
  -> parse the diff: files, hunks, added lines with file + line numbers
  -> review phases run (correctness, security, tests)
  -> findings collected, each with file, line, exact code, severity
  -> verification pass: re-check every finding against the diff
  -> publish gate: only verified findings are posted
  -> findings posted as PR comments; the run and its findings are recorded
```

The reviewer never touches the live system, never edits code, and never
publishes a finding it has not verified. Those three rules are the whole
trust model.

## 2. Phases, not one big prompt

Each review phase is a separate pass with its own rules and its own output:

- **Correctness** — does the changed code do what it claims? Unhandled
  errors, wrong boundaries, broken invariants.
- **Security** — injection, hardcoded secrets, unsafe evaluation, leaked
  credentials.
- **Tests** — does new behavior have a test? Does the change break an
  existing test's assumption?

A phase can be added, removed, or re-run without touching the others. In
production each phase is a model call with a skill (a review method, a
security-audit library, a runtime-verification guide); in this demo each
phase is a small rule set over the diff. The shape is the same either way:
phase in, findings out.

## 3. Verification before publication

A finding is posted only after a second pass confirms it:

1. **The cited line is still there.** The verifier re-reads the diff at the
   cited file and line. If the line moved or changed, the finding is stale
   and is dropped.
2. **Exclusions apply.** Test fixtures, examples, and documentation are
   excluded. A fake API key in a test is not a leak; a `TODO` in an example
   is not a missing ticket.
3. **Coverage is checked against the same diff.** A new function is only
   "untested" if no test file in the same diff covers it. A test added
   alongside the function clears the finding.
4. **Severity is earned, not assumed.** A finding's severity comes from the
   verified impact, not from the pattern that flagged it.

Unverified findings are dropped silently. The reviewer does not post "maybe"
findings with a caveat — a caveat still costs the human's attention, and a
reviewer that cries wolf stops being read.

## 4. The publish gate

The report contains only verified findings, ranked by severity, each with:

- file and line,
- the exact code,
- why it matters, in one sentence,
- what would fix it.

No findings means no report — an empty review is a pass, not an error. The
run is still recorded, so coverage can be measured: which PRs were reviewed,
how many findings were verified vs. dropped, and how long each phase took.

## 5. Replays

A replay re-runs an old review's diff under a different reviewer — a new
model version, a stricter profile, a new phase — and saves the results
without publishing them. Replays are how a new reviewer earns the right to
review live PRs: it must do at least as well as the old one on the same
diffs before it touches a real PR.

## 6. Observability

Every run records: the diff it reviewed, the phases that ran, the findings
each phase produced, which findings verification dropped and why, and what
was published. Token usage per run is recorded too, so the cost of review is
visible next to its value. If a phase starts producing noise, the record
shows it — which phase, which rule, which PRs.

## 7. Learnings trail

After a review session, what was learned goes into `.trail/learnings/` as a
short markdown file: what was decided, what was tried and ruled out, and
what to watch out for. Learnings are summaries, never transcripts. They are
committed with the change they came from, so the next session — yours or a
teammate's — starts from them instead of digging again.

## 8. What production adds

- **Sandboxing:** each review runs in its own throwaway container, so
  untrusted PR code can never touch the reviewer's host or credentials.
- **A model behind the phases:** the rules here are stand-ins for model
  calls guided by review skills and a security-audit library.
- **Prompt versioning:** the system prompt, user turn, and skill are
  versioned and traced, so a finding can be traced to the exact instructions
  that produced it.
- **Queue and dashboard:** a background worker queues and runs reviews;
  a dashboard shows runs, findings, and coverage; sign-in is SSO.
- **GitHub publication:** verified findings are posted as review comments
  on the PR, and the run's status is reported back as a check.
