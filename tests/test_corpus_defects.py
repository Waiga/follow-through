"""Regressions found by running the tool over 1,067 real meeting records.

The corpus was IETF working-group minutes from 2006 to 2026 and US
congressional hearing transcripts. None of it was written by this project, and
that is the point: every earlier test in this repository uses a fixture its own
author composed, so the fixtures shared the code's blind spots. These do not.

Almost every sentence quoted below is a verbatim line from that corpus. Where a
line had to be constructed — because the evidence recorded only the cases the
tool got wrong, and the fix also has to keep the right ones working — the test
says so.

Each test names one defect class and fails without the change that closed it.
"""

import unittest

from follow_through import cues
from follow_through.extract import (
    Document,
    classify,
    infinitive_action,
    logical_lines,
    extract_text,
    find_due_phrase,
    named_owner,
    read_speaker,
    wrap_column,
)
from follow_through.models import UNKNOWN


def fires(sentence: str, speaker: str = "Chair") -> bool:
    return classify(sentence, speaker)[0] != ()


class ContractionsNeedTheirApostrophe(unittest.TestCase):
    """``\\bwe'?ll\\b`` also matches "well". 36.7% of everything the tool found.

    24,996 of 68,028 findings came from this one optional apostrophe, which
    made the ordinary words "well" and "ill" read as "we'll" and "I'll".
    """

    def test_the_word_well_is_not_a_collective_undertaking(self):
        self.assertFalse(fires("They are designed for machine consumption, as well."))

    def test_a_heading_containing_note_well_is_not_a_commitment(self):
        self.assertFalse(fires("Agenda bashing/Note Well"))

    def test_the_word_ill_is_not_a_first_person_undertaking(self):
        # Constructed: the corpus evidence recorded the "well" half of this
        # defect, and "ill" is the same pattern in the first person.
        self.assertFalse(fires("He was ill last week and could not attend."))

    def test_the_real_contraction_still_fires(self):
        self.assertTrue(fires("I'll send the text to the list by Friday."))
        self.assertTrue(fires("We'll take it to the list by Friday."))

    def test_a_typographic_apostrophe_is_read(self):
        # Requiring the apostrophe means accepting both spellings of it. A
        # transcript that uses U+2019 used to produce nothing at all.
        found, owner = classify("I’ll send the text to the list by Friday.", "Mark")
        self.assertNotEqual(found, ())
        self.assertEqual(owner, "Mark")


class QuotedWordsAreNotPromises(unittest.TestCase):
    """A quoted slogan became an open obligation owned by the group it named.

    This is the defect that must never ship. It was found on a real congressional
    hearing transcript, in a passage where a member was condemning a chanted hate
    slogan: the tool read the slogan as a promise and filed it as an open
    obligation owned by the ethnic group named in it.

    The original wording is deliberately not reproduced here. The extractor sees
    grammar, not subject matter, so a neutral sentence of the same shape — a
    capitalised plural group, a negated future, inside quotation marks — drives
    exactly the same code. Putting the slogan itself in a public repository would
    add nothing a test needs and would carry it further than the defect did.

    Two independent guards close the class: a negated future is not a commitment
    in any person, and a commitment read out of quoted material is somebody
    else's words being reported.
    """

    QUOTED = "that a crowd that chanted, quote, ``Outsiders will not settle here''"

    def test_the_quoted_slogan_produces_no_commitment(self):
        self.assertEqual(classify(self.QUOTED, ""), ((), UNKNOWN))

    def test_the_quoted_slogan_produces_no_owner(self):
        self.assertEqual(named_owner(self.QUOTED), UNKNOWN)

    def test_the_same_quotation_without_the_negation_is_still_refused(self):
        # The negation guard alone would close only half of this class, so the
        # positive form has to be refused by the quotation guard on its own.
        positive = "that a crowd that chanted, quote, ``Outsiders will settle here''"
        self.assertEqual(named_owner(positive), UNKNOWN)
        self.assertEqual(classify(positive, ""), ((), UNKNOWN))

    def test_curly_quotation_marks_are_refused_too(self):
        # Transcripts from a word processor use typographic quotes, and a guard
        # that only knows the GPO's doubled backticks would miss half of them.
        curly = "the banner read “Regulators will never touch us” that morning"
        self.assertEqual(classify(curly, ""), ((), UNKNOWN))


class ARefusalIsNotACommitment(unittest.TestCase):
    """333 occurrences: "X will not Y" recorded as a promise by X."""

    def test_a_third_person_refusal_is_not_recorded(self):
        for line in (
            "OneWeb will not have ISLs.",
            "Mozilla will not implement.",
            "as Tero said, CCA will not work.",
            "President Castro will not fully align with the United States.",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, ""))

    def test_the_same_sentence_without_the_negation_is_still_kept(self):
        self.assertTrue(fires("Mozilla will implement the draft.", ""))


