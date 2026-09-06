# Follow Through — Design

**Date:** 6 September 2026
**Author:** Waiga Arya
**Status:** Implemented in v0.1.0.

This is the design the first version was built from, kept in the repository so a
contributor can see what was decided and why, not only what the code does.

## The problem

People commit to things out loud. In a meeting, on a call, in a voice note. The
commitment is real, the record is not: it exists only inside a transcript nobody
re-reads. Days later nobody can say what was promised, by whom, or whether it
happened.

Transcription is now cheap and universal. Nearly every meeting tool emits text.
The gap is not capture. The gap is that captured speech is never converted into
a list of obligations that can be closed.

## What Follow Through does

Follow Through is a local command-line tool. It reads a transcript or a notes
file, finds statements that commit someone to a future action, and tracks each
one until it is explicitly closed.

It is deterministic and offline. It has no network access, no API keys, no
model calls, and no runtime dependencies beyond the Python standard library.
Text that goes in never leaves the machine.

## What Follow Through refuses to do

This section is the product, not a disclaimer.

- It does not claim to find every commitment. Recall is bounded by the patterns
  it can see in text, and it says so in every report.
- It does not guess an owner. If the transcript does not say who committed, the
  owner is recorded as `unknown` and stays `unknown`.
- It does not guess a deadline. No date phrase means `due: unknown`, never a
  default of "this week".
- It does not decide that something was done. Closure is a human act, recorded
  with a reason.
- It does not score a person, rank reliability, or produce a compliance metric.
- It does not send anything anywhere.

The design inherits one rule from Repo Scout: absence of evidence is reported as
unknown, never as a confirmed negative.

## Users

The first user is an operator who speaks their obligations faster than they can
record them, and who already has transcripts. The tool is useful to anyone in
that position: founders, managers, consultants, anyone running recorded calls.

## Interface

```
follow-through extract <file>            show candidate commitments found in a file
follow-through track <file>              add newly found commitments to the local ledger
follow-through list [--state ...]        show ledger entries
follow-through close <id> --note "..."   record that an entry is closed, and why
follow-through report                    write a Markdown and HTML report
```

Global options precede the command, matching Repo Scout:

```
follow-through --ledger-dir ./ledger track meeting.txt
follow-through --reports-dir ./reports report
```

## How extraction works

The extractor is a set of explicit, inspectable rules. There is no model.

**Segmentation.** The file is split into lines, then into sentences. Speaker
labels of the form `Name:` at the start of a line are recognised and become the
speaking context for the sentences that follow, until the next label.

**Commitment cues.** A sentence becomes a candidate when it matches at least one
cue family:

- *First person undertaking* — `I'll`, `I will`, `I'm going to`, `let me`,
  `I can have`, `we'll`, `we will`, `we're going to`.
- *Assignment to another party* — `can you`, `could you`, `please send`,
  `<Name> will`, `<Name> is going to`.

**Owner resolution.** For a first-person undertaking, the owner is the current
speaker label if one exists, otherwise `unknown`. For a named assignment, the
owner is the person named. A collective undertaking — "we'll decide on Friday" —
belongs to nobody, because recording it against whoever said "we" would be an
invention. An open ask does not say who was addressed, so it stays `unknown`.
When two of these fire in one sentence the owner is unclear, and unclear is
recorded as `unknown`. The owner is never inferred from context, frequency, or
who spoke most.

**What counts as a name.** A capitalised word is treated as a name only when no
word in it is an ordinary English word. This is a filter, not name detection: it
can reject, never confirm. It exists because the first version produced owners
called "From", "TODO" and "Brien" — the last of those from splitting "O'Brien" in
half — and the second still produced "Actually" and "Hopefully". Names are matched
without assuming ASCII, so "José" and "Алекс" work, and April, May and June are
allowed through because they are given names as often as months.

The filter cannot close the class, only narrow it. A capitalised word in the
subject position is indistinguishable from a name in one line of text. Two
consequences are accepted and documented rather than hidden: a heading the list
has never seen will read as a speaker, and a named party may be a team or a
company rather than a person. The second is not a defect — "Legal will review the
contract" names who is responsible, and refusing it would lose a real commitment.

**Filler versus hypotheticals.** Exclusions come in two strengths. A hypothetical,
a negation, or something already done is rejected outright — a deadline never
rescues "we'll never get this done by Friday". Conversational filler is rejected
only when nothing was promised by when.

