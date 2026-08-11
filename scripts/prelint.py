"""A dependency-free stand-in for the ruff rules this repository actually trips.

Why this exists
---------------
Development runs in two places. Code is written in a sandbox that cannot install
anything -- its package index is blocked -- and it is run locally where ruff is
installed. So `run_all.py --quick` is the authority and it is only available at
the end of a round trip. Twice now a chunk has been handed over green on tests
and red on lint, for a rule that had been checked by hand in an earlier pass and
then broken by newly written code that the earlier pass could not have seen:
once an unused import (F401), once `zip` without `strict` (B905).

The failure is not that the rules are hard. It is that checking from memory
covers the code that existed when the memory was formed.

**This is not a ruff replacement and must not be treated as one.** It implements
a deliberately small set: the rules in this repository's `select` list that have
actually fired, plus the few next to them that would fire the same way. Ruff
stays the gate. This only shortens the loop.

Usage
-----
    python scripts/prelint.py            # whole repository
    python scripts/prelint.py src tests  # named paths

Exit status is 1 when anything is reported. `# noqa` on a line suppresses every
check on that line, matching ruff closely enough for this purpose.
"""

from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path

#: From `pyproject.toml`, `[tool.ruff] line-length`. Not read from the file,
#: because parsing TOML without a dependency is more code than the check.
LINE_LENGTH = 88

#: Directories never linted, matching what ruff skips by default plus this
#: repository's virtualenv.
SKIP = {".venv", "venv", "__pycache__", ".git", "build", "dist", ".ruff_cache"}

#: Names that are ambiguous in the fonts a reviewer is likely to use (E741).
AMBIGUOUS = {"l", "I", "O"}

#: Typing spellings superseded by builtins on this repository's Python floor
#: (UP006, UP007). Matched through the syntax tree, not through the text: a
#: regex over source finds these words inside this very tuple, which is how the
#: first version of this file failed its own check.
LEGACY_TYPING = frozenset(
    {"Dict", "List", "Tuple", "Set", "FrozenSet", "Optional", "Union", "Type"}
)

Finding = tuple[str, int, str, str]  # path, line, rule, message