class AnAcronymIsNotAPerson(unittest.TestCase):
    """1,761 occurrences: a protocol, a group or a part number as the owner."""

    def test_a_protocol_does_not_own_a_commitment(self):
        self.assertEqual(named_owner("TCPCL will wait for review and final draft."), UNKNOWN)

    def test_a_working_group_acronym_does_not_own_a_commitment(self):
        self.assertEqual(
            named_owner("I am not certain that this WG will worry about other areas"),
            UNKNOWN,
        )

    def test_a_part_number_does_not_own_a_commitment(self):
        self.assertEqual(named_owner("The CH-53K will provide heavy lift capability."), UNKNOWN)

    def test_an_ordinary_name_is_untouched(self):
        self.assertEqual(named_owner("Mark Nottingham will post the draft."), "Mark Nottingham")

    def test_an_acronym_is_still_allowed_as_a_speaker_label(self):
        # The colon is separate evidence that somebody was talking, so the
        # owner rule must not leak into the label rule.
        speaker, structural, _ = read_speaker("EKR: I'll write the text.")
        self.assertEqual(speaker, "EKR")
        self.assertFalse(structural)


class ActionItemsAreFound(unittest.TestCase):
    """9,139 occurrences, and 104 of the 113 items scribes marked themselves.

    Minutes are written after the meeting in note style. "Mark to post the
    draft" carries no finite verb, so every cue in the table missed it.
    """

    def test_a_named_action_item_is_recorded_against_the_person(self):
        # Constructed to the shape the corpus is full of; the evidence file
        # recorded the imperative-opener variants below verbatim.
        found, owner = classify("Mark Nottingham to post the revised draft to the list.", "")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, "Mark Nottingham")

    def test_a_bulleted_action_item_is_recorded(self):
        found, owner = classify("- Chairs to schedule an interim before the cutoff.", "")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, "Chairs")

    def test_ordinary_prose_of_the_same_shape_is_not_an_action_item(self):
        for line in (
            "It is important to note that the draft is stable.",
            "Nothing to report.",
            "Time to move on.",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, ""))


class ImperativeActionItemsNameNobody(unittest.TestCase):
    """The same class, opened by a verb instead of a person.

    "Ask WG to adopt the draft" is a real item with nobody named. Reading the
    opening verb as the person responsible would be an invention, so the item
    is recorded with no owner.
    """

    def test_the_item_is_recorded(self):
        for line in (
            "Plan to send to IESG unless big changes encountered (which is unexpected)",
            "Ask WG to adopt BIBE/Custody Transfer draft as a WG document",
            "Ask WG to adopt BPSec Interoperability Cipher Suites draft as a WG document",
        ):
            with self.subTest(line=line):
                found, owner = classify(line, "")
                self.assertIn(cues.ASSIGNMENT, found)
                self.assertEqual(owner, UNKNOWN)


class AQuestionIsNotAnAssignment(unittest.TestCase):
    """4,809 occurrences: every question asked at a microphone."""

    def test_a_question_that_asks_for_nothing_is_not_recorded(self):
        for line in (
            "can you make that promise, when TLS terminates at one MTA and",
            "Can you explain the difference between the two modes?",
            "Can you go back to slide 4?",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, ""))

    def test_a_question_that_asks_for_something_is_still_recorded(self):
        self.assertTrue(fires("Could you post that to RTGWG list?", ""))

    def test_a_question_with_a_deadline_is_still_recorded(self):
        self.assertTrue(fires("Could you look at that before Friday?", ""))


class AnOfferIsACommitmentAndACapabilityIsNot(unittest.TestCase):
    """4,005 occurrences of "I can". Most of them are not commitments.

    Position is what separates them. "I can write the text" opens a sentence
    and offers; "as I can just mirror it in my code" describes what is
    possible. A hedge anywhere in the sentence stands the cue down.
    """

    def test_a_hedged_capability_is_not_a_commitment(self):
        for line in (
            "I could possibly reach out to reach out to IPR holder.",
            "Someone might say I could do routing",
            "I support JCZ and - for an implementor it is very nice to have SM "
            "as I can just mirror it in my code.",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, "Greg"))

    def test_perception_is_not_an_offer(self):
        # A guard on the new cue. "I can see the slides" is the same
        # audio-visual check as "can you hear me", from the other side.
        for line in ("I can see the slides now.", "I can hear you."):
            with self.subTest(line=line):
                self.assertFalse(fires(line, "Greg"))

    def test_a_plain_offer_is_a_commitment(self):
        # Constructed: the evidence recorded the cases the tool got wrong, and
        # the fix has to keep this shape working.
        for line in (
            "I can write text for that section and send it to the list.",
            "I am happy to review the draft and send comments.",
        ):
            with self.subTest(line=line):
                found, owner = classify(line, "Greg")
                self.assertIn(cues.FIRST_PERSON, found)
                self.assertEqual(owner, "Greg")


class AHeadingAloneOnALineEndsTheTurn(unittest.TestCase):
    """2,757 occurrences. The label regex needed whitespace after the colon.

    A heading at the end of a line has none, so the line matched nothing, the
    previous speaker's turn ran straight through the section break, and the
    action items beneath the heading were recorded against whoever had spoken
    last.
    """

    def test_a_heading_is_structural(self):
        for line in ("Chairs:", "Wrap up:", "Wrap Up:"):
            with self.subTest(line=line):
                speaker, structural, _ = read_speaker(line)
                self.assertEqual(speaker, "")
                self.assertTrue(structural)

    def test_the_previous_speaker_does_not_own_what_follows_the_heading(self):
        text = "Barry Leiba: Nothing else from me.\nAction Items:\nI'll post the minutes by Friday.\n"
        found = extract_text(text, "m.txt")
        self.assertEqual([entry.owner for entry in found], [UNKNOWN])


