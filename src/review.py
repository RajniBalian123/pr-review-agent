"""PR review engine: parse a diff, run review phases, verify, publish.

Phases are small rule sets over the diff. The shape is the point, not the
rules: phase in, findings out — then a verification pass re-checks every
finding before the publish gate lets it out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class AddedLine:
    path: str
    lineno: int
    content: str


@dataclass
class FileDiff:
    path: str
    added: list[AddedLine] = field(default_factory=list)

    @property
    def is_test(self) -> bool:
        return "/tests/" in self.path or self.path.startswith("tests/") \
            or self.path.endswith("_test.py") or "/test_" in self.path


@dataclass
class Finding:
    phase: str
    path: str
    line: int
    code: str
    message: str
    fix: str
    severity: str  # high / medium / low
    verified: bool = False
    dropped_reason: str = ""


def parse_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    new_lineno = 0
    for raw in text.splitlines():
        if raw.startswith("diff --git"):
            current = None
            continue
        if raw.startswith("+++ b/"):
            current = FileDiff(path=raw[len("+++ b/"):])
            files.append(current)
            continue
        if current is None:
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            new_lineno = int(m.group(1)) if m else 0
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            current.added.append(AddedLine(current.path, new_lineno, raw[1:]))
            new_lineno += 1
        elif raw.startswith("-"):
            continue
        else:
            new_lineno += 1
    return files


SECRET_RE = re.compile(
    r"\b(api[_-]?key|password|secret|token)\s*=\s*[\"'][^\"']{8,}[\"']",
    re.IGNORECASE)
SQL_FSTRING_RE = re.compile(
    r"""(f["'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*\{.*\}.*["']|"""
    r"""\.execute\(\s*f["'])""", re.IGNORECASE)
EVAL_RE = re.compile(r"\b(eval|exec)\s*\(")
BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:\s*$")
DEF_RE = re.compile(r"^def\s+(\w+)\s*\(")


def _find(files: list[FileDiff], phase: str, pattern, message: str,
          fix: str, severity: str) -> list[Finding]:
    findings = []
    for f in files:
        for line in f.added:
            if pattern.search(line.content):
                findings.append(Finding(
                    phase=phase, path=f.path, line=line.lineno,
                    code=line.content.strip(), message=message, fix=fix,
                    severity=severity))
    return findings


def phase_security(files: list[FileDiff]) -> list[Finding]:
    findings = _find(
        files, "security", SECRET_RE,
        "Hardcoded secret: a credential is committed in source.",
        "Move it to the secret store and rotate it; never commit credentials.",
        "high")
    findings += _find(
        files, "security", SQL_FSTRING_RE,
        "SQL built with string interpolation: user input can break out of the query.",
        "Use a parameterized query with placeholders instead of interpolation.",
        "high")
    findings += _find(
        files, "security", EVAL_RE,
        "eval()/exec() runs a string as code.",
        "Replace with an explicit dispatch on known values.",
        "high")
    return findings


def phase_correctness(files: list[FileDiff]) -> list[Finding]:
    findings = _find(
        files, "correctness", BARE_EXCEPT_RE,
        "Bare except swallows every error, including the ones you need to see.",
        "Catch the specific exception type, or log and re-raise.",
        "medium")
    return findings


def phase_tests(files: list[FileDiff], profile: str = "standard") -> list[Finding]:
    test_text = "\n".join(
        line.content for f in files if f.is_test for line in f.added)
    severity = "medium" if profile == "strict" else "low"
    findings = []
    for f in files:
        if f.is_test:
            continue
        for line in f.added:
            m = DEF_RE.search(line.content)
            if m and m.group(1) not in test_text:
                findings.append(Finding(
                    phase="tests", path=f.path, line=line.lineno,
                    code=line.content.strip(),
                    message=f"New function {m.group(1)} has no test in this diff.",
                    fix="Add a test covering the new behavior, or say why it needs none.",
                    severity=severity))
    return findings


def review(diff_text: str, profile: str = "standard") -> list[Finding]:
    files = parse_diff(diff_text)
    findings = []
    findings += phase_security(files)
    findings += phase_correctness(files)
    findings += phase_tests(files, profile)
    return verify(findings, files)


def verify(findings: list[Finding], files: list[FileDiff]) -> list[Finding]:
    """Re-check every finding against the diff before publication."""
    added = {(line.path, line.lineno, line.content.strip())
             for f in files for line in f.added}
    test_paths = {f.path for f in files if f.is_test}
    verified = []
    for finding in findings:
        key = (finding.path, finding.line, finding.code)
        if key not in added:
            finding.dropped_reason = "cited line is no longer in the diff"
            verified.append(finding)
            continue
        if finding.phase == "security" and "secret" in finding.message.lower() \
                and finding.path in test_paths:
            finding.dropped_reason = "test fixture, not a real credential"
            verified.append(finding)
            continue
        finding.verified = True
        verified.append(finding)
    return verified


def publish(findings: list[Finding]) -> str:
    """Only verified findings reach the report, ranked by severity."""
    published = sorted(
        (f for f in findings if f.verified),
        key=lambda f: (SEVERITY_RANK[f.severity], f.path, f.line))
    dropped = [f for f in findings if not f.verified]
    lines = ["# PR review\n"]
    if not published:
        lines.append("No verified findings. This change is clear to merge "
                     "on review grounds.\n")
    for f in published:
        lines.append(f"## [{f.severity}] {f.path}:{f.line}\n")
        lines.append(f"```\n{f.code}\n```\n")
        lines.append(f"{f.message}\n")
        lines.append(f"Fix: {f.fix}\n")
    if dropped:
        lines.append("\n---\n")
        lines.append(f"{len(dropped)} finding(s) were dropped by verification "
                     "and not published:\n")
        for f in dropped:
            lines.append(f"- {f.path}:{f.line} — {f.dropped_reason}\n")
    return "\n".join(lines)
