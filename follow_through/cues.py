"""The extraction rules, expressed as data.

Every pattern here is deliberately visible and editable. A contributor can add a
cue without reading the extraction logic, and a reader can audit exactly what the
tool looks for. Nothing outside this module decides what counts as a commitment.

All patterns are matched case-insensitively against a single sentence.
"""

from __future__ import annotations

import re

from . import hinglish

FIRST_PERSON = "first-person-undertaking"
COLLECTIVE = "collective-undertaking"
ASSIGNMENT = "assignment-to-another"
DUE_PHRASE = "due-phrase"

#: An apostrophe, straight or typographic. Transcripts contain both.
#:
#: This is written ``['’]`` and never ``'?`` in a contraction, and the
#: reason is the most expensive defect this tool has had. ``\bwe'?ll\b`` also
#: matches the ordinary word "well", and ``\bi'?ll\b`` also matches "ill". On a
#: corpus of 1,067 real meeting records that single optional apostrophe produced
#: 24,996 of 68,028 findings — 36.7% of everything the tool reported — from
#: sentences like "They are designed for machine consumption, as well." The
#: optional form is only ever safe where dropping the apostrophe leaves a
#: non-word ("dont", "wont", "youll"); it is never safe where it leaves a word.
APOS = r"['’]"

#: Someone undertaking to do something themselves.
FIRST_PERSON_PATTERNS: tuple[str, ...] = (
    r"\bi" + APOS + r"ll\b",
    r"\bi will\b",
    r"\bi" + APOS + r"m going to\b",
    r"\bi am going to\b",
    r"\bi" + APOS + r"ll go ahead and\b",
    r"\blet me\b",
    r"\bi can have\b",
    r"\bi can get\b",
    r"\bi" + APOS + r"ll get\b",
)

#: Offering to do the work, rather than stating it outright.
#:
#: Kept apart from the list above because "I can" is a capability as often as it
#: is an offer, and only its position says which. "I can write the text" opens a
#: sentence and is an offer; "it is nice to have SM as I can just mirror it in my
#: code" is a description of what is possible. So these only count at the start
#: of a sentence or straight after a clause break, and only when the sentence
#: carries no hedge — see :data:`HEDGE_PATTERNS`. Measured against the corpus,
#: this shape appeared 4,005 times and the unanchored version would have taken
#: most of them wrongly.
FIRST_PERSON_OFFER_PATTERNS: tuple[str, ...] = (
    r"^(?:[-*o•·+]\s+)?i (?:can|could)(?!" + APOS + r"?t\b)\s+\w",
    r"[,;:]\s*i (?:can|could)(?!" + APOS + r"?t\b)\s+\w",
    r"\bi am happy to\b",
    r"\bi" + APOS + r"m happy to\b",
    r"\bi" + APOS + r"d be happy to\b",
    r"\bi am willing to\b",
    r"\bi" + APOS + r"m willing to\b",
    r"\bi (?:volunteer|volunteered) to\b",
    r"\bi" + APOS + r"ll volunteer\b",
    r"\bi (?:will |can )?take (?:that|this|it) (?:on|as an action)\b",
)

#: Committing in so many words.
#:
#: "Will you commit to working with my office on this?" is the most literal
#: commitment speech act English has, and the tool had no cue for it at all: a
#: legislator extracting a promise on the record, and the answer given back.
#: The verb itself is the cue, in every person, which is why this is one small
#: table rather than a list of the things people commit to.
#:
#: The request form names nobody — it is addressed to whoever is at the witness
#: table — so it joins the assignment family and takes no owner. The answering
#: form is first person and belongs to the speaker.
COMMITMENT_REQUEST_PATTERNS: tuple[str, ...] = (
    r"\b(?:will|do|would|can|could) you (?:please |also |still )?commit to\b",
    r"\bare you (?:willing|prepared|able) to commit\b",
    r"\b(?:will|do) you commit\b",
    r"\bwe (?:would like|ask|need) you to commit to\b",
)

