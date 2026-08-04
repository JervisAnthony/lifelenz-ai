"""Tests for user-defined wellness-goal domain types."""

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from lifelenz import domain
from lifelenz.domain import (
    BeverageType,
    BodyMeasurementRecord,
    CheckInTag,
    ConfidenceLevel,
    CycleSymptom,
    CycleSymptomEntry,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    DomainValidationError,
    GoalDirection,
    GoalId,
    GoalStatus,
    GoalTarget,
    HydrationRecord,
    InsightSeverity,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
    MealNutrition,
    MealRecord,
    MealType,
    MeasurementSystem,
    MeasurementUnit,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    MenstrualFlow,
    MetricIdentifier,
    MoodCategory,
    PerceivedExertion,
    ProfileId,
    RecordId,
    RecordMetadata,
    SleepQuality,
    SleepRecord,
    SleepStageDurations,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    SymptomIntensity,
    TimeRange,
    TrackedWellnessDomain,
    WeekStart,
    WellnessCategory,
    WellnessGoal,
    WellnessProfile,
    WorkoutRecord,
    WorkoutType,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC

_GOAL_UUID = "223e4567-e89b-12d3-a456-426614174000"
_PROFILE_UUID = "123e4567-e89b-12d3-a456-426614174000"
_DEFAULT_GOAL_ID = GoalId(_GOAL_UUID)
_DEFAULT_PROFILE_ID = ProfileId(_PROFILE_UUID)
_DEFAULT_TARGET = GoalTarget(MetricIdentifier.STEPS, 10_000, MeasurementUnit.COUNT)


def _goal(
    *,
    goal_id: GoalId | object = _DEFAULT_GOAL_ID,
    profile_id: ProfileId | object = _DEFAULT_PROFILE_ID,
    target: GoalTarget | object = _DEFAULT_TARGET,
    direction: GoalDirection | object = GoalDirection.AT_LEAST,
    status: GoalStatus | object = GoalStatus.DRAFT,
    start_date: date | object | None = None,
    target_date: date | object | None = None,
    title: str | object | None = None,
    description: str | object | None = None,
) -> WellnessGoal:
    """Build a wellness goal while keeping test setup concise."""
    return WellnessGoal(
        goal_id=goal_id,  # type: ignore[arg-type]
        profile_id=profile_id,  # type: ignore[arg-type]
        target=target,  # type: ignore[arg-type]
        direction=direction,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        start_date=start_date,  # type: ignore[arg-type]
        target_date=target_date,  # type: ignore[arg-type]
        title=title,  # type: ignore[arg-type]
        description=description,  # type: ignore[arg-type]
    )


def test_goal_id_accepts_and_preserves_canonical_uuid_text() -> None:
    """Canonical UUID text remains exactly supplied."""
    identifier = GoalId(_GOAL_UUID)

    assert identifier.value == _GOAL_UUID
    assert str(identifier) == _GOAL_UUID


def test_goal_id_accepts_uppercase_canonical_uuid_without_normalizing() -> None:
    """Uppercase canonical UUID text follows established preservation behavior."""
    uppercase_value = _GOAL_UUID.upper()
    assert GoalId(uppercase_value).value == uppercase_value


def test_goal_id_generate_returns_unique_uuid4_values() -> None:
    """Generated goal identifiers use standard unique UUID4 text."""
    first = GoalId.generate()
    second = GoalId.generate()

    assert UUID(first.value).version == 4
    assert str(UUID(first.value)) == first.value
    assert first != second


def test_goal_id_has_value_equality_hashing_and_immutability() -> None:
    """Goal identifiers are immutable, hashable values."""
    first = GoalId(_GOAL_UUID)
    same = GoalId(_GOAL_UUID)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.value = _PROFILE_UUID


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "not-a-uuid",
        "{223e4567-e89b-12d3-a456-426614174000}",
        "223e4567e89b12d3a456426614174000",
        True,
        None,
        {},
        RecordId(_GOAL_UUID),
        object(),
    ],
)
def test_goal_id_rejects_invalid_values(value: object) -> None:
    """Empty, malformed, and unrelated values are rejected."""
    with pytest.raises(InvalidIdentifierError, match="goal identifier"):
        GoalId(value)  # type: ignore[arg-type]


