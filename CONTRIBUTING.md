# Contributing

Contributions are welcome, including the kind that tell me the tool is wrong.

## Before you start

Open an issue describing what you intend to change. For a bug, the most useful
issue contains a short piece of transcript text that reproduces it — invented
text, please, not a real meeting. For a new feature, check
[ROADMAP.md](ROADMAP.md); the "deliberately not planned" section explains what
this tool will not become and why.

## Never include real material

This project must stay safe to read, clone, and fork. Do not put real transcripts,
real names, real companies, credentials, or internal information into an issue, a
test, an example, or a commit. Invented examples only. If you find something real
in the repository, please report it privately as described in
[SECURITY.md](SECURITY.md).

## Making a change

```bash
python3 -m unittest discover -s tests -t . -v
```

Everything must pass before and after your change.

- Behaviour changes need a test that fails without the change.
- New cue patterns need two tests: one showing what is now caught, one showing
  what is still correctly rejected. A pattern that catches more by also catching
  ordinary sentences is not an improvement.
- Keep the offline guarantee. `tests/test_offline.py` fails if any module in the
  package imports something capable of opening a connection or starting a
  process. Do not weaken it.
- Match the surrounding style. Comments explain why, not what.

## What review looks like

I read every change myself and I will say plainly what I think. Expect questions
about whether a new rule creates false positives, and expect to be asked for a
test that proves it does not. Disagreement is fine; the tests usually settle it.

Credit stays with the person who wrote the change. Commits keep their author.
