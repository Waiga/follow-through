"""The promise that nothing leaves the machine, enforced as a test.

Follow Through's central claim is that transcripts stay local. A README sentence
cannot enforce that. This test reads the package's own source and fails if any
module imports something capable of opening a connection or starting a process.
"""

import ast
import unittest
from pathlib import Path

import follow_through

PACKAGE = Path(follow_through.__file__).parent

#: Anything here can reach the network or hand work to another program.
FORBIDDEN = {
    "asyncio",
    "ftplib",
    "http",
    "imaplib",
    "poplib",
    "requests",
    "smtplib",
    "socket",
    "socketserver",
    "ssl",
    "subprocess",
    "telnetlib",
    "urllib",
    "webbrowser",
    "xmlrpc",
}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


class NothingLeavesTheMachine(unittest.TestCase):
    def test_the_package_has_modules_to_check(self):
        self.assertGreater(len(list(PACKAGE.glob("*.py"))), 3)

    def test_no_module_imports_anything_that_can_reach_out(self):
        for module in sorted(PACKAGE.glob("*.py")):
            with self.subTest(module=module.name):
                offending = imported_roots(module) & FORBIDDEN
                self.assertEqual(
                    offending,
                    set(),
                    f"{module.name} imports {sorted(offending)}",
                )

    def test_the_check_would_catch_a_violation(self):
        # A guard that cannot fail is not a guard.
        sample = PACKAGE.parent / "tests" / "_offline_fixture.py"
        sample.write_text("import socket\n", encoding="utf-8")
        try:
            self.assertIn("socket", imported_roots(sample))
        finally:
            sample.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
