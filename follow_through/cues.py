"""The extraction rules, expressed as data.

Every pattern here is deliberately visible and editable. A contributor can add a
cue without reading the extraction logic, and a reader can audit exactly what the
tool looks for. Nothing outside this module decides what counts as a commitment.

All patterns are matched case-insensitively against a single sentence.
"""

from __future__ import annotations

import re

FIRST_PERSON = "first-person-undertaking"
COLLECTIVE = "collective-undertaking"
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
)

#: A group undertaking. Kept separate from the first person on purpose: "we'll
#: decide on Friday" commits a room, not the person who happened to say it.
COLLECTIVE_PATTERNS: tuple[str, ...] = (
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

#: ``<Name> will ...``, ``<Name> is going to ...``, ``<Name> has agreed to ...``.
#:
#: The captured group is up to three words. Whether those words are actually a
#: name is decided in :func:`follow_through.extract.named_owner`, not here: the
#: pattern cannot tell "Zhang Wei" from "The team", and a character class cannot
#: tell an accented capital from a lowercase letter. The leading lookbehind stops
#: the match starting mid-word, which is what turned "O'Brien" into "Brien".
NAMED_ASSIGNMENT_PATTERN = (
    r"(?<![^\W\d_]['\u2019-])"
    r"((?:[^\W\d_][\w'\u2019-]*\s+){0,2}[^\W\d_][\w'\u2019-]*)"
    r"\s+(?:will|is going to|has agreed to)\b"
)

#: Timing phrases. Captured verbatim as evidence; never converted to a date.
DUE_PATTERNS: tuple[str, ...] = (
    r"\bby (?:this |next )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bon (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bbefore (?:this |next )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bbefore end of (?:day|week|month)\b",
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
#: Hypotheticals, negations, and things already done. These hold even when a
#: deadline is stated: "I don't think I'll have it by Friday" is not a promise.
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
    r"\bi'?ll never\b",
    r"\bi will never\b",
    r"\bwe'?ll never\b",
    r"\bwe will never\b",
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


#: Capitalised words that begin sentences but are not people.
#:
#: Month names are here, including April, May and June, because "May will be
#: tight for the launch" must not invent a person called May. They are exempted
#: for speaker labels only — see :data:`NAMES_ALLOWED_AS_SPEAKERS` — because
#: "May:" at the start of a line is strong evidence of an actual person. Without this, "We
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
        # Words that open a clause and would otherwise be read as a person.
        "after", "all", "another", "any", "anyone", "as", "at", "because",
        "before", "both", "by", "each", "either", "else", "even", "every",
        "everybody", "everything", "for", "from", "here", "how", "in", "is",
        "it's", "its", "just", "most", "much", "neither", "nobody's", "none",
        "not", "nothing", "of", "on", "once", "only", "other", "others",
        "perhaps", "probably", "she'll", "since", "some", "somebody",
        "something", "still", "such", "team", "than", "though", "to", "today",
        "tomorrow", "tonight", "until", "us", "very", "we'll", "well", "were",
        "whatever", "whether", "while", "whoever", "whose", "why", "with",
        "yesterday", "yours",
        # Adverbs and participles that open a sentence. Without these, "Actually
        # will not work" records an owner called "Actually".
        "absolutely", "actually", "additionally", "afterwards", "again",
        "alternatively", "apparently", "arguably", "attached", "basically",
        "besides", "briefly", "certainly", "clearly", "consequently",
        "conversely", "crucially", "curiously", "eventually", "evidently",
        "frankly", "fortunately", "further", "furthermore", "generally",
        "helpfully", "honestly", "hopefully", "ideally", "importantly",
        "included", "incidentally", "indeed", "initially", "instead",
        "interestingly", "later", "likewise", "luckily", "moreover",
        "naturally", "nevertheless", "nonetheless", "obviously",
        "occasionally", "originally", "personally", "possibly", "presumably",
        "previously", "realistically", "regardless", "sadly", "secondly",
        "seemingly", "separately", "similarly", "sometimes", "specifically",
        "strictly", "subsequently", "surely", "technically", "thankfully",
        "theoretically", "thirdly", "typically", "ultimately", "unfortunately",
        "unusually", "usually", "worryingly",
        # Quantifiers and positions that read as subjects.
        "above", "across", "again", "against", "along", "behind", "below",
        "beside", "beyond", "everyone's", "half", "inside", "outside", "over",
        "throughout", "under", "within", "without",
    }
)



