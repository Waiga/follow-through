"""Follow Through: find the commitments in a transcript and track them to closure.

Offline by design. Nothing in this package opens a network connection.
"""

# This string is written here and again in pyproject.toml, which is exactly the
# shape of mistake that ships a release announcing the wrong version: the copy
# agrees with itself everywhere in the source tree, so nothing notices. Reading
# it from the installed metadata instead would mean importing importlib, and
# tests/test_offline.py refuses that on purpose — importlib can reach anything.
# The guard is worth more than the convenience, so the duplication stays and
# tests/test_version.py fails if the two copies ever disagree.
__version__ = "0.2.1"

__all__ = ["__version__"]