class APluralLabelIsStillALabel(unittest.TestCase):
    """743 fabricated owners, most of them called "Chairs".

    The list of document labels held "chair" and not "chairs". Listing every
    plural by hand is how the list stays wrong, so the lookup now tries the
    singular too.
    """

    def test_a_plural_label_is_not_a_person(self):
        # The shapes are verbatim from the corpus; the names are replaced. Real
        # working-group chairs list their addresses in these lines, and a test
        # does not need somebody's inbox copied into a public repository to
        # prove that "Chairs:" is a label rather than a person.
        for line in (
            "Chairs: Marc Blanchet & Rick Taylor",
            "Chairs: Priya Raman, Chris Bowers",
            "Chairs:    Priya Raman (priya.raman@example.org)",
        ):
            with self.subTest(line=line):
                speaker, structural, _ = read_speaker(line)
                self.assertEqual(speaker, "")
                self.assertTrue(structural)

    def test_a_person_whose_name_ends_in_s_is_unaffected(self):
        speaker, structural, _ = read_speaker("Chris: I'll send the text.")
        self.assertEqual(speaker, "Chris")
        self.assertFalse(structural)


class ALowercaseNicknameIsASpeaker(unittest.TestCase):
    """1,257 occurrences. A jabber handle was read as document structure.

    That lost the owner and also ended the previous speaker's turn, so the cost
    was paid twice.
    """

    def test_a_handle_is_read_as_a_speaker(self):
        for line, name in (
            ("greg: we have another draft, bfd multipoint which had IPR disclosure.", "greg"),
            ("cb: so the IPR disclosed was for the other draft. we'll take it offline", "cb"),
            ("ekr: Interesting idea.", "ekr"),
        ):
            with self.subTest(line=line):
                speaker, structural, _ = read_speaker(line)
                self.assertEqual(speaker, name)
                self.assertFalse(structural)

    def test_an_ordinary_word_is_not_a_handle(self):
        for line in ("however: this is a problem", "important: we should look at this"):
            with self.subTest(line=line):
                speaker, _, _ = read_speaker(line)
                self.assertEqual(speaker, "")


class ALabelWithAnAffiliationIsStillALabel(unittest.TestCase):
    """514 plus 223 occurrences: ``Name (Org):`` and ``Name, Org:``.

    Neither matched, so the line kept its label inside the quoted sentence and
    was recorded against the previous speaker.
    """

    def test_a_parenthesised_affiliation_is_read(self):
        for line, name in (
            ("Sri Gundavelli (SG): Focus has been on how to transmit a packet, but", "Sri Gundavelli"),
            ("Tony Li (TL): Current solution works; no special version of neighbor", "Tony Li"),
            ("Erik Nordmark (EN): There is question on handover behaviour.", "Erik Nordmark"),
        ):
            with self.subTest(line=line):
                speaker, structural, _ = read_speaker(line)
                self.assertEqual(speaker, name)
                self.assertFalse(structural)

    def test_a_comma_separated_affiliation_is_read(self):
        speaker, _, remainder = read_speaker(
            "Suresh Krishnan, Kaloom: IESG review should be ready by next Friday (29th November)"
        )
        self.assertEqual(speaker, "Suresh Krishnan")
        self.assertTrue(remainder.startswith("IESG review"))

    def test_a_sentence_that_merely_contains_a_comma_and_a_colon_is_left_alone(self):
        # The comma form is easy to trigger by accident. When what precedes the
        # colon is not a name the line must be returned untouched, or the front
        # of the sentence is deleted along with the commitment in it.
        line = "Sam, I'll do it by Friday: no problem."
        self.assertEqual(read_speaker(line), ("", False, line))


class QuotedMailIsNotTheCurrentSpeaker(unittest.TestCase):
    """134 occurrences: a pasted mail quote inherited the previous speaker."""

    def test_a_quoted_line_ends_the_turn(self):
        text = (
            "Mark Nottingham: Nothing from me.\n"
            "> I'll post the revised draft by Friday.\n"
        )
        found = extract_text(text, "m.txt")
        self.assertEqual([entry.owner for entry in found], [UNKNOWN])

    def test_the_quote_marker_is_not_kept_in_the_recorded_sentence(self):
        found = extract_text("> Please send the slides to the list.\n", "m.txt")
        self.assertEqual(found[0].text, "Please send the slides to the list.")


class AJabberNicknameLineIsASpeaker(unittest.TestCase):
    """16 occurrences of ``<nick> ...``, which inherited the previous speaker."""

    def test_the_bracketed_nickname_owns_its_own_line(self):
        text = (
            "Mark Nottingham: Nothing from me.\n"
            "<ekr> I'll write the security considerations by Monday.\n"
        )
        found = extract_text(text, "m.txt")
        self.assertEqual(found[0].owner, "ekr")
        self.assertEqual(found[0].text, "I'll write the security considerations by Monday.")


