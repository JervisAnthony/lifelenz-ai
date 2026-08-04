"""Durable SQLite implementations of the LifeLenz repository contracts."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from lifelenz.domain import GoalId, ProfileId, RecordId, TimeRange, WellnessGoal, WellnessProfile
from lifelenz.repositories.contracts import WellnessRecord, WellnessRecordType
from lifelenz.repositories.exceptions import EntityNotFoundError, RepositoryPersistenceError
from lifelenz.repositories.serialization import (
    SerializationError,
    deserialize_wellness_goal,
    deserialize_wellness_profile,
    deserialize_wellness_record,
    record_discriminator,
    serialize_wellness_goal,
    serialize_wellness_profile,
    serialize_wellness_record,
)

_SCHEMA_VERSION = 1
_CONNECTION_TIMEOUT_SECONDS = 5.0
_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS wellness_profiles (
        profile_id TEXT PRIMARY KEY,
        payload TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wellness_goals (
        goal_id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL,
        payload TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wellness_records (
        profile_id TEXT NOT NULL,
        record_id TEXT NOT NULL,
        record_type TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        recorded_at_epoch REAL NOT NULL,
        payload TEXT NOT NULL,
        PRIMARY KEY (profile_id, record_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_wellness_goals_profile_id
    ON wellness_goals(profile_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_wellness_records_profile_recorded_at
    ON wellness_records(profile_id, recorded_at_epoch, record_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_wellness_records_profile_type_time
    ON wellness_records(profile_id, record_type, recorded_at_epoch, record_id)
    """,
)


def _require_profile_id(profile_id: object) -> ProfileId:
    if not isinstance(profile_id, ProfileId):
        raise TypeError(f"profile_id must be a ProfileId; got {profile_id!r}")
    return profile_id


def _require_goal_id(goal_id: object) -> GoalId:
    if not isinstance(goal_id, GoalId):
        raise TypeError(f"goal_id must be a GoalId; got {goal_id!r}")
    return goal_id


def _require_record_id(record_id: object) -> RecordId:
    if not isinstance(record_id, RecordId):
        raise TypeError(f"record_id must be a RecordId; got {record_id!r}")
    return record_id


def _require_time_range(time_range: object) -> TimeRange:
    if not isinstance(time_range, TimeRange):
        raise TypeError(f"time_range must be a TimeRange; got {time_range!r}")
    return time_range


def _deserialize(operation: str, factory: object) -> object:
    try:
        return factory()  # type: ignore[operator]
    except SerializationError as error:
        raise RepositoryPersistenceError(
            f"could not reconstruct stored data during {operation}"
        ) from error


class _SQLiteRepository:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = self._validate_database_path(database_path)
        self._initialize_schema()

    @staticmethod
    def _validate_database_path(database_path: object) -> Path:
        if type(database_path) is str:
            if not database_path.strip():
                raise RepositoryPersistenceError("database path must not be empty or whitespace")
            if database_path == ":memory:":
                raise RepositoryPersistenceError("database path must identify a durable file")
            path = Path(database_path)
        elif isinstance(database_path, Path):
            path = database_path
        else:
            raise TypeError(f"database_path must be a string or Path; got {database_path!r}")
        if not path.parent.exists():
            error = FileNotFoundError("database parent directory does not exist")
            raise RepositoryPersistenceError("database parent directory does not exist") from error
        if path.exists() and path.is_dir():
            error = IsADirectoryError("database path identifies a directory")
            raise RepositoryPersistenceError("database path must identify a file") from error
        return path

    @contextmanager
    def _connection(self, operation: str, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                self._database_path,
                timeout=_CONNECTION_TIMEOUT_SECONDS,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            if write:
                connection.execute("BEGIN")
            yield connection
            if write:
                connection.commit()
        except sqlite3.Error as error:
            if connection is not None and write:
                with suppress(sqlite3.Error):
                    connection.rollback()
            raise RepositoryPersistenceError(f"SQLite {operation} failed") from error
        except BaseException:
            if connection is not None and write:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    def _initialize_schema(self) -> None:
        with self._connection("schema initialization", write=True) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    ("schema_version", str(_SCHEMA_VERSION)),
                )
            else:
                try:
                    version = int(row["value"])
                except (TypeError, ValueError) as error:
                    raise RepositoryPersistenceError("stored schema version is invalid") from error
                if version != _SCHEMA_VERSION:
                    error = ValueError(f"unsupported schema version {version}")
                    raise RepositoryPersistenceError(
                        "stored schema version is unsupported"
                    ) from error
            for statement in _SCHEMA_STATEMENTS:
                connection.execute(statement)


