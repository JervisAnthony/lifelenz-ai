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
)
from lifelenz.repositories.memory import (
    InMemoryGoalRepository,
    InMemoryProfileRepository,
    InMemoryWellnessRecordRepository,
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
    "WellnessRecord",
    "WellnessRecordRepository",
    "WellnessRecordType",
]