class TheDayOfTheMeetingIsNotADeadline(unittest.TestCase):
    """898 occurrences: "later today" and "what we have today" as due dates."""

    def test_a_reported_time_is_not_a_deadline(self):
        for line in (
            "There's work on formally verifying it that we'll hear about later today.",
            "Even with what we have today in YANG you can solve this problem well.",
        ):
            with self.subTest(line=line):
                self.assertEqual(find_due_phrase(line), UNKNOWN)

    def test_a_stated_time_is_still_recorded(self):
        self.assertEqual(find_due_phrase("I'll update the risk register today."), "today")


class NarratingTheMeetingIsNotACommitment(unittest.TestCase):
    """294 occurrences of "we will now", which commits nobody to anything."""

    def test_the_running_order_is_not_a_commitment(self):
        for line in (
            "discussion, and we will now move on to our second panel.",
            "It was suggested that, since we will now need two multicast addresses,",
            "Let us see, no Democrats on this side so we will now go to",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, "Chair"))


class AStageDirectionIsNotACommitment(unittest.TestCase):
    """174 occurrences: a presenter describing the slide they are on."""

    def test_presentation_narration_is_not_recorded(self):
        for line in (
            "Let me start, and Anne has some thoughts on this",
            "Let me start again then.",
            "Let me walk you through that right now.",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, "Chair"))

    def test_a_real_undertaking_with_the_same_opening_survives(self):
        self.assertTrue(fires("Let me draft the shift plan tonight.", "Chair"))


class LetsIsHowARoomCommitsItself(unittest.TestCase):
    """657 occurrences. No cue family matched "let's" at all."""

    def test_it_is_recorded_and_belongs_to_nobody(self):
        found, owner = classify("Let's take it to the WG", "Chair")
        self.assertIn(cues.COLLECTIVE, found)
        self.assertEqual(owner, UNKNOWN)

    def test_a_negative_directive_is_not_a_commitment(self):
        self.assertFalse(fires("Lets not re-invent the", "Chair"))

    def test_let_us_know_is_still_filler(self):
        # A guard on the new cue rather than a regression: "let us" had to
        # inherit every exemption "let me" already had, or the commonest
        # sentence on any call becomes a commitment.
        self.assertFalse(fires("Let us know if that works.", "Chair"))
        self.assertTrue(fires("Let us know the vendor's answer by Friday.", "Chair"))


class AgreementInThePastTenseIsStillACommitment(unittest.TestCase):
    """501 occurrences. Minutes are written afterwards, in the past tense."""

    def test_volunteering_is_an_assignment(self):
        found, owner = classify("Carsten, Jim, Christian volunteered to provide a review.", "")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, "Christian")

    def test_agreeing_is_an_assignment(self):
        # Constructed to the same shape; the corpus evidence recorded the
        # volunteering variants verbatim.
        found, owner = classify("Mark agreed to take the issue to the list.", "")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, "Mark")


class HardWrappedLinesAreRejoined(unittest.TestCase):
    """45% of findings on raw wrapped files were cut off mid-sentence.

    Real transcripts wrap at about 70 columns. The deadline is usually in the
    half that was being thrown away.
    """

    def test_the_sentence_is_recorded_whole(self):
        text = (
            "Chairs: We'll ask the IESG to consider our charter\n"
            "changes on August 13 and report back.\n"
        )
        found = extract_text(text, "w.txt")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].text.endswith("report back."))
        self.assertIn("August 13", found[0].text)

    def test_the_line_number_is_where_the_sentence_started(self):
        text = (
            "Barry Leiba: nothing to report\n"
            "Chairs: We'll ask the IESG to consider our charter\n"
            "changes on August 13 and report back.\n"
        )
        self.assertEqual(extract_text(text, "w.txt")[0].line, 2)

    def test_a_short_list_item_is_not_glued_to_the_next_one(self):
        text = "- send the draft\n- review the text\nand nothing else\n"
        found = extract_text(text, "w.txt")
        self.assertEqual(found, [])


class FormFeedsDoNotShiftLineNumbers(unittest.TestCase):
    """31 documents in 1,067 carry page breaks.

    ``str.splitlines`` treats a form feed as a line ending; an editor does not.
    Every line number after one of them was reported one too high, which is the
    one thing a report has to get right for a reader to check it.
    """

    def test_a_page_break_does_not_count_as_a_line(self):
        text = "Alex: preamble\x0cAlex: I'll send the draft by Friday.\nAlex: next\n"
        found = extract_text(text, "f.txt")
        self.assertEqual(found[0].line, 1)


class AnUnownedUndertakingWithALimitIsRecorded(unittest.TestCase):
    """1,381 occurrences of a third-party "will" dropped outright.

    Recorded with no owner rather than discarded, which is what the project
    promises: absence of evidence is unknown, never a confirmed no. Only when
    the sentence states a limit — see the README for why the rest is left
    alone.
    """

    def test_a_passive_undertaking_with_a_deadline_is_kept(self):
        found, owner = classify("A revised draft will be posted by Friday.", "")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, UNKNOWN)

    def test_a_prediction_without_a_deadline_is_still_left_alone(self):
        self.assertFalse(fires("The routers will have the whole table", ""))