class SQLiteProfileRepository(_SQLiteRepository):
    """Store profiles durably in a local unencrypted SQLite database file.

    Operations use independent connections and provide no additional thread-safety
    guarantee. Saves are atomic upserts; removals do not cascade.
    """

    def save(self, profile: WellnessProfile) -> None:
        """Atomically upsert one exact profile without changing the supplied object."""
        if type(profile) is not WellnessProfile:
            raise TypeError(f"profile must be an exact WellnessProfile; got {profile!r}")
        payload = serialize_wellness_profile(profile)
        with self._connection("profile save", write=True) as connection:
            connection.execute(
                """
                INSERT INTO wellness_profiles(profile_id, payload) VALUES (?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET payload = excluded.payload
                """,
                (profile.profile_id.value, payload),
            )

    def get(self, profile_id: ProfileId) -> WellnessProfile:
        """Return a reconstructed profile or raise EntityNotFoundError when absent."""
        validated_id = _require_profile_id(profile_id)
        with self._connection("profile get") as connection:
            row = connection.execute(
                "SELECT payload FROM wellness_profiles WHERE profile_id = ?",
                (validated_id.value,),
            ).fetchone()
        if row is None:
            raise EntityNotFoundError(
                f"wellness profile not found for profile_id={validated_id.value!r}"
            )
        return _deserialize(
            "profile get",
            lambda: deserialize_wellness_profile(row["payload"]),
        )  # type: ignore[return-value]

    def exists(self, profile_id: ProfileId) -> bool:
        """Return whether the validated profile identifier is stored."""
        validated_id = _require_profile_id(profile_id)
        with self._connection("profile existence check") as connection:
            row = connection.execute(
                "SELECT 1 FROM wellness_profiles WHERE profile_id = ?",
                (validated_id.value,),
            ).fetchone()
        return row is not None

    def list_all(self) -> tuple[WellnessProfile, ...]:
        """Return reconstructed profiles ordered by profile identifier ascending."""
        with self._connection("profile listing") as connection:
            payloads = tuple(
                row["payload"]
                for row in connection.execute(
                    "SELECT payload FROM wellness_profiles ORDER BY profile_id ASC"
                ).fetchall()
            )
        return tuple(
            _deserialize(
                "profile listing", lambda payload=payload: deserialize_wellness_profile(payload)
            )
            for payload in payloads
        )  # type: ignore[return-value]

    def remove(self, profile_id: ProfileId) -> None:
        """Atomically remove one profile without cascading to goals or records."""
        validated_id = _require_profile_id(profile_id)
        with self._connection("profile removal", write=True) as connection:
            cursor = connection.execute(
                "DELETE FROM wellness_profiles WHERE profile_id = ?",
                (validated_id.value,),
            )
            if cursor.rowcount == 0:
                raise EntityNotFoundError(
                    f"wellness profile not found for profile_id={validated_id.value!r}"
                )


