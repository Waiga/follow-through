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

#: ``Alex:``, ``[00:14] Sam Okafor:``, ``Ted Hardie (Google):`` or
#: ``Suresh Krishnan, Kaloom:`` at the start of a line.
#:
#: The name is captured loosely and checked in :func:`read_speaker`. Requiring
#: an ASCII capital here would silently drop every speaker whose name does not
#: start with one.
#:
#: The affiliation group is the fix for 737 lines of real minutes whose speaker
#: was invisible: transcripts write "Tony Li (TL):" and "Suresh Krishnan,
#: Kaloom:" far more often than they write a bare name, and without this the
#: line matched nothing, kept its label inside the quoted text, and was recorded
#: against whoever spoke last.
SPEAKER_LABEL = re.compile(
    r"""^\s*
        (?:[\[(]?\d{1,2}:\d{2}(?::\d{2})?[\])]?\s*)?   # optional timestamp
        (?P<name>[^\W\d_][\w'’.-]*(?:\s+[^\W\d_][\w'’.-]*){0,2}(?:\s+\d{1,3})?)
        (?P<affiliation>
            \s*\([^)\n]{1,60}\)                        # (Google), (SG)
          | \s*,\s*[^\W\d_][\w'’.&/-]*(?:\s+[^\W\d_][\w'’.&/-]*){0,3}
        )?
        \s*:(?:\s|$)
    """,
    re.VERBOSE,
)

#: ``<mnot> ...`` and ``<unknown>: ...``, the shape a jabber or IRC log takes.
IRC_LABEL = re.compile(r"^\s*<\s*(?P<name>[^\W\d_][\w'’.-]*)\s*>\s*:?\s*")

#: A nickname used as a speaker label: ``ekr:``, ``greg:``, ``mnot:``.
#:
#: A lowercase label used to be read as document structure, which lost the owner
#: and also ended the previous speaker's turn: 1,257 occurrences on the corpus.
#: The length bound and the ordinary-word check are what stop "important:" and
#: "however:" from becoming people.
NICKNAME = re.compile(r"^[a-z][a-z0-9_.-]{1,7}$")

#: Words that take a number and are still a speaker: "Speaker 1", "Caller 2".
#:
#: An allowlist, because the numeric suffix was added for exactly these and it
#: also matched "Slide 3:", "Phase 1:" and "Option 2:" — which then became the
#: recorded owner of every commitment in the paragraph beneath them.
NUMBERED_SPEAKERS = frozenset(
    {
        "agent", "attendee", "caller", "guest", "host", "interviewer",
        "participant", "person", "speaker", "unknown", "user", "voice",
    }
)