COMMITMENT_ACCEPTED_PATTERNS: tuple[str, ...] = (
    r"\bi (?:certainly |absolutely |definitely |personally |fully |happily "
    r"|gladly |surely |of course |hereby )*"
    r"(?:can |will |would |do |shall |am able to |am prepared to |am happy to )?"
    r"commit to\b",
    r"\bi am committed to\b",
    r"\bi" + APOS + r"m committed to\b",
)

#: Words that turn an offer back into a possibility. Any of these anywhere in
#: the sentence stands the offer patterns down.
HEDGE_PATTERNS: tuple[str, ...] = (
    r"\bpossibly\b",
    r"\bprobably\b",
    r"\bperhaps\b",
    r"\bmaybe\b",
    r"\bmight\b",
    r"\bhopefully\b",
    r"\bin theory\b",
    r"\btheoretically\b",
    r"\bnot sure\b",
    r"\bsomeone\b",
    r"\bsomebody\b",
    r"\bin principle\b",
)

#: A group undertaking. Kept separate from the first person on purpose: "we'll
#: decide on Friday" commits a room, not the person who happened to say it.
COLLECTIVE_PATTERNS: tuple[str, ...] = (
    r"\bwe" + APOS + r"ll\b",
    r"\bwe will\b",
    r"\bwe" + APOS + r"re going to\b",
    r"\bwe are going to\b",
    # "Let's take it to the list" is how a room commits itself out loud. The
    # bare spelling is only accepted at the start of a sentence, because "lets"
    # in the middle of one is the ordinary verb: "that lets us ship early".
    r"\blet" + APOS + r"s\b",
    r"^lets\b",
    r"\blet us\b",
    r"\bwe (?:can|will|would|do)? ?commit to\b",
    r"\bwe are committed to\b",
    r"\bwe" + APOS + r"re committed to\b",
)

#: Work being handed to somebody else.
ASSIGNMENT_PATTERNS: tuple[str, ...] = (
    r"\bplease send\b",
    r"\bplease share\b",
    r"\bplease confirm\b",
    r"\bplease get\b",
    r"\byou" + APOS + r"ll need to\b",
    r"\byou need to\b",
    # An imperative that opens a sentence. "I'll follow up with him" is first
    # person and must not match, hence the anchor. The bullet marker is part of
    # the anchor because minutes are written as lists: "- Follow up with the AD"
    # is the same sentence with a dash in front of it.
    r"^(?:[-*o•·+]\s+)?(?:just |please )?follow up with\b",
    *COMMITMENT_REQUEST_PATTERNS,
    # An expectation stated on the record. "I hope you will consult with the
    # public" hands over work as plainly as "please send it"; the future or the
    # infinitive after "you" is what keeps "I hope you enjoyed it" out.
    r"\b(?:i|we) (?:would |do |really |certainly |strongly )*"
    r"(?:hope|ask|urge|expect|encourage|request|invite|trust|want|need) "
    r"(?:that )?you (?:will|can|could|would|to|" + APOS + r"ll)\b",
)

#: The question forms. Separated from the list above because a question is not
#: automatically a request — see :data:`REQUEST_VERB_PATTERNS`.
QUESTION_ASSIGNMENT_PATTERNS: tuple[str, ...] = (
    r"\bcan you\b",
    r"\bcould you\b",
    r"\bwould you\b",
)

#: A question is not an instruction.
#:
#: "Can you" opens a request and it also opens most of the questions asked at a
#: microphone: "Could you explain the difference between the two modes?" On the
#: corpus this pattern produced 4,809 findings from questions. A sentence that
#: asks something and hands over no work is not a commitment, so an assignment
#: cue that fires inside a question needs a second signal — an imperative verb,
#: a deadline, or an object being asked for — before it is recorded. These are
#: the verbs that carry a real ask.
REQUEST_VERB_PATTERNS: tuple[str, ...] = (
    r"\b(?:send|share|post|confirm|update|review|check|provide|write|draft|"
    r"circulate|forward|publish|submit|prepare|add|fix|look at|take|bring|"
    r"put|raise|open|close|schedule|arrange|set up|follow up|get back|repeat|"
    r"respond|reply|comment|sign|approve|merge|upload|distribute)\b",
)