# ---------------------------------------------------------------------------
# Round two. The first round moved precision from 0.12 to 0.27 and left recall
# exactly where it was, so these are the classes that recall measurement named.
# ---------------------------------------------------------------------------


class CommittingInSoManyWords(unittest.TestCase):
    """The most literal commitment speech act in English had no cue at all.

    A legislator extracting a promise on the record, and the answer given back.
    The verb is the cue, in every person.
    """

    def test_the_request_is_recorded_and_names_nobody(self):
        for line in (
            "Will you commit to working with my office on this proposal which",
            "If confirmed, do you commit to working with the respective USAID",
            "Will you commit to working with Congress and members of the",
        ):
            with self.subTest(line=line):
                found, owner = classify(line, "Chairman")
                self.assertIn(cues.ASSIGNMENT, found)
                self.assertEqual(owner, UNKNOWN)

    def test_the_answer_belongs_to_whoever_gave_it(self):
        found, owner = classify("I certainly can commit to working with", "Witness")
        self.assertIn(cues.FIRST_PERSON, found)
        self.assertEqual(owner, "Witness")

    def test_an_expectation_put_on_the_record_is_an_ask(self):
        found, owner = classify("I hope you will consult with the public", "Chairman")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, UNKNOWN)

    def test_a_wish_about_the_past_is_not_an_ask(self):
        # Guard on the new cue: the future or the infinitive after "you" is
        # what makes it a request rather than a pleasantry.
        self.assertFalse(fires("I hope you enjoyed the presentation.", "Chairman"))

    def test_a_version_control_commit_is_not_a_promise(self):
        # Guard on the new cue. "commit" is a technical verb in the corpus this
        # tool was written for.
        for line in ("We commit the change to the repository.", "The commit to master broke the build."):
            with self.subTest(line=line):
                self.assertFalse(fires(line, "Alex"))


class ADroppedSubjectBelongsToTheSpeaker(unittest.TestCase):
    """"Fangwei: will move MS PW modeling to that model."

    Scribes drop the pronoun because the label already carried it. The label is
    read, and then nothing fires, so the commitment is lost with its owner
    standing right next to it.
    """

    def test_the_speaker_owns_the_dropped_subject(self):
        found = extract_text("Fangwei: will move MS PW modeling to that model.\n", "m.txt")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].owner, "Fangwei")

    def test_a_progressive_after_will_be_is_still_an_act(self):
        found = extract_text("Alex: will be sending the text tomorrow.\n", "m.txt")
        self.assertEqual(found[0].owner, "Alex")

    def test_a_passive_or_a_state_is_not_an_undertaking(self):
        # Guards on the new cue. "will be discussed" has no agent, and "will
        # need more review" is a state rather than something anybody does.
        for line in ("Alex: will be discussed on the list.\n", "Alex: will need more review.\n"):
            with self.subTest(line=line):
                self.assertEqual(extract_text(line, "m.txt"), [])

    def test_a_question_is_not_a_dropped_subject(self):
        self.assertFalse(fires("will that work for everyone?", "Alex"))

    def test_a_name_after_will_is_not_a_verb(self):
        self.assertFalse(fires("Will Smith presented the draft.", "Alex"))

    def test_without_a_speaker_there_is_no_subject_to_supply(self):
        self.assertFalse(fires("will move the model to the new format.", ""))


class ReportedSpeechCarriesItsCommitment(unittest.TestCase):
    """Past-tense reported speech is the default voice of written minutes.

    "Jankowicz says she will abide by it" names the person committing in front
    of the reporting verb, and the pronoun after it defeated every rule.
    """

    def test_the_name_before_the_reporting_verb_is_the_owner(self):
        found, owner = classify("deposition and Jankowicz says she will abide by it.", "Chair")
        self.assertIn(cues.ASSIGNMENT, found)
        self.assertEqual(owner, "Jankowicz")

    def test_the_past_tense_form_is_read_too(self):
        # Constructed to the same shape, in the tense minutes are written in.
        self.assertEqual(named_owner("Mark said he would send the text to the list."), "Mark")

    def test_a_reported_refusal_is_not_a_commitment(self):
        self.assertFalse(fires("Mark noted that he will not attend.", "Chair"))

    def test_a_reported_preference_is_not_a_commitment(self):
        # Guard on the new cue: wanting a thing is not undertaking to do one.
        self.assertFalse(fires("Mark said he would like a copy.", "Chair"))


