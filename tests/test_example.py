"""The documented example, run end to end.

The README promises a specific result for a specific file. This test runs that
journey and compares the output against the report checked in beside the
example, so the promise cannot quietly stop being true.

The example transcript is also the project's exclusion fixture. Every line it
expects to be rejected contains a real commitment cue, so the exclusion table is
the only thing that can be rejecting it. An earlier version of this file did not:
its rejected lines contained no cue at all, so the tests below passed with the
entire exclusion table deleted. They now fail.
"""

import os
import tempfile
import unittest
from pathlib import Path

from follow_through import cues, ledger, report
from follow_through.extract import classify, extract_file, is_excluded

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "examples" / "weekly-sync.txt"
EXPECTED = ROOT / "examples" / "expected-report.md"

#: Lines in the example that must be rejected, and that would otherwise be kept.
MUST_BE_REJECTED = (
    "Let me know if you cannot hear me.",
    "I already said I'll dig out the insurance certificate.",
    "Maybe I'll take another look at the routing software.",
    "If I get time this month I'll review the carrier contracts.",
    "We'll see how that goes.",
)


class DocumentedExample(unittest.TestCase):
    def setUp(self):
        # Source paths are recorded relative to the working directory, so the
        # checked-in report only matches when the test runs from the repository
        # root. Make that true regardless of where the runner was started.
        os.chdir(ROOT)
        self.addCleanup(os.chdir, Path.cwd())
        self.candidates = extract_file(TRANSCRIPT)
        self.entries, _ = ledger.merge([], self.candidates)

    def test_finds_the_documented_number_of_commitments(self):
        self.assertEqual(len(self.candidates), 9)

    def test_report_matches_the_checked_in_expectation(self):
        rendered = report.render_markdown(self.entries)
        self.assertEqual(rendered, EXPECTED.read_text(encoding="utf-8"))

    def test_rejected_lines_are_absent_from_the_result(self):
        quoted = {entry.text for entry in self.entries}
        for line in MUST_BE_REJECTED:
            with self.subTest(line=line):
                self.assertNotIn(line, quoted)

    def test_every_rejected_line_is_in_the_transcript(self):
        # A fixture that has drifted away from the file it describes proves
        # nothing, so check the lines are really there before trusting them.
        text = TRANSCRIPT.read_text(encoding="utf-8")
        for line in MUST_BE_REJECTED:
            with self.subTest(line=line):
                self.assertIn(line, text)

    def test_every_rejected_line_would_otherwise_be_kept(self):
        # This is what makes the test above mean something. Each rejected line
        # carries a genuine commitment cue; only the exclusion table stops it.
        for line in MUST_BE_REJECTED:
            with self.subTest(line=line):
                self.assertTrue(is_excluded(line), "not rejected by the exclusion table")
                has_cue = (
                    any(pattern.search(line) for pattern in cues.FIRST_PERSON_RE)
                    or any(pattern.search(line) for pattern in cues.COLLECTIVE_RE)
                    or any(pattern.search(line) for pattern in cues.ASSIGNMENT_RE)
                )
                self.assertTrue(has_cue, "carries no cue, so it proves nothing")

    def test_the_example_covers_every_cue_family(self):
        fired = {cue for entry in self.entries for cue in entry.cues}
        self.assertEqual(
            fired,
            {cues.FIRST_PERSON, cues.COLLECTIVE, cues.ASSIGNMENT, cues.DUE_PHRASE},
        )

    def test_the_collective_commitment_belongs_to_nobody(self):
        collective = [e for e in self.entries if cues.COLLECTIVE in e.cues]
        self.assertEqual(len(collective), 1)
        self.assertEqual(collective[0].owner, "unknown")

    def test_a_name_with_an_apostrophe_survives_intact(self):
        owners = {entry.owner for entry in self.entries}
        self.assertIn("O'Brien", owners)

    def test_the_unattributed_asks_stay_unattributed(self):
        unowned = [e for e in self.entries if e.owner == "unknown"]
        self.assertEqual(len(unowned), 3)

    def test_full_journey_writes_a_report(self):
        work = Path(tempfile.mkdtemp())
        ledger.save(work / "ledger", self.entries)
        reloaded = ledger.load(work / "ledger")
        ledger.close(reloaded, reloaded[0].id, "lease countersigned and filed")
        ledger.save(work / "ledger", reloaded)
        markdown_path, _ = report.write(work / "reports", ledger.load(work / "ledger"))
        written = markdown_path.read_text(encoding="utf-8")
        self.assertIn("lease countersigned and filed", written)
        self.assertIn("8 open, 1 closed", written)


class ReadmeStaysTrue(unittest.TestCase):
    """The README prints a listing. Nothing else checks that it is real."""

    def test_the_listing_in_the_readme_is_what_the_tool_prints(self):
        os.chdir(ROOT)
        self.addCleanup(os.chdir, Path.cwd())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for candidate in extract_file(TRANSCRIPT):
            line = f"{candidate.identity}  {candidate.owner}"
            with self.subTest(id=candidate.identity):
                self.assertIn(candidate.identity, readme)
                self.assertIn(candidate.text, readme)
                self.assertIn(line.split()[0], readme)


if __name__ == "__main__":
    unittest.main()
