"""The version is written in two places. This is what stops them drifting.

A hand-written version string agrees with itself everywhere it appears in the
source tree, so no ordinary test notices when one copy is bumped for a release
and the other is not. The package then reports a version it is not, and the
first person to find out is whoever installed it.

Reading the version from the installed metadata would remove the duplication,
but it needs importlib, and tests/test_offline.py refuses importlib because it
can import anything at all including a socket. The offline guarantee is worth
more than the tidiness, so the duplication stays and this file watches it.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import follow_through

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
README = Path(__file__).resolve().parent.parent / "README.md"


def declared_version() -> str:
    """The version in pyproject.toml, read without a TOML parser.

    tomllib exists from Python 3.11 and this package supports it, but the field
    is a plain quoted string at the top level and a regex keeps this file from
    depending on the parser being present under every runner.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise AssertionError("pyproject.toml has no top-level version field")
    return match.group(1)


def version_the_readme_claims() -> str:
    """The version the README's Honest status section states, as major.minor.

    That section is the one place a reader is told which version they hold, and
    it was written by hand in prose, so no version bump touches it. It drifted:
    0.3.0 shipped while this line still read 0.2, inside a paragraph promising
    the documentation cannot drift away from the code. The anchor is the start
    of a line so the historical v0.1 and v0.2 measurement table is not matched.
    """
    text = README.read_text(encoding="utf-8")
    match = re.search(r"^Version (\d+\.\d+)\.", text, re.MULTILINE)
    if match is None:
        raise AssertionError("README.md has no 'Version X.Y.' line")
    return match.group(1)


class TheThreeCopiesOfTheVersionAgree(unittest.TestCase):
    def test_the_package_reports_what_pyproject_declares(self):
        self.assertEqual(
            follow_through.__version__,
            declared_version(),
            "follow_through.__version__ and pyproject.toml disagree. Both have "
            "to be bumped together, or the release announces the wrong version.",
        )

    def test_the_readme_states_the_version_that_ships(self):
        major_minor = ".".join(follow_through.__version__.split(".")[:2])
        self.assertEqual(
            version_the_readme_claims(),
            major_minor,
            "README.md's Honest status section names a different version from "
            "the one that ships. A reader is told which version they hold in "
            "that paragraph and nowhere else.",
        )

    def test_the_version_looks_like_a_version(self):
        self.assertRegex(follow_through.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
