"""Nothing this tool prints or writes may contain a punctuation dash.

The rule is the house writing standard: a dash used as punctuation is the most
recognisable tell of machine written text, so it is banned from anything
published. Hyphens inside genuine compound words are spelling, not punctuation,
and stay: ``follow-through``, ``first-person-undertaking``, ``system-ui``.

0.3.0 shipped because the Markdown report printed an em dash. That was fixed by
hand, and until this file existed nothing stopped it coming back. Every other
tool in the portfolio has this guard. This is the one that did not.

The checks cover every renderer and every output format the README documents:
both report renderers, both report files on disk, the ledger JSON, the standard
output of all five commands, the help text, the error messages on standard
error, every string constant in the package source, and the example reports
checked in beside the README.

Four detector mistakes are deliberately designed out, because each one produced
a wrong answer when this was being written:

* The ASCII spaced double hyphen prints as a dash to a reader and matches no
  search for an em dash. It is in the offence list in its own right.
* ``json.dumps`` escapes a dash to ``\\u2014`` under its default settings, so a
  scan of the raw bytes of a JSON file reports clean while the reader still sees
  a dash. JSON is parsed and its values walked, never scanned as text alone.
* From Python 3.12 the tokenizer splits an f-string literal into
  ``FSTRING_MIDDLE``, which is not ``token.STRING``, so a token based audit walks
  straight past a dash inside an f-string. The syntax tree reports those literal
  parts as ordinary constants on every supported version, so the tree is what is
  walked.
* A shell ``grep`` reported no em dash in a file that visibly contained one.
  Every file here is read as bytes and decoded explicitly.

Every detector below has a test proving it can fail. A guard nobody has seen
fail is not a guard.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

import follow_through
from follow_through import cli, ledger as ledger_module, report as report_module
from follow_through.models import UNKNOWN, Entry

PACKAGE = Path(follow_through.__file__).parent
ROOT = PACKAGE.parent

#: Every character that reads as a dash rather than as a hyphen inside a word.
#:
#: The em and en dashes are the two that get written by hand. The rest are here
#: because a copy and paste from a word processor, a PDF or a spreadsheet brings
#: them in, they render as a dash, and none of them matches a search for the two
#: obvious ones.
DASH_CHARACTERS = {
    "‒": "figure dash",
    "–": "en dash",
    "—": "em dash",
    "―": "horizontal bar",
    "⁃": "hyphen bullet",
    "−": "minus sign",
    "﹘": "small em dash",
    "﹣": "small hyphen minus",
    "－": "fullwidth hyphen minus",
}

#: Two dashes typed as ASCII. It looks like an em dash to a reader and it is not
#: one, so a scan for the Unicode characters alone calls it clean.
ASCII_DOUBLE_HYPHEN = " -- "

#: A hyphen standing alone between two spaces, used where a comma or a full stop
#: belongs. This is banned as punctuation too.
ASCII_SPACED_HYPHEN = " - "

#: A list item opens with a hyphen and a space, which is structure rather than
#: punctuation, so the marker is removed before the spaced hyphen is looked for.
#: Without this every bullet in the Markdown report reads as an offence.
LIST_MARKER = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")


def offences(text: str) -> list[str]:
    """Every kind of punctuation dash in ``text``, named, sorted, deduplicated.

    Returns an empty list when the text is clean, which is what every assertion
    here compares against. Naming the offence rather than returning a count is
    deliberate: a failure message that says "em dash" sends the reader to the
    right character, and a count does not.
    """
    found = {DASH_CHARACTERS[char] for char in text if char in DASH_CHARACTERS}
    if ASCII_DOUBLE_HYPHEN in text:
        found.add("ASCII spaced double hyphen")
    for line in text.splitlines():
        if ASCII_SPACED_HYPHEN in LIST_MARKER.sub("", line):
            found.add("ASCII spaced hyphen")
            break
    return sorted(found)


def text_of(path: Path) -> str:
    """Read a file as bytes and decode it explicitly.

    A shell ``grep`` reported no em dash in a file that contained one, so no
    check in this module goes through an external text search.
    """
    return path.read_bytes().decode("utf-8")


def strings_in(value: object) -> list[str]:
    """Every string anywhere inside a decoded JSON value, keys included.

    A JSON document is parsed before it is inspected. Scanning the raw bytes
    instead would miss ``\\u2014``, which is what ``json.dumps`` writes by
    default and what a reader still sees as a dash.
    """
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            found.append(key)
            found.extend(strings_in(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(strings_in(item))
    return found


def _docstring_constants(tree: ast.Module) -> set[int]:
    """The identity of every docstring node, so they can be skipped.

    A docstring explains the code to somebody reading the source. It is never
    printed, so a dash in one is a style matter for the repository rather than
    something a user of the tool can see, and this module is about output.
    """
    skip: set[int] = set()
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            skip.add(id(first.value))
    return skip


def string_constants(path: Path) -> list[tuple[int, str]]:
    """Every string literal in a module except its docstrings, with line numbers.

    The syntax tree is walked rather than the token stream. From Python 3.12 an
    f-string literal is tokenised as ``FSTRING_MIDDLE`` and not as
    ``token.STRING``, so a token based audit silently skips it. The tree reports
    those same parts as constants on every version this package supports.
    """
    tree = ast.parse(text_of(path), filename=str(path))
    skip = _docstring_constants(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
    ]


def sample_entries() -> list[Entry]:
    """A ledger exercising every branch of both renderers.

    Not one character of it is a dash, so anything a renderer produces that is
    one was written by the tool and not quoted from the input. That is the whole
    reason the fixture is written here instead of being read from the examples,
    whose invented transcripts open with an em dash in their title line. A
    quoted sentence is reproduced verbatim and must stay verbatim, so output
    built from input that contains a dash proves nothing either way.
    """
    common = dict(
        due_phrase="by Friday",
        cues=("first-person-undertaking",),
        source="sample.txt",
        line=1,
    )
    return [
        Entry(id="aaaa", text="I will send the lease to finance.", owner="Alex", **common),
        Entry(id="bbbb", text="Please confirm the headcount.", owner=UNKNOWN, **common),
        Entry(
            id="cccc",
            text="I will pull the carrier rates.",
            owner="Sam",
            state="closed",
            note="rates received and filed",
            **dict(common, due_phrase=UNKNOWN),
        ),
    ]


def run_cli(*argv: str) -> tuple[str, str]:
    """Run a command and return everything it wrote to the two streams."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with contextlib.suppress(SystemExit):
            cli.main(list(argv))
    return out.getvalue(), err.getvalue()