def _sources(roots: list[str]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        base = Path(root)
        paths = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for path in paths:
            if not path.suffix == ".py":
                continue
            if SKIP & set(path.parts):
                continue
            out.append(path)
    return out


def _sort_key(name: str) -> tuple[int, str]:
    """Ruff's isort orders CONSTANTS, then Classes, then everything else.

    This is `order-by-type`, on by default, and it is the part that has been got
    wrong twice by hand: an alphabetical list is not what ruff wants.
    """
    if name.isupper():
        return (0, name)
    if name[:1].isupper():
        return (1, name)
    return (2, name)


def _group(module: str, level: int) -> int:
    if level:
        return 3
    head = module.split(".")[0]
    if head == "__future__":
        return 0
    if head in sys.stdlib_module_names:
        return 1
    return 2


def check(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    suppressed = {i + 1 for i, ln in enumerate(lines) if "# noqa" in ln}
    found: list[Finding] = []

    def report(line: int, rule: str, message: str) -> None:
        if line not in suppressed:
            found.append((str(path), line, rule, message))

    for i, line in enumerate(lines, 1):
        if len(line) > LINE_LENGTH:
            report(i, "E501", f"line too long ({len(line)} > {LINE_LENGTH})")

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        found.append((str(path), exc.lineno or 0, "E999", exc.msg))
        return found

    _imports(tree, text, report)
    _definitions(tree, report)
    _locals(tree, report)
    _statements(tree, report)
    _calls(tree, report)
    return found


def _calls(tree: ast.Module, report) -> None:
    """B905 and UP006, from the tree rather than from the text.

    Both were regexes over source lines in the first version, and both fired on
    this file's own constants. A checker that cannot pass itself is not evidence
    about anything else.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name == "zip" and not any(
                kw.arg == "strict" for kw in node.keywords
            ):
                report(node.lineno, "B905", "zip() without an explicit strict=")
        if isinstance(node, ast.Subscript):
            base = node.value
            label = getattr(base, "id", None) or getattr(base, "attr", None)
            if label in LEGACY_TYPING:
                report(
                    node.lineno, "UP006", f"{label} is superseded by a builtin"
                )


def _module_of(node: ast.stmt) -> str:
    if isinstance(node, ast.ImportFrom):
        return "." * node.level + (node.module or "")
    return node.names[0].name  # type: ignore[attr-defined]


def _imports(tree: ast.Module, text: str, report) -> None:
    bound: dict[str, int] = {}
    blocks: list[list[ast.stmt]] = []
    current: list[ast.stmt] = []
    body_start = 0

    for index, node in enumerate(tree.body):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            body_start = index + 1
            continue
        if isinstance(node, ast.Import | ast.ImportFrom):
            current.append(node)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound[(alias.asname or alias.name).split(".")[0]] = node.lineno
            elif node.module != "__future__":
                for alias in node.names:
                    if alias.name != "*":
                        bound[alias.asname or alias.name] = node.lineno
            if index > body_start and not isinstance(
                tree.body[index - 1], ast.Import | ast.ImportFrom
            ):
                report(node.lineno, "E402", "import not at top of file")
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)

    for block in blocks:
        keys = [
            _group(_module_of(n).lstrip("."), getattr(n, "level", 0))
            for n in block
        ]
        # Group order, then within a group: plain `import x` before
        # `from x import y`, each alphabetical. That is ruff's default with
        # force-sort-within-sections off.
        order = [
            (key, isinstance(n, ast.ImportFrom), _module_of(n))
            for key, n in zip(keys, block, strict=True)
        ]
        if order != sorted(order):
            report(block[0].lineno, "I001", "import block is out of order")
        for node in block:
            if not isinstance(node, ast.ImportFrom) or len(node.names) < 2:
                continue
            names = [a.name for a in node.names]
            if names != sorted(names, key=_sort_key):
                report(
                    node.lineno,
                    "I001",
                    "imported names not in CONSTANT, Class, function order",
                )

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {
        getattr(n.value, "id", "")
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute)
    }
    for name, line in bound.items():
        if name in used or f'"{name}"' in text or f"'{name}'" in text:
            continue
        report(line, "F401", f"{name!r} imported but unused")


def _definitions(tree: ast.Module, report) -> None:
    scopes: list[list[ast.stmt]] = [tree.body]
    scopes += [n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for body in scopes:
        defs = [
            n for n in body if isinstance(n, ast.FunctionDef | ast.ClassDef)
        ]
        counts = Counter(n.name for n in defs)
        seen: set[str] = set()
        for node in defs:
            if counts[node.name] > 1 and node.name in seen:
                report(node.lineno, "F811", f"redefinition of {node.name!r}")
            seen.add(node.name)


def _locals(tree: ast.Module, report) -> None:
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        assigned: dict[str, int] = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned.setdefault(target.id, node.lineno)
        loaded = {
            n.id
            for n in ast.walk(fn)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        }
        for name, line in assigned.items():
            if name in loaded or name.startswith("_"):
                continue
            report(line, "F841", f"local {name!r} assigned but never used")


def _statements(tree: ast.Module, report) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Lambda):
            report(node.lineno, "E731", "lambda assigned to a name; use def")
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            report(node.lineno, "E722", "bare except")
        if isinstance(node, ast.arg) and node.arg in AMBIGUOUS:
            report(node.lineno, "E741", f"ambiguous argument name {node.arg!r}")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if node.id in AMBIGUOUS:
                report(node.lineno, "E741", f"ambiguous variable name {node.id!r}")
        if isinstance(node, ast.Compare):
            for op, other in zip(node.ops, node.comparators, strict=True):
                if not isinstance(op, ast.Eq | ast.NotEq):
                    continue
                if isinstance(other, ast.Constant) and other.value is None:
                    report(node.lineno, "E711", "comparison to None; use is")
                if isinstance(other, ast.Constant) and other.value is True:
                    report(node.lineno, "E712", "comparison to True")


def main(argv: list[str]) -> int:
    roots = argv[1:] or ["src", "tests", "experiments", "scripts", "data"]
    roots = [r for r in roots if Path(r).exists()]
    findings: list[Finding] = []
    for path in _sources(roots):
        findings.extend(check(path))

    if not findings:
        print(f"prelint clean over {len(_sources(roots))} files")
        print("this is not ruff; run scripts/run_all.py --quick for the real gate")
        return 0

    for path, line, rule, message in sorted(findings):
        print(f"{path}:{line}: {rule} {message}")
    print(f"\n{len(findings)} finding(s). Not exhaustive: ruff is still the gate.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
