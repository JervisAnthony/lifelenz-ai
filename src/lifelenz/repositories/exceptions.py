"""Storage-independent exceptions for repository contracts."""


class RepositoryError(Exception):
    """Base exception for repository-layer failures."""


class EntityNotFoundError(RepositoryError):
    """Raised when a requested entity identifier or ownership key is absent."""


class DuplicateEntityError(RepositoryError):
    """Raised when an operation requiring a new identity receives an existing one."""


class RepositoryPersistenceError(RepositoryError):
    """Raised when a storage failure prevents a repository operation from completing."""
