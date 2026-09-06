# Roadmap

Follow Through is deliberately small. The list below is what would genuinely make
it better, not a plan to grow it.

Each item is scoped so one person can finish it without waiting on anyone. If you
want one, open an issue saying so before you start, so two people do not build the
same thing.

## Good first contributions

**More cue patterns.** The rules live in `follow_through/cues.py` as plain data.
Add the phrasings you actually hear — regional English, industry habits, ways of
committing that the current list misses. Each new pattern needs one test showing
what it now catches and one showing what it still correctly rejects.

**More exclusions.** The opposite problem. If the tool records something that was
clearly not a commitment, that is a bug worth a pattern and a test.

**Other transcript formats.** Speaker labels are recognised as `Name:` with an
optional timestamp. WebVTT and SRT files are common exports and are not handled.
Reading them means a small parser that yields the same lines and speakers the
extractor already expects, not a change to the extractor.

**A plain-text report.** Markdown and HTML exist. Something that reads well pasted
into a chat message does not.

## Larger, still bounded

**Multiple transcripts in one run.** `track` takes one file. Taking a directory,
in a stable order, with the same deduplication, is a contained change.

**A `reopen` command.** Closing is one-way today. Reopening with a required reason
would need the same care: a recorded human judgement, not a silent state flip.

**Grouping a series.** A weekly call produces a transcript a week. There is no way
to ask what came out of one series over a month, because the ledger has no notion
of a series.

## Deliberately not planned

These are not oversights.

- **Model-assisted extraction.** It would find more, and it would mean sending
  transcripts somewhere. The offline guarantee is the point of the tool.
- **Calendar dates.** Converting `by Friday` to a date means assuming the date the
  conversation happened. The tool records the phrase and lets a person decide.
- **Reminders, notifications, integrations.** Follow Through produces a list. What
  chases the list is a person's job, or another tool's.
- **A hosted version.** No.
