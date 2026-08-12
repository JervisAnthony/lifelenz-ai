"""Durable SQLite implementations of the LifeLenz repository contracts."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from uuid import UUID

from lifelenz.domain import GoalId, ProfileId, RecordId, TimeRange, WellnessGoal, WellnessProfile
from lifelenz.identity import EmailAddress, UserAccount, UserId
from lifelenz.repositories.contracts import WellnessRecord, WellnessRecordType
from lifelenz.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryPersistenceError,
)
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

_SCHEMA_VERSION = 2
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
    """
    CREATE TABLE IF NOT EXISTS user_accounts (
        user_id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_ownership (
        profile_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_profile_ownership_user_id
    ON profile_ownership(user_id)
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


def _require_user_id(user_id: object) -> UserId:
    if type(user_id) is not UserId:
        raise TypeError("user_id must be a UserId")
    return user_id


def _require_email(email: object) -> EmailAddress:
    if type(email) is not EmailAddress:
        raise TypeError("email must be an EmailAddress")
    return email


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
                if version == 1:
                    for statement in _SCHEMA_STATEMENTS[-3:]:
                        connection.execute(statement)
                    connection.execute(
                        "UPDATE schema_metadata SET value = ? WHERE key = ?",
                        (str(_SCHEMA_VERSION), "schema_version"),
                    )
                    version = _SCHEMA_VERSION
                if version != _SCHEMA_VERSION:
                    error = ValueError(f"unsupported schema version {version}")
                    raise RepositoryPersistenceError(
                        "stored schema version is unsupported"
                    ) from error
            for statement in _SCHEMA_STATEMENTS:
                connection.execute(statement)


class SQLiteUserAccountRepository(_SQLiteRepository):
    """Persist canonical accounts in SQLite without storing plaintext or tokens."""

    def save(self, account: UserAccount) -> None:
        if type(account) is not UserAccount:
            raise TypeError("account must be a UserAccount")
        try:
            with self._connection("user account save", write=True) as connection:
                connection.execute(
                    """
                    INSERT INTO user_accounts(user_id, email, password_hash, is_active)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        email = excluded.email,
                        password_hash = excluded.password_hash,
                        is_active = excluded.is_active
                    """,
                    (
                        str(account.user_id.value),
                        account.email.value,
                        account.password_hash,
                        int(account.is_active),
                    ),
                )
        except RepositoryPersistenceError as error:
            cause = error.__cause__
            if isinstance(cause, sqlite3.IntegrityError) and "user_accounts.email" in str(cause):
                raise DuplicateEntityError("an account already uses this email") from error
            raise

    def get(self, user_id: UserId) -> UserAccount:
        validated = _require_user_id(user_id)
        return self._get_one("user_id = ?", (str(validated.value),), "user account get")

    def get_by_email(self, email: EmailAddress) -> UserAccount:
        validated = _require_email(email)
        return self._get_one("email = ?", (validated.value,), "user account email get")

    def exists(self, user_id: UserId) -> bool:
        validated = _require_user_id(user_id)
        return self._exists("user_id = ?", (str(validated.value),), "user account existence")

    def exists_by_email(self, email: EmailAddress) -> bool:
        validated = _require_email(email)
        return self._exists("email = ?", (validated.value,), "user account email existence")

    def _get_one(
        self, predicate: str, parameters: tuple[object, ...], operation: str
    ) -> UserAccount:
        with self._connection(operation) as connection:
            row = connection.execute(
                f"SELECT user_id, email, password_hash, is_active FROM user_accounts WHERE {predicate}",
                parameters,
            ).fetchone()
        if row is None:
            raise EntityNotFoundError("user account was not found")
        try:
            if row["is_active"] not in (0, 1):
                raise ValueError("invalid active state")
            return UserAccount(
                user_id=UserId(UUID(row["user_id"])),
                email=EmailAddress(row["email"]),
                password_hash=row["password_hash"],
                is_active=bool(row["is_active"]),
            )
        except (TypeError, ValueError) as error:
            raise RepositoryPersistenceError("could not reconstruct stored user account") from error

    def _exists(self, predicate: str, parameters: tuple[object, ...], operation: str) -> bool:
        with self._connection(operation) as connection:
            row = connection.execute(
                f"SELECT 1 FROM user_accounts WHERE {predicate}", parameters
            ).fetchone()
        return row is not None


class SQLiteProfileOwnershipRepository(_SQLiteRepository):
    """Persist explicit profile ownership without cross-table enforcement or cascades."""

    def assign(self, user_id: UserId, profile_id: ProfileId) -> None:
        validated_user = _require_user_id(user_id)
        validated_profile = _require_profile_id(profile_id)
        with self._connection("profile ownership assignment", write=True) as connection:
            connection.execute(
                """
                INSERT INTO profile_ownership(profile_id, user_id) VALUES (?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET user_id = excluded.user_id
                """,
                (validated_profile.value, str(validated_user.value)),
            )

    def get_owner(self, profile_id: ProfileId) -> UserId:
        validated = _require_profile_id(profile_id)
        with self._connection("profile owner get") as connection:
            row = connection.execute(
                "SELECT user_id FROM profile_ownership WHERE profile_id = ?",
                (validated.value,),
            ).fetchone()
        if row is None:
            raise EntityNotFoundError("profile ownership was not found")
        try:
            return UserId(UUID(row["user_id"]))
        except (TypeError, ValueError) as error:
            raise RepositoryPersistenceError(
                "could not reconstruct stored profile owner"
            ) from error

    def is_owner(self, user_id: UserId, profile_id: ProfileId) -> bool:
        validated_user = _require_user_id(user_id)
        validated_profile = _require_profile_id(profile_id)
        with self._connection("profile ownership check") as connection:
            row = connection.execute(
                "SELECT 1 FROM profile_ownership WHERE profile_id = ? AND user_id = ?",
                (validated_profile.value, str(validated_user.value)),
            ).fetchone()
        return row is not None

    def list_for_user(self, user_id: UserId) -> tuple[ProfileId, ...]:
        validated = _require_user_id(user_id)
        with self._connection("profile ownership listing") as connection:
            rows = connection.execute(
                "SELECT profile_id FROM profile_ownership WHERE user_id = ? ORDER BY profile_id ASC",
                (str(validated.value),),
            ).fetchall()
        try:
            return tuple(ProfileId(row["profile_id"]) for row in rows)
        except (TypeError, ValueError) as error:
            raise RepositoryPersistenceError(
                "could not reconstruct stored profile ownership"
            ) from error

    def remove(self, profile_id: ProfileId) -> None:
        validated = _require_profile_id(profile_id)
        with self._connection("profile ownership removal", write=True) as connection:
            cursor = connection.execute(
                "DELETE FROM profile_ownership WHERE profile_id = ?", (validated.value,)
            )
            if cursor.rowcount == 0:
                raise EntityNotFoundError("profile ownership was not found")


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
