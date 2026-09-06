"""Find commitment-shaped statements in a text file.

The extractor is deliberately simple and deterministic. It reads lines, tracks
which speaker is talking, splits each line into sentences, and tests every
sentence against the cue tables in :mod:`follow_through.cues`.

Nothing here infers. When the text does not say who owns a commitment or when it
is due, the answer recorded is ``unknown``.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import cues
from .models import UNKNOWN, Candidate

#: ``Waiga:`` or ``[00:14] Waiga Arya:`` at the start of a line. Each word of the
#: label must be capitalised, so prose rarely matches by accident.
SPEAKER_LABEL = re.compile(
    r"""^\s*
        (?:[\[(]?\d{1,2}:\d{2}(?::\d{2})?[\])]?\s*)?   # optional timestamp
        (?P<name>[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*){0,2})
        \s*:\s
    """,
    re.VERBOSE,
)

#: Labels that look like speakers but are document structure, not people.
NON_SPEAKER_LABELS = frozenset(
    {
        "action",
        "actions",
        "agenda",
        "attendees",
        "date",
        "decision",
        "decisions",
        "next",
        "note",
        "notes",
        "present",
        "subject",
        "summary",
        "time",
        "topic",
        "transcript",
    }
)

#: Sentence boundary: terminal punctuation followed by whitespace or end of line.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split a line into sentences, dropping empties."""
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]


def read_speaker(line: str) -> tuple[str, bool, str]:
    """Return ``(speaker, is_structural, remainder)`` for a line.

    ``speaker`` is an empty string when the line carries no speaker label.
    ``is_structural`` is true when the line opens with a document label such as
    ``Notes:`` or ``Action:``. Those are not people, and they end the previous
    speaker's turn: attributing the text that follows to whoever spoke last
    would be a guess.

    ``remainder`` is the line with any recognised label removed, so a quoted
    commitment reads as the sentence itself. The label is not lost: the speaker
    becomes the owner, and the line number points back at the source.
    """
    match = SPEAKER_LABEL.match(line)
    if not match:
        return "", False, line
    name = match.group("name").strip()
    remainder = line[match.end() :]
    if name.lower() in NON_SPEAKER_LABELS:
        return "", True, remainder
    return name, False, remainder


def find_due_phrase(sentence: str) -> str:
    """Return the timing phrase in a sentence verbatim, or ``unknown``.

    The earliest match wins, so ``by Friday`` is preferred over a later
    ``next week`` in the same sentence.
    """
    best: tuple[int, str] | None = None
    for pattern in cues.DUE_RE:
        match = pattern.search(sentence)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), match.group(0))
    return best[1] if best else UNKNOWN


def is_excluded(sentence: str) -> bool:
    """True when the sentence is hypothetical, negated, or already past."""
    return any(pattern.search(sentence) for pattern in cues.EXCLUSION_RE)


def named_owner(sentence: str) -> str:
    """Return the name in an ``X will ...`` construction, or ``unknown``.

    A capitalised word is only treated as a name when it is not a pronoun or
    other ordinary sentence opener. ``We will ship on Monday`` names nobody.
    """
    for pattern in cues.NAMED_ASSIGNMENT_RE:
        match = pattern.search(sentence)
        if match and match.group(1).lower() not in cues.NON_NAME_WORDS:
            return match.group(1)
    return UNKNOWN


def classify(sentence: str, speaker: str) -> tuple[tuple[str, ...], str]:
    """Return the cue families that fired and the resolved owner.

    Returns an empty cue tuple when the sentence is not a candidate.

    Owner resolution is conservative. A first-person undertaking belongs to the
    current speaker, if the transcript labels one. A named assignment belongs to
    the person named. When both fire in the same sentence the owner is genuinely
    ambiguous, so it is recorded as ``unknown`` rather than guessed.
    """
    if is_excluded(sentence):
        return (), UNKNOWN

    fired: list[str] = []
    owner = UNKNOWN

    first_person = any(p.search(sentence) for p in cues.FIRST_PERSON_RE)
    named = named_owner(sentence)
    assignment = any(p.search(sentence) for p in cues.ASSIGNMENT_RE)

    if first_person:
        fired.append(cues.FIRST_PERSON)
        owner = speaker or UNKNOWN
    if named != UNKNOWN:
        fired.append(cues.ASSIGNMENT)
        owner = UNKNOWN if first_person else named
    elif assignment:
        fired.append(cues.ASSIGNMENT)
        # The addressed party is not stated in the text, so it stays unknown.
        if not first_person:
            owner = UNKNOWN

    if not fired:
        return (), UNKNOWN

    if find_due_phrase(sentence) != UNKNOWN:
        fired.append(cues.DUE_PHRASE)

    return tuple(dict.fromkeys(fired)), owner


def extract_text(text: str, source: str) -> list[Candidate]:
    """Find every candidate commitment in ``text``."""
    found: list[Candidate] = []
    speaker = ""
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        label, structural, remainder = read_speaker(line)
        if label:
            speaker = label
        elif structural:
            speaker = ""
        for sentence in split_sentences(remainder):
            fired, owner = classify(sentence, speaker)
            if not fired:
                continue
            found.append(
                Candidate(
                    text=sentence,
                    owner=owner,
                    due_phrase=find_due_phrase(sentence),
                    cues=fired,
                    source=source,
                    line=number,
                )
            )
    return found


def source_label(path: Path) -> str:
    """How a file is named in the ledger and in reports.

    A path inside the current directory is recorded relative to it. Reports are
    meant to be shareable, and an absolute path would carry the shape of
    someone's home directory into a document they hand to a colleague.
    """
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def extract_file(path: Path) -> list[Candidate]:
    """Find every candidate commitment in a file.

    Raises ``FileNotFoundError`` if the path does not exist, and ``IsADirectoryError``
    if it is a directory. Undecodable bytes are replaced rather than crashing, so a
    stray encoding never loses a whole transcript.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    return extract_text(text, source_label(path))