def test_goal_id_is_semantically_distinct_from_existing_identifiers() -> None:
    """Equal text does not collapse goal, profile, and record identifier types."""
    goal_id = GoalId(_GOAL_UUID)

    assert goal_id != ProfileId(_GOAL_UUID)
    assert goal_id != RecordId(_GOAL_UUID)
    assert not isinstance(goal_id, (ProfileId, RecordId))


def test_goal_direction_has_exact_stable_ordered_members() -> None:
    """Directions expose the complete neutral user-intent vocabulary."""
    expected = [
        ("AT_LEAST", "at_least"),
        ("AT_MOST", "at_most"),
        ("EXACTLY", "exactly"),
        ("INCREASE", "increase"),
        ("DECREASE", "decrease"),
        ("MAINTAIN", "maintain"),
    ]

    assert [(member.name, member.value) for member in GoalDirection] == expected
    assert len({member.value for member in GoalDirection}) == len(expected)
    assert all(str(member) == member.value for member in GoalDirection)
    assert not {"IMPROVE", "OPTIMIZE", "MEDICALLY_RECOMMENDED"} & set(GoalDirection.__members__)


def test_goal_status_has_exact_stable_ordered_members() -> None:
    """Statuses expose the complete explicitly supplied lifecycle vocabulary."""
    expected = [
        ("DRAFT", "draft"),
        ("ACTIVE", "active"),
        ("PAUSED", "paused"),
        ("COMPLETED", "completed"),
        ("CANCELLED", "cancelled"),
    ]

    assert [(member.name, member.value) for member in GoalStatus] == expected
    assert len({member.value for member in GoalStatus}) == len(expected)
    assert all(str(member) == member.value for member in GoalStatus)
    assert not {"FAILED", "OVERDUE", "AT_RISK", "ACHIEVED_AUTOMATICALLY"} & set(
        GoalStatus.__members__
    )


@pytest.mark.parametrize("metric", list(MetricIdentifier))
def test_goal_target_accepts_every_metric_with_canonical_unit(
    metric: MetricIdentifier,
) -> None:
    """Every current taxonomy metric has an accepted canonical target unit."""
    unit = DEFAULT_UNIT_BY_METRIC[metric]
    target = GoalTarget(metric, 1, unit)

    assert target.metric is metric
    assert target.unit is unit


@pytest.mark.parametrize(
    ("metric", "value", "unit"),
    [
        (MetricIdentifier.SLEEP_DURATION, 8, MeasurementUnit.HOURS),
        (MetricIdentifier.STEPS, 10_000, MeasurementUnit.COUNT),
        (MetricIdentifier.WATER_INTAKE, 2_000.5, MeasurementUnit.MILLILITERS),
        (MetricIdentifier.CALORIES, 0, MeasurementUnit.KCAL),
        (MetricIdentifier.WEIGHT, 70.25, MeasurementUnit.KILOGRAMS),
        (MetricIdentifier.BODY_FAT, 0.001, MeasurementUnit.PERCENT),
        (MetricIdentifier.MOOD_SCORE, 7, MeasurementUnit.SCORE),
    ],
)
def test_goal_target_preserves_representative_values(
    metric: MetricIdentifier,
    value: int | float,
    unit: MeasurementUnit,
) -> None:
    """Integer, float, zero, and small positive targets remain exact."""
    target = GoalTarget(metric, value, unit)

    assert target.metric is metric
    assert target.value is value
    assert target.unit is unit


def test_goal_target_has_value_equality_hashing_and_immutability() -> None:
    """Equivalent metric targets are immutable, hashable values."""
    first = GoalTarget(MetricIdentifier.DISTANCE, 5.5, MeasurementUnit.KILOMETERS)
    same = GoalTarget(MetricIdentifier.DISTANCE, 5.5, MeasurementUnit.KILOMETERS)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.value = 6


