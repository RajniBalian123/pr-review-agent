"""Checks for detection, verification, the publish gate, and replay."""

import unittest
from pathlib import Path

from src.review import parse_diff, publish, review

ROOT = Path(__file__).resolve().parents[1]
DIFF = (ROOT / "data" / "sample_diff.diff").read_text(encoding="utf-8")
CLEAN = (ROOT / "data" / "sample_diff_clean.diff").read_text(encoding="utf-8")


class TestDetection(unittest.TestCase):
    def test_planted_bugs_are_found(self):
        findings = review(DIFF)
        published = {(f.path, f.line): f for f in findings if f.verified}
        messages = " ".join(f.message for f in published.values())
        self.assertIn("Hardcoded secret", messages)
        self.assertIn("SQL built with string interpolation", messages)
        self.assertIn("eval()", messages)
        self.assertIn("Bare except", messages)
        self.assertIn("New function charge_card", messages)
        self.assertIn("New function refund_invoice", messages)

    def test_clean_diff_has_no_findings(self):
        findings = review(CLEAN)
        self.assertEqual([f for f in findings if f.verified], [])
        self.assertIn("clear to merge", publish(findings))


class TestVerification(unittest.TestCase):
    def test_test_fixture_secret_is_dropped(self):
        findings = review(DIFF)
        dropped = [f for f in findings if not f.verified]
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0].path, "tests/test_billing.py")
        self.assertEqual(dropped[0].dropped_reason,
                         "test fixture, not a real credential")

    def test_report_contains_only_verified_findings(self):
        findings = review(DIFF)
        report = publish(findings)
        self.assertNotIn("sk-test-", report)
        self.assertNotIn("tests/test_billing.py", report.split("---")[0])
        self.assertIn("src/billing.py", report)


class TestReplay(unittest.TestCase):
    def test_strict_profile_changes_severity_not_findings(self):
        standard = [f for f in review(DIFF, "standard") if f.verified]
        strict = [f for f in review(DIFF, "strict") if f.verified]
        self.assertEqual({(f.path, f.line) for f in standard},
                         {(f.path, f.line) for f in strict})
        std = {(f.path, f.line): f.severity for f in standard}
        stc = {(f.path, f.line): f.severity for f in strict}
        changed = [k for k in std if std[k] != stc[k]]
        self.assertTrue(changed)  # untested functions rise to medium
        self.assertTrue(all(stc[k] == "medium" for k in changed))


if __name__ == "__main__":
    unittest.main()
