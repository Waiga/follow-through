# Follow Through

People commit to things out loud. In a meeting, on a call, in a voice note. The
commitment is real; the record is not. It sits inside a transcript nobody reads
again, and a week later nobody can say what was promised, by whom, or whether it
happened.

Transcription is already solved. Almost every meeting tool emits text. What is
missing is the step after: turning that text into a list of obligations you can
actually close.

Follow Through is a command-line tool that reads a transcript, finds the
statements that commit someone to a future action, and tracks each one until you
say it is done.

It reads English and Hinglish — Hindi spoken in Roman script, which is what
transcription tools return for most of India. That is not a bonus feature.
English-only rules do not degrade gracefully on a Hindi conversation: they
return nothing at all, while reporting nothing wrong.

The Hinglish rules were added after the English-only version missed the
commitments in one real Hindi-English meeting transcript, where every promise
looked like "main hi follow up dalta hu". That is a single private transcript,
scored by the person who wrote the rules. It explains why the module exists; it
is not evidence that it works. The Hinglish rules have never been measured
against any public corpus, no such corpus is known to me, and the Hinglish
example in this repository is invented.

It runs entirely on your machine. No account, no API key, no network call. Your
transcripts are never uploaded anywhere.

That is enforced, not just promised. `tests/test_offline.py` reads this package's
own source on every run and fails if any module imports something that can reach
the network, names one of the `os` functions that starts another program —
however it is spelled, including behind an alias, an aliased import, or a string
passed to `getattr` — or reaches for `__import__`, `eval` or `exec`. Each
detector has its own test proving it can fail, and one test smuggles a working
exfiltration path in to confirm it is caught.

Being precise about what that is: it is a static read of this package's source, on
a package that declares no dependencies. It is a guard against drift, not a
sandbox. It does not run the code and it cannot vouch for your Python
installation. What it does is make the offline promise expensive to break by
accident and impossible to break in the obvious ways without a test turning red.

## Install

Follow Through needs Python 3.11 or newer and has no dependencies.

```bash
pip install follow-through
```

To install from a clone instead, `python3 -m pip install --no-deps .` from the
repository root.

## Use it

Start with a transcript. Any plain text file works — exported meeting notes, a
transcription, or something you typed yourself.

```bash
follow-through extract examples/weekly-sync.txt
```

```
8a6295803ccc  Sam                   by Friday             I'll send the signed lease to finance by Friday.
35a117fe08a0  owner not stated      no stated deadline    Can you also share the insurance certificate?
ab66f295b196  Jordan                by October 3          Jordan will pull the carrier rates by October 3.
1f0e51f8120a  Jordan                in 3 days             I'll have a first cut ready in 3 days.
4312edaecc56  owner not stated      no stated deadline    We'll need to decide on the second shift before the move.
4095a62ef115  Jordan                tonight               Let me draft the shift plan tonight.
694cf1f34f39  owner not stated      no stated deadline    Please confirm the headcount with HR.
37f8c8a83e0d  Alex                  today                 I'll update the risk register today.
0bc8f26c2cae  O'Brien               next week             O'Brien will countersign the lease next week.
```

Five other lines in that transcript were left out on purpose: two hypotheticals,
one thing already done, one "maybe", and a "let me know". Each of them contains a
phrase the tool otherwise treats as a commitment.

`extract` records nothing. When the list looks right, keep it:

```bash
follow-through track examples/weekly-sync.txt
```

That writes a ledger to `.follow-through/ledger.json`. Run it again over the same
file after it has grown and only the new commitments are added — nothing is
duplicated, and nothing you have already closed comes back.

A commitment is identified by its wording, its owner, and the file it came from.
The file matters: people promise the same thing, in the same words, every week.
If last week's transcript and this week's were treated as one, the second promise
would silently match the first one you closed and disappear.

The file is recorded as the path you gave, shortened, not as an absolute path —
otherwise the same transcript would produce different ids on different machines.
One consequence worth knowing: if two directories each hold a `standup.txt` and
both are tracked from inside themselves into one shared ledger, both record
`standup.txt` and merge. Run `track` from a common parent and the paths differ,
so they stay separate.