Two details make that rule safe. The overriding phrase must set a deadline
("by Friday", "before Monday", "within two days"), not merely mention a time,
or "can you hear me today?" would be recorded. And each filler pattern must
match a whole utterance rather than an opening: an earlier version matched
"let me start", "let me add" and "let me finish", and threw away every genuine
commitment that began with them. Dropping a real commitment is the worst failure
this tool has, and it was doing it silently.

**Sentence boundaries.** A fragment ending in an abbreviation or an initial is
joined to the next one, so "Dr. Smith will send it" stays whole. "No." is not on
that list: as an abbreviation for "number" it is rare in speech, and treating it
as one joined "the answer is no." to the commitment after it, whereupon the
exclusion phrase in the first half discarded both.

**Due-date cues.** Recognised phrases are recorded verbatim as evidence:
`by <weekday>`, `by <month> <day>`, `today`, `tomorrow`, `tonight`, `EOD`,
`end of day`, `end of week`, `this week`, `next week`, `in N days`,
`by the <ordinal>`. The phrase is stored as text. No calendar date is computed,
because computing one would require assuming the date the conversation happened.

**Exclusions.** A sentence is rejected when it is a question about capability
rather than an ask (`will I be able to`), when it is hypothetical or negated
(`if I`, `I would have`, `I don't think I'll`, `I might`, `maybe I'll`), or when
the undertaking is in the past (`I sent`, `I already did`).

**Output.** Every candidate carries the cue families that fired, the exact source
line number, and the quoted sentence. A reader can always check the tool's work
against the source.

## The ledger

The ledger is a single JSON file, written locally, holding one record per
commitment: a stable id, the quoted text, owner, due phrase, source file and
line, the cues that fired, the state, and the closing note if closed.

Identity is a hash of the normalised quoted text, the owner, and the source file.
Running `track` twice over the same file adds nothing the second time; running it
over that file after it has grown adds only what is new.

The source belongs in the identity. People promise the same thing, in the same
words, every week. Without it, week two's promise would match week one's closed
entry and disappear — a confirmed "nothing open" where the honest answer is that
a new commitment exists.

States are `open` and `closed`, and a ledger containing anything else is refused
on load rather than passed through: an unrecognised state would leave an entry
counted in the total, listed under neither heading, and reported to nobody. A
closed entry with no reason is refused for the same kind of reason — closure is
supposed to be a recorded human judgement.

There is deliberately no `overdue` state, because the tool does not compute dates.
A report can show which entries have a due phrase and are still open; it will not
assert that a deadline passed.

## Reports

`report` writes Markdown and HTML. The report opens with counts, then lists open
entries grouped by owner, with `unknown` owners in their own group so they are
visible rather than buried. Every entry shows its evidence. Every report carries
the same limitations paragraph as the README.

## Structure

```
follow_through/
  cli.py          argument parsing, command dispatch, exit codes
  extract.py      segmentation, cue matching, owner and due resolution
  cues.py         the cue tables, as data
  ledger.py       load, merge, save, close; identity hashing
  report.py       Markdown and HTML rendering
  models.py       the record types shared across the above
```

Each module has one job and can be read alone. `cues.py` is data so the rules can
be reviewed and extended by a contributor without touching logic.

## Safety for public release

- No network calls exist anywhere in the package. A test parses the package's own
  source on every run and fails on a forbidden import, on the `os` calls that
  launch another program, or on `__import__`, `eval`, `compile` or `exec`. Each
  detector has its own test proving it can fail.
- No file is written outside the ledger and reports directories.
- The repository ships only invented example transcripts, with invented people
  and companies.
- `.gitignore` excludes ledgers, reports, and any `transcripts/` directory, so a
  contributor cannot casually commit their own material.
- The five Repo Scout release gates apply: authorship, confidentiality,
  engineering quality, project clarity, external confirmation.

## Testing

Unit tests cover each cue family, each exclusion, owner resolution including the
unknown path, due-phrase capture, ledger identity and idempotent merge, closure
recording, and report rendering. One end-to-end test runs the documented example and compares against a
checked-in expected report, and another checks that the listing printed in the
README is still what the tool prints.

The example transcript doubles as the exclusion fixture, and every line it
expects to reject carries a real commitment cue. The first version's rejected
lines carried none, which meant the end-to-end test passed with the entire
exclusion table deleted. A fixture that appears to test something and does not is
worse than no fixture.

## Out of scope for v0.1

Calendar dates, reminders, notifications, calendar or email integration, audio
input, model-assisted extraction, multi-user state, and any hosted component.
Each of these is a defensible future step; none is needed to make the tool useful
on day one.
