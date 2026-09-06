"""The documented example, run end to end.

The README promises a specific result for a specific file. This test runs that
journey and compares the output against the report checked in beside the
example, so the promise cannot quietly stop being true.
"""

import os
import tempfile
import unittest
from pathlib import Path

from follow_through import ledger, report
from follow_through.extract import extract_file

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "examples" / "weekly-sync.txt"
EXPECTED = ROOT / "examples" / "expected-report.md"


class DocumentedExample(unittest.TestCase):
    def setUp(self):
        # Source paths are recorded relative to the working directory, so the
        # checked-in report only matches when the test runs from the repository
        # root. Make that true regardless of where the runner was started.
        self.previous = Path.cwd()
        os.chdir(ROOT)
        self.addCleanup(os.chdir, self.previous)
        self.candidates = extract_file(TRANSCRIPT)
        self.entries, _ = ledger.merge([], self.candidates)

    def test_finds_the_documented_number_of_commitments(self):
        self.assertEqual(len(self.candidates), 8)

    def test_report_matches_the_checked_in_expectation(self):
        rendered = report.render_markdown(self.entries)
        self.assertEqual(rendered, EXPECTED.read_text(encoding="utf-8"))

    def test_hypotheticals_in_the_example_are_not_recorded(self):
        quoted = " ".join(entry.text for entry in self.entries)
        self.assertNotIn("If I get time", quoted)
        self.assertNotIn("I might look", quoted)
        self.assertNotIn("I already sent", quoted)

    def test_the_unattributed_asks_stay_unattributed(self):
        unowned = [e for e in self.entries if e.owner == "unknown"]
        self.assertEqual(len(unowned), 2)

    def test_full_journey_writes_a_report(self):
        work = Path(tempfile.mkdtemp())
        ledger.save(work / "ledger", self.entries)
        reloaded = ledger.load(work / "ledger")
        ledger.close(reloaded, reloaded[0].id, "lease countersigned and filed")
        ledger.save(work / "ledger", reloaded)
        markdown_path, html_path = report.write(work / "reports", ledger.load(work / "ledger"))
        self.assertIn("lease countersigned and filed", markdown_path.read_text(encoding="utf-8"))
        self.assertIn("7 open, 1 closed", markdown_path.read_text(encoding="utf-8"))
        self.assertTrue(html_path.exists())


if __name__ == "__main__":
    unittest.main()
