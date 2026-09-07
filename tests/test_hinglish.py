"""Hinglish extraction: Hindi conversation transliterated into Roman script.

This is not a nice-to-have. On a real Delhi meeting transcript the English-only
rules found zero commitments in a conversation that contained seven, because the
promises were all of the form "main hi follow up dalta hu". Every test here
exists to stop that from being true again.

The example transcript is invented. Lumen Freight does not exist, and neither do
Neha, Rohit or Farhan.
"""

import os
import unittest
from pathlib import Path

from follow_through import cues, ledger, report
from follow_through.extract import classify, extract_file, is_excluded, named_owner
from follow_through.models import UNKNOWN

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "examples" / "weekly-sync-hinglish.txt"
EXPECTED = ROOT / "examples" / "expected-report-hinglish.md"


class FirstPerson(unittest.TestCase):
    """"-unga", "-ungi", "-ta hu": the speaker is committing."""

    LINES = (
        "Main kal tak bhej dungi.",
        "Main hi follow up dalta hu.",
        "Report main shaam tak update kar dunga.",
        "Main pehla draft aaj hi bana deta hu.",
        "Main to is contract se mail kar raha hu.",
    )

    def test_each_belongs_to_the_speaker(self):
        for line in self.LINES:
            with self.subTest(line=line):
                fired, owner = classify(line, "Neha")
                self.assertIn(cues.FIRST_PERSON, fired)
                self.assertEqual(owner, "Neha")

    def test_the_ending_is_the_cue_not_a_list_of_verbs(self):
        # Verbs nobody listed. Hindi conjugates the future into the word, so
        # matching the ending covers the whole language rather than a sample.
        for line in ("Main dikhaunga.", "Main karwaungi.", "Main samjha dunga."):
            with self.subTest(line=line):
                self.assertNotEqual(classify(line, "Neha")[0], ())


class Collective(unittest.TestCase):
    """"-enge", "-te hai": a group is committing, so nobody owns it."""

    def test_we_will_belongs_to_nobody(self):
        fired, owner = classify("Move se pehle decide karenge.", "Rohit")
        self.assertIn(cues.COLLECTIVE, fired)
        self.assertEqual(owner, UNKNOWN)

    def test_an_unlisted_verb_still_matches(self):
        self.assertNotEqual(classify("Do teen ke liye banayenge.", "Rohit")[0], ())

    def test_an_impersonal_obligation_is_recorded(self):
        self.assertNotEqual(classify("Follow ups lene hai.", "Rohit")[0], ())

    def test_it_will_get_done_is_deliberately_not_recorded(self):
        # "ho jayega" reads like a commitment and is almost always a prediction.
        # It produced two false positives on the first real transcript it met -
        # "tight bhi ho jayegi", "easy ho jayega" - so the rule was removed.
        self.assertEqual(classify("Countersign agle hafte tak ho jayegi.", "")[0], ())


class Assignment(unittest.TestCase):
    def test_an_imperative_names_nobody(self):
        fired, owner = classify("Insurance certificate bhi share kar do.", "Rohit")
        self.assertIn(cues.ASSIGNMENT, fired)
        self.assertEqual(owner, UNKNOWN)

    def test_tell_him_is_an_instruction(self):
        self.assertNotEqual(classify("Usko bol dena ki quote cancel hai.", "R")[0], ())

    def test_a_named_person_in_the_future_tense_owns_the_work(self):
        # This is how work is handed out in a Hindi conversation, and missing it
        # made every assignment in a real meeting invisible.
        self.assertEqual(named_owner("Anjali karegi."), "Anjali")
        self.assertEqual(named_owner("Rahul bhejega invoice."), "Rahul")
        self.assertEqual(named_owner("Carrier rates Farhan nikalega."), "Farhan")

    def test_an_english_word_that_looks_like_a_hindi_future_is_not_one(self):
        for line in ("That is a challenge for us.", "We need revenge."):
            with self.subTest(line=line):
                self.assertEqual(named_owner(line), UNKNOWN)

    def test_challenge_does_not_become_a_commitment(self):
        self.assertEqual(classify("That is a challenge for us.", "R")[0], ())


