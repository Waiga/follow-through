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

        outside = Path(tempfile.mkdtemp()).resolve() / "elsewhere.txt"
        self.assertEqual(source_label(outside), str(outside))


class NamesThatAreNotNames(unittest.TestCase):
    """Every one of these once produced an owner. None of them is a person."""

    def test_a_header_is_not_a_speaker(self):
        for line in ("From: alex@example.com", "TODO: I will fix it.", "Action Items: I will circulate notes."):
            with self.subTest(line=line):
                speaker, structural, _ = read_speaker(line)
                self.assertEqual(speaker, "")
                self.assertTrue(structural)

    def test_a_common_document_header_is_rejected(self):
        speaker, structural, _ = read_speaker("Discussion: I will fix it.")
        self.assertEqual(speaker, "")
        self.assertTrue(structural)

    def test_known_limit_an_unlisted_header_still_reads_as_a_speaker(self):
        # Recorded, not hidden. The defence is a list of known headers plus a
        # capitalisation and ordinary-word filter; a capitalised word that is
        # none of those is indistinguishable from a name in one line of text.
        # The README says so. If this test starts failing because the check got
        # better, delete it.
        speaker, _, _ = read_speaker("Procurement: I will fix it.")
        self.assertEqual(speaker, "Procurement")

    def test_an_ordinary_noun_phrase_is_not_an_owner(self):
        self.assertEqual(named_owner("The team will revisit the budget."), UNKNOWN)


class NamesThatAre(unittest.TestCase):
    def test_an_apostrophe_does_not_split_a_name(self):
        self.assertEqual(named_owner("O'Brien will confirm the headcount."), "O'Brien")

    def test_a_two_word_name_is_kept_whole(self):
        self.assertEqual(named_owner("Zhang Wei will pull the rates."), "Zhang Wei")

    def test_a_name_is_not_swallowed_by_the_words_before_it(self):
        self.assertEqual(named_owner("I think Priya will send it."), "Priya")

    def test_an_accented_name_is_recognised(self):
        self.assertEqual(named_owner("José will send the deck."), "José")

    def test_a_non_latin_speaker_label_is_recognised(self):
        speaker, structural, remainder = read_speaker("Алекс: I'll send it.")
        self.assertEqual(speaker, "Алекс")
        self.assertFalse(structural)
        self.assertEqual(remainder, "I'll send it.")


class CollectiveUndertakings(unittest.TestCase):
    def test_we_belongs_to_nobody(self):
        fired, owner = classify("We'll decide on the shift by Friday.", "Sam")
        self.assertIn(cues.COLLECTIVE, fired)
        self.assertEqual(owner, UNKNOWN)

    def test_it_is_still_recorded(self):
        fired, _ = classify("We will ship the order tomorrow.", "Sam")
        self.assertNotEqual(fired, ())

    def test_mixing_we_and_i_leaves_the_owner_unclear(self):
        _, owner = classify("I'll draft it and we'll sign it off.", "Sam")
        self.assertEqual(owner, UNKNOWN)


class ConversationalFiller(unittest.TestCase):
    """The most common sentences on any call. None of them is a commitment."""

    FILLER = (
        "Let me know if you have any questions.",
        "Can you hear me?",
        "We'll see how it goes.",
        "Let me think about that for a second.",
        "Could you repeat that?",
        "I'll be honest, that surprised me.",
        "I will never understand that decision.",
    )

    def test_none_of_it_is_recorded(self):
        for line in self.FILLER:
            with self.subTest(line=line):
                self.assertEqual(classify(line, "Alex")[0], ())

    def test_the_real_thing_still_gets_through(self):
        # The filter must not be so wide that it swallows genuine commitments
        # built from the same openings.
        for line in ("Let me draft the plan tonight.", "Can you send the invoice?"):
            with self.subTest(line=line):
                self.assertNotEqual(classify(line, "Alex")[0], ())


class SourceLabelsAndHome(unittest.TestCase):
    def test_a_path_under_home_is_written_with_a_tilde(self):
        from pathlib import Path as _Path

        from follow_through.extract import source_label

        target = _Path.home() / "transcripts" / "q3.txt"
        self.assertEqual(source_label(target), "~/transcripts/q3.txt")

    def test_no_username_reaches_a_recorded_path(self):
        from pathlib import Path as _Path

        from follow_through.extract import source_label

        label = source_label(_Path.home() / "notes.txt")
        self.assertNotIn(_Path.home().name, label)