#: ``<Name> will ...``, ``<Name> is going to ...``, ``<Name> has agreed to ...``.
#:
#: The captured group is up to three words. Whether those words are actually a
#: name is decided in :func:`follow_through.extract.named_owner`, not here: the
#: pattern cannot tell "Zhang Wei" from "The team", and a character class cannot
#: tell an accented capital from a lowercase letter. The leading lookbehind stops
#: the match starting mid-word, which is what turned "O'Brien" into "Brien".
#:
#: The trailing lookahead refuses a negated future. Without it "Mozilla will not
#: implement" and "OneWeb will not have ISLs" were recorded as promises — 333 of
#: them on the corpus — and so was a quoted slogan, which produced an open
#: obligation owned by an ethnic group. A stated refusal is the opposite of a
#: commitment and must never be recorded as one.
NAMED_ASSIGNMENT_PATTERN = (
    r"(?<![^\W\d_]['’-])"
    r"((?:[^\W\d_][\w'’-]*\s+){0,2}[^\W\d_][\w'’-]*)"
    r"\s+(?:will|is going to|has agreed to|agreed to|has volunteered to"
    r"|volunteered to|has offered to|offered to|has committed to|committed to)\b"
    r"(?!\s+(?:not|never|no longer)\b)"
)

#: ``<Name> says she will ...``, ``<Name> said he would ...``.
#:
#: Reported speech is the default voice of a written meeting record, and the
#: pronoun in it defeated every rule: "she" is not a name, so nothing fired and
#: the commitment vanished along with the person who made it. The name in front
#: of the reporting verb is the person committing.
REPORTED_COMMITMENT_PATTERN = (
    r"(?<![^\W\d_]['’-])"
    r"((?:[^\W\d_][\w'’-]*\s+){0,2}[^\W\d_][\w'’-]*)"
    r"\s+(?:says?|said|indicated|noted|confirmed|stated|reported|mentioned"
    r"|explained|added|clarified|told (?:us|me|the \w+))"
    r"(?:\s+that)?\s+(?:he|she|they)\s*"
    r"(?:will|would|" + APOS + r"ll|is going to|are going to)\b"
    r"(?!\s+(?:not|never|no longer|like|prefer|rather)\b)"
)

#: ``<Name> to <verb> ...``, the form a scribe writes an action item in.
#:
#: This is the single largest thing the tool used to miss: 9,139 occurrences on
#: the corpus, and 104 of the 113 items that human scribes had themselves
#: marked under "Action items:". Minutes are written after the meeting in note
#: style — "Mark to post the revised draft", "Ask WG to adopt the draft" — and
#: none of it contains a finite verb for the cue table to match.
#:
#: Everything before "to" must be capitalised, which is what keeps "It is
#: important to note that ..." out. At least two words must follow the verb,
#: which is what keeps "Nothing to report" and "Slides to follow" out.
INFINITIVE_ACTION_PATTERN = (
    r"^(?:[-*o•·+]\s+|\d+[.)]\s+|\(\d+\)\s+)?"
    r"(?P<name>[^\W\d_][\w'’-]*(?:\s+[^\W\d_][\w'’-]*){0,2})"
    r"\s+to\s+(?P<verb>[a-z][a-z'’-]+)(?:\s+\S+){2,}"
)

