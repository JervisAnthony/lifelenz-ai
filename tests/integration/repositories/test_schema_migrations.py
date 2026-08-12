import sqlite3
from pathlib import Path

import pytest

from lifelenz.repositories import RepositoryPersistenceError, SQLiteUserAccountRepository


def create_v1(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO schema_metadata VALUES ('schema_version', '1');
            CREATE TABLE wellness_profiles (profile_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE wellness_goals (goal_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE wellness_records (
                profile_id TEXT NOT NULL, record_id TEXT NOT NULL, record_type TEXT NOT NULL,
                recorded_at TEXT NOT NULL, recorded_at_epoch REAL NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY (profile_id, record_id)
            );
            INSERT INTO wellness_profiles VALUES ('profile-marker', '{"schema_version":1}');
            INSERT INTO wellness_goals VALUES ('goal-marker', 'profile-marker', '{"schema_version":1}');
            INSERT INTO wellness_records VALUES (
                'profile-marker', 'record-marker', 'hydration', '2026-01-01T00:00:00+00:00',
                1767225600, '{"schema_version":1}'
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_v1_migrates_transactionally_without_changing_wellness_rows(tmp_path: Path) -> None:
    path = tmp_path / "migration.db"
    create_v1(path)
    SQLiteUserAccountRepository(path)
    SQLiteUserAccountRepository(path)
    connection = sqlite3.connect(path)
    try:
        assert (
            connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()[0]
            == "2"
        )
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
        assert tables >= {
            "wellness_profiles",
            "wellness_goals",
            "wellness_records",
            "user_accounts",
            "profile_ownership",
        }
        assert "idx_profile_ownership_user_id" in indexes
        assert (
            connection.execute("SELECT payload FROM wellness_profiles").fetchone()[0]
            == '{"schema_version":1}'
        )
        assert connection.execute("SELECT COUNT(*) FROM wellness_goals").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM wellness_records").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0] == 0
    finally:
        connection.close()


@pytest.mark.parametrize("version", ["0", "3", "banana"])
def test_unsupported_schema_versions_are_rejected_without_reset(
    tmp_path: Path, version: str
) -> None:
    path = tmp_path / f"unsupported-{version}.db"
    create_v1(path)
    connection = sqlite3.connect(path)
    connection.execute("UPDATE schema_metadata SET value=?", (version,))
    connection.commit()
    connection.close()
    with pytest.raises(RepositoryPersistenceError):
        SQLiteUserAccountRepository(path)
