import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from follow_through import ledger
from follow_through.cli import main

TRANSCRIPT = (
    "Alex: I'll send the lease by Friday.\n"
    "Sam: Can you confirm the headcount?\n"
    "Alex: I already sent the insurance certificate.\n"
)


def run(*argv):
    """Run the CLI and return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.transcript = self.work / "sync.txt"
        self.transcript.write_text(TRANSCRIPT, encoding="utf-8")
        self.ledger_dir = self.work / "ledger"
        self.reports_dir = self.work / "reports"

    def track(self):
        return run("--ledger-dir", str(self.ledger_dir), "track", str(self.transcript))

    def test_extract_records_nothing(self):
        code, out, _ = run(
            "--ledger-dir", str(self.ledger_dir), "extract", str(self.transcript)
        )
        self.assertEqual(code, 0)
        self.assertIn("Nothing was recorded", out)
        self.assertFalse(ledger.ledger_path(self.ledger_dir).exists())

    def test_extract_says_so_when_it_finds_nothing(self):
        quiet = self.work / "quiet.txt"
        quiet.write_text("Good morning. The weather is fine.\n", encoding="utf-8")
        code, out, _ = run("--ledger-dir", str(self.ledger_dir), "extract", str(quiet))
        self.assertEqual(code, 0)
        self.assertIn("does not prove", out)

    def test_track_writes_the_ledger(self):
        code, out, _ = self.track()
        self.assertEqual(code, 0)
        self.assertIn("2 new", out)
        self.assertEqual(len(ledger.load(self.ledger_dir)), 2)

    def test_tracking_twice_adds_nothing(self):
        self.track()
        _, out, _ = self.track()
        self.assertIn("0 new, 2 already known", out)

    def test_list_shows_open_entries_by_default(self):
        self.track()
        code, out, _ = run("--ledger-dir", str(self.ledger_dir), "list")
        self.assertEqual(code, 0)
        self.assertIn("I'll send the lease by Friday.", out)

    def test_list_on_an_empty_ledger_is_not_an_error(self):
        code, out, _ = run("--ledger-dir", str(self.ledger_dir), "list")
        self.assertEqual(code, 0)
        self.assertIn("Nothing open.", out)

    def test_close_then_list_moves_the_entry(self):
        self.track()
        identity = ledger.load(self.ledger_dir)[0].id
        code, out, _ = run(
            "--ledger-dir", str(self.ledger_dir), "close", identity, "--note", "signed"
        )
        self.assertEqual(code, 0)
        self.assertIn("signed", out)
        _, open_list, _ = run("--ledger-dir", str(self.ledger_dir), "list")
        self.assertNotIn(identity, open_list)
        _, closed_list, _ = run(
            "--ledger-dir", str(self.ledger_dir), "list", "--state", "closed"
        )
        self.assertIn(identity, closed_list)

    def test_close_with_an_unknown_id_fails_cleanly(self):
        self.track()
        code, _, err = run(
            "--ledger-dir", str(self.ledger_dir), "close", "zzzz", "--note", "x"
        )
        self.assertEqual(code, 1)
        self.assertIn("no entry matches", err)

    def test_report_writes_both_files(self):
        self.track()
        code, out, _ = run(
            "--ledger-dir", str(self.ledger_dir),
            "--reports-dir", str(self.reports_dir),
            "report",
        )
        self.assertEqual(code, 0)
        self.assertTrue((self.reports_dir / "follow-through.md").exists())
        self.assertTrue((self.reports_dir / "follow-through.html").exists())
        self.assertIn("follow-through.md", out)

    def test_missing_file_fails_cleanly(self):
        code, _, err = run(
            "--ledger-dir", str(self.ledger_dir), "track", str(self.work / "nope.txt")
        )
        self.assertEqual(code, 1)
        self.assertIn("No such file", err)

    def test_a_directory_is_not_a_transcript(self):
        code, _, err = run("--ledger-dir", str(self.ledger_dir), "track", str(self.work))
        self.assertEqual(code, 1)
        self.assertIn("directory", err)

    def test_a_corrupt_ledger_fails_cleanly(self):
        self.ledger_dir.mkdir(parents=True)
        ledger.ledger_path(self.ledger_dir).write_text("{oh no", encoding="utf-8")
        code, _, err = run("--ledger-dir", str(self.ledger_dir), "list")
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)

    def test_undecodable_bytes_do_not_crash(self):
        rough = self.work / "rough.txt"
        rough.write_bytes(b"Alex: I'll send it by Friday.\n\xff\xfe\n")
        code, _, _ = run("--ledger-dir", str(self.ledger_dir), "extract", str(rough))
        self.assertEqual(code, 0)

    def test_no_command_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as caught:
            run()
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