#: ``will move MS PW modeling to that model`` — a sentence whose subject the
#: scribe dropped because the speaker label already said it.
#:
#: Case-sensitive, and the verb has to be lowercase: that is what separates
#: "will move the model" from "Will Smith", and the negative lookahead is what
#: separates a dropped subject from a question ("Will you commit to ...") or
#: from a subject that is simply a pronoun.
#:
#: "will be" is only read as an undertaking when a participle follows it. "will
#: be sending the text" is an act; "will be out next week" is a state.
ELIDED_SUBJECT_PATTERN = (
    r"^(?:[Ww]ill|[Ss]hall)\s+"
    r"(?:be\s+[a-z]+ing\b"
    r"|(?!be\b|you\b|we\b|i\b|he\b|she\b|it\b|they\b|there\b|that\b"
    r"|this\b|these\b|those\b|the\b|an?\b|not\b|never\b|no\b|any\b"
    r"|some\b|all\b|our\b|your\b|their\b|his\b|her\b|its\b|my\b"
    r"|need\b|needs\b|require\b|remain\b|become\b|seem\b|appear\b"
    r"|depend\b|mean\b|have\b|has\b|had\b|exist\b|matter\b)"
    r"[a-z]{2,})"
)

#: Verbs that open a note-style action item. "Plan to send to IESG" and "Ask WG
#: to adopt the draft" are real items with nobody named; without this list the
#: opening verb was read as the person responsible.
ACTION_OPENERS = frozenset(
    {
        "add", "adopt", "agree", "announce", "arrange", "ask", "assign",
        "check", "circulate", "clarify", "close", "complete", "confirm",
        "consider", "contact", "continue", "coordinate", "create", "decide",
        "define", "discuss", "document", "draft", "evaluate", "explore",
        "finalise", "finalize", "find", "fix", "follow", "identify",
        "implement", "investigate", "merge", "move", "open", "organise",
        "organize", "plan", "post", "prepare", "present", "propose", "provide",
        "publish", "raise", "remove", "reply", "report", "request", "resolve",
        "respond", "review", "revise", "schedule", "send", "share", "submit",
        "summarise", "summarize", "test", "track", "update", "verify", "write",
    }
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
    # A calendar date the sentence states in full. "on August 13" is the half
    # of a wrapped line that used to be thrown away with the rest of the tail.
    r"\b(?:by|before|on) (?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
    r"\b(?:by|before|on) \d{1,2}(?:st|nd|rd|th)? (?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
    # A deadline named as an event rather than as a date. Recorded verbatim,
    # like every other phrase here, and never turned into a date.
    r"\b(?:by|before) (?:the )?(?:next |this )?(?:meeting|cut-?off|deadline"
    r"|interim|session|call|review|last call|wglc)\b",
    r"\b(?:by|before) ietf[ -]?\d{2,3}\b",
)

#: Words that turn a time phrase into a report of when something happened, or
#: of when it was heard about, rather than a statement of when work is due.
#:
#: "later today" and "what we have today" were both being recorded as deadlines:
#: 898 occurrences on the corpus. The phrase is still English; it just is not a
#: due date, and inventing one is exactly what this tool promises not to do.
NOT_A_DEADLINE_BEFORE = frozenset(
    {
        "about", "already", "earlier", "from", "had", "has", "have", "heard",
        "later", "since", "until", "was", "were", "yesterday",
    }
)