#: Conversational filler that borrows the grammar of a commitment. These are the
#: most common sentences spoken on any call, and without them the ledger fills
#: with noise on the first real transcript.
#:
#: Unlike the list above, filler yields to a stated deadline. "Let me know if you
#: have questions" is filler; "Let me know the vendor's answer by Friday" is a
#: real ask that happens to start the same way. A deadline is the strongest
#: evidence available in one sentence that something was actually meant, so when
#: one is present these patterns stand down. Dropping a genuine commitment is the
#: worst thing this tool can do, and it must not happen quietly.
FILLER_PATTERNS: tuple[str, ...] = (
    # Each of these must match the whole filler utterance, not the two words it
    # opens with. "Let me start by welcoming Priya" is filler; "Let me start the
    # migration on the staging box" is a commitment, and an earlier version of
    # this list threw both away.
    r"\blet me know\s*(?:if\b|$|[,.?!])",
    r"\blet me know your thoughts\b",
    r"\blet me think about (?:that|it|this)\b",
    r"\blet me think\s*(?:$|[,.?!])",
    r"\blet me be (?:honest|frank|clear|blunt)\b",
    r"\blet me (?:just )?say (?:that|this)\b",
    r"\blet me start\s+(?:\w+\s+){0,2}by\b",
    r"\blet me finish (?:my|the) (?:point|thought|sentence)\b",
    r"\blet me add (?:that|one thing)\b",
    r"\bcan you hear (?:me|us)\b",
    r"\bcan you see (?:me|my|the screen)\b",
    r"\b(?:can|could) you repeat (?:that|what|it|the last|the question)\b",
    r"\bcould you say that again\b",
    r"\bwe'?ll see\s*(?:how|what|if|about|$|[,.?!])",
    # Only as a discourse marker. "I'll be honest with the client about
    # the delay on Monday" is a commitment, not a preamble.
    r"\bi'?ll be (?:honest|frank)(?: with you)?\s*[,.]",
    r"\bi'?ll admit (?:that|it|i)\b",
    r"\bi'?ll tell you (?:what|this|that|something|honestly|frankly)\b",
    r"\bi'?ll say (?:this|that)\b",
    r"\bi'?ll bet (?:you|it|that)\b",
)


#: Words blocked as owners but allowed as speaker labels. A colon after a name
#: is evidence a person is talking; the same word inside a sentence is not.
NAMES_ALLOWED_AS_SPEAKERS = frozenset(
    {
        "april", "august", "december", "february", "friday", "january",
        "july", "june", "march", "may", "monday", "november", "october",
        "saturday", "september", "sunday", "thursday", "tuesday", "wednesday",
    }
)


def _compile(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


FIRST_PERSON_RE = _compile(FIRST_PERSON_PATTERNS)
ASSIGNMENT_RE = _compile(ASSIGNMENT_PATTERNS)
DUE_RE = _compile(DUE_PATTERNS)
EXCLUSION_RE = _compile(EXCLUSION_PATTERNS)
FILLER_RE = _compile(FILLER_PATTERNS)

COLLECTIVE_RE = _compile(COLLECTIVE_PATTERNS)

#: Case-sensitive on purpose: the capital letter is the evidence of a name.
NAMED_ASSIGNMENT_RE = re.compile(NAMED_ASSIGNMENT_PATTERN)
