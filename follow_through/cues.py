"""The extraction rules, expressed as data.

Every pattern here is deliberately visible and editable. A contributor can add a
cue without reading the extraction logic, and a reader can audit exactly what the
tool looks for. Nothing outside this module decides what counts as a commitment.

All patterns are matched case-insensitively against a single sentence.
"""

from __future__ import annotations

import re

FIRST_PERSON = "first-person-undertaking"
ASSIGNMENT = "assignment-to-another"
DUE_PHRASE = "due-phrase"

#: Someone undertaking to do something themselves.
FIRST_PERSON_PATTERNS: tuple[str, ...] = (
    r"\bi'?ll\b",
    r"\bi will\b",
    r"\bi'?m going to\b",
    r"\bi am going to\b",
    r"\bi'?ll go ahead and\b",
    r"\blet me\b",
    r"\bi can have\b",
    r"\bi can get\b",
    r"\bi'?ll get\b",
    r"\bwe'?ll\b",
    r"\bwe will\b",
    r"\bwe'?re going to\b",
    r"\bwe are going to\b",
)

#: Work being handed to somebody else.
ASSIGNMENT_PATTERNS: tuple[str, ...] = (
    r"\bcan you\b",
    r"\bcould you\b",
    r"\bwould you\b",
    r"\bplease send\b",
    r"\bplease share\b",
    r"\bplease confirm\b",
    r"\bplease get\b",
    r"\byou'?ll need to\b",
    r"\byou need to\b",
)

#: ``<Name> will ...`` and ``<Name> is going to ...``. The captured group is the
#: named owner. Requires a capitalised name so ordinary sentences do not match.
NAMED_ASSIGNMENT_PATTERNS: tuple[str, ...] = (
    r"\b([A-Z][a-z]+)\s+will\b",
    r"\b([A-Z][a-z]+)\s+is going to\b",
    r"\b([A-Z][a-z]+)\s+has agreed to\b",
)

#: Timing phrases. Captured verbatim as evidence; never converted to a date.
DUE_PATTERNS: tuple[str, ...] = (
    r"\bby (?:this |next )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bon (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bby (?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
    r"\bby the \d{1,2}(?:st|nd|rd|th)\b",
    r"\bby end of (?:day|week|month)\b",
    r"\bend of (?:day|week|month)\b",
    r"\bby eod\b",
    r"\beod\b",
    r"\bby tomorrow\b",
    r"\btomorrow\b",
    r"\btonight\b",
    r"\btoday\b",
    r"\bthis week\b",
    r"\bnext week\b",
    r"\bin \d+ (?:days?|weeks?)\b",
    r"\bwithin \d+ (?:days?|weeks?)\b",
    r"\bby the end of (?:the )?(?:day|week|month)\b",
)

#: A sentence matching any of these is never a commitment, whatever else fired.
#: Hypotheticals, negations, and things already done.
EXCLUSION_PATTERNS: tuple[str, ...] = (
    r"\bif i\b",
    r"\bif we\b",
    r"\bi would have\b",
    r"\bwe would have\b",
    r"\bi don'?t think i'?ll\b",
    r"\bi'?m not going to\b",
    r"\bwe'?re not going to\b",
    r"\bi won'?t\b",
    r"\bwe won'?t\b",
    r"\bi might\b",
    r"\bwe might\b",
    r"\bmaybe i'?ll\b",
    r"\bmaybe we'?ll\b",
    r"\bi already\b",
    r"\bwe already\b",
    r"\bi sent\b",
    r"\bi shared\b",
    r"\bwill i be able to\b",
    r"\bwould you have\b",
    r"\bi used to\b",
)


#: Capitalised words that begin sentences but are not people. Without this, "We
#: will ship on Monday" would record an owner called "We", and "There will be a
#: delay" an owner called "There". A pronoun is not a name.
NON_NAME_WORDS = frozenset(
    {
        "and", "also", "april", "august", "but", "december", "everyone",
        "february", "finally", "first", "friday", "he", "her", "his", "however",
        "i", "if", "it", "january", "july", "june", "let", "march", "may",
        "meanwhile", "monday", "my", "next", "no", "nobody", "november", "now",
        "october", "one", "or", "otherwise", "our", "please", "saturday",
        "september", "she", "so", "someone", "sunday", "that", "the", "their",
        "then", "there", "these", "they", "this", "those", "thursday",
        "tuesday", "we", "wednesday", "what", "when", "which", "who", "yes",
        "you", "your",
    }
)


def _compile(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


FIRST_PERSON_RE = _compile(FIRST_PERSON_PATTERNS)
ASSIGNMENT_RE = _compile(ASSIGNMENT_PATTERNS)
DUE_RE = _compile(DUE_PATTERNS)
EXCLUSION_RE = _compile(EXCLUSION_PATTERNS)

#: Named-assignment patterns are case-sensitive on purpose: the capital letter is
#: the evidence that a person was named.
NAMED_ASSIGNMENT_RE = tuple(re.compile(p) for p in NAMED_ASSIGNMENT_PATTERNS)
