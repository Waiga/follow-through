# Security

## Reporting something

If you find a vulnerability, or find real personal or company information that
has ended up in this repository, please report it privately using GitHub's
[report a vulnerability](https://github.com/Waiga/follow-through/security/advisories/new)
form rather than opening a public issue.

Please include enough detail to reproduce it. You will get an acknowledgement,
and I will tell you what I intend to do and when.

## What this tool does and does not do

Follow Through reads text files you point it at and writes a ledger and reports
into directories you choose. It makes no network connection, runs no other
program, and requires no credentials.

`tests/test_offline.py` enforces that by parsing the package's own source on
every test run. It fails if any module imports something that can reach the
network or load native code, calls one of the `os` functions that launches
another program, or uses `__import__`, `eval`, `compile` or `exec` to get at
either indirectly. `os` itself is permitted, because writing a file atomically
needs it, so the check is on the specific calls rather than the import.

What this does not cover: it is a static check of this package, not of Python
itself or of anything you install alongside it, and a determined author could
still find a construction it does not model. It is a guard against drift, not a
sandbox.

It reads whatever you give it, so treat the ledger and any report you generate as
being as sensitive as the transcript they came from. Reports are plain files;
sharing one shares its contents.

## Supported versions

The latest release is supported. This is a small project maintained by one
person, and I will say so plainly if I cannot fix something.
