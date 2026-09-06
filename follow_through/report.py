"""Render the ledger as Markdown and HTML.

Reports show evidence, not conclusions. Every entry carries the quoted sentence,
where it came from, and which cues fired, so a reader can check the tool's work
against the source instead of trusting it.
"""

from __future__ import annotations

import html
from pathlib import Path

from .ledger import CLOSED, OPEN
from .models import UNKNOWN, Entry

LIMITATIONS = (
    "Follow Through finds statements that look like commitments. It does not "
    "find every commitment, and some of what it finds will not be one. It does "
    "not decide who owns a commitment or when it is due unless the text says so, "
    "and it does not decide that anything was done. Read the quoted line before "
    "acting on an entry."
)


def one_line(text: str) -> str:
    """Collapse text to a single line before it is placed in a report.

    Quoted sentences and closing notes are written by people, and a note can
    contain newlines. In Markdown a newline ends the list item, so an unescaped
    note could close the list and open a heading, and a reader would see
    structure and entries that the tool never found. Collapsing to one line
    removes the only lever that has.
    """
    return " ".join(text.split())


def group_by_owner(entries: list[Entry]) -> list[tuple[str, list[Entry]]]:
    """Group entries by owner, named owners first and ``unknown`` last.

    Unknown owners get their own visible group rather than being scattered or
    dropped: an unattributed commitment is the one most likely to be lost.
    """
    groups: dict[str, list[Entry]] = {}
    for entry in entries:
        groups.setdefault(entry.owner, []).append(entry)
    named = sorted((k for k in groups if k != UNKNOWN), key=str.casefold)
    ordered = [(name, groups[name]) for name in named]
    if UNKNOWN in groups:
        ordered.append((UNKNOWN, groups[UNKNOWN]))
    return ordered


def counts(entries: list[Entry]) -> dict[str, int]:
    open_entries = [e for e in entries if e.state == OPEN]
    return {
        "total": len(entries),
        "open": len(open_entries),
        "closed": len([e for e in entries if e.state == CLOSED]),
        "open_with_due_phrase": len(
            [e for e in open_entries if e.due_phrase != UNKNOWN]
        ),
        "open_without_owner": len([e for e in open_entries if e.owner == UNKNOWN]),
    }


def _markdown_entry(entry: Entry) -> list[str]:
    due = entry.due_phrase if entry.due_phrase != UNKNOWN else "no stated deadline"
    return [
        f"- **{entry.id}** — {one_line(entry.text)}",
        f"  - Deadline: {one_line(due)}",
        f"  - Source: `{one_line(entry.source)}` line {entry.line}",
        f"  - Cues: {', '.join(entry.cues)}",
    ]


def render_markdown(entries: list[Entry]) -> str:
    figures = counts(entries)
    lines = [
        "# Follow Through report",
        "",
        f"{figures['open']} open, {figures['closed']} closed, "
        f"{figures['total']} recorded in total.",
        "",
        f"Of the open entries, {figures['open_with_due_phrase']} state a deadline "
        f"and {figures['open_without_owner']} name nobody.",
        "",
    ]

    open_entries = [e for e in entries if e.state == OPEN]
    if open_entries:
        lines.append("## Open")
        lines.append("")
        for owner, group in group_by_owner(open_entries):
            heading = "No owner stated" if owner == UNKNOWN else owner
            lines.append(f"### {heading} ({len(group)})")
            lines.append("")
            for entry in group:
                lines.extend(_markdown_entry(entry))
            lines.append("")
    else:
        lines.extend(["## Open", "", "Nothing open.", ""])

    closed_entries = [e for e in entries if e.state == CLOSED]
    if closed_entries:
        lines.extend([f"## Closed ({len(closed_entries)})", ""])
        for entry in closed_entries:
            lines.append(f"- **{entry.id}** — {one_line(entry.text)}")
            lines.append(f"  - Closed because: {one_line(entry.note)}")
        lines.append("")

    lines.extend(["## Limitations", "", LIMITATIONS, ""])
    return "\n".join(lines)


def _html_entry(entry: Entry) -> str:
    due = entry.due_phrase if entry.due_phrase != UNKNOWN else "no stated deadline"
    return (
        "<li>"
        f"<code>{html.escape(entry.id)}</code> {html.escape(one_line(entry.text))}"
        f"<dl><dt>Deadline</dt><dd>{html.escape(due)}</dd>"
        f"<dt>Source</dt><dd>{html.escape(entry.source)} line {entry.line}</dd>"
        f"<dt>Cues</dt><dd>{html.escape(', '.join(entry.cues))}</dd></dl>"
        "</li>"
    )


def render_html(entries: list[Entry]) -> str:
    figures = counts(entries)
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Follow Through report</title>",
        "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:52rem;"
        "margin:2rem auto;padding:0 1rem}dl{margin:.25rem 0 .75rem 1rem;"
        "font-size:.9rem;color:#444}dt{font-weight:600;display:inline}"
        "dd{display:inline;margin:0 1rem 0 .25rem}li{margin-bottom:.5rem}"
        "</style></head><body>",
        "<h1>Follow Through report</h1>",
        f"<p>{figures['open']} open, {figures['closed']} closed, "
        f"{figures['total']} recorded in total.</p>",
        f"<p>Of the open entries, {figures['open_with_due_phrase']} state a "
        f"deadline and {figures['open_without_owner']} name nobody.</p>",
    ]

    open_entries = [e for e in entries if e.state == OPEN]
    parts.append("<h2>Open</h2>")
    if open_entries:
        for owner, group in group_by_owner(open_entries):
            heading = "No owner stated" if owner == UNKNOWN else owner
            parts.append(f"<h3>{html.escape(heading)} ({len(group)})</h3><ul>")
            parts.extend(_html_entry(entry) for entry in group)
            parts.append("</ul>")
    else:
        parts.append("<p>Nothing open.</p>")

    closed_entries = [e for e in entries if e.state == CLOSED]
    if closed_entries:
        parts.append(f"<h2>Closed ({len(closed_entries)})</h2><ul>")
        for entry in closed_entries:
            parts.append(
                f"<li><code>{html.escape(entry.id)}</code> "
                f"{html.escape(one_line(entry.text))}<dl><dt>Closed because</dt>"
                f"<dd>{html.escape(one_line(entry.note))}</dd></dl></li>"
            )
        parts.append("</ul>")

    parts.append(f"<h2>Limitations</h2><p>{html.escape(LIMITATIONS)}</p>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def write(reports_dir: Path, entries: list[Entry]) -> tuple[Path, Path]:
    """Write both reports and return their paths."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = reports_dir / "follow-through.md"
    html_path = reports_dir / "follow-through.html"
    markdown_path.write_text(render_markdown(entries), encoding="utf-8")
    html_path.write_text(render_html(entries), encoding="utf-8")
    return markdown_path, html_path
