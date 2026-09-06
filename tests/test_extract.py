import unittest

from follow_through import cues
from follow_through.extract import (
    classify,
    extract_text,
    find_due_phrase,
    named_owner,
    read_speaker,
    split_sentences,
)
from follow_through.models import UNKNOWN


class SentenceSplitting(unittest.TestCase):
    def test_splits_on_terminal_punctuation(self):
        self.assertEqual(
            split_sentences("I'll send it. Can you confirm? Yes!"),
            ["I'll send it.", "Can you confirm?", "Yes!"],
        )

    def test_drops_empty_fragments(self):
        self.assertEqual(split_sentences("   "), [])


class SpeakerLabels(unittest.TestCase):
    def test_reads_a_plain_label(self):
        speaker, structural, remainder = read_speaker("Alex: I'll do it.")
        self.assertEqual(speaker, "Alex")
        self.assertFalse(structural)
        self.assertEqual(remainder, "I'll do it.")

    def test_reads_a_label_behind_a_timestamp(self):
        speaker, _, remainder = read_speaker("[00:14] Sam Okafor: I'll do it.")
        self.assertEqual(speaker, "Sam Okafor")
        self.assertEqual(remainder, "I'll do it.")

    def test_structural_label_is_not_a_speaker(self):
        speaker, structural, remainder = read_speaker("Notes: Priya will send it.")
        self.assertEqual(speaker, "")
        self.assertTrue(structural)
        self.assertEqual(remainder, "Priya will send it.")

    def test_unlabelled_line_is_returned_whole(self):
        speaker, structural, remainder = read_speaker("I'll do it.")
        self.assertEqual(speaker, "")
        self.assertFalse(structural)
        self.assertEqual(remainder, "I'll do it.")


class DuePhrases(unittest.TestCase):
    def test_captures_the_phrase_verbatim(self):
        self.assertEqual(find_due_phrase("I'll send it by Friday."), "by Friday")

    def test_no_phrase_is_unknown_not_a_default(self):
        self.assertEqual(find_due_phrase("I'll send it."), UNKNOWN)

    def test_earliest_phrase_wins(self):
        self.assertEqual(
            find_due_phrase("I'll send it by Friday, not next week."), "by Friday"
        )

    def test_recognises_a_relative_window(self):
        self.assertEqual(find_due_phrase("I'll have it in 3 days."), "in 3 days")


class Owners(unittest.TestCase):
    def test_first_person_belongs_to_the_speaker(self):
        fired, owner = classify("I'll send the deck.", "Alex")
        self.assertIn(cues.FIRST_PERSON, fired)
        self.assertEqual(owner, "Alex")

    def test_first_person_without_a_speaker_is_unknown(self):
        _, owner = classify("I'll send the deck.", "")
        self.assertEqual(owner, UNKNOWN)

    def test_named_assignment_uses_the_name(self):
        fired, owner = classify("Priya will send the deck.", "Alex")
        self.assertIn(cues.ASSIGNMENT, fired)
        self.assertEqual(owner, "Priya")

    def test_pronouns_are_not_names(self):
        self.assertEqual(named_owner("We will ship on Monday."), UNKNOWN)
        self.assertEqual(named_owner("There will be a delay."), UNKNOWN)
        self.assertEqual(named_owner("It will take two weeks."), UNKNOWN)

    def test_open_assignment_names_nobody(self):
        fired, owner = classify("Can you confirm the headcount?", "Alex")
        self.assertEqual(fired, (cues.ASSIGNMENT,))
        self.assertEqual(owner, UNKNOWN)

    def test_ambiguous_sentence_is_left_unowned(self):
        # Both a first-person undertaking and a named assignment fire, so the
        # owner is genuinely unclear and must not be guessed.
        _, owner = classify("I'll check, and Priya will send the deck.", "Alex")
        self.assertEqual(owner, UNKNOWN)


class Exclusions(unittest.TestCase):
    def test_hypothetical_is_not_a_commitment(self):
        self.assertEqual(classify("If I get time I'll review it.", "Alex")[0], ())

    def test_negation_is_not_a_commitment(self):
        self.assertEqual(classify("I don't think I'll get to it.", "Alex")[0], ())

    def test_tentative_is_not_a_commitment(self):
        self.assertEqual(classify("I might look at it again.", "Alex")[0], ())

    def test_past_tense_is_not_a_commitment(self):
        self.assertEqual(classify("I already sent that one.", "Alex")[0], ())

    def test_capability_question_is_not_an_assignment(self):
        self.assertEqual(classify("Will I be able to see the file?", "Alex")[0], ())


class ExtractingText(unittest.TestCase):
    SAMPLE = (
        "Alex: I'll send the lease by Friday.\n"
        "\n"
        "Sam: Can you confirm the headcount?\n"
        "Notes: Priya will pull the rates tomorrow.\n"
        "I'll update the register today.\n"
    )

    def test_finds_every_candidate(self):
        found = extract_text(self.SAMPLE, "sample.txt")
        self.assertEqual(len(found), 4)

    def test_records_the_source_line(self):
        found = extract_text(self.SAMPLE, "sample.txt")
        self.assertEqual(found[0].line, 1)
        self.assertEqual(found[0].source, "sample.txt")

    def test_quoted_text_omits_the_speaker_label(self):
        found = extract_text(self.SAMPLE, "sample.txt")
        self.assertEqual(found[0].text, "I'll send the lease by Friday.")

    def test_structural_label_ends_the_previous_speaker_turn(self):
        # The last line has no label of its own. Because a "Notes:" line came
        # between, attributing it to Sam would be a guess.
        found = extract_text(self.SAMPLE, "sample.txt")
        self.assertEqual(found[-1].owner, UNKNOWN)

    def test_blank_lines_are_skipped_without_shifting_line_numbers(self):
        found = extract_text(self.SAMPLE, "sample.txt")
        self.assertEqual(found[1].line, 3)

    def test_empty_input_finds_nothing(self):
        self.assertEqual(extract_text("", "empty.txt"), [])


if __name__ == "__main__":
    unittest.main()


class SourceLabels(unittest.TestCase):
    def test_a_path_inside_the_working_directory_is_recorded_relative(self):
        import os
        import tempfile
        from pathlib import Path

        from follow_through.extract import source_label

        work = Path(tempfile.mkdtemp()).resolve()
        (work / "notes").mkdir()
        target = work / "notes" / "sync.txt"
        target.write_text("hello", encoding="utf-8")
        previous = Path.cwd()
        os.chdir(work)
        try:
            self.assertEqual(source_label(target), "notes/sync.txt")
        finally:
            os.chdir(previous)

    def test_a_path_outside_the_working_directory_is_left_alone(self):
        import tempfile
        from pathlib import Path

        from follow_through.extract import source_label

        outside = Path(tempfile.mkdtemp()) / "elsewhere.txt"
        self.assertEqual(source_label(outside), str(outside))