See what is still open, close something, and write a report:

```bash
follow-through list
follow-through close 8a62 --note "lease countersigned and filed"
follow-through report
```

`report` writes Markdown and HTML to `reports/`. Open commitments are grouped by
person, with the unattributed ones in their own visible group — those are the
ones that actually go missing.

A worked example of the finished report is in
[`examples/expected-report.md`](examples/expected-report.md).

## Hinglish

The same command, on [`examples/weekly-sync-hinglish.txt`](examples/weekly-sync-hinglish.txt):

```
30c32ccddb01  Neha                  kal tak               Main signed copy finance ko kal tak bhej dungi.
```

Hindi puts two things in different places from English, and both matter.

**Who is committing is in the verb ending, not in a pronoun.** `-unga` / `-ungi`
is "I will", `-enge` is "we will", `-ega` / `-egi` after a name is "she will" or
"he will" — which is how work actually gets handed to someone in a Hindi meeting.
The rules match the ending, so verbs nobody thought to list are still caught.

**When it is due is at the end of the phrase.** `kal` is "tomorrow"; `kal tak` is
"by tomorrow". Only the second one sets a deadline, and only the second one
overrules the filler list.

**The Hindi rules only run on Hindi sentences.** Roman script hides the
difference between a Hindi verb and an ordinary English word: `fungi` ends like
`karungi`, `Ortega` like `karega`, `karo` is a syrup and `bolo` is a tie. Applied
to everything, these rules invented commitments in English sentences and invented
people to own them.

So a sentence has to look like Hindi first. Either it contains a Hindi function
word — `hai`, `ko`, `kar`, `nahi` — or it contains an unmistakably Hindi verb: a
**lowercase** word ending `-ega`, `-egi`, `-enge`, `-unga`, `-ungi`. The
lowercase part is what does the work. Hindi verbs are not capitalised in the
middle of a sentence, and the English words that share those endings are proper
nouns: Ortega, Vega, Omega, Noriega. That one distinction separates
"Amazon listing Farhan update karega" from "Maria Ortega raised the issue"
without needing a dictionary of either language.

Transliteration is not standardised — people write `hu` and `hoon`, `kar dunga`
and `kardunga`. The common spellings are covered and the list will always be
incomplete. Adding to it is the single most useful contribution anyone can make,
and the rules are plain data in
[`follow_through/hinglish.py`](follow_through/hinglish.py).

## What it will not do

This list is the design, not a disclaimer.

- **It will not find every commitment.** It matches patterns in text. Something
  phrased unusually will be missed, and some of what it finds will not really be
  a commitment. Every report says so.
- **It will not guess who owns something.** If the transcript does not say, the
  owner stays `unknown`. It will not attribute a line to whoever was talking
  most, and it will not turn `From:` or `TODO:` into an owner. "We'll decide on
  Friday" commits a room, not whoever said "we", so that stays `unknown` too.
  An owner is whoever the text names, which may be a team — "Legal will review
  the contract" records Legal, because that is who was named.
- **It will not guess a deadline.** No timing phrase means no deadline. It records
  the phrase the speaker actually used — `by Friday`, `in 3 days` — as text, and
  never converts it to a calendar date, because that would mean assuming when the
  conversation happened.
- **It will not decide that something was done.** Only you close an entry, and a
  reason is required when you do.
- **It will not score anyone.** There is no reliability metric and no leaderboard.
- **It will not send anything anywhere.**

One rule sits underneath all of these: absence of evidence is reported as
unknown, never as a confirmed no.

### Deliberate trade-offs

These are choices, not oversights. Each one loses something real, and each one
was measured against 1,067 real meeting records before it was made.

- **A conditional is not a commitment.** "If we extend the last call, we will
  need to ask people to check the model" is rejected, and so is the genuine
  undertaking that sometimes follows one. On the corpus most sentences of this
  shape were conditions rather than promises, so the exclusion stays.
- **A bare third-party future is only kept when it states a limit.** "A revised
  draft will be posted by Friday" is recorded with no owner. "The routers will
  have the whole table" is not recorded at all, because in a technical meeting
  "will" is more often a prediction than a promise.
