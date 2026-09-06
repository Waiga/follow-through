"""Command line interface.

Global options precede the command:

    follow-through --ledger-dir ./ledger track meeting.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, report as report_module
from .extract import extract_file
from .ledger import CLOSED, LedgerError, OPEN, close, load, merge, save
from .models import UNKNOWN, Candidate, Entry

DEFAULT_LEDGER_DIR = Path(".follow-through")
DEFAULT_REPORTS_DIR = Path("reports")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="follow-through",
        description=(
            "Find commitment-shaped statements in a transcript and track each "
            "one until it is closed. Runs entirely on this machine."
        ),
    )
    parser.add_argument("--version", action="version", version=f"follow-through {__version__}")
    parser.add_argument(
        "--ledger-dir",
        type=Path,
        default=DEFAULT_LEDGER_DIR,
        help=f"where the ledger is kept (default: {DEFAULT_LEDGER_DIR})",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help=f"where reports are written (default: {DEFAULT_REPORTS_DIR})",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    extract = commands.add_parser(
        "extract", help="show candidate commitments in a file without recording them"
    )
    extract.add_argument("file", type=Path)

    track = commands.add_parser(
        "track", help="add newly found commitments in a file to the ledger"
    )
    track.add_argument("file", type=Path)

    listing = commands.add_parser("list", help="show ledger entries")
    listing.add_argument(
        "--state",
        choices=(OPEN, CLOSED, "all"),
        default=OPEN,
        help="which entries to show (default: open)",
    )

    closing = commands.add_parser("close", help="record that an entry is closed")
    closing.add_argument("id", help="full id, or an unambiguous prefix")
    closing.add_argument("--note", required=True, help="why it is closed")

    commands.add_parser("report", help="write a Markdown and HTML report")

    return parser


def _describe(item: Candidate | Entry) -> str:
    identity = item.identity if isinstance(item, Candidate) else item.id
    owner = item.owner if item.owner != UNKNOWN else "owner not stated"
    due = item.due_phrase if item.due_phrase != UNKNOWN else "no stated deadline"
    return f"{identity}  {owner:<20}  {due:<20}  {item.text}"


def command_extract(args: argparse.Namespace) -> int:
    candidates = extract_file(args.file)
    if not candidates:
        print("No commitment-shaped statements found.")
        print(f"Read {args.file}. This does not prove the file contains none.")
        return 0
    for candidate in candidates:
        print(_describe(candidate))
    print(f"\n{len(candidates)} candidate(s). Nothing was recorded; use track to keep them.")
    return 0


def command_track(args: argparse.Namespace) -> int:
    candidates = extract_file(args.file)
    entries = load(args.ledger_dir)
    entries, added = merge(entries, candidates)
    path = save(args.ledger_dir, entries)
    for entry in added:
        print(_describe(entry))
    print(
        f"\n{len(added)} new, {len(candidates) - len(added)} already known. "
        f"Ledger: {path}"
    )
    return 0


def command_list(args: argparse.Namespace) -> int:
    entries = load(args.ledger_dir)
    if args.state != "all":
        entries = [entry for entry in entries if entry.state == args.state]
    if not entries:
        print(f"Nothing {args.state}." if args.state != "all" else "The ledger is empty.")
        return 0
    for entry in entries:
        print(_describe(entry))
    print(f"\n{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")
    return 0


def command_close(args: argparse.Namespace) -> int:
    entries = load(args.ledger_dir)
    entry = close(entries, args.id, args.note)
    save(args.ledger_dir, entries)
    print(f"Closed {entry.id}: {entry.text}")
    print(f"Reason: {entry.note}")
    return 0


def command_report(args: argparse.Namespace) -> int:
    entries = load(args.ledger_dir)
    markdown_path, html_path = report_module.write(args.reports_dir, entries)
    print(f"Wrote {markdown_path}")
    print(f"Wrote {html_path}")
    return 0


COMMANDS = {
    "extract": command_extract,
    "track": command_track,
    "list": command_list,
    "close": command_close,
    "report": command_report,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except FileNotFoundError as exc:
        print(f"No such file: {exc.filename}", file=sys.stderr)
        return 1
    except IsADirectoryError as exc:
        print(f"That is a directory, not a file: {exc.filename}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"Not allowed to read or write {exc.filename}", file=sys.stderr)
        return 1
    except LedgerError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