class AdverbsAreNotPeople(unittest.TestCase):
    """Sentence openers that a capitalisation rule alone reads as names."""

    OPENERS = (
        "Actually will not work.",
        "Hopefully will be ready.",
        "Regardless will be fine.",
        "Certainly will help.",
        "Below will show the numbers.",
        "Attached will explain it.",
        "Later will be too late.",
        "Nevertheless will be needed.",
    )

    def test_none_of_them_becomes_an_owner(self):
        for line in self.OPENERS:
            with self.subTest(line=line):
                self.assertEqual(named_owner(line), UNKNOWN)

    def test_an_adverb_does_not_shield_a_real_name_behind_it(self):
        self.assertEqual(named_owner("Hopefully Priya will do it."), "Priya")


class TeamsAndCompaniesAreNamedParties(unittest.TestCase):
    """A named party need not be a person, and recording one is not a guess.

    "Legal will review the contract" names who is responsible. Refusing it
    because Legal is not a human would lose a real commitment.
    """

    def test_a_department_is_recorded(self):
        self.assertEqual(named_owner("Legal will review the contract."), "Legal")

    def test_an_article_still_blocks_a_bare_noun_phrase(self):
        self.assertEqual(named_owner("The team will revisit it."), UNKNOWN)


class NamesThatAreAlsoOtherWords(unittest.TestCase):
    def test_a_month_that_is_also_a_given_name_is_allowed(self):
        # May, June and April are people as often as they are months, and the
        # months are recognised as deadlines by a different rule anyway.
        for name in ("May", "June", "April"):
            with self.subTest(name=name):
                self.assertEqual(named_owner(f"{name} will send the report."), name)

    def test_such_a_name_is_still_a_valid_speaker(self):
        speaker, structural, _ = read_speaker("May: I'll send the deck.")
        self.assertEqual(speaker, "May")
        self.assertFalse(structural)


class Abbreviations(unittest.TestCase):
    def test_a_title_does_not_end_a_sentence(self):
        self.assertEqual(
            split_sentences("Dr. Smith will send it by Friday. Then we start."),
            ["Dr. Smith will send it by Friday.", "Then we start."],
        )

    def test_an_initial_does_not_end_a_sentence(self):
        self.assertEqual(
            split_sentences("J. Okafor will confirm it."),
            ["J. Okafor will confirm it."],
        )

    def test_the_quote_a_reader_sees_is_the_whole_sentence(self):
        found = extract_text("Dr. Smith will send it by Friday.", "s.txt")
        self.assertEqual(found[0].text, "Dr. Smith will send it by Friday.")

    def test_ordinary_sentences_still_split(self):
        self.assertEqual(
            split_sentences("I will send it. Then we start."),
            ["I will send it.", "Then we start."],
        )


class FillerYieldsToADeadline(unittest.TestCase):
    """Filler is only filler when nothing was actually promised by when."""

    WITH_A_DEADLINE = (
        "Let me start the migration tomorrow.",
        "Let me finish the deck by Friday.",
        "Let me add the numbers to the model today.",
        "Let me just send the contract today.",
        "Let me know the vendor's answer by Friday.",
        "I'll tell you the final number on Monday.",
        "I'll say yes or no by end of week.",
        "Can you repeat the analysis by Friday?",
        "We'll see the data before Monday.",
    )

    def test_a_stated_deadline_rescues_the_sentence(self):
        for line in self.WITH_A_DEADLINE:
            with self.subTest(line=line):
                self.assertNotEqual(classify(line, "Alex")[0], (), "lost a commitment")

    def test_the_same_opening_without_a_deadline_is_still_filler(self):
        for line in ("Let me know if that works.", "Could you repeat that?"):
            with self.subTest(line=line):
                self.assertEqual(classify(line, "Alex")[0], ())

    def test_a_negation_is_not_rescued_by_a_deadline(self):
        # Hard exclusions outrank the deadline. "I don't think I'll have it by
        # Friday" states a deadline and is the opposite of a promise.
        self.assertEqual(classify("I don't think I'll have it by Friday.", "Alex")[0], ())


if __name__ == "__main__":
    unittest.main()
