"""Public repository contracts for LifeLenz wellness data."""

from lifelenz.repositories.contracts import (
    GoalRepository,
    ProfileRepository,
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
    SQLiteProfileRepository,
    SQLiteWellnessRecordRepository,
)

__all__ = [
    "DuplicateEntityError",
    "EntityNotFoundError",
    "GoalRepository",
    "InMemoryGoalRepository",
    "InMemoryProfileRepository",
    "InMemoryWellnessRecordRepository",
    "ProfileRepository",
    "RepositoryError",
    "RepositoryPersistenceError",
    "SQLiteGoalRepository",
    "SQLiteProfileRepository",
    "SQLiteWellnessRecordRepository",
    "WellnessRecord",
    "WellnessRecordRepository",
    "WellnessRecordType",
]
