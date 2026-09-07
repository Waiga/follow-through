"""Commitment cues for Hinglish — Hindi spoken in Roman script.

Most transcription tools return Hindi conversation transliterated rather than
translated, so a meeting in Delhi arrives as "main kal tak bhej dunga" and not as
"I'll send it by tomorrow". An English-only rule set finds nothing in it, which
is not a small gap: it is every commitment in the conversation.

The patterns follow the same shape as the English ones in
:mod:`follow_through.cues` and are merged into the same families, so nothing
downstream needs to know which language a sentence was in. A third language
would be added the same way.

Hindi marks who is committing in the verb ending rather than with a pronoun, and
that ending is what these patterns key on:

* ``-unga`` / ``-ungi`` / ``-ta hu`` / ``-ti hu`` — I will, I do. First person.
* ``-enge`` / ``-te hai`` / ``-lenge`` — we will. Collective.
* ``-o`` / ``-do`` / ``-dena`` / ``-lena`` — do this. An instruction to somebody
  else, who is almost never named, so the owner stays unknown.

Transliteration is not standardised. People write "hu" and "hoon", "kar dunga"
and "kardunga". Common spellings are covered where they are genuinely common;
this list will always be incomplete, and adding to it is the most useful
contribution anyone can make.
"""

from __future__ import annotations

#: English words that end like a Hindi future tense and are not one. Without
#: these, "that's a challenge" and "we need revenge" become commitments.
FALSE_FUTURES: tuple[str, ...] = (
    "challenge",
    "challenges",
    "revenge",
    "avenge",
    "scavenge",
    "lozenge",
    "stonehenge",
    "omega",
    "bodega",
    "mega",
    "vega",
    "rutabega",
)

#: A guard that refuses the words above before any morphological rule runs.
_NOT_A_FUTURE = r"(?!(?:" + "|".join(FALSE_FUTURES) + r")\b)"

#: "I will do it" / "I am doing it". The speaker owns these.
FIRST_PERSON: tuple[str, ...] = (
    r"\bkar\s?d?unga\b",
    r"\bkar\s?d?ungi\b",
    r"\bkarunga\b",
    r"\bkarungi\b",
    r"\bkar (?:deta|leta) (?:hu|hun|hoon)\b",
    r"\bkar (?:lunga|lungi)\b",
    r"\bkarta (?:hu|hun|hoon)\b",
    r"\bkarti (?:hu|hun|hoon)\b",
    r"\b(?:dalta|dalti) (?:hu|hun|hoon)\b",
    r"\bdal (?:dunga|dungi|deta hu|deti hu)\b",
    r"\bbhej (?:dunga|dungi|deta hu|deti hu|raha hu|rahi hu)\b",
    r"\b(?:bhejta|bhejti) (?:hu|hun|hoon)\b",
    r"\bbhijwa (?:dunga|dungi|deta hu|deti hu)\b",
    r"\bde (?:dunga|dungi|deta hu|deti hu|raha hu|rahi hu)\b",
    r"\bdekh (?:lunga|lungi|leta hu|leti hu)\b",
    r"\b(?:dekhta|dekhti) (?:hu|hun|hoon)\b",
    r"\ble (?:lunga|lungi|leta hu|leti hu)\b",
    r"\bbol (?:dunga|dungi|deta hu|deti hu)\b",
    r"\bbata (?:dunga|dungi|deta hu|deti hu)\b",
    r"\bmangwa (?:lunga|lungi|dunga|leta hu)\b",
    r"\blaga (?:dunga|dungi|deta hu)\b",
    r"\bnikal (?:dunga|dungi|deta hu)\b",
    r"\bpuch (?:lunga|lungi|leta hu)\b",
    r"\bkar (?:raha|rahi) (?:hu|hun|hoon)\b",
    # Any verb plus "deta hu" / "leta hu": bana deta hu, bhijwa deta hu.
    r"\b\w{2,} (?:deta|deti|leta|leti) (?:hu|hun|hoon)\b",
    # Hindi conjugates the future into the verb, so the ending is the cue and a
    # list of verbs is not needed: anything ending -unga or -ungi is "I will".
    # This catches bhejunga, dikhaunga, karwaunga and every verb nobody thought
    # to list. Very few English words end this way; the guard below holds them.
    r"\b" + _NOT_A_FUTURE + r"\w*(?:unga|ungi|aunga|aungi)\b",
)

#: "we will do it", and impersonal obligations — "follow ups lene hai". Both
#: commit a group rather than a person, so neither takes an owner.
COLLECTIVE: tuple[str, ...] = (
    r"\bkarenge\b",
    r"\bkar (?:lenge|denge)\b",
    r"\bkarte (?:hai|hain)\b",
    r"\bkar dete (?:hai|hain)\b",
    r"\bdekh lenge\b",
    r"\bdekhte (?:hai|hain)\b",
    r"\bdekhenge\b",
    r"\bbhej denge\b",
    r"\bbhejte (?:hai|hain)\b",
    r"\bbhejenge\b",
    r"\ble lenge\b",
    r"\bbol denge\b",
    # "bolte hai" is deliberately absent: it is already a hard exclusion, as a
    # report of what people say. A rule that can never fire is noise.
    r"\brakh (?:lenge|denge)\b",
    # "karna hai" / "karni hai" / "karne hai" - "it has to be done". The most
    # common way an obligation is stated, in all three gender-number endings.
    #
    # The verb stems are listed rather than matched as "any word ending -na hai",
    # because Hinglish is full of English nouns that would match: "done hai",
    # "phone hai", "online hai" are not commitments.
    r"\b(?:kar|le|de|bhej|bana|nikal|laga|puch|dekh|rakh|mangwa|bhijwa|banwa"
    r"|karwa|dilwa|bhar|jod|hata|badal|likh|bhugta)(?:na|ni|ne) (?:hai|hain)\b",
    # The same morphological shortcut as above: -enge is "we will". banayenge,
    # lagayenge, karwayenge, dilwayenge and everything else in that family.
    r"\b" + _NOT_A_FUTURE + r"\w*enge\b",
    #
    # "ho jayega" — "it will get done" — is deliberately absent. It reads as a
    # commitment and is almost always a prediction: "tight bhi ho jayegi",
    # "easy ho jayega". It produced two false positives in the first real
    # transcript it met, and caught one genuine item. Not worth the trade.
)

