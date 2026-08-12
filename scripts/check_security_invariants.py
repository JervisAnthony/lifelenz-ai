"""Check narrow, deterministic LifeLenz source-security invariants."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_DATABASE_SUFFIXES = (".db", ".db-journal", ".db-shm", ".db-wal", ".sqlite", ".sqlite3")
_PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"
_BEARER_TOKEN_PATTERN = re.compile(r"Bearer\s+eyJ[A-Za-z0-9_-]+\.")
_DISABLED_JWT_PATTERN = re.compile(r"['\"]verify_(?:signature|exp)['\"]\s*:\s*False")
_PLAINTEXT_PASSWORD_COLUMN = re.compile(r"\bpassword\s+TEXT\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Violation:
    """A safe path-and-rule finding that never includes matched source content."""

    path: Path
    rule: str


def _candidate_files(root: Path) -> tuple[Path, ...]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return tuple(
            path
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts
        )
    return tuple(root / entry.decode() for entry in result.stdout.split(b"\0") if entry)


def _artifact_violations(root: Path, files: tuple[Path, ...]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        relative = path.relative_to(root)
        name = relative.name
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            violations.append(Violation(relative, "tracked-environment-file"))
        if name.casefold().endswith(_DATABASE_SUFFIXES):
            violations.append(Violation(relative, "tracked-database-file"))
    return violations


def _module_string_constants(tree: ast.AST) -> dict[str, str]:
    constants: dict[str, str] = {}
    if not isinstance(tree, ast.Module):
        return constants
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if (
            isinstance(target, ast.Name)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            constants[target.id] = statement.value.value
    return constants


def _literal_string(node: ast.AST, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _jwt_decode_violation(tree: ast.AST) -> bool:
    constants = _module_string_constants(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "decode" or not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "jwt":
            continue
        algorithms = next((item.value for item in node.keywords if item.arg == "algorithms"), None)
        if not isinstance(algorithms, ast.List) or len(algorithms.elts) != 1:
            return True
        if _literal_string(algorithms.elts[0], constants) != "HS256":
            return True
    return False


def _python_violations(relative: Path, text: str) -> list[Violation]:
    violations: list[Violation] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [Violation(relative, "unparseable-production-python")]
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "eval"
        ):
            violations.append(Violation(relative, "dynamic-eval"))
            break
    if any(
        (isinstance(node, ast.Import) and any(alias.name == "pickle" for alias in node.names))
        or (isinstance(node, ast.ImportFrom) and node.module == "pickle")
        for node in ast.walk(tree)
    ):
        violations.append(Violation(relative, "pickle-import"))
    if _jwt_decode_violation(tree):
        violations.append(Violation(relative, "jwt-algorithm-not-fixed-hs256"))
    return violations


def check_repository(root: Path) -> tuple[Violation, ...]:
    """Return deterministic findings for tracked artifacts and production source."""
    resolved = root.resolve()
    files = _candidate_files(resolved)
    violations = _artifact_violations(resolved, files)
    for path in files:
        relative = path.relative_to(resolved)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _PRIVATE_KEY_MARKER in text:
            violations.append(Violation(relative, "private-key-material"))
        if _BEARER_TOKEN_PATTERN.search(text):
            violations.append(Violation(relative, "bearer-token-fixture"))
        if relative.parts[:2] == ("src", "lifelenz"):
            if path.suffix == ".py":
                violations.extend(_python_violations(relative, text))
            if _DISABLED_JWT_PATTERN.search(text):
                violations.append(Violation(relative, "disabled-jwt-verification"))
            if _PLAINTEXT_PASSWORD_COLUMN.search(text):
                violations.append(Violation(relative, "plaintext-password-column"))
    return tuple(sorted(set(violations), key=lambda item: (item.path.as_posix(), item.rule)))


def main(argv: list[str] | None = None) -> int:
    """Run the repository check without printing source or secret contents."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    violations = check_repository(args.root)
    if violations:
        for violation in violations:
            print(f"{violation.path.as_posix()}: {violation.rule}")
        return 1
    print("Security invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
