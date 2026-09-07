"""Commitment cues for Hinglish — Hindi spoken in Roman script.

Most transcription tools return Hindi conversation transliterated rather than
translated, so a meeting in Delhi arrives as "main kal tak bhej dunga" and not as
"I'll send it by tomorrow". An English-only rule set finds nothing in it, which
is not a small gap: it is every commitment in the conversation.

The patterns follow the same shape as the English ones in
:mod:`follow_through.cues` and feed the same families, so nothing downstream
needs to know which language a sentence was in. A third language would be added
the same way.

They are **not** applied to every sentence. Roman script hides the difference
between a Hindi verb and an ordinary English word: "fungi" ends like "karungi",
"Ortega" like "karega", "karo" is a syrup and "bolo" is a tie. Applied blindly,
these rules invented commitments in English sentences and invented people to own
them. A sentence has to look like Hindi first — see :data:`FUNCTION_WORDS`.

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

#: The cheapest reliable sign that a sentence is Hindi rather than English.
#:
#: These are function words — pronouns, postpositions, auxiliaries, connectives.
#: They carry no meaning worth matching on their own, they are impossible to
#: avoid in a Hindi sentence, and they almost never appear in an English one.
#: Every rule in this module is gated on at least one of them being present.
#:
#: This is a filter, not language identification. It will pass an English
#: sentence about a person called Sehai, and it will fail a Hindi sentence
#: written entirely in English loanwords. It exists to stop the morphological
#: rules from reaching sentences they were never meant to see.
FUNCTION_WORDS = frozenset(
    {
        # Pronouns, postpositions, auxiliaries, connectives.
        "aap", "aapko", "abhi", "acha", "achha", "apna", "apne", "aur",
        "bas", "bhai", "bhi", "chahiye", "diya", "fir", "gaya", "hai", "hain",
        "haan", "ho", "hoon", "hu", "hum", "hun", "ismein", "iska", "iske",
        "isko", "isme", "jo", "ka", "kar", "ke", "ki", "ko", "koi", "kuch",
        "kya", "kyunki", "lekin", "liye", "magar", "mai", "maine", "matlab",
        "mein", "mera", "mere", "mujhe", "na", "nahi", "nahin", "pe", "phir",
        "raha", "rahe", "rahi", "sab", "se", "sirf", "tha", "thi", "theek",
        "thoda", "tu", "tum", "tumhe", "unka", "unke", "unko", "usko", "uska",
        "uske", "wala", "wale", "wo", "woh", "ye", "yeh", "yaar",
        # Time and measure words that are unmistakably Hindi.
        "aaj", "baat", "din", "hafte", "kaam", "kal", "mahine", "parso",
        "raat", "shaam", "subah", "tak", "waqt", "zyada",
        # Adverbs and question words with no English twin.
        "andar", "baad", "bahar", "bahut", "bilkul", "dobara", "hamesha",
        "isliye", "jaldi", "kab", "kahan", "kaise", "kaun", "kitna", "pehle",
        "sabhi", "shayad", "turant", "wapas", "warna", "zaroor",
        #
        # Deliberately absent, because they are also ordinary English words and
        # a single false hit opens every Hindi rule on an English sentence:
        # "the" (Hindi tha/the, past tense), "to", "me", "us", "main", "hi",
        # "par", and "agar" — which is Hindi for "if" and also a laboratory
        # growth medium, so "I'll ship the agar order by Friday" was being read
        # as Hindi and thrown away by the Hindi rule for "if". Their absence
        # costs almost nothing: a Hindi sentence contains several of the words
        # above, not one.
    }
)

#: English words that end like a Hindi future tense and are not one. Without
#: these, "that's a challenge" and "we need revenge" become commitments.
FALSE_FUTURES: tuple[str, ...] = (
    "challenge",
    "revenge",
    "avenge",
    "scavenge",
    "lozenge",
    "stonehenge",
    "omega",
    "bodega",
    "mega",
    "vega",
    "fungi",
    "lungi",
    "pungi",
    "tunga",
    "bunga",
    "ortega",
    "noriega",
    "talega",
    "galega",
    "fanega",
    "senega",
    "telega",
    "strategi",
    "rutabaga",
)

#: "main" is Hindi for "I" and English for "principal". It counts as Hindi only
#: as the first word of a sentence, where English would not put it: Hindi says
#: "Main bhej dunga", English says "the main issue".
SENTENCE_INITIAL = frozenset({"main", "mai", "hum", "hamein", "humein"})

#: A guard that refuses the words above before any morphological rule runs.
_NOT_A_FUTURE = r"(?!(?:" + "|".join(FALSE_FUTURES) + r")\b)"

#: "I will do it" / "I am doing it". The speaker owns these.
FIRST_PERSON: tuple[str, ...] = (
    r"\bkar\s?d?unga\b",
    r"\bkar\s?d?ungi\b",
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
    r"\b" + _NOT_A_FUTURE + r"\w*(?:unga|ungi)\b",
)

#: "we will do it", and impersonal obligations — "follow ups lene hai". Both
#: commit a group rather than a person, so neither takes an owner.
COLLECTIVE: tuple[str, ...] = (
    r"\bkarenge\b",
    r"\bkar (?:lenge|denge)\b",
    r"\bkarte (?:hai|hain)\b",
    r"\bkar dete (?:hai|hain)\b",
    r"\bdekh lenge\b",
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
    r"|karwa|dilwa|bhar|jod|hata|badal|likh|bhugta|karana|karwana)"
    r"(?:na|ni|ne)? (?:hai|hain|padega|padegi|hoga|hogi)\b",
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
#: Only -ega and -egi. The -enge form is deliberately absent: whenever it
#: matches, the collective rule matches too, and a collective undertaking has no
#: owner by design — so that branch could never produce one on real input.
FUTURE_VERB = _NOT_A_FUTURE + r"\w*(?:ega|egi)"

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
    r"\b(?:bhej|kar|de|le|dekh|rakh|bata|bhar|likh)(?:iye|iyega)\b",
    r"\b(?:batao|mangao|bhijwao|karwao|dilao|nikalo|bharo|likho)\b",
    r"\blaga (?:do|dena|lo)\b",
    r"\bnikal (?:do|dena|lo)\b",
    r"\brakh (?:do|dena|lo|lena)\b",
    # "tell him", "tell them" — an instruction aimed at somebody in the room
    # about somebody who is not.
    r"\b(?:usko|isko|unko|inko|use|ise|unhe|inhe) (?:bol|bata|keh|de|bhej)\b",
)

#: When something is due. Hindi puts the marker at the end: "kal tak" is "by
#: tomorrow", where "kal" alone is only "tomorrow".
DUE: tuple[str, ...] = (
    r"\b(?:kal|aaj|parso|shaam|subah|raat|dopahar) tak\b",
    r"\baaj hi\b",
    r"\babhi ke abhi\b",
    r"\bturant\b",
    r"\b(?:is|agle) (?:hafte|mahine|saal)(?: (?:tak|me|mein))?\b",
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
    # Predictions. "-enge" is a future tense, not a promise: sales will fall,
    # costs will rise, it will get done. "ho jayega" was removed from the
    # collective rules for this reason and the plural came back in through the
    # morphological shortcut, so it is refused explicitly here.
    r"\bho (?:jayega|jayegi|jayenge|jaayega|jaayegi|jaayenge)\b",
    r"\b(?:girenge|badhenge|ghatenge|bighdenge|hatenge|rukenge)\b",
)

#: Filler that borrows the grammar of a commitment. As with the English list,
#: these stand down when the sentence actually states a deadline.
FILLER: tuple[str, ...] = (
    r"\bdekhte (?:hai|hain)\b",
    r"\bkya karo\b",
    r"\bkya karenge\b",
    r"\bkaro na\b",
    r"\btheek hai\s*(?:na)?\s*[,.?!]",
    r"\bsuno\b",
    r"\bbolo (?:kya|na)\b",
)