def working_directory(case: unittest.TestCase) -> Path:
    """A temporary directory, made current for the duration of one test.

    The report prints the source of every entry, and the CLI shortens a path
    relative to the directory it was run in. Run from somewhere else and the
    report carries an absolute path belonging to whichever machine ran the
    suite, which is content this test does not control and cannot vouch for.
    Running from inside the temporary directory is also how the README
    documents the tool, so the output under inspection is the real one.
    """
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    root = Path(directory.name).resolve()
    context = contextlib.chdir(root)
    context.__enter__()
    case.addCleanup(context.__exit__, None, None, None)
    return root


class TheDetectorCanFail(unittest.TestCase):
    """Proof that each detector fires. A guard nobody has seen fail is not one."""

    def test_it_finds_an_em_dash(self):
        self.assertEqual(offences("open — closed"), ["em dash"])

    def test_it_finds_an_en_dash(self):
        self.assertEqual(offences("2016 – 2024"), ["en dash"])

    def test_it_finds_the_ascii_double_hyphen_that_no_unicode_search_matches(self):
        text = "open -- closed"
        self.assertNotIn("—", text)
        self.assertEqual(offences(text), ["ASCII spaced double hyphen"])

    def test_it_finds_a_spaced_hyphen_used_as_punctuation(self):
        self.assertEqual(offences("open - closed"), ["ASCII spaced hyphen"])

    def test_it_finds_the_dashes_a_word_processor_pastes_in(self):
        for char, name in DASH_CHARACTERS.items():
            with self.subTest(name=name):
                self.assertEqual(offences(f"before{char}after"), [name])

    def test_it_reports_every_kind_present_at_once(self):
        self.assertEqual(
            offences("a — b -- c – d"),
            ["ASCII spaced double hyphen", "em dash", "en dash"],
        )

    def test_a_hyphen_inside_a_compound_word_is_not_an_offence(self):
        for clean in (
            "follow-through",
            "first-person-undertaking",
            "non-technical",
            "font:16px/1.5 system-ui,sans-serif;max-width:52rem",
            "--ledger-dir",
            "read-only",
        ):
            with self.subTest(text=clean):
                self.assertEqual(offences(clean), [])

    def test_a_list_marker_is_structure_and_not_punctuation(self):
        self.assertEqual(offences("- Deadline: by Friday"), [])
        self.assertEqual(offences("  - Source: sample.txt line 1"), [])
        self.assertEqual(offences("* Cues: first-person-undertaking"), [])
        self.assertEqual(offences("1. Cues: first-person-undertaking"), [])

    def test_a_list_marker_does_not_hide_a_dash_later_in_the_line(self):
        self.assertEqual(offences("- Deadline - by Friday"), ["ASCII spaced hyphen"])


