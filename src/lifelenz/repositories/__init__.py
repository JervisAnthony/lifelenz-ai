"""Public repository contracts for LifeLenz wellness data."""

from lifelenz.repositories.contracts import (
    GoalRepository,
    ProfileOwnershipRepository,
    ProfileRepository,
    UserAccountRepository,
    WellnessRecord,
    WellnessRecordRepository,
    WellnessRecordType,
)
from lifelenz.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryError,
    RepositoryPersistenceError,
)
from lifelenz.repositories.memory import (
    InMemoryGoalRepository,
    InMemoryProfileRepository,
    InMemoryWellnessRecordRepository,
)
from lifelenz.repositories.sqlite import (
    SQLiteGoalRepository,
    SQLiteProfileOwnershipRepository,
    SQLiteProfileRepository,
    SQLiteUserAccountRepository,
    SQLiteWellnessRecordRepository,
)

__all__ = [
    "DuplicateEntityError",
    "EntityNotFoundError",
    "GoalRepository",
    "InMemoryGoalRepository",
    "InMemoryProfileRepository",
    "InMemoryWellnessRecordRepository",
    "ProfileOwnershipRepository",
    "ProfileRepository",
    "RepositoryError",
    "RepositoryPersistenceError",
    "SQLiteGoalRepository",
    "SQLiteProfileOwnershipRepository",
    "SQLiteProfileRepository",
    "SQLiteUserAccountRepository",
    "SQLiteWellnessRecordRepository",
    "UserAccountRepository",
    "WellnessRecord",
    "WellnessRecordRepository",
    "WellnessRecordType",
]