#: Labels that look like speakers but are document structure, not people.
#:
#: This list can never be complete, which is why it is not the only defence: a
#: label is also rejected when it is alone on its line, when everything after it
#: is a list of names or an address rather than speech, and unless every word in
#: it is capitalised and none of the words is an ordinary English word from
#: :data:`follow_through.cues.NON_NAME_WORDS`. Without those checks, ``From:``
#: and ``TODO:`` become people.
#:
#: Membership is tested with a trailing "s" removed as well as intact, so
#: ``Chairs:`` is caught by ``chair``. That plural was 743 fabricated owners on
#: the corpus, and listing every plural by hand is how the list stays wrong.
NON_SPEAKER_LABELS = frozenset(
    {
        "a", "absent", "action", "action item", "action items", "actions", "agenda",
        "agenda bashing", "apologies", "ask", "asks", "attendees", "background",
        "bcc", "cc", "chair", "context", "date", "deadline", "decision", "decisions",
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
        # Labels a meeting record uses that a business call does not. Every one
        # of these was read as a person on the corpus.
        "administrivia", "admin", "agenda item", "ai", "attending", "audio",
        "blue sheets", "chat", "charter", "document", "documents", "draft",
        "drafts", "etherpad", "intro", "introduction", "irc", "jabber",
        "link", "links", "logistics", "materials", "meeting", "meetecho",
        "milestone", "milestones", "minute taker", "note taker", "note-taker",
        "notetaker", "ok", "presenter", "presenters", "roll call", "room",
        "scribe", "secretary", "see", "session", "slide", "slides",
        "slot", "speaker", "url", "urls", "video", "webex", "welcome", "wg",
        "working group", "wrap up", "wrap-up", "wrapup",
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

#: Line endings, spelled out rather than left to ``str.splitlines``.
#:
#: ``splitlines`` also breaks on a form feed, a vertical tab and U+2028. Real
#: minutes from the 2000s carry form feeds as page breaks — 31 documents in a
#: corpus of 1,067 — and every line number after one of them was reported one
#: too high, which quietly breaks the promise that a reader can check the quote
#: against the source.
LINE_BREAK = re.compile(r"\r\n|\r|\n")

#: Page breaks and other stray control characters, removed from the text of a
#: line rather than allowed to split it.
CONTROL = re.compile(r"[\x0b\x0c\x1c-\x1f]")

#: A line that starts a new item rather than continuing the one above it.
LIST_MARKER = re.compile(r"^\s*(?:[-*o•·+>#|]\s|\d+[.)]\s|\(\d+\)\s|\[\d+\]\s)")

#: How long a line has to be before its lack of a full stop reads as a wrap
#: rather than as the end of a short note. Transcripts are wrapped at 70 to 80
#: columns; agenda fragments are shorter than that.
WRAP_WIDTH = 40

#: How a wrap column is measured. The percentile is the ceiling of the text
#: rather than of the file, so one long table row cannot move it; the bounds are
#: the range human-wrapped text actually occupies; the band is how far below the
#: ceiling a line still counts as full; and a document shorter than the minimum
#: is not measured at all.
CEILING = 0.95
NARROWEST_WRAP = 40
WIDEST_WRAP = 100
BAND = 10
#: Below this, the percentile cannot exclude anything: at twelve lines the 95th
#: is the longest line, which is the statistic this replaced. A file needs a
#: tail of at least two lines above the ceiling for the ceiling to mean
#: anything, and 5% of forty is two.
MINIMUM_LINES = 40

#: An address or a link, removed before a label's remainder is judged.
EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
URL = re.compile(r"\b(?:https?://|ftp://|www\.)\S+")


class Document:
    """What the rest of a document says about the sentence being read.

    One thing so far: which words this document also writes in lower case.

    A capitalised word at the start of a sentence carries no information — the
    capital is the sentence, not the word. When the same document writes that
    word in lower case somewhere else, the capital was punctuation and the word
    is an ordinary one: "Due to visa rules ..." in a document that elsewhere
    says "due to". A name gets no such contradiction, because a name is
    capitalised wherever it appears.

    This is the only test available here that separates "Due to" from "Mark to"
    without a list of English prepositions, and a list is what a stop-list is.
    """

    __slots__ = ("lowercased",)

    def __init__(self, lowercased: frozenset[str]) -> None:
        self.lowercased = lowercased

    @classmethod
    def read(cls, text: str) -> "Document":
        return cls(
            frozenset(
                word.group(0)
                for word in WORD.finditer(text)
                if word.group(0)[:1].islower()
            )
        )

    def contradicts(self, words: list[str]) -> bool:
        """True when every word given is also written lower case elsewhere.

        Every word, not any: "Mark Nottingham" survives a document that happens
        to contain the verb "mark", because "nottingham" is never lower case.
        """
        return bool(words) and all(
            word.strip("'’-").lower() in self.lowercased for word in words
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


def wrap_column(lines: list[str]) -> int:
    """The column this document is hard-wrapped at, or 0 if it is not wrapped.

    A hard-wrapped file has a ceiling: nearly every line stops just short of one
    column, and the few that pass it are a URL, a table row or an ASCII diagram.
    A file of free text has no ceiling at all — its lengths keep climbing.

    So the ceiling is read off a high percentile and not off the longest line.
    The first version of this used the maximum, and the maximum is exactly the
    outlier the ceiling has to be measured in spite of: on real files p90 was 72
    and the longest line 114, so the band ``longest - 10`` sat above almost
    everything and the test failed. It missed 76% of the files it was written
    for, including the transcript it was written from, and the fixture it was
    tested against passed because a synthetic paragraph has no URL in it.

    Three things have to hold. The ceiling has to sit where text is actually
    wrapped, a quarter of the lines have to pile up in the band just under it,
    and the document has to be long enough for either statistic to mean
    anything. Anything else returns 0 and keeps the cautious rule.
    """
    lengths = sorted(len(line.rstrip()) for line in lines if line.strip())
    total = len(lengths)
    if total < MINIMUM_LINES:
        return 0
    column = lengths[min(total - 1, int(total * CEILING))]
    if not NARROWEST_WRAP <= column <= WIDEST_WRAP:
        return 0
    band = [length for length in lengths if column - BAND <= length <= column]
    return column if len(band) * 4 >= total else 0


def _continues(current: str, following: str, column: int = 0) -> bool:
    """True when ``following`` is the rest of a hard-wrapped ``current``.

    Real transcripts are wrapped at a fixed width, so a sentence routinely spans
    two physical lines. Read one line at a time, 45% of what the tool found on
    raw wrapped files was cut off mid-sentence, and the deadline was usually in
    the half that was thrown away: "We'll ask the IESG to consider our charter"
    ends the line, and "changes on August 13" begins the next one.

    The line above has to end mid-sentence and be long enough to have been
    wrapped, and the line below has to carry no marker of its own. The line
    below also has to begin in lower case — unless the document has been
    measured as hard-wrapped, in which case a line that stops just short of the
    wrap column without punctuation is a continuation whatever case it
    continues in.
    """
    stripped = current.rstrip()
    minimum = column - 10 if column else WRAP_WIDTH
    if len(stripped) < minimum or stripped.endswith((".", "!", "?", ":", ";")):
        return False
    nxt = following.strip()
    if not nxt or LIST_MARKER.match(following):
        return False
    if not column and not nxt[0].islower():
        return False
    return not (SPEAKER_LABEL.match(following) or IRC_LABEL.match(following))


def logical_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(line number, text)`` for each line, rejoining wrapped ones.

    The number is the line the text started on, so a report still points a
    reader at a line they can find.
    """
    raw = [CONTROL.sub(" ", line) for line in LINE_BREAK.split(text)]
    column = wrap_column(raw)
    result: list[tuple[int, str]] = []
    index = 0
    while index < len(raw):
        line = raw[index]
        start = index + 1
        while index + 1 < len(raw) and _continues(line, raw[index + 1], column):
            index += 1
            line = f"{line.rstrip()} {raw[index].strip()}"
        result.append((start, line))
        index += 1
    return result


def _label_key(name: str) -> str:
    """A label reduced for lookup: lowercased, and also tried without a plural."""
    return " ".join(name.lower().split())


def _is_structural_label(name: str) -> bool:
    key = _label_key(name)
    return key in NON_SPEAKER_LABELS or key.rstrip("s") in NON_SPEAKER_LABELS


def _is_metadata(remainder: str) -> bool:
    """True when what follows a label is a record, not somebody speaking.

    ``Chairs: Marc Blanchet & Rick Taylor`` and ``Slides: https://...`` are
    lines about the meeting. Attributing the commitments below them to a person
    called Chairs or Slides is the mistake this catches.
    """
    text = URL.sub(" ", EMAIL.sub(" ", remainder))
    words = [word.group(0) for word in WORD.finditer(text)]
    if not words:
        return True
    return len(words) >= 3 and all(word[0].isupper() for word in words)


def looks_like_a_nickname(name: str) -> bool:
    """True when a lowercase label is a handle rather than a word.

    Short, single, lowercase, and not an ordinary English word: ``ekr``,
    ``mnot``, ``greg``. The guards are what keep ``however:`` and ``important:``
    out; the length bound does most of the work.
    """
    if not NICKNAME.match(name):
        return False
    return name not in cues.NON_NAME_WORDS and not _is_structural_label(name)


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
    if line.lstrip().startswith(">"):
        # Quoted mail pasted into the notes. Somebody else's words, so the
        # current speaker's turn ends here rather than continuing over them.
        return "", True, line.lstrip().lstrip(">").lstrip()

    irc = IRC_LABEL.match(line)
    if irc:
        return _judge(irc.group("name").strip(), line[irc.end():], affiliated=False, line=line)

    match = SPEAKER_LABEL.match(line)
    if not match:
        return "", False, line
    return _judge(
        match.group("name").strip(),
        line[match.end():],
        affiliated=bool(match.group("affiliation")),
        line=line,
    )


def _judge(name: str, remainder: str, affiliated: bool, line: str) -> tuple[str, bool, str]:
    """Decide whether a matched label is a person, and hand back the remainder.

    ``affiliated`` says the match only held because an affiliation was allowed
    between the name and the colon. That form is far easier to trigger by
    accident — "First, we will need to decide: option A" matches it — so when
    the name turns out not to be a name the line is left completely alone
    instead of being treated as document structure. Treating it as structure
    would delete the front of the sentence and lose the commitment in it.
    """
    rejected: tuple[str, bool, str] = ("", False, line) if affiliated else ("", True, remainder)

    words = name.split()
    if len(words) > 1 and words[-1].isdigit():
        # "Speaker 1", and also "Male Speaker 1", so check every word rather
        # than only the first.
        if not any(word.lower() in NUMBERED_SPEAKERS for word in words[:-1]):
            return rejected
    if _is_structural_label(name):
        return "", True, remainder
    if _is_metadata(remainder):
        # A label alone on its line is a heading. So is one followed only by a
        # list of names or a link. Both end the previous speaker's turn.
        return "", True, remainder
    if looks_like_a_name(name, allow=cues.NAMES_ALLOWED_AS_SPEAKERS):
        return name, False, remainder
    if len(words) == 1 and looks_like_a_nickname(name):
        return name, False, remainder
    return rejected


#: A word stripped of the punctuation that surrounds it in a sentence.
WORD = re.compile(r"[^\W\d_][\w'’-]*")


def is_hinglish(sentence: str) -> bool:
    """True when a sentence contains Hindi, and Hindi rules may be applied.

    Roman script hides the difference between a Hindi verb and an English word.
    "fungi" ends like "karungi", "Ortega" like "karega"; "karo" is a syrup and
    "bolo" is a tie. Applied to every sentence, the Hindi rules recorded
    commitments that were not there and invented people to own them.

    Two signals, either of which is enough.

    A Hindi function word — hai, ko, kar, nahi. They are unavoidable in a Hindi
    sentence, near-absent from an English one, and unlike content words they
    carry no meaning worth matching on.

    Or an unmistakably Hindi verb: a lowercase word ending -ega, -egi, -enge,
    -unga or -ungi, or one of a short list of imperatives. Most Hinglish is
    code-mixed — English nouns with a single Hindi verb, "Amazon listing Farhan
    update karega" — and the function-word test alone missed eleven of twenty
    realistic lines of that shape. Only lowercase words count for this signal,
    because Hindi verbs are not capitalised mid-sentence while the English words
    that share those endings are proper nouns: Ortega, Vega, Omega, Noriega.

    This is a filter, not language identification. It exists to keep the Hindi
    rules away from sentences they were never meant to see.
    """
    found = [word.group(0) for word in WORD.finditer(sentence)]
    lowered = {word.lower() for word in found}
    if lowered & cues.hinglish.FUNCTION_WORDS:
        return True
    if lowered & cues.hinglish.UNAMBIGUOUS_IMPERATIVES:
        return True
    for word in found:
        if word[0].isupper() or word.lower() in cues.hinglish.FALSE_FUTURES:
            continue
        if word.lower().endswith(cues.hinglish.VERB_ENDINGS):
            return True
    return False


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
    # Transcripts label unidentified voices "Speaker 1", "Participant 2". The
    # number is part of the label, not a word that has to look like a name.
    if len(words) > 1 and words[-1].isdigit():
        words = words[:-1]
    for word in words:
        stripped = word.strip("'’-")
        if not stripped or not stripped[0].isupper():
            return False
        lowered = stripped.lower()
        if lowered in cues.NON_NAME_WORDS and lowered not in allow:
            return False
    return True


def is_acronym(word: str) -> bool:
    """True when a capitalised token is a thing rather than somebody.

    ``TCPCL will wait for review`` and ``The CH-53K will provide ...`` were
    recorded as promises owned by TCPCL and by CH-53K: 1,761 of them on the
    corpus. An all-capital token or one carrying a digit is a protocol, a
    document, a group or a part number, and naming it as the owner of an
    obligation is the invention this tool exists not to make.

    Acronyms are still accepted as speaker labels, where the colon is separate
    evidence that somebody was talking.
    """
    stripped = word.strip("'’-")
    if len(stripped) < 2:
        return False
    if any(character.isdigit() for character in stripped):
        return True
    return stripped.isupper()


def _behind_a_determiner(sentence: str, index: int, skipped: list[str]) -> bool:
    """True when the word in front of a candidate owner is a determiner.

    English does not put an article in front of a person's name. "The Committee
    will hold a hearing" and "our Chairs will decide" name a thing and a role;
    "Priya will send the deck" names a person. The rule needs no list of
    institutions, which is the point: on a real corpus the owner column was led
    by Chairs, Committee, Department, Chair and Subcommittee, and almost all of
    them arrived wearing "the".

    The word before the candidate is either the last one the caller skipped
    inside the captured run, or, when nothing was skipped, the last word of the
    sentence before the match.
    """
    if skipped:
        previous = skipped[-1]
    else:
        before = [word.group(0) for word in WORD.finditer(sentence[:index])]
        if not before:
            return False
        previous = before[-1]
    return previous.strip("'’-").lower() in cues.DETERMINERS


def _reads_as_a_person(phrase: str) -> bool:
    return looks_like_a_name(phrase) and not any(
        is_acronym(word) for word in phrase.split()
    )


#: The opening of a quotation, in the spellings a transcript uses.
_QUOTE_MARK = re.compile(r"``|''|[\"“”]")
_SPOKEN_QUOTE = re.compile(r"\bquote[,:]?\s*$|\bquote,\s", re.IGNORECASE)


def inside_a_quotation(sentence: str, index: int) -> bool:
    """True when ``index`` falls inside quoted material.

    A scribe quoting somebody else's words is reporting, not recording a
    promise. This matters more than the count suggests: on the corpus a quoted
    slogan produced an open obligation owned by the group the slogan named. The
    tool must not do that, and refusing to read a commitment out of quoted text
    is the general rule that stops it.
    """
    depth = 0
    for mark in _QUOTE_MARK.finditer(sentence):
        if mark.start() >= index:
            break
        token = mark.group(0)
        if token in ('"', "``"):
            depth = 0 if (depth and token == '"') else depth + 1
        else:
            depth = max(0, depth - 1)
    if depth > 0:
        return True
    return bool(_SPOKEN_QUOTE.search(sentence[:index]))


def find_due_phrase(sentence: str) -> str:
    """Return the timing phrase in a sentence verbatim, or ``unknown``.

    The earliest match wins, so ``by Friday`` is preferred over a later
    ``next week`` in the same sentence.

    A phrase that reports when something happened, or when the room will hear
    about it, is skipped: "later today" and "what we have today" are English
    about time and not statements of when work is due.
    """
    patterns = cues.DUE_RE
    if is_hinglish(sentence):
        patterns = patterns + cues.DUE_HI_RE
    best: tuple[int, str] | None = None
    for pattern in patterns:
        for match in pattern.finditer(sentence):
            if _reports_a_time(sentence, match.start()):
                continue
            if best is None or match.start() < best[0]:
                best = (match.start(), match.group(0))
            break
    return best[1] if best else UNKNOWN


def _reports_a_time(sentence: str, index: int) -> bool:
    words = [word.group(0).lower() for word in WORD.finditer(sentence[:index])]
    return bool(words) and words[-1] in cues.NOT_A_DEADLINE_BEFORE


#: A phrase that sets a deadline rather than merely mentioning a time. "by
#: Friday" and "on Monday" name a point work is due; "today" appears in "can you
#: hear me today?" and commits nothing.
DEADLINE_SHAPED = re.compile(
    r"^(?:by|before|within|in \d|end of|eod|on (?:monday|tuesday|wednesday"
    r"|thursday|friday|saturday|sunday))\b",
    re.IGNORECASE,
)


#: The subset of the above that names a limit rather than a day. A weekday on
#: its own is as often the day of the meeting as it is the day work is due.
HARD_DEADLINE_SHAPED = re.compile(
    r"^(?:by|before|within|in \d|end of|eod)\b", re.IGNORECASE
)


#: Hindi marks a deadline at the end of the phrase rather than the start:
#: "kal tak" is "by tomorrow", where "kal" on its own is only "tomorrow".
DEADLINE_SHAPED_SUFFIX = re.compile(r"\b(?:tak|ke andar|hi|me|mein)$", re.IGNORECASE)


def sets_a_deadline(phrase: str) -> bool:
    """True when a due phrase actually sets a deadline."""
    if phrase == UNKNOWN:
        return False
    return bool(DEADLINE_SHAPED.match(phrase) or DEADLINE_SHAPED_SUFFIX.search(phrase))


def sets_a_hard_deadline(phrase: str) -> bool:
    """True when a due phrase names a limit: ``by``, ``before``, ``within``."""
    if phrase == UNKNOWN:
        return False
    return bool(
        HARD_DEADLINE_SHAPED.match(phrase) or DEADLINE_SHAPED_SUFFIX.search(phrase)
    )


def is_excluded(sentence: str) -> bool:
    """True when the sentence should not be recorded as a commitment.

    Two rules, not one. A hypothetical, a negation, or something already done is
    rejected outright. Conversational filler is rejected only when the sentence
    states no deadline: "let me know if you have questions" is noise, while
    "let me know the vendor's answer by Friday" is a real ask wearing the same
    opening. A stated deadline is the strongest evidence one sentence can carry
    that something was meant, so it overrules the filler list.
    """
    hindi = is_hinglish(sentence)
    exclusions = cues.EXCLUSION_RE + (cues.EXCLUSION_HI_RE if hindi else ())
    if any(pattern.search(sentence) for pattern in exclusions):
        return True
    if sets_a_deadline(find_due_phrase(sentence)):
        return False
    filler = cues.FILLER_RE + (cues.FILLER_HI_RE if hindi else ())
    return any(pattern.search(sentence) for pattern in filler)


def named_owner(sentence: str) -> str:
    """Return the name in an ``X will ...`` construction, or ``unknown``.

    The regular expression captures up to three words before the verb. The
    longest run of those words that still looks like a name wins, so
    ``Zhang Wei will pull the rates`` yields "Zhang Wei" while
    ``I think Priya will send it`` yields "Priya" rather than "I think Priya".
    ``We will ship on Monday`` and ``There will be a delay`` yield nothing, and
    neither does ``TCPCL will wait for review``: an acronym is a thing.
    """
    for pattern in (cues.NAMED_ASSIGNMENT_RE, cues.REPORTED_COMMITMENT_RE):
        for match in pattern.finditer(sentence):
            if inside_a_quotation(sentence, match.start(1)):
                continue
            words = match.group(1).split()
            for start in range(len(words)):
                candidate = " ".join(words[start:])
                if not looks_like_a_name(candidate):
                    continue
                if _behind_a_determiner(sentence, match.start(1), words[:start]):
                    return UNKNOWN
                return candidate if _reads_as_a_person(candidate) else UNKNOWN

    # Hindi puts the verb last, so the name is not adjacent to it: "Rohit ye
    # deck banayega" has two words in between.
    #
    # The run of name-like words closest to the verb wins. Hindi is
    # subject-first, but the object is often fronted for emphasis — "Carrier
    # rates Farhan nikalega" is Farhan's job, not Carrier's — so proximity to
    # the verb is a better guide than position in the sentence. Taking the whole
    # run rather than one word keeps "Priya Sharma" and "Lumen Freight" intact.
    if is_hinglish(sentence):
        verb = cues.FUTURE_VERB_RE.search(sentence)
        if verb:
            words = [w.group(0) for w in WORD.finditer(sentence[: verb.start()])]
            last = None
            for index, word in enumerate(words):
                if looks_like_a_name(word):
                    last = index
            if last is not None:
                name = [words[last]]
                # Reach back over adjacent name words so "Priya Sharma" and
                # "Lumen Freight" stay whole, but stop at an acronym: "Ye SOP
                # Priya Sharma likhegi" is Priya Sharma's job, not SOP's.
                while (
                    len(name) < 3
                    and last > 0
                    and looks_like_a_name(words[last - 1])
                    and not words[last - 1].isupper()
                ):
                    last -= 1
                    name.insert(0, words[last])
                return " ".join(name)
    return UNKNOWN


def _is_marked_as_an_item(sentence: str) -> bool:
    """True when something other than the words says this is an action item.

    A bullet in front of it, or a deadline inside it. Either is evidence the
    scribe was writing an item rather than a sentence, and either is enough to
    keep a head the document also writes in lower case: "- Chairs to schedule
    an interim" and "Mark to send the draft by Friday" survive a document that
    also says "the chairs" and "mark that as done".
    """
    return bool(LIST_MARKER.match(sentence)) or sets_a_deadline(find_due_phrase(sentence))


def infinitive_action(sentence: str, document: "Document | None" = None) -> str | None:
    """Read a note-style action item: ``Mark to post the revised draft``.

    Returns the owner, ``unknown`` when the line names an action but nobody to
    do it, and ``None`` when the sentence is not an action item at all.

    This cue is the tool's largest single source of recall and, before the
    guards below, of its own worst noise: 5.5% of everything found on a real
    corpus was this pattern reading the ordinary preposition frame as an item,
    and reporting owners called According, Due, Thanks and Want.

    Three things have to hold, and each rules out a different way of being
    wrong.

    The word after "to" must be able to begin an infinitive. "Mark to post the
    draft" continues with a verb; "According to this scheme" continues with a
    determiner, which makes the "to" a preposition.

    Everything before "to" must be capitalised, so ordinary prose — "It is
    important to note that ..." — does not match.

    The head must not be a word this document also writes in lower case. That
    is what a sentence-initial capital actually means when it means nothing:
    see :class:`Document`. A bullet in front of the line or a deadline inside
    it overrides that test, because either is independent evidence that a
    scribe was writing an item.

    When the opening word is one of the imperatives a scribe writes items with
    ("Ask WG to adopt the draft"), the item is recorded with no owner rather
    than with a person called Ask.
    """
    match = cues.INFINITIVE_ACTION_RE.match(sentence)
    if not match:
        return None
    if match.group("verb").lower() in cues.NOT_AN_INFINITIVE:
        return None
    prefix = match.group("name")
    words = prefix.split()
    if not all(word[0].isupper() for word in words):
        return None
    if looks_like_a_name(prefix):
        if (
            document is not None
            and document.contradicts(words)
            and not _is_marked_as_an_item(sentence)
        ):
            return None
        return prefix if _reads_as_a_person(prefix) else UNKNOWN
    if words[0].lower() in cues.ACTION_OPENERS:
        return UNKNOWN
    return None


#: ``will`` with nobody the tool can name in front of it: "The WGA call will be
#: taken to the list", "A revised draft will be posted".
BARE_FUTURE = re.compile(r"\b(?:will|shall)\s+(?!not\b|never\b|no\b)[a-z]", re.IGNORECASE)


def unowned_future(sentence: str) -> bool:
    """True when a third-party undertaking states a limit but names nobody.

    Bare "will" in a technical meeting is usually a prediction — "the routers
    will have the whole table" — so it is not enough on its own. A stated limit
    is: "the draft will be posted before the cutoff" is somebody's job, even
    when the sentence never says whose. The owner stays unknown, which is what
    the sentence actually supports.
    """
    return bool(BARE_FUTURE.search(sentence)) and sets_a_hard_deadline(
        find_due_phrase(sentence)
    )


def classify(
    sentence: str, speaker: str, document: "Document | None" = None
) -> tuple[tuple[str, ...], str]:
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

    hindi = is_hinglish(sentence)
    first_person_re = cues.FIRST_PERSON_RE + (cues.FIRST_PERSON_HI_RE if hindi else ())
    collective_re = cues.COLLECTIVE_RE + (cues.COLLECTIVE_HI_RE if hindi else ())
    assignment_re = cues.ASSIGNMENT_RE + (cues.ASSIGNMENT_HI_RE if hindi else ())

    due = find_due_phrase(sentence)

    first_person = any(p.search(sentence) for p in first_person_re)
    if not first_person:
        first_person = any(p.search(sentence) for p in cues.COMMITMENT_ACCEPTED_RE)
    if not first_person and not any(p.search(sentence) for p in cues.HEDGE_RE):
        first_person = any(p.search(sentence) for p in cues.FIRST_PERSON_OFFER_RE)
    if not first_person and speaker and cues.ELIDED_SUBJECT_RE.match(sentence):
        # "Fangwei: will move MS PW modeling to that model." The scribe dropped
        # the subject because the label already carried it. Only with a label:
        # without one there is no subject to supply, and a bare "will ..." is
        # more likely the tail of something else.
        first_person = True
    collective = any(p.search(sentence) for p in collective_re)
    named = named_owner(sentence)
    open_ask = any(p.search(sentence) for p in assignment_re)
    if not open_ask and any(p.search(sentence) for p in cues.QUESTION_ASSIGNMENT_RE):
        # A question only hands work over when it asks for something. Without
        # this, every question asked at a microphone became an obligation.
        open_ask = sets_a_deadline(due) or any(
            p.search(sentence) for p in cues.REQUEST_VERB_RE
        )

    action = infinitive_action(sentence, document)
    if action is not None:
        if named == UNKNOWN and action != UNKNOWN:
            named = action
        elif action == UNKNOWN:
            open_ask = True

    fired: list[str] = []
    if first_person:
        fired.append(cues.FIRST_PERSON)
    if collective:
        fired.append(cues.COLLECTIVE)
    if named != UNKNOWN or open_ask:
        fired.append(cues.ASSIGNMENT)
    if not fired and unowned_future(sentence):
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

    if due != UNKNOWN:
        fired.append(cues.DUE_PHRASE)

    return tuple(dict.fromkeys(fired)), owner


def extract_text(text: str, source: str) -> list[Candidate]:
    """Find every candidate commitment in ``text``."""
    found: list[Candidate] = []
    speaker = ""
    document = Document.read(text)
    for number, line in logical_lines(text):
        if not line.strip():
            continue
        label, structural, remainder = read_speaker(line)
        if label:
            speaker = label
        elif structural:
            speaker = ""
        for sentence in split_sentences(remainder):
            fired, owner = classify(sentence, speaker, document)
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