@pytest.mark.parametrize("metric", ["steps", DataSource.MANUAL, True, 1, {}, object()])
def test_goal_target_rejects_invalid_metrics(metric: object) -> None:
    """Raw and unrelated values are not converted into taxonomy metrics."""
    with pytest.raises(DomainValidationError, match="metric must be a MetricIdentifier"):
        GoalTarget(metric, 1, MeasurementUnit.COUNT)  # type: ignore[arg-type]


@pytest.mark.parametrize("unit", ["count", DataSource.MANUAL, True, 1, {}, object()])
def test_goal_target_rejects_invalid_units(unit: object) -> None:
    """Raw and unrelated values are not converted into taxonomy units."""
    with pytest.raises(DomainValidationError, match="unit must be a MeasurementUnit"):
        GoalTarget(MetricIdentifier.STEPS, 1, unit)  # type: ignore[arg-type]


def test_goal_target_rejects_incompatible_metric_unit() -> None:
    """Targets require the taxonomy's canonical unit without conversion."""
    with pytest.raises(DomainValidationError, match=r"unit must be.*for metric"):
        GoalTarget(MetricIdentifier.WEIGHT, 70, MeasurementUnit.GRAMS)


@pytest.mark.parametrize(
    "value",
    [True, "1", None, float("nan"), float("inf"), float("-inf"), -1, {}, object()],
)
def test_goal_target_rejects_invalid_numeric_values(value: object) -> None:
    """Target values must be finite non-negative numbers excluding bool."""
    with pytest.raises(InvalidNumericValueError, match="value"):
        GoalTarget(MetricIdentifier.STEPS, value, MeasurementUnit.COUNT)  # type: ignore[arg-type]


def test_goal_accepts_required_fields_with_draft_default() -> None:
    """Identifiers, target, and direction form a draft goal."""
    goal = _goal()

    assert goal.goal_id is _DEFAULT_GOAL_ID
    assert goal.profile_id is _DEFAULT_PROFILE_ID
    assert goal.target is _DEFAULT_TARGET
    assert goal.direction is GoalDirection.AT_LEAST
    assert goal.status is GoalStatus.DRAFT
    assert goal.start_date is None
    assert goal.target_date is None
    assert goal.title is None
    assert goal.description is None


@pytest.mark.parametrize("direction", list(GoalDirection))
def test_goal_accepts_every_direction_without_metric_reconciliation(
    direction: GoalDirection,
) -> None:
    """Every user-selected direction is accepted for a controlled target."""
    assert _goal(direction=direction).direction is direction


@pytest.mark.parametrize("status", list(GoalStatus))
def test_goal_accepts_every_explicit_status(status: GoalStatus) -> None:
    """Every supplied lifecycle status remains exact without progress checks."""
    assert _goal(status=status).status is status


@pytest.mark.parametrize(
    ("start_date", "target_date"),
    [
        (None, None),
        (date(2026, 1, 1), None),
        (None, date(2026, 1, 7)),
        (date(2026, 1, 1), date(2026, 1, 1)),
        (date(2026, 1, 1), date(2026, 1, 7)),
    ],
)
def test_goal_accepts_optional_user_supplied_dates(
    start_date: date | None,
    target_date: date | None,
) -> None:
    """Absent, independent, same-day, and ordered dates remain exact."""
    goal = _goal(start_date=start_date, target_date=target_date)

    assert goal.start_date is start_date
    assert goal.target_date is target_date


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (None, None),
        ("", None),
        (" \t\n ", None),
        ("  Weekly movement  ", "Weekly movement"),
        ("Movement  target", "Movement  target"),
        ("\u76ee\u6a19 \u041f\u043b\u0430\u043d", "\u76ee\u6a19 \u041f\u043b\u0430\u043d"),
    ],
)
def test_goal_normalizes_optional_title(title: str | None, expected: str | None) -> None:
    """Blank titles become None while non-empty Unicode text trims only edges."""
    assert _goal(title=title).title == expected


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (None, None),
        ("", None),
        (" \t\n ", None),
        ("  User context  ", "User context"),
        ("Keep  internal spacing", "Keep  internal spacing"),
        ("Line one\nLine two", "Line one\nLine two"),
        ("\u8a18\u9332 \u043e\u043f\u0438\u0441", "\u8a18\u9332 \u043e\u043f\u0438\u0441"),
    ],
)
def test_goal_normalizes_optional_description(
    description: str | None,
    expected: str | None,
) -> None:
    """Descriptions trim edges while preserving Unicode, spacing, and lines."""
    assert _goal(description=description).description == expected