- **An acronym never owns a commitment.** "TCPCL will wait for review" records
  nothing. That also means "IESG will publish it" records nothing. A protocol,
  a document and a working-group short name all look identical to a part
  number, and naming one as the person responsible is exactly the invention
  this tool exists not to make. Write the owner as a word — `Legal`, `Chairs` —
  and it is recorded.
- **"I can" counts only at the start of a clause, and only unhedged.** "I can
  write the text" is an offer. "It is nice to have this as I can just mirror it
  in my code" is not, and "I could possibly reach out" is not either.
- **An exclusion applies to the whole sentence.** "I sent the draft last week
  and I'll post the update by Friday" is rejected because of its first half.
  Splitting a sentence into clauses reliably is a bigger change than this tool
  is, and rejecting too much is the safer failure.
- **A bare institution or a country is still recorded as an owner.** "China will
  continue to expand its fleet" records China, and it is a forecast rather than
  anything anybody in the room can be held to. The article rule above catches
  "the Committee" and "the Department"; it cannot catch "China" or "Congress",
  because a bare capitalised proper noun naming a state has exactly the same
  shape as a surname. Separating them needs a gazetteer or a part-of-speech
  tagger, and this package carries no dependencies. It is a limit of the tool in
  this genre, written down here rather than half-filtered.
- **Ambiguous narration is kept rather than dropped.** "Let me go to Mr
  Pugliaresi" is floor management; "I will go to the vendor and get a quote" is
  work, and one sentence does not separate them. So verbs like *go to*, *move
  on* and *turn to* are only treated as narration after "let me" or "let us", or
  when they address somebody by title. Everywhere else the false positive is
  kept, because losing a commitment is the worse error.
- **A document under forty lines is never measured for wrapping.** Below that
  the percentile is just the longest line again, which is the statistic that
  failed, so short files keep the cautious rule and a wrapped one may still be
  read in fragments. This is the shape of the tool's own examples, which is
  worth saying: the fixtures in this repository are too short to exercise the
  measurement, and that is exactly how the defect in it survived a test suite.
- **The orthography test needs the evidence to be in the file.** "Due to visa
  rules, we would not comment" is refused in a transcript that says "due to"
  somewhere in lower case, which any real one does many times over. In a file of
  a few lines that happens to use the word only once, and capitalised, there is
  nothing to contradict it and the line is recorded. The test gets stronger the
  longer the document is, which is the opposite of the usual failure and worth
  knowing.
- **An unmarked action item can lose its owner to the orthography test.**
  "Chairs to schedule an interim", with no bullet and no deadline, in a document
  that also writes "the chairs" in lower case, is dropped. Put a bullet in front
  of it or a date inside it and it is kept. The test removes 630 findings on a
  real corpus that were the preposition frame wearing a capital letter; this is
  what it costs, and it costs it only to single-word owners that are also
  ordinary English words.
- **One sentence yields one owner.** "Carsten, Jim and Christian volunteered to
  review" records Christian, the name nearest the verb. It records a real
  person, and it under-reports the other two.

## How it decides

The rules are ordinary regular expressions, kept together as data in
[`follow_through/cues.py`](follow_through/cues.py) so you can read and extend
them without touching any logic. There is no model involved.

A sentence becomes a candidate when it contains someone undertaking to do
something (`I'll`, `we will`, `let me`, `let's`, `I can write`), handing work to
somebody else (`please send`, `Priya will`, `Mark agreed to`), or writing it down
as an action item (`Mark to post the revised draft`, `Ask the WG to adopt it`).
It is rejected when it is hypothetical, negated, tentative, or already in the
past — `if I get time`, `I don't think I'll`, `I might`, `I already sent`,
`Mozilla will not implement`.

Contractions require their apostrophe, straight or typographic. This reads like
a detail and is not one: `we'?ll` also matches the ordinary word "well", and on
1,067 real transcripts that single optional character produced 36.7% of
everything the tool reported.

