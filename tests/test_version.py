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


class TheTwoCopiesOfTheVersionAgree(unittest.TestCase):
    def test_the_package_reports_what_pyproject_declares(self):
        self.assertEqual(
            follow_through.__version__,
            declared_version(),
            "follow_through.__version__ and pyproject.toml disagree. Both have "
            "to be bumped together, or the release announces the wrong version.",
        )

    def test_the_version_looks_like_a_version(self):
        self.assertRegex(follow_through.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