class NarratingTheFloorIsNotACommitment(unittest.TestCase):
    """The largest remaining class of false positive.

    What is being undertaken is the next few seconds of the meeting: yielding,
    recognising, going back, refreshing a memory. It does not outlive the room.
    """

    def test_floor_management_is_not_recorded(self):
        for line in (
            "And let me back up for just a second.",
            "Let me go to Mr. Pugliaresi.",
            "Let me follow on a couple of topics that seem to be a bit",
            "I am sure you remember it, but I will just refresh your memory,",
            "the line, we will go to Senator Cortez Masto.",
            "I will tell you that during the 1940s things were different.",
        ):
            with self.subTest(line=line):
                self.assertFalse(fires(line, "Chairman"))

    def test_the_same_verbs_doing_real_work_still_fire(self):
        # The point of the split between the two verb tables. Every one of
        # these would be lost by a wider rule, and losing a commitment is the
        # worse error.
        for line in (
            "I will go to the vendor and get a quote.",
            "We will move on to the new supplier next quarter.",
            "I'll go back to the supplier about the invoice.",
            "I will read the draft and send comments.",
            "I'll tell you the exact freight cost once the quote lands.",
            "I'll get back to you with the numbers.",
        ):
            with self.subTest(line=line):
                self.assertTrue(fires(line, "Alex"), "lost a commitment")


class AnArticleMeansItIsNotAPerson(unittest.TestCase):
    """After the first round the ten commonest owners were all institutions.

    English does not put an article in front of a person's name, so the word in
    front of the candidate settles it without a list of institutions to
    maintain. See the README for the part of this that is not fixable here.
    """

    def test_a_determiner_blocks_the_owner(self):
        for line in (
            "The Committee will hold a hearing next week.",
            "The Department will provide the documents.",
            "The Chairs will issue a call for adoption.",
            "The Subcommittee will reconvene.",
            "The United States will continue to lead.",
            "our Chairs will decide",
        ):
            with self.subTest(line=line):
                self.assertEqual(named_owner(line), UNKNOWN)

    def test_a_bare_name_is_still_an_owner(self):
        for line, name in (
            ("Priya will send the deck.", "Priya"),
            ("Legal will review the contract.", "Legal"),
            ("Zhang Wei will pull the rates.", "Zhang Wei"),
            ("This Friday Priya will send the deck.", "Priya"),
        ):
            with self.subTest(line=line):
                self.assertEqual(named_owner(line), name)

    def test_the_documented_limit_still_stands(self):
        # Not a fix, a record. A bare capitalised proper noun naming a state or
        # an institution is the same shape as a surname, and separating them
        # needs a gazetteer this package will not carry. The README says so.
        self.assertEqual(named_owner("China will continue to expand its fleet."), "China")


# ---------------------------------------------------------------------------
# Round three. The action-item cue added in round one fired on the ordinary
# English preposition frame: 630 of 11,468 findings across a 2,000-document
# slice, producing report sections headed "According", "Deferring" and "Due".
# A defect this project introduced, so it is written down the same way.
# ---------------------------------------------------------------------------


def in_a_document(line: str, elsewhere: str) -> list:
    """Run one line through a document that also uses its head word normally."""
    return [
        entry
        for entry in extract_text(f"{elsewhere}\n{line}\n", "d.txt")
        if entry.text.startswith(line[:12])
    ]


class APrepositionIsNotAPerson(unittest.TestCase):
    """"According to this scheme" is not "Mark to post the draft".

    What separates them is the word after "to". A bare verb begins an
    infinitive; a determiner or a pronoun begins a noun phrase, which makes the
    "to" a preposition and the line a sentence.
    """

    def test_a_prepositional_frame_is_not_an_action_item(self):
        for line in (
            "According to this scheme, the Venezuelan supreme court declared the assembly void.",
            "Deferring to my colleagues from the Department of Defense.",
            "Thanks to the Chair for scheduling something sane at the end of the day.",
        ):
            with self.subTest(line=line):
                self.assertIsNone(infinitive_action(line, Document.read("")))

    def test_it_holds_without_any_help_from_the_document(self):
        # The closed-class test stands on its own: these need no evidence from
        # the rest of the file, which is what makes them the reliable half.
        self.assertIsNone(infinitive_action("According to the report, it failed.", None))

    def test_an_infinitive_of_being_is_still_an_action_item(self):
        # Guard. "to be" must not be banned: this is a real assignment.
        self.assertEqual(
            infinitive_action("Mirja to be the responsible AD for this document.", Document.read("")),
            "Mirja",
        )


class AWordTheDocumentAlsoWritesInLowerCase(unittest.TestCase):
    """A sentence-initial capital is punctuation, not evidence of a name.

    When the same document writes the word in lower case somewhere else, the
    capital was the sentence. A name gets no such contradiction.
    """

    def test_an_ordinary_word_at_the_start_is_not_an_owner(self):
        for line, elsewhere in (
            ("Due to visa confidentiality rules, we would not be making public the names.",
             "the delay was due to the schedule"),
            ("Want to be able to do something like .size only allows lengths of the frame.",
             "we want to keep this simple"),
            ("Need to have something that talks about the difference between the two.",
             "we need to fix the text"),
            ("Related to protocol negotiation draft.",
             "this is related to the other draft"),
            ("Things to be done: Move security considerations from media type registration.",
             "a few things came up"),
        ):
            with self.subTest(line=line):
                self.assertEqual(in_a_document(line, elsewhere), [])

    def test_a_name_survives_a_document_that_uses_it_as_a_verb(self):
        # Guard: every word of the head has to be contradicted, not any one of
        # them, so a two-word name is safe from a stray lower-case "mark".
        found = in_a_document(
            "Mark Nottingham to post the revised draft to the list.",
            "please mark that message as read",
        )
        self.assertEqual([entry.owner for entry in found], ["Mark Nottingham"])

    def test_a_bullet_or_a_deadline_overrides_the_test(self):
        # Guard: independent evidence that a scribe was writing an item beats
        # the orthographic test, which is what keeps "- Chairs to schedule an
        # interim" in a document that also says "the chairs".
        for line in ("- Chairs to schedule an interim.", "Chairs to schedule an interim by Friday."):
            with self.subTest(line=line):
                found = in_a_document(line, "the chairs will decide this later")
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].owner, "Chairs")


