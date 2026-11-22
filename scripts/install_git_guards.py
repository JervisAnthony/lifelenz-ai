"""Opt in to clone-local Git guards without replacing another hook setup."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

HOOKS = ("pre-commit", "pre-push")
SETTINGS = {
    "core.hooksPath": ".githooks",
    "branch.autoSetupMerge": "simple",
    "push.default": "simple",
}


class GuardInstallError(RuntimeError):
    """A prerequisite, configuration operation, or rollback failed."""


def _git(
    root: Path, *args: str, allowed: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    except OSError as error:
        raise GuardInstallError(f"Cannot run Git: {error}") from error
    if result.returncode not in allowed:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GuardInstallError(f"git {' '.join(args)} failed ({result.returncode}): {detail}")
    return result


def _values(root: Path, key: str, *, local: bool = False) -> tuple[str, ...]:
    scope = ("--local",) if local else ()
    result = _git(root, "config", *scope, "--null", "--get-all", key, allowed=(0, 1))
    if result.returncode == 1:
        return ()
    return tuple(result.stdout.decode("utf-8").removesuffix("\0").split("\0"))


def _effective_hook_path(root: Path, *, local: bool = False) -> Path | None:
    scope = ("--local",) if local else ()
    result = _git(root, "config", *scope, "--path", "--get", "core.hooksPath", allowed=(0, 1))
    if result.returncode == 1:
        return None
    return (root / result.stdout.decode("utf-8").removesuffix("\n")).resolve()


def _prerequisites(root: Path) -> None:
    hooks_dir = root / ".githooks"
    if hooks_dir.is_symlink():
        raise GuardInstallError(".githooks must be a tracked directory, not a symlink.")
    for name in HOOKS:
        relative = f".githooks/{name}"
        hook = root / relative
        entry = _git(root, "ls-files", "--stage", "--", relative).stdout.decode("utf-8")
        if not entry.startswith("100755 ") or entry.count("\n") != 1 or " 0\t" not in entry:
            raise GuardInstallError(f"{relative} must be tracked at stage 0 with Git mode 100755.")
        if hook.is_symlink() or not hook.is_file():
            raise GuardInstallError(f"Missing regular hook file: {relative}")
        content = hook.read_bytes()
        if (
            not content.startswith(b"#!/bin/sh\n")
            or b"\r" in content
            or not content.endswith(b"\n")
        ):
            raise GuardInstallError(f"{relative} requires a POSIX sh shebang and LF line endings.")
        if content != _git(root, "show", f":{relative}").stdout:
            raise GuardInstallError(f"{relative} differs from the tracked index; review it first.")
        if not os.access(hook, os.X_OK):
            raise GuardInstallError(
                f"{relative} is not executable; restore its checkout permissions."
            )

    effective = _effective_hook_path(root)
    if effective is not None:
        if effective != hooks_dir.resolve():
            raise GuardInstallError(
                "Another effective core.hooksPath would be displaced. Inspect "
                "git config --show-origin --get core.hooksPath and reconcile it manually; "
                "no settings changed."
            )
        return
    default_path = _git(root, "rev-parse", "--git-path", "hooks").stdout.decode().strip()
    default_hooks = root / default_path
    if default_hooks.is_dir():
        active = [
            hook.name
            for hook in default_hooks.iterdir()
            if not hook.name.endswith(".sample") and hook.is_file() and os.access(hook, os.X_OK)
        ]
        if active:
            raise GuardInstallError(
                "Active default-directory hooks would be displaced: "
                + ", ".join(sorted(active))
                + ". Reconcile the hook setup manually; no settings changed."
            )


def _incomplete(root: Path) -> list[str]:
    missing = []
    for key, desired in SETTINGS.items():
        local = _values(root, key, local=True)
        effective = _values(root, key)
        if key == "core.hooksPath":
            desired_path = (root / ".githooks").resolve()
            matches = (
                len(local) == 1
                and _effective_hook_path(root, local=True) == desired_path
                and _effective_hook_path(root) == desired_path
            )
        else:
            matches = local == (desired,) and bool(effective) and effective[-1] == desired
        if not matches:
            missing.append(key)
    return missing


def _restore(root: Path, key: str, values: tuple[str, ...]) -> None:
    _git(root, "config", "--local", "--unset-all", key, allowed=(0, 5))
    for value in values:
        _git(root, "config", "--local", "--add", key, value)


def install(root: Path) -> None:
    """Enable all settings, restoring prior local values if any write/check fails."""
    previous = {key: _values(root, key, local=True) for key in SETTINGS}
    changed = []
    try:
        for key, desired in SETTINGS.items():
            if key not in _incomplete(root):
                continue
            changed.append(key)
            _git(root, "config", "--local", "--replace-all", key, desired)
        if incomplete := _incomplete(root):
            raise GuardInstallError("Effective settings are overridden: " + ", ".join(incomplete))
    except (GuardInstallError, OSError, UnicodeError) as error:
        failures = []
        for key in reversed(changed):
            try:
                _restore(root, key, previous[key])
            except (GuardInstallError, OSError, UnicodeError) as restore_error:
                failures.append(str(restore_error))
        if failures:
            raise GuardInstallError(
                f"{error}; rollback incomplete: {'; '.join(failures)}"
            ) from error
        raise GuardInstallError(f"{error}; prior local settings restored.") from error


def main(argv: list[str] | None = None) -> int:
    """Install from the caller's repository, or inspect it without writing with --check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="read-only verification; no Git writes"
    )
    args = parser.parse_args(argv)
    try:
        root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").stdout.decode().strip())
        _prerequisites(root)
        if args.check:
            if incomplete := _incomplete(root):
                raise GuardInstallError(
                    "Guards/settings inactive or conflicting: " + ", ".join(incomplete)
                )
        else:
            install(root)
        installed = {key: _values(root, key, local=True)[-1] for key in SETTINGS}
    except (GuardInstallError, OSError, UnicodeError) as error:
        print(f"Git guards: {error}", file=sys.stderr)
        return 1
    print("Git guards active (clone-local configuration; no existing upstreams changed):")
    for key, value in installed.items():
        print(f"  {key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
