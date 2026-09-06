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

#: ``Alex:`` or ``[00:14] Sam Okafor:`` at the start of a line.
#:
#: The name is captured loosely and checked in :func:`read_speaker`. Requiring
#: an ASCII capital here would silently drop every speaker whose name does not
#: start with one.
SPEAKER_LABEL = re.compile(
    r"""^\s*
        (?:[\[(]?\d{1,2}:\d{2}(?::\d{2})?[\])]?\s*)?   # optional timestamp
        (?P<name>[^\W\d_][\w'’-]*(?:\s+[^\W\d_][\w'’-]*){0,2})
        \s*:\s
    """,
    re.VERBOSE,
)

#: Labels that look like speakers but are document structure, not people.
#:
#: This list can never be complete, which is why it is not the only defence: a
#: label is also rejected unless every word in it is capitalised and none of the
#: words is an ordinary English word from :data:`follow_through.cues.NON_NAME_WORDS`.
#: Without both checks, ``From:`` and ``TODO:`` become people.
NON_SPEAKER_LABELS = frozenset(
    {
        "a", "absent", "action", "action item", "action items", "actions", "agenda",
        "apologies", "ask", "asks", "attendees", "background", "bcc", "cc",
        "chair", "context", "date", "deadline", "decision", "decisions",
        "follow up", "follow-up", "from", "item", "items", "location",
        "minutes", "next", "next step", "next steps", "note", "notes",
        "blocker", "blockers", "followup", "homework", "objective", "outcome",
        "owner", "participants", "present", "purpose", "recap", "warning",
        "questions", "re", "recording", "reminder", "risks", "sent", "status",
        "answer", "attendance", "budget", "closing", "comments", "conclusion",
        "discussion", "issue", "opening", "problem", "q", "question",
        "resolution", "risk", "scope", "solution", "subject", "summary",
        "time", "timeline", "to", "todo", "to do", "topic", "transcript",
        "update", "venue",
    }
)

#: Titles and short forms whose full stop does not end a sentence. Without this,
#: "Dr. Smith will send it" splits in two and records an owner called "Smith"
#: against a quote the reader cannot find in the file.
ABBREVIATIONS = (
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "mt", "vs", "etc",
    "eg", "ie", "approx", "dept", "inc", "ltd",
)
# "no." is deliberately absent. As an abbreviation for "number" it is rare in
# speech; as an answer it ends sentences constantly, and treating it as an
# abbreviation joined "the answer is no." to the commitment that followed and
# swallowed both.

#: Sentence boundary: terminal punctuation followed by whitespace or end of line.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

#: A fragment ending like this did not really end a sentence: an abbreviation
#: from the list above, or a single initial as in "J. Okafor".
FALSE_ENDING = re.compile(
    r"(?:\b(?:" + "|".join(ABBREVIATIONS) + r")|\b[^\W\d_])\.$",
    re.IGNORECASE,
)


def split_sentences(text: str) -> list[str]:
    """Split a line into sentences, dropping empties.

    A fragment that ends in an abbreviation or an initial is joined back to the
    one after it. Otherwise "Dr. Smith will send it" becomes two sentences, and
    the commitment is recorded against a quote that does not appear in the file.
    """
    parts = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]
    joined: list[str] = []
    for part in parts:
        if joined and FALSE_ENDING.search(joined[-1]):
            joined[-1] = f"{joined[-1]} {part}"
        else:
            joined.append(part)
    return joined


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
    if name.lower() in NON_SPEAKER_LABELS or not looks_like_a_name(
        name, allow=cues.NAMES_ALLOWED_AS_SPEAKERS
    ):
        return "", True, remainder
    return name, False, remainder


def looks_like_a_name(phrase: str, allow: frozenset[str] = frozenset()) -> bool:
    """True when every word in ``phrase`` could be part of a person's name.

    Each word must start with an uppercase letter and must not be an ordinary
    English word. This is what keeps ``The team will ship`` from producing an
    owner called "The team", and ``From: alex@example.com`` from producing one
    called "From". It is a filter, not a name detector: it can only reject.
    """
    words = phrase.split()
    if not words:
        return False
    for word in words:
        stripped = word.strip("'\u2019-")
        if not stripped or not stripped[0].isupper():
            return False
        lowered = stripped.lower()
        if lowered in cues.NON_NAME_WORDS and lowered not in allow:
            return False
    return True


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


