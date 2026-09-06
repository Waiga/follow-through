"""The local ledger: a single JSON file holding one record per commitment.

The ledger is the only state Follow Through keeps. It lives on disk, next to the
person using it, and is never transmitted anywhere.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import Candidate, Entry

LEDGER_VERSION = 1
LEDGER_FILENAME = "ledger.json"

OPEN = "open"
CLOSED = "closed"
STATES = (OPEN, CLOSED)


class LedgerError(Exception):
    """Raised when the ledger cannot be read, or an id does not resolve."""


def ledger_path(ledger_dir: Path) -> Path:
    return ledger_dir / LEDGER_FILENAME


def load(ledger_dir: Path) -> list[Entry]:
    """Read the ledger. A missing ledger is an empty one, not an error."""
    path = ledger_path(ledger_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or "entries" not in raw:
        raise LedgerError(f"{path} is not a Follow Through ledger")
    try:
        return [Entry.from_dict(item) for item in raw["entries"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise LedgerError(f"{path} contains a malformed entry: {exc}") from exc


def save(ledger_dir: Path, entries: list[Entry]) -> Path:
    """Write the ledger atomically, so an interrupted write cannot corrupt it."""
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_path(ledger_dir)
    payload = {
        "version": LEDGER_VERSION,
        "entries": [entry.to_dict() for entry in entries],
    }
    handle, temporary = tempfile.mkstemp(dir=str(ledger_dir), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return path


def merge(entries: list[Entry], candidates: list[Candidate]) -> tuple[list[Entry], list[Entry]]:
    """Add candidates that are not already in the ledger.

    Returns ``(all_entries, newly_added)``. An entry already present is left
    exactly as it is, including its state and closing note, so re-running over a
    growing transcript never reopens settled work.
    """
    known = {entry.id for entry in entries}
    added: list[Entry] = []
    for candidate in candidates:
        if candidate.identity in known:
            continue
        entry = Entry.from_candidate(candidate)
        entries.append(entry)
        known.add(entry.id)
        added.append(entry)
    return entries, added


def resolve(entries: list[Entry], wanted: str) -> Entry:
    """Find one entry by full id or by an unambiguous id prefix."""
    if not wanted:
        raise LedgerError("no id given")
    matches = [entry for entry in entries if entry.id.startswith(wanted)]
    if not matches:
        raise LedgerError(f"no entry matches id {wanted!r}")
    if len(matches) > 1:
        ids = ", ".join(entry.id for entry in matches)
        raise LedgerError(f"id {wanted!r} is ambiguous; it matches {ids}")
    return matches[0]


def close(entries: list[Entry], wanted: str, note: str) -> Entry:
    """Record that an entry is closed, and why.

    A closing note is required. Closure is a human judgement, and the reason is
    the only evidence that the judgement was made.
    """
    if not note.strip():
        raise LedgerError("a closing note is required")
    entry = resolve(entries, wanted)
    if entry.state == CLOSED:
        raise LedgerError(f"entry {entry.id} is already closed: {entry.note}")
    entry.state = CLOSED
    entry.note = note.strip()
    return entry
