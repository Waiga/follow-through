"""The promise that nothing leaves the machine, enforced as a test.

Follow Through's central claim is that transcripts stay local. A sentence in a
README cannot enforce that. This test reads the package's own source and fails
if any module gains the ability to open a connection or start a process.

It checks three things, because the first one alone is not enough:

* imports of modules that can reach out;
* calls to the parts of ``os`` that start another program, since ``os`` itself
  is needed for writing files safely and cannot simply be banned;
* the dynamic escape hatches — ``__import__``, ``eval``, ``exec`` — that would
  let any of the above in without an import statement to find.

Every one of these detectors has a test proving it can fail. A guard nobody has
seen fail is not a guard.
"""

import ast
import tempfile
import unittest
from pathlib import Path

import follow_through

PACKAGE = Path(follow_through.__file__).parent

#: Modules that can reach the network, start a process, or load native code.
FORBIDDEN_MODULES = frozenset(
    {
        "asyncio", "ctypes", "ftplib", "http", "imaplib", "importlib",
        "multiprocessing", "poplib", "requests", "smtplib", "socket",
        "socketserver", "ssl", "subprocess", "telnetlib", "urllib",
        "webbrowser", "xmlrpc",
    }
)

#: ``os`` is allowed, because atomic file writing needs it. These are not.
FORBIDDEN_OS_CALLS = frozenset(
    {
        "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
        "execl", "execle", "execlp", "execv", "execve", "execvp", "execvpe",
        "spawnl", "spawnle", "spawnlp", "spawnv", "spawnve", "spawnvp",
        "startfile",
    }
)

#: Ways to reach a forbidden module without writing an import statement.
FORBIDDEN_BUILTINS = frozenset({"__import__", "compile", "eval", "exec"})


def modules() -> list[Path]:
    """Every Python file in the package, including in subpackages."""
    return sorted(PACKAGE.rglob("*.py"))


def offences(source: str, filename: str = "<source>") -> set[str]:
    """Return everything in ``source`` that would break the offline promise."""
    tree = ast.parse(source, filename=filename)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    found.add(f"import {root}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                root = node.module.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    found.add(f"from {root} import ...")
        elif isinstance(node, ast.Attribute):
            value = node.value
            if isinstance(value, ast.Name) and value.id == "os":
                if node.attr in FORBIDDEN_OS_CALLS:
                    found.add(f"os.{node.attr}")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_BUILTINS:
                found.add(node.id)
    return found


class NothingLeavesTheMachine(unittest.TestCase):
    def test_there_are_modules_to_check(self):
        self.assertGreater(len(modules()), 3)

    def test_the_whole_package_is_scanned_including_subpackages(self):
        names = {path.name for path in modules()}
        self.assertIn("cli.py", names)
        self.assertIn("ledger.py", names)

    def test_no_module_can_reach_out(self):
        for module in modules():
            with self.subTest(module=str(module.relative_to(PACKAGE))):
                found = offences(module.read_text(encoding="utf-8"), str(module))
                self.assertEqual(found, set(), f"{module.name}: {sorted(found)}")


class TheGuardCanFail(unittest.TestCase):
    """Each detector, shown catching the thing it exists to catch."""

    def assert_caught(self, source: str, expected: str):
        self.assertIn(expected, offences(source))

    def test_catches_a_plain_import(self):
        self.assert_caught("import socket\n", "import socket")

    def test_catches_a_dotted_import(self):
        self.assert_caught("import urllib.request\n", "import urllib")

    def test_catches_a_from_import(self):
        self.assert_caught("from http import client\n", "from http import ...")

    def test_catches_a_process_launch_through_os(self):
        self.assert_caught("import os\nos.popen('curl example.com')\n", "os.popen")

    def test_catches_exec_through_os(self):
        self.assert_caught("import os\nos.execv('/bin/sh', [])\n", "os.execv")

    def test_catches_the_dynamic_import_hatch(self):
        self.assert_caught("x = __import__('socket')\n", "__import__")

    def test_catches_importlib(self):
        self.assert_caught("import importlib\n", "import importlib")

    def test_catches_eval_and_exec(self):
        self.assert_caught("eval('1')\n", "eval")
        self.assert_caught("exec('pass')\n", "exec")

    def test_allows_the_os_calls_the_package_actually_needs(self):
        source = "import os\nos.replace('a', 'b')\nos.fdopen(1)\n"
        self.assertEqual(offences(source), set())

    def test_scanner_reads_a_file_from_disk(self):
        # The real test reads files; prove that path works, outside the repo.
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "sample.py"
            sample.write_text("import socket\n", encoding="utf-8")
            self.assertIn("import socket", offences(sample.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