def test_goal_accepts_all_optional_fields_and_preserves_objects() -> None:
    """All supplied domain objects and dates remain exactly supplied."""
    goal_id = GoalId("33333333-3333-4333-8333-333333333333")
    profile_id = ProfileId("44444444-4444-4444-8444-444444444444")
    target = GoalTarget(MetricIdentifier.WATER_INTAKE, 2_000, MeasurementUnit.MILLILITERS)
    start_date = date(2026, 1, 1)
    target_date = date(2026, 2, 1)
    goal = _goal(
        goal_id=goal_id,
        profile_id=profile_id,
        target=target,
        direction=GoalDirection.MAINTAIN,
        status=GoalStatus.ACTIVE,
        start_date=start_date,
        target_date=target_date,
        title="Hydration target",
        description="User-selected target",
    )

    assert goal.goal_id is goal_id
    assert goal.profile_id is profile_id
    assert goal.target is target
    assert goal.direction is GoalDirection.MAINTAIN
    assert goal.status is GoalStatus.ACTIVE
    assert goal.start_date is start_date
    assert goal.target_date is target_date


def test_goal_has_value_equality_and_hashing() -> None:
    """Equivalent normalized goals are equal hashable values."""
    first = _goal(title=" Target ", description=" Context ")
    same = _goal(title="Target", description="Context")

    assert first == same
    assert hash(first) == hash(same)


@pytest.mark.parametrize(
    "goal_id",
    [_GOAL_UUID, ProfileId(_GOAL_UUID), RecordId(_GOAL_UUID), {}, None, SubjectiveScore(5)],
)
def test_goal_rejects_invalid_goal_identifier_objects(goal_id: object) -> None:
    """The parent boundary requires an explicitly constructed GoalId."""
    with pytest.raises(DomainValidationError, match="goal_id must be a GoalId"):
        _goal(goal_id=goal_id)


@pytest.mark.parametrize(
    "profile_id",
    [_PROFILE_UUID, GoalId(_PROFILE_UUID), RecordId(_PROFILE_UUID), {}, None, SubjectiveScore(5)],
)
def test_goal_rejects_invalid_profile_identifier_objects(profile_id: object) -> None:
    """The parent boundary requires an explicitly constructed ProfileId."""
    with pytest.raises(DomainValidationError, match="profile_id must be a ProfileId"):
        _goal(profile_id=profile_id)


@pytest.mark.parametrize(
    "target", [{}, (MetricIdentifier.STEPS, 1, MeasurementUnit.COUNT), 1, None, object()]
)
def test_goal_rejects_invalid_target_objects(target: object) -> None:
    """The parent boundary requires an explicitly constructed GoalTarget."""
    with pytest.raises(DomainValidationError, match="target must be a GoalTarget"):
        _goal(target=target)


@pytest.mark.parametrize(
    "direction",
    ["at_least", DataSource.MANUAL, 1, True, None, {}, object()],
)
def test_goal_rejects_invalid_directions(direction: object) -> None:
    """Raw and unrelated values are not converted into directions."""
    with pytest.raises(DomainValidationError, match="direction must be a GoalDirection"):
        _goal(direction=direction)


@pytest.mark.parametrize("status", ["draft", DataSource.MANUAL, 1, True, None, {}, object()])
def test_goal_rejects_invalid_statuses(status: object) -> None:
    """Raw and unrelated values are not converted into statuses."""
    with pytest.raises(DomainValidationError, match="status must be a GoalStatus"):
        _goal(status=status)


