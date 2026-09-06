"""Record types shared across extraction, the ledger, and reporting."""

from __future__ import annotations

import dataclasses
import hashlib
import re

UNKNOWN = "unknown"

_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Lowercase and collapse whitespace, for identity only.

    Used to decide whether two quoted sentences are the same commitment. Never
    used for display: reports always show the original text.
    """
    return _WHITESPACE.sub(" ", text.strip().lower())


@dataclasses.dataclass(frozen=True)
class Candidate:
    """A commitment-shaped statement found in a source file.

    ``owner`` and ``due_phrase`` are ``UNKNOWN`` when the text does not say.
    They are never inferred.
    """

    text: str
    owner: str
    due_phrase: str
    cues: tuple[str, ...]
    source: str
    line: int

    @property
    def identity(self) -> str:
        """Stable short id for this commitment.

        Derived from the normalised text, the owner, and the file it came from.

        Text and owner alone are not enough. People promise the same thing every
        week, in the same words, in a different meeting. Ignoring the source
        would mean the second week's promise silently matched the first week's
        closed entry and vanished: a confirmed "nothing open" where the honest
        answer is that a new commitment exists.

        Including the source keeps re-running over the same growing transcript
        idempotent, which is the case the deduplication is actually for.
        """
        digest = hashlib.sha256(
            f"{normalise(self.text)}\x00{self.owner}\x00{self.source}".encode("utf-8")
        ).hexdigest()
        return digest[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.identity,
            "text": self.text,
            "owner": self.owner,
            "due_phrase": self.due_phrase,
            "cues": list(self.cues),
            "source": self.source,
            "line": self.line,
        }


@dataclasses.dataclass
class Entry:
    """A ledger record: a candidate plus its state and closing note."""

    id: str
    text: str
    owner: str
    due_phrase: str
    cues: tuple[str, ...]
    source: str
    line: int
    state: str = "open"
    note: str = ""

    @classmethod
    def from_candidate(cls, candidate: Candidate) -> "Entry":
        return cls(
            id=candidate.identity,
            text=candidate.text,
            owner=candidate.owner,
            due_phrase=candidate.due_phrase,
            cues=tuple(candidate.cues),
            source=candidate.source,
            line=candidate.line,
        )

    @classmethod
    def from_dict(cls, raw: dict) -> "Entry":
        return cls(
            id=raw["id"],
            text=raw["text"],
            owner=raw.get("owner", UNKNOWN),
            due_phrase=raw.get("due_phrase", UNKNOWN),
            cues=tuple(raw.get("cues", ())),
            source=raw.get("source", ""),
            line=int(raw.get("line", 0)),
            state=raw.get("state", "open"),
            note=raw.get("note", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "owner": self.owner,
            "due_phrase": self.due_phrase,
            "cues": list(self.cues),
            "source": self.source,
            "line": self.line,
            "state": self.state,
            "note": self.note,
        }