#: A phrase that sets a deadline rather than merely mentioning a time. "by
#: Friday" commits; "today" appears in "can you hear me today?" and commits
#: nothing.
DEADLINE_SHAPED = re.compile(
    r"^(?:by|before|within|in \d|end of|eod)\b", re.IGNORECASE
)


def sets_a_deadline(phrase: str) -> bool:
    """True when a due phrase actually sets a deadline."""
    return phrase != UNKNOWN and bool(DEADLINE_SHAPED.match(phrase))


def is_excluded(sentence: str) -> bool:
    """True when the sentence should not be recorded as a commitment.

    Two rules, not one. A hypothetical, a negation, or something already done is
    rejected outright. Conversational filler is rejected only when the sentence
    states no deadline: "let me know if you have questions" is noise, while
    "let me know the vendor's answer by Friday" is a real ask wearing the same
    opening. A stated deadline is the strongest evidence one sentence can carry
    that something was meant, so it overrules the filler list.
    """
    if any(pattern.search(sentence) for pattern in cues.EXCLUSION_RE):
        return True
    if sets_a_deadline(find_due_phrase(sentence)):
        return False
    return any(pattern.search(sentence) for pattern in cues.FILLER_RE)


def named_owner(sentence: str) -> str:
    """Return the name in an ``X will ...`` construction, or ``unknown``.

    The regular expression captures up to three words before the verb. The
    longest run of those words that still looks like a name wins, so
    ``Zhang Wei will pull the rates`` yields "Zhang Wei" while
    ``I think Priya will send it`` yields "Priya" rather than "I think Priya".
    ``We will ship on Monday`` and ``There will be a delay`` yield nothing.
    """
    for match in cues.NAMED_ASSIGNMENT_RE.finditer(sentence):
        words = match.group(1).split()
        for start in range(len(words)):
            candidate = " ".join(words[start:])
            if looks_like_a_name(candidate):
                return candidate
    return UNKNOWN


def classify(sentence: str, speaker: str) -> tuple[tuple[str, ...], str]:
    """Return the cue families that fired and the resolved owner.

    Returns an empty cue tuple when the sentence is not a candidate.

    Owner resolution is deliberately reluctant:

    * A first-person undertaking belongs to the current speaker, when the
      transcript labels one.
    * A named assignment belongs to the person named.
    * A collective undertaking ("we'll decide on Friday") belongs to nobody in
      particular. Recording it against whoever happened to say "we" would be an
      invention, so the owner stays unknown.
    * An open ask ("can you confirm?") does not say who was addressed, so the
      owner stays unknown.
    * When two of these fire in the same sentence the owner is genuinely
      unclear, and unclear is recorded as unknown.
    """
    if is_excluded(sentence):
        return (), UNKNOWN

    first_person = any(p.search(sentence) for p in cues.FIRST_PERSON_RE)
    collective = any(p.search(sentence) for p in cues.COLLECTIVE_RE)
    named = named_owner(sentence)
    open_ask = any(p.search(sentence) for p in cues.ASSIGNMENT_RE)

    fired: list[str] = []
    if first_person:
        fired.append(cues.FIRST_PERSON)
    if collective:
        fired.append(cues.COLLECTIVE)
    if named != UNKNOWN or open_ask:
        fired.append(cues.ASSIGNMENT)

    if not fired:
        return (), UNKNOWN

    claimants = [
        source
        for source in (
            speaker if first_person else "",
            named if named != UNKNOWN else "",
        )
        if source
    ]
    if collective or open_ask or len(claimants) != 1:
        owner = UNKNOWN
    else:
        owner = claimants[0]

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

    Reports are meant to be shareable, so the path is shortened as far as it can
    be without losing which file it was: relative to the working directory when
    the file is below it, otherwise written with ``~`` for the home directory.
    Only a path outside both is recorded in full, and then there is nothing left
    to hide.

    A username is not a secret, but it does not belong in a document handed to
    somebody outside the company either.
    """
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        pass
    try:
        return str(Path("~") / resolved.relative_to(Path.home().resolve()))
    except ValueError:
        return str(resolved)


def extract_file(path: Path) -> list[Candidate]:
    """Find every candidate commitment in a file.

    Raises ``FileNotFoundError`` if the path does not exist, and ``IsADirectoryError``
    if it is a directory. Undecodable bytes are replaced rather than crashing, so a
    stray encoding never loses a whole transcript.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    return extract_text(text, source_label(path))
