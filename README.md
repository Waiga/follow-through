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
transcription tools return for most of India. That is not a bonus feature. On a
real meeting transcript, English-only rules found zero commitments in a
conversation that contained seven, because every promise in it looked like
"main hi follow up dalta hu".

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
python3 -m pip install --no-deps .
```

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
people to own them. So a sentence has to contain a Hindi function word — `hai`,
`ko`, `kar`, `nahi` — before any of them is allowed near it. The cost is that a
two-word fragment with no Hindi in it is left alone; that is the right trade.

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

## How it decides

The rules are ordinary regular expressions, kept together as data in
[`follow_through/cues.py`](follow_through/cues.py) so you can read and extend
them without touching any logic. There is no model involved.

A sentence becomes a candidate when it contains someone undertaking to do
something (`I'll`, `we will`, `let me`) or handing work to somebody else
(`can you`, `please send`, `Priya will`). It is rejected when it is hypothetical,
negated, tentative, or already in the past — `if I get time`, `I don't think I'll`,
`I might`, `I already sent`.

Owners come from speaker labels (`Alex:` at the start of a line, with or without a
timestamp). A first-person undertaking belongs to whoever is speaking. A named
assignment belongs to the person named. A collective undertaking belongs to
nobody. When two of these appear in one sentence the owner is genuinely unclear,
so it is left unknown.

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

An owner is not necessarily a person. Whoever the sentence names is recorded.

Every entry keeps the quoted sentence, the file and line it came from, and which
rules fired. You can always check the tool's work against the source.

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

Version 0.1. It is a first release. The behaviour described here is covered by
tests that run on every change, and the example above is checked in and compared
against real output, so the documentation cannot drift away from the code.

What it has not had is users. The cue patterns reflect English as spoken in
business meetings, and they have not been tested against many people's
transcripts. If it misses things in yours, that is the most useful thing you
could tell me, and an issue is welcome.

Follow Through was built with AI assistance, under human direction and reviewed
before release.

## Licence

MIT. See [LICENSE](LICENSE).
