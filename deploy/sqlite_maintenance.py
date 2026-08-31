"""Operational SQLite backup, verification, and restore helpers for LifeLenz deployments."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


class SQLiteMaintenanceError(RuntimeError):
    """Raised when a backup, verification, or restore operation is unsafe or invalid."""


def _normalized(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _require_file(path: Path, label: str) -> Path:
    resolved = _normalized(path)
    if not resolved.is_file():
        raise SQLiteMaintenanceError(f"{label} must identify an existing SQLite file: {resolved}")
    return resolved


def _require_distinct(source: Path, destination: Path) -> None:
    if _normalized(source) == _normalized(destination):
        raise SQLiteMaintenanceError("source and destination must be different files")


def _readonly_uri(path: Path) -> str:
    return f"{_normalized(path).as_uri()}?mode=ro"


def verify_database(database_path: Path) -> None:
    """Raise when the supplied SQLite file is missing, unreadable, or fails integrity checks."""
    database = _require_file(database_path, "database")
    try:
        with closing(sqlite3.connect(_readonly_uri(database), uri=True)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as error:
        raise SQLiteMaintenanceError(f"SQLite verification failed for {database}") from error
    if result != ("ok",):
        detail = "unknown" if not result else str(result[0])
        raise SQLiteMaintenanceError(f"SQLite integrity_check failed: {detail}")


def _copy_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink(missing_ok=True)

    try:
        with (
            closing(sqlite3.connect(_readonly_uri(source), uri=True)) as source_connection,
            closing(sqlite3.connect(temporary)) as destination_connection,
        ):
            source_connection.backup(destination_connection)
        verify_database(temporary)
        os.replace(temporary, destination)
    except (OSError, sqlite3.Error, SQLiteMaintenanceError) as error:
        temporary.unlink(missing_ok=True)
        if isinstance(error, SQLiteMaintenanceError):
            raise
        raise SQLiteMaintenanceError(
            f"unable to copy SQLite database from {source} to {destination}"
        ) from error


def create_backup(database_path: Path, output_path: Path) -> None:
    """Create an integrity-checked SQLite backup without logging database contents."""
    database = _require_file(database_path, "database")
    output = _normalized(output_path)
    _require_distinct(database, output)
    _copy_database(database, output)


def restore_backup(
    backup_path: Path,
    database_path: Path,
    *,
    replace: bool,
    api_stopped_confirmed: bool,
) -> None:
    """Restore an integrity-checked backup after the operator confirms API writers are stopped."""
    if not api_stopped_confirmed:
        raise SQLiteMaintenanceError(
            "restore requires explicit confirmation that the LifeLenz API is stopped"
        )

    backup = _require_file(backup_path, "backup")
    database = _normalized(database_path)
    _require_distinct(backup, database)
    verify_database(backup)

    if database.exists() and not replace:
        raise SQLiteMaintenanceError(
            f"database already exists; pass --replace only after stopping the API: {database}"
        )

    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{database}{suffix}")
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError as error:
                raise SQLiteMaintenanceError(
                    f"unable to remove SQLite sidecar: {sidecar}"
                ) from error

    _copy_database(backup, database)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, verify, or restore LifeLenz SQLite deployment backups."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="create an integrity-checked backup")
    backup_parser.add_argument("--database", required=True, type=Path)
    backup_parser.add_argument("--output", required=True, type=Path)

    verify_parser = subparsers.add_parser("verify", help="verify an SQLite file")
    verify_parser.add_argument("--database", required=True, type=Path)

    restore_parser = subparsers.add_parser("restore", help="restore an integrity-checked backup")
    restore_parser.add_argument("--input", required=True, type=Path)
    restore_parser.add_argument("--database", required=True, type=Path)
    restore_parser.add_argument("--replace", action="store_true")
    restore_parser.add_argument(
        "--confirm-api-stopped",
        action="store_true",
        help="required safety acknowledgement before restore",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the deployment-maintenance command."""
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "backup":
            create_backup(args.database, args.output)
            print(f"Backup created and verified: {_normalized(args.output)}")
        elif args.command == "verify":
            verify_database(args.database)
            print(f"SQLite integrity check passed: {_normalized(args.database)}")
        else:
            restore_backup(
                args.input,
                args.database,
                replace=args.replace,
                api_stopped_confirmed=args.confirm_api_stopped,
            )
            print(f"Backup restored and verified: {_normalized(args.database)}")
    except SQLiteMaintenanceError as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
