from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "deploy" / "sqlite_maintenance.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lifelenz_sqlite_maintenance", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


maintenance = _load_module()
SQLiteMaintenanceError = maintenance.SQLiteMaintenanceError


def _create_database(path: Path, values: list[str]) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany(
            "INSERT INTO sample(value) VALUES (?)",
            [(value,) for value in values],
        )
        connection.commit()


def _read_values(path: Path) -> list[str]:
    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute("SELECT value FROM sample ORDER BY id").fetchall()
    return [row[0] for row in rows]


def test_backup_and_restore_round_trip(tmp_path: Path) -> None:
    database = tmp_path / "lifelenz.db"
    backup = tmp_path / "lifelenz-backup.db"
    _create_database(database, ["before"])

    maintenance.create_backup(database, backup)
    maintenance.verify_database(backup)

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("INSERT INTO sample(value) VALUES ('after')")
        connection.commit()

    Path(f"{database}-wal").write_text("stale", encoding="utf-8")
    Path(f"{database}-shm").write_text("stale", encoding="utf-8")

    maintenance.restore_backup(
        backup,
        database,
        replace=True,
        api_stopped_confirmed=True,
    )

    assert _read_values(database) == ["before"]
    assert not Path(f"{database}-wal").exists()
    assert not Path(f"{database}-shm").exists()


def test_restore_requires_api_stop_confirmation(tmp_path: Path) -> None:
    database = tmp_path / "lifelenz.db"
    backup = tmp_path / "lifelenz-backup.db"
    _create_database(database, ["current"])
    maintenance.create_backup(database, backup)

    with pytest.raises(SQLiteMaintenanceError, match="explicit confirmation"):
        maintenance.restore_backup(
            backup,
            database,
            replace=True,
            api_stopped_confirmed=False,
        )


def test_restore_refuses_existing_database_without_replace(tmp_path: Path) -> None:
    database = tmp_path / "lifelenz.db"
    backup = tmp_path / "lifelenz-backup.db"
    _create_database(database, ["current"])
    maintenance.create_backup(database, backup)

    with pytest.raises(SQLiteMaintenanceError, match="database already exists"):
        maintenance.restore_backup(
            backup,
            database,
            replace=False,
            api_stopped_confirmed=True,
        )


def test_backup_rejects_same_source_and_destination(tmp_path: Path) -> None:
    database = tmp_path / "lifelenz.db"
    _create_database(database, ["current"])

    with pytest.raises(SQLiteMaintenanceError, match="source and destination"):
        maintenance.create_backup(database, database)


def test_verify_rejects_missing_and_invalid_files(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    invalid = tmp_path / "invalid.db"
    invalid.write_text("not a sqlite database", encoding="utf-8")

    with pytest.raises(SQLiteMaintenanceError, match="existing SQLite file"):
        maintenance.verify_database(missing)

    with pytest.raises(SQLiteMaintenanceError, match="SQLite verification failed"):
        maintenance.verify_database(invalid)


def test_verify_cli_reports_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database = tmp_path / "lifelenz.db"
    _create_database(database, ["current"])

    assert maintenance.main(["verify", "--database", str(database)]) == 0

    output = capsys.readouterr().out
    assert "SQLite integrity check passed" in output
    assert str(database.resolve()) in output