class SQLiteGoalRepository(_SQLiteRepository):
    """Store goals durably in a local unencrypted SQLite database file.

    Independent operation connections add no thread-safety guarantee. Profile
    existence is not enforced, saves are upserts, and removals do not cascade.
    """

    def save(self, goal: WellnessGoal) -> None:
        """Atomically upsert one exact goal independently of profile storage."""
        if type(goal) is not WellnessGoal:
            raise TypeError(f"goal must be an exact WellnessGoal; got {goal!r}")
        payload = serialize_wellness_goal(goal)
        with self._connection("goal save", write=True) as connection:
            connection.execute(
                """
                INSERT INTO wellness_goals(goal_id, profile_id, payload) VALUES (?, ?, ?)
                ON CONFLICT(goal_id) DO UPDATE SET
                    profile_id = excluded.profile_id,
                    payload = excluded.payload
                """,
                (goal.goal_id.value, goal.profile_id.value, payload),
            )

    def get(self, goal_id: GoalId) -> WellnessGoal:
        """Return a reconstructed goal or raise EntityNotFoundError when absent."""
        validated_id = _require_goal_id(goal_id)
        with self._connection("goal get") as connection:
            row = connection.execute(
                "SELECT payload FROM wellness_goals WHERE goal_id = ?",
                (validated_id.value,),
            ).fetchone()
        if row is None:
            raise EntityNotFoundError(f"wellness goal not found for goal_id={validated_id.value!r}")
        return _deserialize(
            "goal get",
            lambda: deserialize_wellness_goal(row["payload"]),
        )  # type: ignore[return-value]

    def exists(self, goal_id: GoalId) -> bool:
        """Return whether the validated goal identifier is stored."""
        validated_id = _require_goal_id(goal_id)
        with self._connection("goal existence check") as connection:
            row = connection.execute(
                "SELECT 1 FROM wellness_goals WHERE goal_id = ?",
                (validated_id.value,),
            ).fetchone()
        return row is not None

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessGoal, ...]:
        """Return matching goals ordered by goal identifier without a profile lookup."""
        validated_id = _require_profile_id(profile_id)
        with self._connection("profile goal listing") as connection:
            payloads = tuple(
                row["payload"]
                for row in connection.execute(
                    """
                    SELECT payload FROM wellness_goals
                    WHERE profile_id = ? ORDER BY goal_id ASC
                    """,
                    (validated_id.value,),
                ).fetchall()
            )
        return tuple(
            _deserialize(
                "profile goal listing",
                lambda payload=payload: deserialize_wellness_goal(payload),
            )
            for payload in payloads
        )  # type: ignore[return-value]

    def list_all(self) -> tuple[WellnessGoal, ...]:
        """Return every reconstructed goal ordered by goal identifier ascending."""
        with self._connection("goal listing") as connection:
            payloads = tuple(
                row["payload"]
                for row in connection.execute(
                    "SELECT payload FROM wellness_goals ORDER BY goal_id ASC"
                ).fetchall()
            )
        return tuple(
            _deserialize("goal listing", lambda payload=payload: deserialize_wellness_goal(payload))
            for payload in payloads
        )  # type: ignore[return-value]

    def remove(self, goal_id: GoalId) -> None:
        """Atomically remove one goal without modifying profiles or records."""
        validated_id = _require_goal_id(goal_id)
        with self._connection("goal removal", write=True) as connection:
            cursor = connection.execute(
                "DELETE FROM wellness_goals WHERE goal_id = ?",
                (validated_id.value,),
            )
            if cursor.rowcount == 0:
                raise EntityNotFoundError(
                    f"wellness goal not found for goal_id={validated_id.value!r}"
                )