# ---------------------------------------------------------------------------
# Rounds three and four, the wrap detector, tested on one real document.
#
# Round three loosened the rejoin so a continuation beginning with a capital
# letter could be recognised. Round four fixed the measurement that decides
# whether to loosen it: it anchored on the longest line in the file, and a real
# file always carries lines far above the wrap column — a URL, a table row, an
# ASCII rule. It missed 76% of the hard-wrapped documents in a 2,500-document
# slice, including the transcript it had been written from.
#
# The fixture that hid that is deleted. Every line below is copied verbatim
# from chrg/CHRG-114hhrg20529.txt: two lines of GPO front matter, the paragraph
# the fragment came from, and a later passage carrying a commitment. Front
# matter included, because the front matter is the thing that broke it.
# ---------------------------------------------------------------------------

HEARING = (
    "http://bookstore.gpo.gov. For more information, contact the GPO Customer Contact Center,\n"
    "U.S. Government Publishing Office. Phone 202-512-1800, or 866-512-1800 (toll-free).\n"
    "blocked roads throughout the country and metro stations near\n"
    "the national electoral council offices.\n"
    "    President Maduro and his party have politicized the\n"
    "judiciary. Judge Maria Lourdes Afiuni was charged with\n"
    "corruption and abuse of authority after not convicting a\n"
    "prisoner on politicized charges--in other words, for doing her\n"
    "job.\n"
    "    She was arrested, jailed, and brutally treated 6 years ago.\n"
    "Thirteen hearings have been held since then. No evidence has\n"
    "ever been adduced that she committed any crime. She had never\n"
    "been convicted or sentenced.\n"
    "    Nevertheless, she continues to be subjected to what they\n"
    "call conditional release. This restricts her movement and\n"
    "ability to talk to the media or use social media, even though\n"
    "the law in Venezuela states that such measures may not last\n"
    "more than 2 years.\n"
    "    There is substantial evidence of the systematic scheme of\n"
    "the government to torture that involves judges, prosecutors and\n"
    "jailers. Venezuelan NGO Foro Penal counts 81 political\n"
    "prisoners behind bars. Twenty-six of them are in deteriorating\n"
    "health.\n"
    "    On September 10, 2015, Judge Susanna Barreiros found\n"
    "Leopoldo Lopez, the leader of the opposition party Popular\n"
    "Will, guilty on counts of public incitement, damage to\n"
    "property, fire damage and association for conspiracy related to\n"
    "the February 2014 protest.\n"
    "    This was supposedly for transmitting subliminally messages\n"
    "to the crowd. The judge issued a sentence of 13 years and 9\n"
    "months in prison, almost the maximum allowed by law. The 14-\n"
    "month trial was marked by lack of due process and shows abuse\n"
    "of the judicial system to punish government critics.\n"
    "    The judge accepted more than 100 witnesses for the\n"
    "prosecution. She rejected all but two for the defense. She\n"
    "deliberated less than 1 hour before announcing her decision to\n"
    "convict.\n"
    "    So we call once again for the immediate release of Leopoldo\n"
    "Lopez and all the other political prisoners.\n"
    "    The ability of the press to publish freely and for\n"
    "Venezuelans to speak their minds has crumbled in the face of\n"
    "government actions.\n"
    "    President Maduro's administration has used a potent\n"
    "combination of politicized libel laws, media content\n"
    "regulations, legal harassment and physical intimidation to\n"
    "silence independent media.\n"
    "    The ruling party uses force and arbitrarily detains\n"
    "protestors who peacefully assemble to express their views,\n"
    "signatures of those expressing support for a recall referendum.\n"
    "This important process offers an opportunity for the Venezuelan\n"
    "people to express their political will in a constitutional,\n"
    "peaceful, and democratic manner.\n"
    "    We favor Venezuelan solutions to Venezuelan problems with\n"
    "the support of the region. We are prepared to continue to use\n"
    "all appropriate tools in our toolkit and we will continue to\n"
    "call attention to all actions that undermine democratic\n"
    "principles.\n"
    "    We did just that at the OAS General Assembly and we will\n"
    "continue to do so at the OAS permanent council meetings\n"
)