A question is only an assignment when it asks for something. "Could you post
that to the list?" is a request; "Can you explain the difference between the two
modes?" is a question at a microphone, and recording it as an obligation was the
tool's second largest source of noise.

Nothing quoted is read as a commitment. A scribe writing down what somebody else
said is reporting, not recording a promise, and a negated future — "X will not
do Y" — is refused in every person.

Four shapes carry a commitment without any of the words above, and all four are
read:

- **Committing in so many words.** "Will you commit to working with my office?"
  and the answer, "I certainly can commit to working with you." The verb is the
  cue. So is an expectation put on the record — "I hope you will consult with
  the public".
- **A subject the scribe dropped.** "Fangwei: will move the model to that
  format." The label already said who, so the sentence does not. Only read
  where a label is present, and only for an act: "will be sending the text" is
  an undertaking, "will be discussed on the list" has no agent in it and "will
  need more review" is a state.
- **Reported speech.** "Jankowicz says she will abide by it." Minutes are
  written afterwards, so this is their ordinary voice. The name in front of the
  reporting verb is the person committing.
- **A note-style action item.** "Mark to post the revised draft."

That last one is also the most dangerous cue in the tool, because English uses
the same shape for something else entirely: "According to this scheme", "Due to
visa rules", "Thanks to the Chair". Three tests keep them apart, and none of
them is a list of prepositions.

The word after `to` has to be able to begin an infinitive. A bare verb does; a
determiner or a pronoun does not, and that makes the `to` a preposition. `be` is
allowed, because "Mirja to be the responsible AD" is a real assignment.

The head must not be a word this document also writes in lower case. A capital
at the start of a sentence carries no information — the capital is the sentence.
When the same file says "due to" and "want to" in lower case elsewhere, the
capital was punctuation. A name never gets that contradiction, and every word of
a name has to be contradicted before the head is refused, so "Mark Nottingham"
survives a document that also contains the verb "mark".

A bullet in front of the line, or a deadline inside it, overrides that last
test. Either is independent evidence that a scribe was writing an item.

Against all of that runs one more filter: a first-person undertaking whose verb
is an act of speech inside the meeting is narration, not a commitment. Yielding,
recognising, backing up, refreshing your memory and going to the next witness do
not outlive the room.

Owners come from speaker labels. `Alex:`, `[00:14] Sam Okafor:`,
`Tony Li (TL):`, `Suresh Krishnan, Kaloom:`, `ekr:` and `<mnot>` are all read as
people; a real transcript uses every one of those shapes. A first-person
undertaking belongs to whoever is speaking. A named assignment belongs to the
person named. A collective undertaking belongs to nobody. When two of these
appear in one sentence the owner is genuinely unclear, so it is left unknown.

A heading ends the current speaker's turn, including when it sits alone on its
line — `Action items:` with nothing after it. A pasted mail quote (`> ...`) ends
it too: those are somebody else's words.

Filler is treated differently from a hypothetical. "I might look at it" and
"we'll never get this done" are rejected outright, whatever else the sentence
says. "Let me know if that works" is rejected only because nothing was promised
by when — "Let me know the vendor's answer by Friday" is kept.

What counts for that second rule is a phrase that names when work is due: `by
Friday`, `before Monday`, `within two days`, `end of week`, `on Thursday`.
Merely mentioning a time does not, or "can you hear me today?" would be recorded
as a commitment.

The filler patterns match whole utterances rather than openings, because "let me
start by welcoming everyone" and "let me start the migration" begin identically
and only one of them is noise.

Three details worth knowing, because they are where this could surprise you.

A speaker label applies to the lines that follow it until the next label. That is
how transcripts work, but it does mean an unlabelled line is attributed to
whoever spoke last. A structural label such as `Notes:` ends that turn rather
than continuing it.

A word is treated as a name when it is capitalised and is not an ordinary English
word. That is a filter, not name detection. It rejects `From:`, `TODO:` and
`Actually`; it cannot tell an unusual name from an unusual noun, so a heading it
has never heard of will read as a speaker. There is a test that says so.

