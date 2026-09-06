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

It runs entirely on your machine. No account, no API key, no network call. Your
transcripts are never uploaded anywhere, because the tool has no way to upload
anything — and there is a test in this repository that fails if that ever stops
being true.

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
5839899d7645  Sam                   by Friday             I'll send the signed lease to finance by Friday.
edee66854bf3  owner not stated      no stated deadline    Can you also share the insurance certificate?
b624cb073898  Jordan                by October 3          Jordan will pull the carrier rates by October 3.
de7265f453ff  Jordan                in 3 days             I'll have a first cut ready in 3 days.
87f684df85d6  Alex                  no stated deadline    We'll need to decide on the second shift before the move.
d6f02c843675  Jordan                tonight               Let me draft the shift plan tonight.
2124eabca805  owner not stated      no stated deadline    Please confirm the headcount with HR.
f8fdc884499c  Alex                  today                 I'll update the risk register today.
```

`extract` records nothing. When the list looks right, keep it:

```bash
follow-through track examples/weekly-sync.txt
```

That writes a ledger to `.follow-through/ledger.json`. Run it again over a longer
transcript from the same series and only the new commitments are added — nothing
is duplicated, and nothing you have already closed comes back.

See what is still open, close something, and write a report:

```bash
follow-through list
follow-through close 5839 --note "lease countersigned and filed"
follow-through report
```

`report` writes Markdown and HTML to `reports/`. Open commitments are grouped by
person, with the unattributed ones in their own visible group — those are the
ones that actually go missing.

A worked example of the finished report is in
[`examples/expected-report.md`](examples/expected-report.md).

## What it will not do

This list is the design, not a disclaimer.

- **It will not find every commitment.** It matches patterns in text. Something
  phrased unusually will be missed, and some of what it finds will not really be
  a commitment. Every report says so.
- **It will not guess who owns something.** If the transcript does not say, the
  owner stays `unknown`. It will not attribute a line to whoever was talking most.
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
assignment belongs to the person named. When both appear in one sentence the
owner is genuinely unclear, so it is left unknown.

Every entry keeps the quoted sentence, the file and line it came from, and which
rules fired. You can always check the tool's work against the source.

## Your data

- Everything stays in the directory you run it in.
- File paths inside your working directory are recorded relative to it, so a
  report you share does not carry the shape of your home directory.
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