class TheJsonDetectorLooksAtValuesAndNotAtBytes(unittest.TestCase):
    """The second trap, written as a test so it cannot come back.

    ``json.dumps`` escapes a dash by default. The raw document is then clean by
    inspection while every reader of the parsed data sees a dash.
    """

    def test_the_default_encoder_hides_a_dash_from_a_scan_of_the_raw_text(self):
        raw = json.dumps({"note": "closed — filed"})
        self.assertIn("\\u2014", raw)
        self.assertEqual(offences(raw), [])

    def test_walking_the_decoded_values_finds_it(self):
        raw = json.dumps({"note": "closed — filed"})
        found = [o for s in strings_in(json.loads(raw)) for o in offences(s)]
        self.assertEqual(found, ["em dash"])

    def test_it_walks_keys_nested_objects_and_lists(self):
        payload = {
            "entries": [{"cues": ["a — b"]}],
            "note – key": "clean",
        }
        found = sorted({o for s in strings_in(payload) for o in offences(s)})
        self.assertEqual(found, ["em dash", "en dash"])


class TheSourceScannerSeesInsideFStrings(unittest.TestCase):
    """The third trap. Measured on Python 3.14.7 while this was written:
    the tokenizer returned no ``token.STRING`` at all for the sample below,
    while the syntax tree returned both literal parts of it.
    """

    def _scan(self, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text(source, encoding="utf-8")
            return [value for _, value in string_constants(path)]

    def test_a_dash_inside_an_f_string_is_seen(self):
        values = self._scan('name = "x"\nline = f"open — {name}"\n')
        self.assertTrue(any(offences(value) for value in values))

    def test_a_dash_in_an_ordinary_string_is_seen(self):
        values = self._scan('LABEL = "open — closed"\n')
        self.assertIn("open — closed", values)

    def test_a_docstring_is_not_scanned(self):
        values = self._scan('"""Module — doc."""\n\n\ndef f():\n    """Doc — here."""\n')
        self.assertEqual([value for value in values if offences(value)], [])

    def test_a_string_that_merely_follows_a_docstring_is_still_scanned(self):
        values = self._scan('"""Doc."""\n\nLABEL = "open — closed"\n')
        self.assertIn("open — closed", values)


class TheMarkdownReport(unittest.TestCase):
    def test_no_dash_in_a_report_with_open_and_closed_entries(self):
        self.assertEqual(offences(report_module.render_markdown(sample_entries())), [])

    def test_no_dash_in_an_empty_report(self):
        self.assertEqual(offences(report_module.render_markdown([])), [])

    def test_no_dash_in_the_limitations_paragraph(self):
        self.assertEqual(offences(report_module.LIMITATIONS), [])

    def test_the_report_really_did_contain_every_branch(self):
        rendered = report_module.render_markdown(sample_entries())
        for expected in ("## Open", "### Alex (1)", "No owner stated", "## Closed", "## Limitations"):
            self.assertIn(expected, rendered)


class TheHtmlReport(unittest.TestCase):
    def test_no_dash_in_a_report_with_open_and_closed_entries(self):
        self.assertEqual(offences(report_module.render_html(sample_entries())), [])

    def test_no_dash_in_an_empty_report(self):
        self.assertEqual(offences(report_module.render_html([])), [])

    def test_the_report_really_did_contain_every_branch(self):
        rendered = report_module.render_html(sample_entries())
        for expected in ("<h2>Open</h2>", "<h3>Alex (1)</h3>", "No owner stated", "<h2>Closed", "<h2>Limitations</h2>"):
            self.assertIn(expected, rendered)


class TheFilesWrittenToDisk(unittest.TestCase):
    """The README documents that ``report`` writes Markdown and HTML to a
    directory. The files are read back from that directory rather than the
    return value of the renderer, because a file is what a reader opens."""

    def test_neither_written_report_contains_a_dash(self):
        with tempfile.TemporaryDirectory() as directory:
            markdown_path, html_path = report_module.write(
                Path(directory) / "reports", sample_entries()
            )
            for path in (markdown_path, html_path):
                with self.subTest(path=path.name):
                    self.assertTrue(path.exists())
                    self.assertEqual(offences(text_of(path)), [])

    def test_the_ledger_json_contains_no_dash_as_written_or_as_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = ledger_module.save(Path(directory) / "ledger", sample_entries())
            raw = text_of(path)
            self.assertEqual(offences(raw), [])
            decoded = [o for s in strings_in(json.loads(raw)) for o in offences(s)]
            self.assertEqual(decoded, [])


class TheCommandLineOutput(unittest.TestCase):
    """Every command the README documents, run for real, both streams read."""

    def setUp(self):
        root = working_directory(self)
        self.reports_dir = Path("reports")
        self.transcript = Path("sample.txt")
        (root / self.transcript).write_text(
            "Alex: I will send the signed lease to finance by Friday.\n"
            "Sam: Please confirm the headcount with HR.\n"
            "Sam: I will pull the carrier rates by October 3.\n",
            encoding="utf-8",
        )
        self.empty = Path("empty.txt")
        (root / self.empty).write_text("Good morning everybody.\n", encoding="utf-8")

    def _run(self, *argv: str) -> tuple[str, str]:
        return run_cli(
            "--ledger-dir", "ledger",
            "--reports-dir", str(self.reports_dir),
            *argv,
        )

    def _assert_clean(self, streams: tuple[str, str], *, expect_output: bool = True) -> None:
        out, err = streams
        if expect_output:
            self.assertTrue(out.strip() or err.strip(), "the command printed nothing")
        self.assertEqual(offences(out), [], f"standard output: {out!r}")
        self.assertEqual(offences(err), [], f"standard error: {err!r}")

    def test_extract(self):
        self._assert_clean(self._run("extract", str(self.transcript)))

    def test_extract_when_it_finds_nothing(self):
        out, err = self._run("extract", str(self.empty))
        self.assertIn("No commitment-shaped statements found.", out)
        self._assert_clean((out, err))

    def test_track(self):
        self._assert_clean(self._run("track", str(self.transcript)))

    def test_list_in_each_state(self):
        self._run("track", str(self.transcript))
        for state in ("open", "closed", "all"):
            with self.subTest(state=state):
                self._assert_clean(self._run("list", "--state", state))

    def test_list_when_the_ledger_is_empty(self):
        for state in ("open", "closed", "all"):
            with self.subTest(state=state):
                self._assert_clean(self._run("list", "--state", state))

    def test_close_and_then_report(self):
        out, _ = self._run("track", str(self.transcript))
        identity = out.split()[0]
        self._assert_clean(self._run("close", identity, "--note", "lease filed"))
        self._assert_clean(self._run("report"))
        for name in ("follow-through.md", "follow-through.html"):
            with self.subTest(name=name):
                self.assertEqual(offences(text_of(self.reports_dir / name)), [])

    def test_the_version_banner(self):
        out, err = run_cli("--version")
        self.assertIn(follow_through.__version__, out + err)
        self._assert_clean((out, err))


class TheHelpText(unittest.TestCase):
    """Help is the first output most people see, and argparse never gets read
    as prose by anybody writing it, so it drifts unwatched."""

    def test_the_main_help(self):
        out, err = run_cli("--help")
        self.assertIn("follow-through", out)
        self.assertEqual(offences(out), [], out)
        self.assertEqual(offences(err), [], err)

    def test_the_help_of_every_command(self):
        for command in ("extract", "track", "list", "close", "report"):
            with self.subTest(command=command):
                out, err = run_cli(command, "--help")
                self.assertTrue(out.strip())
                self.assertEqual(offences(out), [], out)
                self.assertEqual(offences(err), [], err)


class TheErrorMessages(unittest.TestCase):
    """The messages a person sees on the worst day of using the tool."""

    def setUp(self):
        self.root = working_directory(self)
        self.ledger_dir = Path("ledger")

    def _run(self, *argv: str) -> tuple[str, str]:
        return run_cli("--ledger-dir", str(self.ledger_dir), *argv)

    def _assert_clean(self, streams: tuple[str, str]) -> None:
        out, err = streams
        self.assertTrue(err.strip(), "expected a message on standard error")
        self.assertEqual(offences(out), [], out)
        self.assertEqual(offences(err), [], err)

    def test_a_missing_file(self):
        self._assert_clean(self._run("extract", "absent.txt"))

    def test_a_directory_given_where_a_file_belongs(self):
        Path("a_folder").mkdir()
        self._assert_clean(self._run("extract", "a_folder"))

    def test_a_ledger_that_is_not_json(self):
        self.ledger_dir.mkdir(parents=True)
        ledger_module.ledger_path(self.ledger_dir).write_text("{oh no", encoding="utf-8")
        self._assert_clean(self._run("list"))

    def test_a_ledger_from_a_future_version(self):
        self.ledger_dir.mkdir(parents=True)
        ledger_module.ledger_path(self.ledger_dir).write_text(
            json.dumps({"version": 99, "entries": []}), encoding="utf-8"
        )
        self._assert_clean(self._run("list"))

    def test_a_file_that_is_not_a_ledger_at_all(self):
        self.ledger_dir.mkdir(parents=True)
        ledger_module.ledger_path(self.ledger_dir).write_text("[]", encoding="utf-8")
        self._assert_clean(self._run("list"))

    def test_an_id_that_matches_nothing(self):
        ledger_module.save(self.ledger_dir, sample_entries())
        self._assert_clean(self._run("close", "zzzz", "--note", "done"))

    def test_an_id_that_is_ambiguous(self):
        entries = sample_entries()
        entries[0].id = "abcd1"
        entries[1].id = "abcd2"
        ledger_module.save(self.ledger_dir, entries)
        self._assert_clean(self._run("close", "abcd", "--note", "done"))

    def test_an_entry_that_is_already_closed(self):
        ledger_module.save(self.ledger_dir, sample_entries())
        self._assert_clean(self._run("close", "cccc", "--note", "done"))

    def test_a_closing_note_that_is_only_whitespace(self):
        ledger_module.save(self.ledger_dir, sample_entries())
        self._assert_clean(self._run("close", "aaaa", "--note", "   "))

    def test_a_ledger_entry_in_a_state_the_tool_does_not_know(self):
        entries = sample_entries()
        entries[0].state = "pending"
        ledger_module.save(self.ledger_dir, entries)
        self._assert_clean(self._run("list"))

    def test_a_closed_entry_with_no_reason(self):
        entries = sample_entries()
        entries[2].note = ""
        ledger_module.save(self.ledger_dir, entries)
        self._assert_clean(self._run("list"))


class EveryStringInTheSource(unittest.TestCase):
    """A string constant that no test happens to render is still shipped.

    The renderers above are exercised with a fixture that reaches every branch,
    but a message on a path nothing here triggers would go unseen. This reads
    the package source instead, so a dash cannot arrive in a template that is
    only printed on somebody else's Tuesday.
    """

    def test_the_package_has_modules_to_scan(self):
        self.assertGreaterEqual(len(sorted(PACKAGE.rglob("*.py"))), 7)

    def test_no_string_constant_in_the_package_contains_a_dash(self):
        for path in sorted(PACKAGE.rglob("*.py")):
            for line, value in string_constants(path):
                found = offences(value)
                with self.subTest(module=path.name, line=line):
                    self.assertEqual(
                        found,
                        [],
                        f"{path.name} line {line} has a {', '.join(found)} in a "
                        f"string the tool can print: {value!r}",
                    )


class TheDocumentsBesideTheCode(unittest.TestCase):
    """The README, the secondary documents, and the example reports.

    The example reports are output: the install job in CI compares them against
    what the tool actually produces. The rest is prose published under an author
    name, and the same rule covers it. The corpus under ``docs/corpus`` is
    deliberately not here. Those files are real meeting records that were not
    written for this repository, and a dash in one of them is evidence.
    """

    def _documents(self) -> list[Path]:
        found = sorted(ROOT.glob("*.md"))
        found += sorted((ROOT / "docs").glob("*.md"))
        found += sorted((ROOT / "examples").glob("*.md"))
        return found

    def test_there_are_documents_to_check(self):
        names = {path.name for path in self._documents()}
        self.assertIn("README.md", names)
        self.assertIn("expected-report.md", names)

    def test_no_document_contains_a_dash(self):
        for path in self._documents():
            with self.subTest(document=path.name):
                found = offences(text_of(path))
                self.assertEqual(found, [], f"{path.name} has a {', '.join(found)}")


if __name__ == "__main__":
    unittest.main()
