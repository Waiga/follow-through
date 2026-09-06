import json
import tempfile
import unittest
from pathlib import Path

from follow_through import ledger
from follow_through.extract import extract_text
from follow_through.models import Entry


def candidates(text="Alex: I'll send the lease by Friday."):
    return extract_text(text, "sample.txt")


class Identity(unittest.TestCase):
    def test_same_sentence_and_owner_is_the_same_commitment(self):
        first = candidates()[0]
        second = candidates()[0]
        self.assertEqual(first.identity, second.identity)

    def test_whitespace_and_case_do_not_change_identity(self):
        first = candidates("Alex: I'll send the lease by Friday.")[0]
        second = candidates("Alex:   i'll SEND the   lease by friday.")[0]
        self.assertEqual(first.identity, second.identity)

    def test_a_different_speaker_is_a_different_commitment(self):
        first = candidates("Alex: I'll send the lease by Friday.")[0]
        second = candidates("Sam: I'll send the lease by Friday.")[0]
        self.assertNotEqual(first.identity, second.identity)

    def test_the_same_promise_in_a_different_file_is_a_new_commitment(self):
        # A weekly promise repeated word for word in next week's transcript is a
        # new obligation. Without the source in the identity it would match the
        # closed entry from last week and vanish.
        from follow_through.extract import extract_text

        line = "Alex: I'll send the status report by Friday."
        week_one = extract_text(line, "week-01.txt")[0]
        week_two = extract_text(line, "week-02.txt")[0]
        self.assertNotEqual(week_one.identity, week_two.identity)

    def test_a_recurring_promise_survives_last_weeks_closure(self):
        from follow_through.extract import extract_text

        line = "Alex: I'll send the status report by Friday."
        entries, _ = ledger.merge([], extract_text(line, "week-01.txt"))
        ledger.close(entries, entries[0].id, "sent")
        entries, added = ledger.merge(entries, extract_text(line, "week-02.txt"))
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].state, ledger.OPEN)


class Merging(unittest.TestCase):
    def test_adds_new_candidates(self):
        entries, added = ledger.merge([], candidates())
        self.assertEqual(len(entries), 1)
        self.assertEqual(len(added), 1)

    def test_running_twice_adds_nothing(self):
        entries, _ = ledger.merge([], candidates())
        entries, added = ledger.merge(entries, candidates())
        self.assertEqual(len(entries), 1)
        self.assertEqual(added, [])

    def test_a_closed_entry_is_not_reopened_by_a_rerun(self):
        entries, _ = ledger.merge([], candidates())
        ledger.close(entries, entries[0].id, "done")
        entries, added = ledger.merge(entries, candidates())
        self.assertEqual(added, [])
        self.assertEqual(entries[0].state, ledger.CLOSED)
        self.assertEqual(entries[0].note, "done")


class Persistence(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())

    def test_missing_ledger_loads_as_empty(self):
        self.assertEqual(ledger.load(self.directory), [])

    def test_round_trips_every_field(self):
        entries, _ = ledger.merge([], candidates())
        ledger.close(entries, entries[0].id, "sent it")
        ledger.save(self.directory, entries)
        loaded = ledger.load(self.directory)
        self.assertEqual(loaded[0].to_dict(), entries[0].to_dict())

    def test_creates_the_directory_if_absent(self):
        nested = self.directory / "a" / "b"
        ledger.save(nested, [])
        self.assertTrue(ledger.ledger_path(nested).exists())

    def test_invalid_json_is_reported_not_swallowed(self):
        ledger.ledger_path(self.directory).write_text("{oh no", encoding="utf-8")
        with self.assertRaises(ledger.LedgerError):
            ledger.load(self.directory)

    def test_foreign_json_is_rejected(self):
        ledger.ledger_path(self.directory).write_text('{"cats": 3}', encoding="utf-8")
        with self.assertRaises(ledger.LedgerError):
            ledger.load(self.directory)

    def test_no_temporary_file_is_left_behind(self):
        entries, _ = ledger.merge([], candidates())
        ledger.save(self.directory, entries)
        leftovers = list(self.directory.glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_an_unrecognised_state_is_refused(self):
        # It would otherwise be counted in the total and listed under neither
        # open nor closed: invisible, with no warning.
        ledger.ledger_path(self.directory).write_text(
            '{"version": 1, "entries": [{"id": "a1", "text": "t", "owner": "Alex",'
            ' "due_phrase": "unknown", "cues": [], "source": "s", "line": 1,'
            ' "state": "done", "note": ""}]}',
            encoding="utf-8",
        )
        with self.assertRaises(ledger.LedgerError) as caught:
            ledger.load(self.directory)
        self.assertIn("done", str(caught.exception))

    def test_a_closed_entry_with_no_reason_is_refused(self):
        ledger.ledger_path(self.directory).write_text(
            '{"version": 1, "entries": [{"id": "a1", "text": "t", "owner": "Alex",'
            ' "due_phrase": "unknown", "cues": [], "source": "s", "line": 1,'
            ' "state": "closed", "note": "  "}]}',
            encoding="utf-8",
        )
        with self.assertRaises(ledger.LedgerError) as caught:
            ledger.load(self.directory)
        self.assertIn("no reason", str(caught.exception))

    def test_written_file_is_readable_json(self):
        ledger.save(self.directory, [])
        raw = json.loads(ledger.ledger_path(self.directory).read_text(encoding="utf-8"))
        self.assertEqual(raw["version"], ledger.LEDGER_VERSION)


class Closing(unittest.TestCase):
    def setUp(self):
        self.entries, _ = ledger.merge([], candidates())
        self.identity = self.entries[0].id

    def test_closes_by_full_id(self):
        entry = ledger.close(self.entries, self.identity, "sent it")
        self.assertEqual(entry.state, ledger.CLOSED)

    def test_closes_by_unambiguous_prefix(self):
        entry = ledger.close(self.entries, self.identity[:4], "sent it")
        self.assertEqual(entry.state, ledger.CLOSED)

    def test_a_note_is_required(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.close(self.entries, self.identity, "   ")

    def test_unknown_id_is_an_error(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.close(self.entries, "zzzzzz", "sent it")

    def test_ambiguous_prefix_is_an_error(self):
        self.entries.append(
            Entry(
                id=self.identity[:2] + "ffffffffff",
                text="another",
                owner="Sam",
                due_phrase="unknown",
                cues=(),
                source="s",
                line=1,
            )
        )
        with self.assertRaises(ledger.LedgerError) as caught:
            ledger.close(self.entries, self.identity[:2], "sent it")
        self.assertIn("ambiguous", str(caught.exception))

    def test_closing_twice_is_an_error(self):
        ledger.close(self.entries, self.identity, "sent it")
        with self.assertRaises(ledger.LedgerError):
            ledger.close(self.entries, self.identity, "again")


if __name__ == "__main__":
    unittest.main()