An owner is not necessarily a person. Whoever the sentence names is recorded —
unless an article stands in front of the name. English does not put one in front
of a person: "Priya will send the deck" names somebody, "The Committee will hold
a hearing" and "our Chairs will decide" name a thing and a role. That single test
replaces a list of institutions, and on a real corpus the institutions arrived
almost entirely wearing "the".

Transcripts are usually hard-wrapped at seventy or eighty columns, so a sentence
routinely spans two lines. Read one line at a time, nearly half of what the tool
found on raw wrapped files was cut off, and the deadline was normally in the half
it threw away.

So the file is measured first. A hard-wrapped file has a ceiling: nearly every
line stops just short of one column, and the few that pass it are a URL, a table
row or a rule of equals signs. That ceiling is read off the 95th percentile of
the line lengths, never off the longest line — the longest line is the outlier
the ceiling has to be measured in spite of. A file needs at least forty lines
before the percentile can exclude anything, and a quarter of its lines have to
sit in the band just under the ceiling; otherwise it is note-style minutes,
where joining bullets into each other would be worse than not joining prose.

In a file measured as wrapped, a line that stops short of the ceiling without
punctuation is joined to the one below it whatever case that line starts in.
Everywhere else the join only happens when the next line begins in lower case,
which is the cautious rule. The cautious rule on its own was not enough:
political testimony is full of proper nouns, so continuations begin with a
capital constantly, and half-sentences like "Venezuelans to speak their minds
has crumbled" were left looking like action items because they began a line.

Every entry keeps the quoted sentence, the file and line it came from, and which
rules fired. You can always check the tool's work against the source. The line
number is the line the sentence started on, counted the way an editor counts:
a page break inside an old plain-text transcript is not a new line.

## Your data

- Everything stays in the directory you run it in.
- File paths are shortened before they are recorded: relative to the directory
  you ran in when the file is below it, otherwise written with `~` in place of
  your home directory. A file outside both is recorded in full, because by then
  there is nothing left to hide.
- `.gitignore` already excludes `transcripts/`, ledgers, and reports, so your own
  material does not end up in a commit by accident.
- The examples in this repository are invented. Lumen Freight does not exist, and
  neither do Alex, Sam, or Jordan.

## Tests

```bash
python3 -m unittest discover -s tests -t . -v
```

## Contributing

Bounded, useful tasks are listed in [ROADMAP.md](ROADMAP.md), and
[CONTRIBUTING.md](CONTRIBUTING.md) explains how the project is reviewed. New cue
patterns are especially welcome — they are data, they are easy to test, and every
one of them makes the tool find something it used to miss.

## Honest status

Version 0.2. The behaviour described here is covered by tests that run on every
change, and the example above is checked in and compared against real output, so
the documentation cannot drift away from the code.

What it has not had is users. If it misses things in your transcripts, that is
the most useful thing you could tell me, and an issue is welcome.

## Against real documents

Everything above says what the tool is meant to do. This section says what it
did when it was pointed at documents nobody involved with it had written.

**How this was measured.** Which 6,320 documents, how they were selected, which
of the four measurement passes each figure below belongs to, and the complete
800-sentence labelled set with its labels:
[`docs/corpus-manifest.md`](docs/corpus-manifest.md). Its opening section carries
the full account of how the 800 labels were produced, including the dispatch-by-
dispatch record.

### The corpus

6,320 real meeting records, 184 MB: 5,733 IETF working-group minutes spanning
IETF 65 in 2006 to IETF 126 in 2026, and 587 United States congressional hearing
transcripts from seven years between 2016 and 2024 (2017 and 2020 were not
sampled). Both are public records, neither was written for this tool, and no
example in this repository came from either.

### How it was scored

A tool must not be allowed to grade itself, so two measures it did not produce.
One of them is weaker than that phrasing suggests, and the weakness is stated below
rather than left for the reader to discover.

**The scribes' own answers.** Many IETF minutes carry an "Action items" block a
human wrote during the meeting. The tool never sees that block; it reads the
discussion, and the block says what a person present thought was agreed.