#: "<somebody> will do it", Hindi form: ``Anjali karegi``, ``Rahul bhejega``,
#: ``dono karenge``. Used by the named-assignment rule in
#: :mod:`follow_through.cues`, which decides whether the word before it is
#: really a name. This is how work is handed out in a Hindi conversation, and
#: without it every assignment in the meeting is invisible.
FUTURE_VERB = _NOT_A_FUTURE + r"\w*(?:ega|egi|enge)"

#: "you do it" — an instruction. Hindi imperatives do not name the person they
#: are aimed at, so these never produce an owner.
ASSIGNMENT: tuple[str, ...] = (
    r"\bkar (?:do|dena|lo|lena|dijiye|dijiyega)\b",
    r"\bkaro\b",
    r"\bbhej (?:do|dena|dijiye|dijiyega)\b",
    r"\bbhejo\b",
    r"\bbhijwa (?:do|dena|lo)\b",
    r"\bbol (?:do|dena|dijiye)\b",
    r"\bbolo\b",
    r"\bde (?:do|dena|dijiye|dijiyega)\b",
    r"\bdekh (?:lo|lena|lijiye)\b",
    r"\bdekho\b",
    r"\ble (?:lo|lena|lijiye)\b",
    r"\bmangwa (?:lo|do|lena|dena)\b",
    r"\bpuch (?:lo|lena|lijiye)\b",
    r"\blaga (?:do|dena|lo)\b",
    r"\bnikal (?:do|dena|lo)\b",
    r"\brakh (?:do|dena|lo|lena)\b",
    # "tell him", "tell them" — an instruction aimed at somebody in the room
    # about somebody who is not.
    r"\b(?:usko|isko|unko|inko|use|ise|unhe|inhe) (?:bol|bata|keh|de|bhej)\b",
    # An English imperative that opens a sentence. "I'll follow up with him" is
    # first person and must not match, hence the anchor.
    r"^(?:just |please )?follow up with\b",
)

#: When something is due. Hindi puts the marker at the end: "kal tak" is "by
#: tomorrow", where "kal" alone is only "tomorrow".
DUE: tuple[str, ...] = (
    r"\b(?:kal|aaj|parso|shaam|subah|raat|dopahar) tak\b",
    r"\baaj hi\b",
    r"\babhi ke abhi\b",
    r"\bturant\b",
    r"\b(?:is|agle) (?:hafte|hafte|mahine|saal) (?:tak|me|mein)?\b",
    r"\b(?:ek|do|teen|char|paanch|\d+) din (?:me|mein|ke andar|tak)\b",
    r"\b(?:ek|do|\d+) (?:hafte|mahine) (?:me|mein|ke andar|tak)\b",
    r"\b(?:somvar|mangalvar|budhvar|guruvar|shukravar|shanivar|ravivar) tak\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday) tak\b",
    r"\bkal\b",
    r"\bparso\b",
    r"\baaj\b",
)

#: Never a commitment: hypotheticals, refusals, things already done, and reports
#: of what somebody else said.
EXCLUSIONS: tuple[str, ...] = (
    r"\bshayad\b",
    r"\bho sakta hai\b",
    r"\bho sakti hai\b",
    r"\bagar\b",
    r"\bpata nahi\b",
    r"\bnahi (?:karunga|karungi|karenge|bhejunga|dunga|denge)\b",
    r"\bmat (?:karo|bhejo|do)\b",
    # Already done.
    r"\b(?:kar|bhej|de|le|bata|bol) (?:diya|diye|di|liya|liye)\b",
    r"\bkar chuka (?:hu|hun|hai)\b",
    r"\bho (?:gaya|gayi|chuka hai)\b",
    r"\bho gaya na\b",
    r"\b(?:kar|bhej|chala|nikal) gaya\b",
    r"\bkar rahe the\b",
    # Thinking about it is not doing it.
    r"\bsocha\b",
    r"\bsoch (?:raha|rahi) (?:hu|hun)\b",
    r"\b(?:sochta|sochti) (?:hu|hun)\b",
    r"\bdekhta (?:hu|hun) (?:kya|kaise)\b",
    # Reporting what someone else said or is doing.
    r"\b(?:bol|keh|kar|bhej) (?:raha|rahi|rahe) (?:hai|hain|tha|the)\b",
    r"\b(?:kehta|kehte|kehti|bolta|bolte|bolti) (?:hai|hain)\b",
    r"\bmaine kaha\b",
    r"\bmaine bola\b",
)

#: Filler that borrows the grammar of a commitment. As with the English list,
#: these stand down when the sentence actually states a deadline.
FILLER: tuple[str, ...] = (
    r"\bdekhte hai (?:kya|kaise|ab)\b",
    r"\bkya karo\b",
    r"\bkya karenge\b",
    r"\bkaro na\b",
    r"\btheek hai\s*(?:na)?\s*[,.?!]",
    r"\bsuno\b",
    r"\bbolo (?:kya|na)\b",
)
