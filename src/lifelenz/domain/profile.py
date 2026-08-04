"""Immutable, privacy-conscious wellness-profile domain types."""

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import Self
from unicodedata import category
from uuid import UUID, uuid4

from lifelenz.domain.exceptions import DomainValidationError, InvalidIdentifierError


@dataclass(frozen=True, slots=True)
class ProfileId:
    """A semantically distinct profile identifier using canonical UUID text.

    Supplied canonical UUID text is validated and preserved exactly without
    case normalization. Profile identifiers are not authentication identities.

    Raises:
        InvalidIdentifierError: If ``value`` is not canonical UUID text.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate canonical UUID text without changing the supplied value."""
        if not isinstance(self.value, str):
            raise InvalidIdentifierError(f"profile identifier must be a string; got {self.value!r}")
        if not self.value:
            raise InvalidIdentifierError("profile identifier must not be empty")
        if any(character.isspace() for character in self.value):
            raise InvalidIdentifierError(
                f"profile identifier must not contain whitespace; got {self.value!r}"
            )

        try:
            parsed_value = UUID(self.value)
        except (ValueError, AttributeError) as error:
            raise InvalidIdentifierError(
                f"profile identifier must be a valid UUID; got {self.value!r}"
            ) from error
        if self.value.lower() != str(parsed_value):
            raise InvalidIdentifierError(
                f"profile identifier must use canonical UUID text; got {self.value!r}"
            )

    @classmethod
    def generate(cls) -> Self:
        """Return a new profile identifier backed by a standard UUID4 value."""
        return cls(str(uuid4()))

    def __str__(self) -> str:
        """Return the exact stored identifier text."""
        return self.value


@unique
class MeasurementSystem(StrEnum):
    """Future presentation preference that leaves canonical record units unchanged."""

    METRIC = "metric"
    IMPERIAL = "imperial"


@unique
class WeekStart(StrEnum):
    """User-selected week boundary for future calendar grouping."""

    MONDAY = "monday"
    SUNDAY = "sunday"


@unique
class TrackedWellnessDomain(StrEnum):
    """User-selected LifeLenz capabilities without health-status meaning."""

    SLEEP = "sleep"
    ACTIVITY = "activity"
    HYDRATION = "hydration"
    NUTRITION = "nutrition"
    BODY_MEASUREMENTS = "body_measurements"
    SUBJECTIVE_CHECK_INS = "subjective_check_ins"
    MENSTRUAL_CYCLE = "menstrual_cycle"


@dataclass(frozen=True, slots=True)
class WellnessProfile:
    """Privacy-conscious LifeLenz preferences without identity or medical data.

    The profile is not an authentication account. Its optional display name is
    non-unique, and its structurally validated time-zone identifier supports
    future local-date grouping without device or location inference. Measurement
    system and week start are future presentation and grouping preferences;
    existing records retain canonical units. Tracked domains form an immutable
    ordered tuple of selected capabilities, with duplicates rejected and no
    health or demographic meaning.

    Raises:
        DomainValidationError: If an object or preference violates the profile
            contract.
    """

    profile_id: ProfileId
    time_zone: str
    display_name: str | None = None
    measurement_system: MeasurementSystem = MeasurementSystem.METRIC
    week_start: WeekStart = WeekStart.MONDAY
    tracked_domains: tuple[TrackedWellnessDomain, ...] = ()

    def __post_init__(self) -> None:
        """Validate and preserve explicit preferences without inference."""
        if not isinstance(self.profile_id, ProfileId):
            raise DomainValidationError(f"profile_id must be a ProfileId; got {self.profile_id!r}")
        self._validate_time_zone()

        if self.display_name is not None and not isinstance(self.display_name, str):
            raise DomainValidationError(
                f"display_name must be a string or None; got {self.display_name!r}"
            )
        normalized_name = self.display_name.strip() if self.display_name is not None else None
        object.__setattr__(self, "display_name", normalized_name or None)

        if not isinstance(self.measurement_system, MeasurementSystem):
            raise DomainValidationError(
                f"measurement_system must be a MeasurementSystem; got {self.measurement_system!r}"
            )
        if not isinstance(self.week_start, WeekStart):
            raise DomainValidationError(f"week_start must be a WeekStart; got {self.week_start!r}")
        if type(self.tracked_domains) is not tuple:
            raise DomainValidationError(
                "tracked_domains must be a tuple of TrackedWellnessDomain values; "
                f"got {self.tracked_domains!r}"
            )
        if any(not isinstance(domain, TrackedWellnessDomain) for domain in self.tracked_domains):
            raise DomainValidationError(
                "every tracked domain must be a TrackedWellnessDomain; "
                f"got {self.tracked_domains!r}"
            )
        if len(set(self.tracked_domains)) != len(self.tracked_domains):
            raise DomainValidationError(
                f"tracked_domains must not contain duplicates; got {self.tracked_domains!r}"
            )

    def _validate_time_zone(self) -> None:
        """Validate a time-zone identifier structurally without host lookup."""
        if type(self.time_zone) is not str:
            raise DomainValidationError(f"time_zone must be a plain string; got {self.time_zone!r}")
        if not self.time_zone:
            raise DomainValidationError("time_zone must not be empty")
        if any(
            character.isspace() or character == "\\" or category(character).startswith("C")
            for character in self.time_zone
        ):
            raise DomainValidationError(
                "time_zone must not contain whitespace, control characters, or backslashes; "
                f"got {self.time_zone!r}"
            )
        if self.time_zone == "UTC":
            return
        if "/" not in self.time_zone or any(not segment for segment in self.time_zone.split("/")):
            raise DomainValidationError(
                "time_zone must be UTC or a slash-separated identifier with non-empty segments; "
                f"got {self.time_zone!r}"
            )

    @property
    def has_display_name(self) -> bool:
        """Return whether a non-blank display name is present."""
        return self.display_name is not None

    @property
    def tracked_domain_count(self) -> int:
        """Return the number of selected wellness capabilities."""
        return len(self.tracked_domains)

    def tracks(self, domain: TrackedWellnessDomain) -> bool:
        """Return whether an explicitly supplied controlled domain is selected."""
        if not isinstance(domain, TrackedWellnessDomain):
            raise DomainValidationError(f"domain must be a TrackedWellnessDomain; got {domain!r}")
        return domain in self.tracked_domains