**A blind labelling, by a model rather than by people.** 800 sentences were drawn
uniformly at random from a population defined without reference to this tool's
rules: any sentence in the corpus containing a marker from a fixed list of ordinary
English future and obligation words. Each was marked a commitment or not by an
isolated language model instance, five in total: four labelling 200 sentences each,
and a fifth re-labelling one block of 200 to measure agreement. The fifth agreed
with the first on 197 of 200, Cohen's kappa 0.92.

No person labelled any of the 800 sentences. The isolation was real — each
instance started fresh, was given the task from linguistic criteria alone, and was
instructed not to read this tool's source and not to look for its answers, so no
labeller could have copied it. But the labels come from the same model family that
wrote the tool being graded, which satisfies "a tool must not grade itself" less
completely than human annotation would. And the kappa is not human
inter-annotator agreement: it is two runs of one model on one prompt, so read it
as rubric stability rather than as evidence that two people would mark these
sentences the same way. The scribes' own answers above do not have this problem,
and they are the measure to weight.

### What it did

| | v0.1 | v0.2 |
|---|---|---|
| precision, 800 blind labels | 0.131 | 0.348 |
| recall, 800 blind labels | 0.432 | 0.605 |
| recall, whole pipeline over whole documents | 0.318 | 0.455 |
| action items the scribes marked and it missed | 1,598 of 1,760 | 1,249 of 1,760 |
| findings quoted cut off mid-sentence | 62.6% | 11.7% |
| findings carrying a deadline | 1.5% | 3.7% |
| hard-wrapped files correctly detected as wrapped | 24% | 84% |
| total findings over the corpus | 90,529 | 63,540 |

Four rounds of fixes sit behind that, and `tests/test_corpus_defects.py` is
their regression suite: 88 tests whose fixtures are real corpus sentences rather
than invented ones.

The largest single defect was one optional apostrophe. `\bwe'?ll\b` matches the
ordinary word **well**, and `\bi'?ll\b` matches **ill** — 31,599 findings, more
than a third of everything the tool reported, came from that alone. It is now 96.

The worst was a quoted slogan recorded as an open obligation owned by the group
the slogan named. Two guards close it, and neither is a list of words.

Two of the four rounds existed to fix something an earlier round had introduced.
The cue added to catch `Mark to post the draft` also fired on the ordinary
English preposition, so a report carried owners called According, Deferring and
Due — 5.5% of all findings, now 1.8%. The line-rejoiner added to fix that
measured a file's width from its longest line, so one URL or table row hid the
wrap column and it missed 76% of the hard-wrapped files it existed for,
including the transcript it had been written from. Both were caught by measuring
again rather than by reading the summary of the fix. A synthetic fixture passes
because whoever wrote it wrote it clean; only real files disagree with you.

### What this establishes, and what it does not

It establishes that the tool survives real input. 6,320 documents, zero crashes,
zero timeouts, about a seventh of a second each.

It establishes that every defect class listed above is real, because each one was
found in a document somebody actually published.

**It does not establish that this tool is good at reading your meetings.**
Standards-body minutes and parliamentary hearings are two genres it was not
designed for, in which most sentences containing "will" are prediction,
procedure or rhetoric rather than promise. These are numbers from hostile
ground, not a description of ordinary use. No measurement on ordinary business
meeting transcripts exists, because no public corpus of them does — and a
precision of 0.348 is not a good score by any reading.

Three further limits, stated rather than buried. Both corpora are hard-wrapped
at about seventy columns, so two thirds of the sampled sentences are cut
mid-line; that is what the tool sees too, but it is harsher than
one-sentence-per-line input. The whole corpus is English, so nothing in this
section says anything at all about the Hinglish rules. And 71% of what human
scribes wrote down as an action item is still missed: on written minutes this
tool finds under a third of what a person in the room recorded.

Follow Through was built with AI assistance, under human direction and reviewed
before release.

## Licence

MIT. See [LICENSE](LICENSE).

## Author

[Waiga Arya](https://www.linkedin.com/in/waigaarya/), Director of Business Strategy and
Innovation at Sadaway Pvt. Ltd. These tools were built for my own operating problems first.