def test_goal_status_is_not_derived_from_dates() -> None:
    """Past or absent dates never alter an explicitly supplied status."""
    completed_without_dates = _goal(status=GoalStatus.COMPLETED)
    future_independent = _goal(status=GoalStatus.ACTIVE, target_date=date(2000, 1, 1))

    assert completed_without_dates.status is GoalStatus.COMPLETED
    assert future_independent.status is GoalStatus.ACTIVE
    assert not hasattr(future_independent, "overdue")


@pytest.mark.parametrize("field_name", ["start_date", "target_date"])
@pytest.mark.parametrize(
    "value",
    [datetime(2026, 1, 1, tzinfo=UTC), "2026-01-01", True, {}, [], object()],
)
def test_goal_rejects_invalid_optional_dates(field_name: str, value: object) -> None:
    """Known dates must be exact date objects without parsing or conversion."""
    with pytest.raises(DomainValidationError, match=field_name):
        _goal(**{field_name: value})  # type: ignore[arg-type]


def test_goal_rejects_target_date_before_start_date() -> None:
    """A supplied target date cannot precede the supplied start date."""
    with pytest.raises(DomainValidationError, match="target_date must not precede start_date"):
        _goal(start_date=date(2026, 1, 2), target_date=date(2026, 1, 1))


@pytest.mark.parametrize("title", [True, 1, 1.5, {}, [], object()])
def test_goal_rejects_invalid_title_types(title: object) -> None:
    """Titles accept only strings or None without generation."""
    with pytest.raises(DomainValidationError, match="title"):
        _goal(title=title)


@pytest.mark.parametrize("description", [True, 1, 1.5, {}, [], object()])
def test_goal_rejects_invalid_description_types(description: object) -> None:
    """Descriptions accept only strings or None without analysis."""
    with pytest.raises(DomainValidationError, match="description"):
        _goal(description=description)


@pytest.mark.parametrize(
    "field_name",
    [
        "goal_id",
        "profile_id",
        "target",
        "direction",
        "status",
        "start_date",
        "target_date",
        "title",
        "description",
    ],
)
def test_wellness_goal_is_immutable(field_name: str) -> None:
    """Every stored goal field rejects reassignment."""
    with pytest.raises(FrozenInstanceError):
        setattr(_goal(), field_name, None)


def test_goal_has_exact_progress_free_field_set() -> None:
    """The record stores only approved user-defined goal fields."""
    assert tuple(field.name for field in fields(WellnessGoal)) == (
        "goal_id",
        "profile_id",
        "target",
        "direction",
        "status",
        "start_date",
        "target_date",
        "title",
        "description",
    )


@pytest.mark.parametrize(
    ("title", "description", "start_date", "target_date", "expected"),
    [
        (None, None, None, None, (False, False, False, False)),
        ("Title", "Description", date(2026, 1, 1), date(2026, 1, 7), (True, True, True, True)),
    ],
)
def test_goal_reports_optional_field_presence(
    title: str | None,
    description: str | None,
    start_date: date | None,
    target_date: date | None,
    expected: tuple[bool, bool, bool, bool],
) -> None:
    """Presence properties directly reflect normalized optional fields."""
    goal = _goal(
        title=title,
        description=description,
        start_date=start_date,
        target_date=target_date,
    )

    assert (
        goal.has_title,
        goal.has_description,
        goal.has_start_date,
        goal.has_target_date,
    ) == expected


@pytest.mark.parametrize(
    ("start_date", "target_date", "expected"),
    [
        (None, None, None),
        (date(2026, 1, 1), None, None),
        (None, date(2026, 1, 7), None),
        (date(2026, 1, 1), date(2026, 1, 1), 1),
        (date(2026, 1, 1), date(2026, 1, 7), 7),
        (date(2026, 1, 30), date(2026, 2, 2), 4),
        (date(2028, 2, 28), date(2028, 3, 1), 3),
    ],
)
def test_goal_scheduled_span_is_inclusive_and_deterministic(
    start_date: date | None,
    target_date: date | None,
    expected: int | None,
) -> None:
    """Scheduled spans use direct inclusive month and leap-day arithmetic."""
    goal = _goal(start_date=start_date, target_date=target_date)

    assert goal.scheduled_span_days == expected
    assert goal.scheduled_span_days == goal.scheduled_span_days