class SQLiteWellnessRecordRepository(_SQLiteRepository):
    """Store profile-owned records durably under exact composite ownership keys.

    Records are ordered and filtered chronologically through UTC epoch values while
    original aware offsets remain in reconstructed metadata. Exact concrete record
    types are supported without profile-existence enforcement or cascading deletion.
    The local database is not encrypted, and independent operation connections add
    no thread-safety guarantee beyond SQLite's standard behavior.
    """

    def save(self, profile_id: ProfileId, record: WellnessRecord) -> None:
        """Atomically upsert an exact record under its profile-and-record key."""
        validated_profile_id = _require_profile_id(profile_id)
        record_type, payload = serialize_wellness_record(record)
        metadata = record.metadata
        with self._connection("wellness record save", write=True) as connection:
            connection.execute(
                """
                INSERT INTO wellness_records(
                    profile_id, record_id, record_type, recorded_at,
                    recorded_at_epoch, payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, record_id) DO UPDATE SET
                    record_type = excluded.record_type,
                    recorded_at = excluded.recorded_at,
                    recorded_at_epoch = excluded.recorded_at_epoch,
                    payload = excluded.payload
                """,
                (
                    validated_profile_id.value,
                    metadata.record_id.value,
                    record_type,
                    metadata.recorded_at.isoformat(),
                    metadata.recorded_at.timestamp(),
                    payload,
                ),
            )

    def get(self, profile_id: ProfileId, record_id: RecordId) -> WellnessRecord:
        """Return the exact reconstructed owned record or report its absence."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        with self._connection("wellness record get") as connection:
            row = connection.execute(
                """
                SELECT record_type, payload FROM wellness_records
                WHERE profile_id = ? AND record_id = ?
                """,
                (validated_profile_id.value, validated_record_id.value),
            ).fetchone()
        if row is None:
            raise EntityNotFoundError(
                "wellness record not found for "
                f"profile_id={validated_profile_id.value!r}, "
                f"record_id={validated_record_id.value!r}"
            )
        return self._record_from_row(row, operation="wellness record get")

    def exists(self, profile_id: ProfileId, record_id: RecordId) -> bool:
        """Return whether the validated composite ownership key is stored."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        with self._connection("wellness record existence check") as connection:
            row = connection.execute(
                """
                SELECT 1 FROM wellness_records
                WHERE profile_id = ? AND record_id = ?
                """,
                (validated_profile_id.value, validated_record_id.value),
            ).fetchone()
        return row is not None

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessRecord, ...]:
        """Return owned records in chronological timestamp and identifier order."""
        validated_id = _require_profile_id(profile_id)
        return self._list(
            """
            SELECT record_type, payload FROM wellness_records
            WHERE profile_id = ? ORDER BY recorded_at_epoch ASC, record_id ASC
            """,
            (validated_id.value,),
            operation="profile wellness record listing",
        )

    def list_in_time_range(
        self,
        profile_id: ProfileId,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Return owned records in a start-inclusive, end-exclusive aware range."""
        validated_id = _require_profile_id(profile_id)
        validated_range = _require_time_range(time_range)
        return self._list(
            """
            SELECT record_type, payload FROM wellness_records
            WHERE profile_id = ? AND recorded_at_epoch >= ? AND recorded_at_epoch < ?
            ORDER BY recorded_at_epoch ASC, record_id ASC
            """,
            (
                validated_id.value,
                validated_range.start.timestamp(),
                validated_range.end.timestamp(),
            ),
            operation="time-range wellness record listing",
        )

    def list_by_type(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
    ) -> tuple[WellnessRecord, ...]:
        """Return owned records of one exact supported concrete record type."""
        validated_id = _require_profile_id(profile_id)
        discriminator = record_discriminator(record_type)
        return self._list(
            """
            SELECT record_type, payload FROM wellness_records
            WHERE profile_id = ? AND record_type = ?
            ORDER BY recorded_at_epoch ASC, record_id ASC
            """,
            (validated_id.value, discriminator),
            operation="typed wellness record listing",
        )

    def list_by_type_in_time_range(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Return exact-type owned records within an aware metadata-time range."""
        validated_id = _require_profile_id(profile_id)
        discriminator = record_discriminator(record_type)
        validated_range = _require_time_range(time_range)
        return self._list(
            """
            SELECT record_type, payload FROM wellness_records
            WHERE profile_id = ? AND record_type = ?
                AND recorded_at_epoch >= ? AND recorded_at_epoch < ?
            ORDER BY recorded_at_epoch ASC, record_id ASC
            """,
            (
                validated_id.value,
                discriminator,
                validated_range.start.timestamp(),
                validated_range.end.timestamp(),
            ),
            operation="typed time-range wellness record listing",
        )

    def remove(self, profile_id: ProfileId, record_id: RecordId) -> None:
        """Atomically remove one composite key without affecting another profile."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        with self._connection("wellness record removal", write=True) as connection:
            cursor = connection.execute(
                """
                DELETE FROM wellness_records
                WHERE profile_id = ? AND record_id = ?
                """,
                (validated_profile_id.value, validated_record_id.value),
            )
            if cursor.rowcount == 0:
                raise EntityNotFoundError(
                    "wellness record not found for "
                    f"profile_id={validated_profile_id.value!r}, "
                    f"record_id={validated_record_id.value!r}"
                )

    def _list(
        self,
        statement: str,
        parameters: tuple[object, ...],
        *,
        operation: str,
    ) -> tuple[WellnessRecord, ...]:
        with self._connection(operation) as connection:
            rows = tuple(connection.execute(statement, parameters).fetchall())
        return tuple(self._record_from_row(row, operation=operation) for row in rows)

    @staticmethod
    def _record_from_row(row: sqlite3.Row, *, operation: str) -> WellnessRecord:
        return _deserialize(
            operation,
            lambda: deserialize_wellness_record(row["record_type"], row["payload"]),
        )  # type: ignore[return-value]
