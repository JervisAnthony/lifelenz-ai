"""Package and verify the flat files distributed as GitHub Release assets."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path

CHECKSUMS = "SHA256SUMS"


class BundleError(ValueError):
    """A bundle cannot be packaged or verified safely."""


def _require_name(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) or name in {".", ".."}:
        raise BundleError(f"unsafe asset filename: {name!r}")


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_bundle(directory: Path) -> tuple[Path, ...]:
    """Reject unsafe entries and verify the exact payload set and every digest."""
    checksum_path = directory / CHECKSUMS
    if checksum_path.is_symlink() or not checksum_path.is_file():
        raise BundleError("missing regular SHA256SUMS")
    entries: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise BundleError("invalid checksum entry")
        digest, name = match.groups()
        _require_name(name)
        if name == CHECKSUMS or name in entries:
            raise BundleError(f"duplicate or self-referencing checksum: {name}")
        entries[name] = digest
    if not entries:
        raise BundleError("empty checksum manifest")
    actual = {path.name for path in directory.iterdir()}
    if actual != {*entries, CHECKSUMS}:
        raise BundleError("missing or unexpected release assets")
    for name, digest in entries.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise BundleError(f"asset is not a regular file: {name}")
        if _digest(path) != digest:
            raise BundleError(f"checksum mismatch: {name}")
    return tuple(directory / name for name in sorted(actual))


def package_bundle(assets: list[Path], directory: Path) -> tuple[Path, ...]:
    """Flatten validated inputs and write a deterministic sha256sum manifest."""
    names: set[str] = set()
    for path in assets:
        _require_name(path.name)
        if path.name in names or path.name == CHECKSUMS:
            raise BundleError(f"duplicate asset basename: {path.name}")
        if path.is_symlink() or not path.is_file():
            raise BundleError(f"missing regular asset: {path}")
        names.add(path.name)
    if not assets:
        raise BundleError("no release assets")
    if directory.exists() and (directory.is_symlink() or any(directory.iterdir())):
        raise BundleError("bundle output must be an empty directory")
    directory.mkdir(parents=True, exist_ok=True)
    for path in assets:
        shutil.copyfile(path, directory / path.name)
    lines = [f"{_digest(directory / name)}  {name}\n" for name in sorted(names)]
    (directory / CHECKSUMS).write_text("".join(lines), encoding="utf-8", newline="\n")
    return verify_bundle(directory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    package = commands.add_parser("package")
    package.add_argument("--output", type=Path, required=True)
    package.add_argument("assets", type=Path, nargs="+")
    verify = commands.add_parser("verify")
    verify.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "package":
            files = package_bundle(args.assets, args.output)
        else:
            files = verify_bundle(args.directory)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: release bundle validation failed: {error}\n")
    for path in files:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