#: A sentence matching any of these is never a commitment, whatever else fired.
#: Hypotheticals, negations, and things already done. These hold even when a
#: deadline is stated: "I don't think I'll have it by Friday" is not a promise.
EXCLUSION_PATTERNS: tuple[str, ...] = (
    r"\bif i\b",
    r"\bif we\b",
    r"\bi would have\b",
    r"\bwe would have\b",
    r"\bi don" + APOS + r"?t think i" + APOS + r"ll\b",
    r"\bi" + APOS + r"m not going to\b",
    r"\bwe" + APOS + r"re not going to\b",
    r"\bi won" + APOS + r"?t\b",
    r"\bwe won" + APOS + r"?t\b",
    r"\bi" + APOS + r"ll never\b",
    r"\bi will never\b",
    r"\bwe" + APOS + r"ll never\b",
    r"\bwe will never\b",
    r"\bi might\b",
    r"\bwe might\b",
    r"\bmaybe i" + APOS + r"ll\b",
    r"\bmaybe we" + APOS + r"ll\b",
    r"\bi already\b",
    r"\bwe already\b",
    r"\bi sent\b",
    r"\bi shared\b",
    r"\bwill i be able to\b",
    r"\bwould you have\b",
    r"\bi used to\b",
    # A negated future, in any person. The first-person forms above cover "I
    # won't"; these cover everybody else. "Mozilla will not implement" is a
    # refusal, and recording it as an obligation is the worst mistake in the
    # tool's range: on the corpus this shape also turned a quoted slogan into an
    # open commitment owned by the group it named.
    r"\bwill (?:not|never|no longer)\b",
    r"\bwon" + APOS + r"?t\b",
    r"\b(?:is|are|was|were) not going to\b",
    r"\bi (?:can|could)n" + APOS + r"?t\b",
    r"\blet" + APOS + r"?s not\b",
    # Narrating the meeting's own running order. "We will now move on to our
    # second panel" commits nobody to anything after the meeting ends.
    r"\bwe (?:will|" + APOS + r"ll) now\b",
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
        "seemingly", "similarly", "sometimes", "specifically",
        "strictly", "subsequently", "surely", "technically", "thankfully",
        "theoretically", "thirdly", "typically", "ultimately", "unfortunately",
        "unusually", "usually", "worryingly",
        # Quantifiers and positions that read as subjects.
        "above", "across", "again", "against", "along", "behind", "below",
        "beside", "beyond", "everyone's", "half", "inside", "outside", "over",
        "throughout", "under", "within", "without",
        # The subject of a sentence in a technical meeting is usually a thing,
        # and a thing that is capitalised because it opened the sentence is
        # still a thing. Every word here was recorded as a person by an earlier
        # build: "Consensus will be judged on the list", "Adoption will be
        # reconsidered after Prague".
        "adoption", "agenda", "answer", "approach", "call", "change",
        "changes", "charter", "client", "code", "consensus", "data",
        "deadline", "deployment", "design", "discussion", "document",
        "documents", "draft", "drafts", "error", "feedback", "goal",
        "implementation", "input", "interim", "issue", "issues", "key",
        "meeting", "message", "milestone", "minutes", "network", "output",
        "packet", "packets", "plan", "plans", "policy", "presentation",
        "problem", "process", "progress", "proposal", "protocol", "question",
        "questions", "result", "results", "review", "router", "routers",
        "rule", "rules", "section", "server", "session", "slide", "slides",
        "solution", "spec", "specification", "standard", "status", "text",
        "time", "topic", "traffic", "version", "work",
        # Imperative verbs that open an action item. Blocked as names so that
        # "Ask WG to adopt the draft" does not record a person called Ask; the
        # item itself is still recorded, with no owner.
        *ACTION_OPENERS,
        # Hindi time words that would otherwise read as names: "Kal Rohit
        # karega" must find Rohit, not Kal.
        "aaj", "kal", "parso", "abhi", "shaam", "subah", "raat",
        # "Main challenge is the Omega launch" must not record an owner called
        # Main. It is Hindi for "I" and English for "principal".
        "main",
    }
    | hinglish.NOT_NAMES
)



#: Acts of speech inside this meeting, rather than work that outlives it.
#:
#: "Let me go to Mr Pugliaresi", "I will just refresh your memory", "we will go
#: to Senator Cortez Masto" — the thing being undertaken is the next few
#: seconds of the meeting. Managing the floor and narrating your own remarks are
#: the largest remaining source of noise, and the class is the verb: recognise,
#: yield, turn to, go back to, move on to, read, quote, remind, refresh.
#:
#: These are filler rather than exclusions, so a stated deadline still overrules
#: them. Where a verb is genuinely ambiguous the verb is left out: "I'll tell
#: you the number" and "I'll get back to you" are real commitments, so "tell"
#: is only matched with a that-clause after it and "get back" is not matched at
#: all. That choice keeps a false positive rather than losing a commitment.
MEETING_FLOOR_VERBS = (
    r"back up|recognise|recognize|yield|call on|adjourn|recess|take a break"
    r"|wrap up|stop (?:there|here)|pause|hand (?:over|it) to|open it up"
    r"|refresh (?:your|our|the) memory"
    r"|remind (?:you|us|everyone|people|the \w+)"
    r"|walk (?:you|us) through|show (?:you|us)|point out|quote|follow on"
    r"|touch on"
)