@pytest.mark.parametrize(
    ("status", "active", "terminal"),
    [
        (GoalStatus.DRAFT, False, False),
        (GoalStatus.ACTIVE, True, False),
        (GoalStatus.PAUSED, False, False),
        (GoalStatus.COMPLETED, False, True),
        (GoalStatus.CANCELLED, False, True),
    ],
)
def test_goal_status_predicates_reflect_only_supplied_status(
    status: GoalStatus,
    active: bool,
    terminal: bool,
) -> None:
    """Status conveniences perform direct controlled-enum checks only."""
    goal = _goal(status=status)

    assert goal.is_active is active
    assert goal.is_terminal is terminal


def test_goal_exposes_no_progress_overdue_or_recommendation_properties() -> None:
    """Goals contain no progress, achievement, overdue, or recommendation output."""
    goal = _goal()

    for name in (
        "progress",
        "progress_percentage",
        "percentage_complete",
        "remaining_value",
        "days_remaining",
        "overdue",
        "achieved",
        "on_track",
        "recommendation",
        "success_probability",
    ):
        assert not hasattr(goal, name)


def test_domain_package_exposes_complete_goal_domain_api() -> None:
    """The goal tests authoritatively define the complete public domain API."""
    expected_exports = {
        "BeverageType": BeverageType,
        "BodyMeasurementRecord": BodyMeasurementRecord,
        "CheckInTag": CheckInTag,
        "ConfidenceLevel": ConfidenceLevel,
        "CycleSymptom": CycleSymptom,
        "CycleSymptomEntry": CycleSymptomEntry,
        "DailyActivityRecord": DailyActivityRecord,
        "DailyNutritionRecord": DailyNutritionRecord,
        "DataSource": DataSource,
        "DomainValidationError": DomainValidationError,
        "GoalDirection": GoalDirection,
        "GoalId": GoalId,
        "GoalStatus": GoalStatus,
        "GoalTarget": GoalTarget,
        "HydrationRecord": HydrationRecord,
        "InsightSeverity": InsightSeverity,
        "InvalidIdentifierError": InvalidIdentifierError,
        "InvalidNumericValueError": InvalidNumericValueError,
        "InvalidTimeRangeError": InvalidTimeRangeError,
        "InvalidTimestampError": InvalidTimestampError,
        "MealNutrition": MealNutrition,
        "MealRecord": MealRecord,
        "MealType": MealType,
        "MeasurementSystem": MeasurementSystem,
        "MeasurementUnit": MeasurementUnit,
        "MenstrualBleedingRecord": MenstrualBleedingRecord,
        "MenstrualCycleRecord": MenstrualCycleRecord,
        "MenstrualFlow": MenstrualFlow,
        "MetricIdentifier": MetricIdentifier,
        "MoodCategory": MoodCategory,
        "PerceivedExertion": PerceivedExertion,
        "ProfileId": ProfileId,
        "RecordId": RecordId,
        "RecordMetadata": RecordMetadata,
        "SleepQuality": SleepQuality,
        "SleepRecord": SleepRecord,
        "SleepStageDurations": SleepStageDurations,
        "SubjectiveScore": SubjectiveScore,
        "SubjectiveWellnessCheckIn": SubjectiveWellnessCheckIn,
        "SymptomIntensity": SymptomIntensity,
        "TimeRange": TimeRange,
        "TrackedWellnessDomain": TrackedWellnessDomain,
        "WeekStart": WeekStart,
        "WellnessCategory": WellnessCategory,
        "WellnessGoal": WellnessGoal,
        "WellnessProfile": WellnessProfile,
        "WorkoutRecord": WorkoutRecord,
        "WorkoutType": WorkoutType,
    }

    assert domain.__all__ == list(expected_exports)
    assert len(domain.__all__) == len(set(domain.__all__)) == 48
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