class Deadlines(unittest.TestCase):
    def test_the_marker_at_the_end_is_read(self):
        from follow_through.extract import find_due_phrase, sets_a_deadline

        for phrase, text in (
            ("kal tak", "Main kal tak bhej dungi."),
            ("shaam tak", "Main shaam tak update kar dunga."),
            ("do din me", "Rates do din me nikal dunga."),
            ("agle hafte tak", "Ye agle hafte tak ho jayega."),
        ):
            with self.subTest(text=text):
                self.assertEqual(find_due_phrase(text), phrase)
                self.assertTrue(sets_a_deadline(phrase))

    def test_a_bare_time_word_is_recorded_but_sets_nothing(self):
        from follow_through.extract import find_due_phrase, sets_a_deadline

        self.assertEqual(find_due_phrase("Kal meeting thi.").lower(), "kal")
        self.assertFalse(sets_a_deadline("kal"))


class Exclusions(unittest.TestCase):
    """Each of these carries a real cue and must still be thrown away."""

    CASES = (
        ("Shayad main routing software dobara dekh lunga.", "maybe"),
        ("Agar time mila to main contracts review kar lunga.", "if"),
        ("Wo to maine kal hi bhej diya, warna aaj bhej deta hu.", "already done"),
        ("Wo bolta hai ki main kal tak kar dunga.", "reporting somebody else"),
        ("Main nahi karunga.", "refusal"),
        ("Theek hai, shuru karte hain.", "filler"),
    )

    def test_each_is_rejected(self):
        for line, why in self.CASES:
            with self.subTest(why=why):
                self.assertEqual(classify(line, "Neha")[0], (), why)

    def test_each_would_otherwise_have_been_kept(self):
        # Without this the tests above would pass on sentences that contain no
        # cue at all, and would prove nothing.
        for line, why in self.CASES:
            with self.subTest(why=why):
                self.assertTrue(is_excluded(line), f"{why}: not excluded")
                has_cue = (
                    any(p.search(line) for p in cues.FIRST_PERSON_RE)
                    or any(p.search(line) for p in cues.COLLECTIVE_RE)
                    or any(p.search(line) for p in cues.ASSIGNMENT_RE)
                )
                self.assertTrue(has_cue, f"{why}: carries no cue")


class SpeakerLabels(unittest.TestCase):
    def test_a_numbered_speaker_is_recognised(self):
        from follow_through.extract import read_speaker

        # Transcription tools label unidentified voices this way. Missing it
        # attributed one person's promise to whoever spoke before them.
        for label in ("Speaker 1", "Speaker_1", "Participant 2"):
            with self.subTest(label=label):
                speaker, structural, _ = read_speaker(f"{label}: main kar dunga.")
                self.assertEqual(speaker, label)
                self.assertFalse(structural)


class TheHinglishExample(unittest.TestCase):
    def setUp(self):
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(ROOT)
        self.candidates = extract_file(TRANSCRIPT)

    def test_finds_the_documented_number(self):
        self.assertEqual(len(self.candidates), 8)

    def test_report_matches_the_checked_in_expectation(self):
        entries, _ = ledger.merge([], self.candidates)
        self.assertEqual(
            report.render_markdown(entries), EXPECTED.read_text(encoding="utf-8")
        )

    def test_owners_and_deadlines_survive_the_round_trip(self):
        owned = {c.owner for c in self.candidates}
        self.assertIn("Neha", owned)
        self.assertIn("Farhan", owned)
        self.assertIn(UNKNOWN, owned)
        self.assertIn("kal tak", {c.due_phrase for c in self.candidates})

    def test_the_english_example_is_unaffected(self):
        # The two languages share one set of families. Adding Hinglish must not
        # change what the English transcript produces.
        english = extract_file(ROOT / "examples" / "weekly-sync.txt")
        self.assertEqual(len(english), 9)


if __name__ == "__main__":
    unittest.main()