#: Verbs that only read as floor management after "let me" or "let us".
#:
#: "Let me go to Mr Pugliaresi" moves the meeting on. "I will go to the vendor
#: and get a quote" is work, and "we will move on to the new supplier next
#: quarter" is a decision. Nothing in one sentence separates those two senses,
#: so these verbs are only treated as narration where the floor sense
#: dominates, and the remaining false positives are kept. Losing a commitment
#: is the worse error.
NARRATOR_ONLY_VERBS = (
    r"go back|go over|go on to|go to|move on|move to|turn to|come back to"
    r"|circle back to|proceed to|skip|jump to|start with|begin with"
    r"|introduce|welcome|read|explain|clarify|summarise|summarize|repeat"
    r"|highlight|emphasise|emphasize|stress"
)

#: Moving the floor to a named participant. The honorific is what makes this
#: unambiguous where the bare verb is not: you go to Senator Cortez Masto in a
#: hearing, and you go to the vendor in a business.
ADDRESSING_THE_ROOM = (
    r"(?:go|move|turn|come back|hand it|hand over)\s+(?:on\s+|back\s+)?to\s+"
    r"(?:mr|mrs|ms|dr|sen|senator|rep|representative|congressman|congresswoman"
    r"|chairman|chairwoman|the gentleman|the gentlewoman"
    r"|the (?:next|first|second|third|last) "
    r"(?:panel|witness|speaker|question|item|slide|topic))\b"
)

#: The subjects that can narrate a meeting, and the fillers between them and
#: the verb: "I will just", "we are now going to", "let me first".
_NARRATOR = (
    r"(?:i|we) (?:will|" + APOS + r"ll|am going to|" + APOS + r"m going to"
    r"|are going to|" + APOS + r"re going to)"
)
_HEDGING_ADVERBS = r"(?:just |now |also |then |again |first |quickly |briefly |simply )*"

MEETING_NARRATION_PATTERNS: tuple[str, ...] = (
    r"\b" + _NARRATOR + r"\s+" + _HEDGING_ADVERBS + r"(?:" + MEETING_FLOOR_VERBS + r")\b",
    r"\b" + _NARRATOR + r"\s+" + _HEDGING_ADVERBS + r"(?:" + ADDRESSING_THE_ROOM + r")",
    r"\blet (?:me|us) " + _HEDGING_ADVERBS + r"(?:" + MEETING_FLOOR_VERBS + r")\b",
    r"\blet (?:me|us) " + _HEDGING_ADVERBS + r"(?:" + NARRATOR_ONLY_VERBS + r")\b",
    # "I will tell you that ..." narrates; "I'll tell you the number after the
    # hearing" undertakes. Only the complement clause is filler.
    r"\b" + _NARRATOR + r"\s+" + _HEDGING_ADVERBS + r"tell you (?:that\b|,)",
)


#: Determiners. A word after one of these is a common noun, whatever its
#: capitalisation: English does not put an article in front of a person's name.
#:
#: This is what separates "The Committee will hold a hearing" from "Priya will
#: send the deck" without a list of institutions. The owner list on a real
#: corpus was led by Chairs, Committee, Department, Chair and Subcommittee, and
#: nearly all of them arrived wearing "the".
DETERMINERS = frozenset(
    {
        "a", "all", "an", "another", "any", "both", "each", "either", "every",
        "her", "his", "its", "my", "neither", "no", "one", "our", "some",
        "such", "that", "the", "their", "these", "this", "those", "your",
    }
)


