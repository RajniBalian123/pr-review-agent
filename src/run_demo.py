"""Demo runner: review a diff, verify, publish. Local only."""

import argparse
from pathlib import Path

from src.review import publish, review

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", default="data/sample_diff.diff")
    parser.add_argument("--replay", choices=["standard", "strict"], default=None,
                        help="Re-run the same diff under a different profile")
    args = parser.parse_args()

    diff_text = (ROOT / args.diff).read_text(encoding="utf-8")
    profile = args.replay or "standard"
    findings = review(diff_text, profile)
    published = [f for f in findings if f.verified]
    dropped = [f for f in findings if not f.verified]

    print(f"Reviewed {args.diff} (profile: {profile})")
    print(f"Findings: {len(findings)} flagged, {len(published)} verified "
          f"and published, {len(dropped)} dropped by verification")
    for f in published:
        print(f"  [{f.severity}] {f.path}:{f.line} — {f.message}")

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    report = publish(findings)
    (out / "review.md").write_text(report, encoding="utf-8")
    print(f"\nWrote {out / 'review.md'}")

    if args.replay:
        baseline = review(diff_text, "standard")
        base_published = [f for f in baseline if f.verified]
        print(f"\nReplay comparison vs standard profile: "
              f"{len(base_published)} published standard, "
              f"{len(published)} published {profile}")
        for f in published:
            match = next((b for b in base_published
                          if (b.path, b.line) == (f.path, f.line)), None)
            if match and match.severity != f.severity:
                print(f"  severity changed: {f.path}:{f.line} "
                      f"{match.severity} -> {f.severity}")


if __name__ == "__main__":
    main()