#: The opening of ft_corpus/minutes-101-jmap.txt, also verbatim. Note-style
#: minutes: short bullets and headings, no wrapped prose, so the band under the
#: ceiling is nearly empty and the file has to keep the cautious rule. Joining
#: bullets into one another would be a worse error than not joining prose.
NOTE_STYLE = (
    "JMAP minutes - 22 Mar 2018 - IETF101, London\n"
    "Meeting only took 1 hour from 3:50 to 4:50, with 10 attending\n"
    "locally and 6 remotely.\n"
    'Discussion of: "fetch text parts, includes images!!!"\n'
    "* just the list of parts, don't need to fetch the data in same\n"
    "  round trip, can then extra list of\n"
    "  actual bits to fetch\n"
    "* was clarified, all good\n"
    "Capabilities:\n"
    "* format discussion - urn is easiest to use and search reliably\n"
    "* registry - Chris already wrote the text\n"
    "* makes it easy for future extension writers\n"
    "* ACTION: urn for standards track docs,\n"
    "  URI for vendor extensions #185\n"
    "proxying creationIds?:\n"
    "* Question about parallelisation\n"
    "* Have client declare up-front which IDs it's planning to\n"
    "  backreference?  Hard to implement on client.\n"
    "* ACTION: send to list for more feedback\n"
    "* ACTION: clarify that client IDs are scoped to request,\n"
    "  must not be reused within it. #191\n"
    "anchor offset direction:\n"
    "* ACTION: make it be 'anchor' + 'position'\n"
    "IDs:\n"
    "* already discussed in EXTRA - limit charset to [a-zA-Z0-9_-]\n"
    "* ACTION: bron - can IMAP atom start/end with - and _ ?\n"
    "Inline video/audio?\n"
    "* Alexey - yes, probably should.\n"
    "* oplevel font/, should it be allowed? - seems silly\n"
    "* ACTION: allow video/audio #192\n"
    "Use case for really simple body part:\n"
    "* all HTML, no dependencies\n"
    "* Alexey: if you have it, then I'd use it.\n"
    "* things like web clients would want something like this - stick\n"
    "  it in a web page\n"
    "* ACTION: make an extension, fold back if we want towards end #193\n"
    "* security considerations are going to be fun!\n"
    "IANA considerations:\n"
    "* Chris Newman will do #194\n"
    "EXTENSIONS:\n"
    "- html body probably\n"
    "   - requested by WG\n"
    "- s/mime extension\n"
    "   - just adds verification status\n"
    "   - adopted by WG\n"
    "- imapdata - shelved\n"
    "Submissions:\n"
    "- reference defacto XCLIENT extension to SMTP\n"
)


class TheWrapColumnSurvivesRealFiles(unittest.TestCase):
    """A real file's longest line is not its wrap column."""

    def test_an_outlier_does_not_defeat_the_measurement(self):
        # p95 of this text is 63 and its longest line is 88. Anchoring on the
        # longest put the measuring band above every line of prose beneath it.
        self.assertEqual(wrap_column(HEARING.split("\n")), 63)

    def test_the_paragraph_is_read_as_one_sentence(self):
        joined = [line for _, line in logical_lines(HEARING) if "Venezuelans" in line]
        self.assertEqual(len(joined), 1)
        self.assertIn("The ability of the press to publish freely", joined[0])
        self.assertIn("has crumbled in the face of government actions.", joined[0])

    def test_the_fragment_is_no_longer_an_owner(self):
        owners = {entry.owner for entry in extract_text(HEARING, "chrg.txt")}
        self.assertNotIn("Venezuelans", owners)

    def test_a_commitment_split_across_two_lines_is_recorded_whole(self):
        # The other half of the same fix. "we will continue to" ends a line and
        # "call attention to all actions ..." begins the next one; read a line
        # at a time the commitment is recorded without its object.
        found = [
            entry
            for entry in extract_text(HEARING, "chrg.txt")
            if "call attention to all actions" in entry.text
        ]
        self.assertEqual(len(found), 1)
        self.assertIn("we will continue to", found[0].text)

    def test_no_text_is_lost_in_the_joining(self):
        # Guard. Rejoining must not drop a line on the floor.
        joined = " ".join(line for _, line in logical_lines(HEARING))
        for line in HEARING.split("\n"):
            if line.strip():
                self.assertIn(line.strip(), joined)

    def test_note_style_minutes_are_not_treated_as_wrapped(self):
        # Guard.
        self.assertEqual(wrap_column(NOTE_STYLE.split("\n")), 0)

    def test_a_short_document_is_not_measured_at_all(self):
        # The percentile only means something once the file has a tail. At
        # twenty lines the 95th percentile is the longest line, which is the
        # statistic this replaced — so below the minimum nothing is measured
        # and the cautious rule stands. These are the first twenty lines of the
        # same real text that measures cleanly at full length, with the two
        # lines of front matter dropped so nothing but the length is deciding.
        self.assertEqual(wrap_column(HEARING.split("\n")[2:22]), 0)

    def test_a_document_too_short_to_measure_is_left_alone(self):
        # Guard. Below the minimum the percentile is just the longest line
        # again, so short files keep the cautious rule instead.
        self.assertEqual(wrap_column(["Alex: I will send it.", "Sam: Can you confirm?"]), 0)


if __name__ == "__main__":
    unittest.main()