#: Words that cannot begin an infinitive, so a ``to`` in front of one is the
#: preposition and not the infinitive marker.
#:
#: "Mark to post the revised draft" and "According to this scheme" are the same
#: shape. What separates them is what comes after "to": a bare verb begins an
#: infinitive, and a determiner or a pronoun begins a noun phrase, which makes
#: the "to" a preposition and the line a sentence rather than an action item.
#:
#: This enumerates closed word classes — determiners, pronouns, prepositions,
#: conjunctions — rather than the words that happened to go wrong. A closed
#: class can be finished; a list of content words never can. ``be`` is
#: deliberately absent: "Mirja to be the responsible AD" is a real action item.
NOT_AN_INFINITIVE = (
    frozenset(
        {
            # Pronouns and possessives.
            "me", "us", "him", "them", "it", "you", "he", "she", "they", "i",
            "we", "myself", "ourselves", "himself", "herself", "themselves",
            "itself", "yourself", "who", "whom", "whose", "which", "what",
            "hers", "theirs", "ours", "yours", "mine",
            # Prepositions and conjunctions. These follow the preposition "to"
            # and never the infinitive marker.
            "of", "in", "on", "at", "for", "with", "from", "by", "into",
            "onto", "about", "over", "under", "between", "among", "through",
            "during", "and", "or", "but", "nor", "so", "than", "then",
            "because", "if", "when", "while", "where", "as", "though",
            "although",
        }
    )
    # An article or a possessive after "to" makes it a preposition just as
    # surely as a pronoun does: "Thanks to the Chair", "Deferring to my
    # colleagues".
    | DETERMINERS
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
    r"\blet (?:me|us) know\s*(?:if\b|$|[,.?!])",
    r"\blet (?:me|us) know your thoughts\b",
    r"\blet (?:me|us) think about (?:that|it|this)\b",
    r"\blet (?:me|us) think\s*(?:$|[,.?!])",
    r"\blet me be (?:honest|frank|clear|blunt)\b",
    r"\blet me (?:just )?say (?:that|this)\b",
    r"\blet me start\s+(?:\w+\s+){0,2}by\b",
    r"\blet me finish (?:my|the) (?:point|thought|sentence)\b",
    r"\blet me add (?:that|one thing)\b",
    r"\bcan you hear (?:me|us)\b",
    # The same audio-visual check from the other side of the call. "I can see
    # the slides" is not an offer to do anything, and neither is "I can hear
    # you"; these are perception, not undertaking.
    r"\bi (?:can|could) (?:see|hear|read|tell|imagine|understand|remember)\b",
    r"\bcan you see (?:me|my|the screen)\b",
    r"\b(?:can|could) you repeat (?:that|what|it|the last|the question)\b",
    r"\bcould you say that again\b",
    r"\bwe" + APOS + r"ll see\s*(?:how|what|if|about|$|[,.?!])",
    r"\blet" + APOS + r"?s see\s*(?:how|what|if|about|$|[,.?!])",
    # Narrating a presentation. The speaker is describing what the room is
    # about to look at, not undertaking anything that outlives the meeting.
    r"\blet me start\s*(?:$|[,.?!])",
    r"\blet me start (?:again|over)\b",
    r"\blet me start,",
    r"\blet me (?:walk|take) (?:you|us) (?:through|back)\b",
    r"\blet me (?:go back|go on|move on|turn|come back|return)\b",
    r"\blet me (?:show|share) (?:you|us|my|the|this|that)\b",
    r"\blet me (?:explain|clarify|repeat|recap|summarise|summarize|elaborate)\b",
    r"\blet me remind (?:you|us|everyone|people|the)\b",
    r"\blet me introduce\b",
    r"\blet me pull up\b",
    r"\bwe (?:will|" + APOS + r"ll) hear (?:about|from|more)\b",
    # Only as a discourse marker. "I'll be honest with the client about
    # the delay on Monday" is a commitment, not a preamble.
    r"\bi" + APOS + r"ll be (?:honest|frank)(?: with you)?\s*[,.]",
    r"\bi" + APOS + r"ll admit (?:that|it|i)\b",
    r"\bi" + APOS + r"ll tell you (?:what|this|that|something|honestly|frankly)\b",
    r"\bi" + APOS + r"ll say (?:this|that)\b",
    r"\bi" + APOS + r"ll bet (?:you|it|that)\b",
    # Describing the method just agreed, not undertaking anything new.
    r"\bthat" + APOS + r"?s how we" + APOS + r"ll\b",
    r"\bthat is how we" + APOS + r"ll\b",
    *MEETING_NARRATION_PATTERNS,
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


#: The two languages are compiled separately, not merged.
#:
#: Merging them was the first design and it was wrong. Roman script cannot tell
#: a Hindi verb from an English word by shape alone: "fungi" ends like "karungi",
#: "Ortega" like "karega", "karo" is a syrup, "bolo" is a tie. Applying Hindi
#: rules to an English sentence invented commitments and invented owners.
#:
#: A sentence is now tested for Hindi before the Hindi rules are allowed near it.
#: See :func:`follow_through.extract.is_hinglish`.
FIRST_PERSON_RE = _compile(FIRST_PERSON_PATTERNS)
FIRST_PERSON_OFFER_RE = _compile(FIRST_PERSON_OFFER_PATTERNS)
COMMITMENT_ACCEPTED_RE = _compile(COMMITMENT_ACCEPTED_PATTERNS)
HEDGE_RE = _compile(HEDGE_PATTERNS)
FIRST_PERSON_HI_RE = _compile(hinglish.FIRST_PERSON)
ASSIGNMENT_RE = _compile(ASSIGNMENT_PATTERNS)
QUESTION_ASSIGNMENT_RE = _compile(QUESTION_ASSIGNMENT_PATTERNS)
REQUEST_VERB_RE = _compile(REQUEST_VERB_PATTERNS)
ASSIGNMENT_HI_RE = _compile(hinglish.ASSIGNMENT)
DUE_RE = _compile(DUE_PATTERNS)
DUE_HI_RE = _compile(hinglish.DUE)
EXCLUSION_RE = _compile(EXCLUSION_PATTERNS)
EXCLUSION_HI_RE = _compile(hinglish.EXCLUSIONS)
FILLER_RE = _compile(FILLER_PATTERNS)
FILLER_HI_RE = _compile(hinglish.FILLER)

COLLECTIVE_RE = _compile(COLLECTIVE_PATTERNS)
COLLECTIVE_HI_RE = _compile(hinglish.COLLECTIVE)

#: Case-sensitive on purpose: the capital letter is the evidence of a name.
NAMED_ASSIGNMENT_RE = re.compile(NAMED_ASSIGNMENT_PATTERN)

#: Case-sensitive for the same reason: everything before "to" has to be
#: capitalised for the line to read as an action item rather than as prose.
INFINITIVE_ACTION_RE = re.compile(INFINITIVE_ACTION_PATTERN)

#: Case-sensitive too: a lowercase verb after "will" is what says the subject
#: was dropped rather than named.
ELIDED_SUBJECT_RE = re.compile(ELIDED_SUBJECT_PATTERN)

#: Case-sensitive, like the other name patterns: the capital is the evidence.
REPORTED_COMMITMENT_RE = re.compile(REPORTED_COMMITMENT_PATTERN)

#: The Hindi equivalent, used differently. English puts the name immediately
#: before "will"; Hindi is subject-object-verb, so "Rohit ye deck banayega" has
#: two words in between. The name is taken from whichever name-like words sit
#: closest to the verb. See :func:`follow_through.extract.named_owner`.
#: Case-insensitive, like every other pattern here. It was not, and that made
#: the whole guard list inert in this one place: the list is lowercase, and
#: Ortega, Vega, Omega and Bodega only ever appear capitalised.
FUTURE_VERB_RE = re.compile(r"\b" + hinglish.FUTURE_VERB + r"\b", re.IGNORECASE)
