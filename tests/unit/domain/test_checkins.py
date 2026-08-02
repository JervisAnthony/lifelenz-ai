"""Tests for subjective wellness check-in domain types."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from lifelenz import domain
from lifelenz.domain import (
    BeverageType,
    BodyMeasurementRecord,
    CheckInTag,
    ConfidenceLevel,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    DomainValidationError,
    HydrationRecord,
    InsightSeverity,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
    MealNutrition,
    MealRecord,
    MealType,
    MeasurementUnit,
    MetricIdentifier,
    MoodCategory,
    PerceivedExertion,
    RecordId,
    RecordMetadata,
    SleepQuality,
    SleepRecord,
    SleepStageDurations,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WellnessCategory,
    WorkoutRecord,
    WorkoutType,
)

_UNSET = object()


def _metadata(*, notes: str | None = "Self-reported after lunch") -> RecordMetadata:
    """Return valid metadata for a subjective check-in."""
    return RecordMetadata(
        record_id=RecordId("check-in-1"),
        recorded_at=datetime(2026, 8, 6, 13, 15, tzinfo=UTC),
        source=DataSource.MANUAL,
        notes=notes,
    )


def _check_in(
    *,
    metadata: RecordMetadata | None = None,
    mood_score: SubjectiveScore | object = _UNSET,
    energy_score: SubjectiveScore | object = _UNSET,
    stress_score: SubjectiveScore | object = _UNSET,
    motivation_score: SubjectiveScore | object | None = None,
    mood_category: MoodCategory | object | None = None,
    tags: tuple[CheckInTag, ...] | object = (),
) -> SubjectiveWellnessCheckIn:
    """Build a check-in while keeping test setup concise."""
    return SubjectiveWellnessCheckIn(
        metadata=metadata or _metadata(),
        mood_score=SubjectiveScore(6) if mood_score is _UNSET else mood_score,  # type: ignore[arg-type]
        energy_score=SubjectiveScore(7) if energy_score is _UNSET else energy_score,  # type: ignore[arg-type]
        stress_score=SubjectiveScore(4) if stress_score is _UNSET else stress_score,  # type: ignore[arg-type]
        motivation_score=motivation_score,  # type: ignore[arg-type]
        mood_category=mood_category,  # type: ignore[arg-type]
        tags=tags,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("value", [1, 5, 10])
def test_subjective_score_accepts_inclusive_range(value: int) -> None:
    """Minimum, representative, and maximum scores remain exact."""
    score = SubjectiveScore(value)

    assert score.value is value
    assert str(score) == str(value)


def test_subjective_score_has_value_equality_hashing_and_immutability() -> None:
    """Scores are immutable, hashable value objects."""
    first = SubjectiveScore(6)
    same = SubjectiveScore(6)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.value = 7


@pytest.mark.parametrize("value", [0, -1, 11])
def test_subjective_score_rejects_out_of_range_integers(value: int) -> None:
    """Plain integers outside the reporting scale are invalid."""
    with pytest.raises(InvalidNumericValueError, match="value"):
        SubjectiveScore(value)


@pytest.mark.parametrize("value", [True, 5.0, "5", None, PerceivedExertion(5)])
def test_subjective_score_rejects_non_plain_integers(value: object) -> None:
    """Booleans, floats, strings, None, and unrelated objects are not converted."""
    with pytest.raises(InvalidNumericValueError, match="plain integer"):
        SubjectiveScore(value)  # type: ignore[arg-type]


def test_mood_category_has_exact_stable_ordered_members() -> None:
    """Mood categories expose the complete neutral serialized vocabulary."""
    expected = [
        ("VERY_LOW", "very_low"),
        ("LOW", "low"),
        ("NEUTRAL", "neutral"),
        ("HIGH", "high"),
        ("VERY_HIGH", "very_high"),
    ]

    assert [(member.name, member.value) for member in MoodCategory] == expected
    assert len({member.value for member in MoodCategory}) == len(expected)
    assert all(str(member) == member.value for member in MoodCategory)


def test_check_in_tag_has_exact_stable_ordered_members() -> None:
    """Context tags expose the complete neutral serialized vocabulary."""
    expected = [
        ("RESTED", "rested"),
        ("TIRED", "tired"),
        ("FOCUSED", "focused"),
        ("DISTRACTED", "distracted"),
        ("CALM", "calm"),
        ("TENSE", "tense"),
        ("MOTIVATED", "motivated"),
        ("UNMOTIVATED", "unmotivated"),
        ("SOCIAL", "social"),
        ("SOLITARY", "solitary"),
        ("OTHER", "other"),
    ]

    assert [(member.name, member.value) for member in CheckInTag] == expected
    assert len({member.value for member in CheckInTag}) == len(expected)
    assert all(str(member) == member.value for member in CheckInTag)


def test_check_in_accepts_required_fields_only() -> None:
    """Metadata plus mood, energy, and stress form a valid check-in."""
    record = _check_in()

    assert record.motivation_score is None
    assert record.mood_category is None
    assert record.tags == ()


def test_check_in_accepts_each_optional_value() -> None:
    """Motivation, mood category, and tags may be supplied independently."""
    motivation = SubjectiveScore(8)

    assert _check_in(motivation_score=motivation).motivation_score is motivation
    assert _check_in(mood_category=MoodCategory.HIGH).mood_category is MoodCategory.HIGH
    assert _check_in(tags=(CheckInTag.CALM,)).tags == (CheckInTag.CALM,)


def test_check_in_accepts_all_optional_values_and_preserves_objects() -> None:
    """Metadata, scores, category, and ordered tags remain exactly supplied."""
    metadata = _metadata()
    mood = SubjectiveScore(8)
    energy = SubjectiveScore(6)
    stress = SubjectiveScore(3)
    motivation = SubjectiveScore(9)
    tags = (CheckInTag.FOCUSED, CheckInTag.CALM, CheckInTag.SOCIAL)
    record = _check_in(
        metadata=metadata,
        mood_score=mood,
        energy_score=energy,
        stress_score=stress,
        motivation_score=motivation,
        mood_category=MoodCategory.VERY_HIGH,
        tags=tags,
    )

    assert record.metadata is metadata
    assert record.mood_score is mood
    assert record.energy_score is energy
    assert record.stress_score is stress
    assert record.motivation_score is motivation
    assert record.mood_category is MoodCategory.VERY_HIGH
    assert record.tags is tags
    assert record.tags == tags


@pytest.mark.parametrize("notes", [None, "User note"])
def test_check_in_uses_metadata_for_optional_notes(notes: str | None) -> None:
    """Notes remain solely in preserved shared metadata."""
    metadata = _metadata(notes=notes)
    record = _check_in(metadata=metadata)

    assert record.metadata is metadata
    assert record.metadata.notes == notes
    assert not hasattr(record, "notes")


def test_check_in_has_value_equality_and_hashing() -> None:
    """Equivalent check-ins are equal immutable hashable values."""
    first = _check_in(motivation_score=SubjectiveScore(8), tags=(CheckInTag.CALM,))
    same = _check_in(motivation_score=SubjectiveScore(8), tags=(CheckInTag.CALM,))

    assert first == same
    assert hash(first) == hash(same)


@pytest.mark.parametrize("metadata", [{}, "metadata", None, BodyMeasurementRecord(_metadata(), 70)])
def test_check_in_rejects_invalid_metadata(metadata: object) -> None:
    """Mappings, text, None, and unrelated domain records are not converted."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        SubjectiveWellnessCheckIn(  # type: ignore[arg-type]
            metadata,
            SubjectiveScore(5),
            SubjectiveScore(5),
            SubjectiveScore(5),
        )


@pytest.mark.parametrize("field_name", ["mood_score", "energy_score", "stress_score"])
@pytest.mark.parametrize(
    "value",
    [5, 5.0, "5", True, None, PerceivedExertion(5)],
)
def test_check_in_rejects_invalid_required_score_objects(
    field_name: str,
    value: object,
) -> None:
    """Required scores must be explicitly constructed SubjectiveScore values."""
    with pytest.raises(DomainValidationError, match=field_name):
        _check_in(**{field_name: value})  # type: ignore[arg-type]


def test_check_in_preserves_valid_required_score_for_each_field() -> None:
    """Each required score position accepts and preserves its value object."""
    for field_name in ("mood_score", "energy_score", "stress_score"):
        score = SubjectiveScore(9)
        record = _check_in(**{field_name: score})  # type: ignore[arg-type]
        assert getattr(record, field_name) is score


@pytest.mark.parametrize("value", [5, 5.0, "5", True, PerceivedExertion(5)])
def test_check_in_rejects_invalid_motivation_score_objects(value: object) -> None:
    """Known motivation requires an explicitly constructed SubjectiveScore."""
    with pytest.raises(DomainValidationError, match="motivation_score"):
        _check_in(motivation_score=value)


@pytest.mark.parametrize("mood_category", [None, *MoodCategory])
def test_check_in_accepts_optional_mood_categories(
    mood_category: MoodCategory | None,
) -> None:
    """None and every controlled mood category are accepted unchanged."""
    assert _check_in(mood_category=mood_category).mood_category is mood_category


@pytest.mark.parametrize("value", ["high", DataSource.MANUAL, 1, True, {}, object()])
def test_check_in_rejects_invalid_mood_categories(value: object) -> None:
    """Raw and unrelated values are not converted into mood categories."""
    with pytest.raises(DomainValidationError, match="mood_category"):
        _check_in(mood_category=value)


def test_check_in_does_not_reconcile_score_and_mood_category() -> None:
    """Independently reported score and category are never reconciled."""
    record = _check_in(mood_score=SubjectiveScore(2), mood_category=MoodCategory.HIGH)

    assert record.mood_score.value == 2
    assert record.mood_category is MoodCategory.HIGH


@pytest.mark.parametrize(
    "tags",
    [(), (CheckInTag.CALM,), (CheckInTag.TIRED, CheckInTag.SOLITARY, CheckInTag.OTHER)],
)
def test_check_in_accepts_unique_ordered_tag_tuples(tags: tuple[CheckInTag, ...]) -> None:
    """Empty, single, and multiple unique tag tuples retain exact order."""
    record = _check_in(tags=tags)

    assert record.tags is tags
    assert record.tags == tags


def test_check_in_rejects_duplicate_tags() -> None:
    """The same controlled tag cannot appear twice."""
    with pytest.raises(DomainValidationError, match="must not contain duplicates"):
        _check_in(tags=(CheckInTag.CALM, CheckInTag.CALM))


@pytest.mark.parametrize(
    "tags",
    [
        [CheckInTag.CALM],
        {CheckInTag.CALM},
        "calm",
        {"tag": CheckInTag.CALM},
    ],
)
def test_check_in_rejects_non_tuple_tag_collections(tags: object) -> None:
    """Lists, sets, strings, and mappings are not converted into tuples."""
    with pytest.raises(DomainValidationError, match="tags must be a tuple"):
        _check_in(tags=tags)


@pytest.mark.parametrize("tag", ["calm", DataSource.MANUAL, object()])
def test_check_in_rejects_invalid_values_inside_tag_tuple(tag: object) -> None:
    """Tuple elements must already be controlled CheckInTag values."""
    with pytest.raises(DomainValidationError, match="every tag must be a CheckInTag"):
        _check_in(tags=(tag,))


def test_check_in_tags_are_immutable() -> None:
    """Stored tags cannot be item-mutated or replaced on the frozen record."""
    record = _check_in(tags=(CheckInTag.CALM, CheckInTag.FOCUSED))

    with pytest.raises(TypeError):
        record.tags[0] = CheckInTag.TENSE  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        record.tags = (CheckInTag.TENSE,)


@pytest.mark.parametrize(
    "field_name",
    [
        "metadata",
        "mood_score",
        "energy_score",
        "stress_score",
        "motivation_score",
        "mood_category",
        "tags",
    ],
)
def test_check_in_is_immutable(field_name: str) -> None:
    """Every stored field rejects reassignment."""
    record = _check_in()

    with pytest.raises(FrozenInstanceError):
        setattr(record, field_name, None)


@pytest.mark.parametrize(
    ("motivation_score", "expected"),
    [(None, False), (SubjectiveScore(8), True)],
)
def test_check_in_reports_motivation_presence(
    motivation_score: SubjectiveScore | None,
    expected: bool,
) -> None:
    """Motivation presence reflects only an explicitly supplied score."""
    record = _check_in(motivation_score=motivation_score)

    assert record.has_motivation_score is expected
    assert record.has_motivation_score is expected


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ((), 0),
        ((CheckInTag.CALM,), 1),
        ((CheckInTag.CALM, CheckInTag.FOCUSED, CheckInTag.SOCIAL), 3),
    ],
)
def test_check_in_tag_count_is_direct_and_stable(
    tags: tuple[CheckInTag, ...],
    expected: int,
) -> None:
    """Tag count directly reflects the immutable tuple length."""
    record = _check_in(tags=tags)

    assert record.tag_count == expected
    assert record.tag_count == record.tag_count


def test_check_in_exposes_no_aggregate_or_interpreted_properties() -> None:
    """The record contains no composite, recovery, advice, or classification output."""
    record = _check_in()

    for name in (
        "average_score",
        "combined_wellness_score",
        "wellbeing_score",
        "recovery_score",
        "classification",
        "recommendation",
        "advice",
    ):
        assert not hasattr(record, name)


def test_domain_package_exposes_complete_check_in_domain_api() -> None:
    """The check-in tests authoritatively define the complete public domain API."""
    expected_exports = {
        "BeverageType": BeverageType,
        "BodyMeasurementRecord": BodyMeasurementRecord,
        "CheckInTag": CheckInTag,
        "ConfidenceLevel": ConfidenceLevel,
        "DailyActivityRecord": DailyActivityRecord,
        "DailyNutritionRecord": DailyNutritionRecord,
        "DataSource": DataSource,
        "DomainValidationError": DomainValidationError,
        "HydrationRecord": HydrationRecord,
        "InsightSeverity": InsightSeverity,
        "InvalidIdentifierError": InvalidIdentifierError,
        "InvalidNumericValueError": InvalidNumericValueError,
        "InvalidTimeRangeError": InvalidTimeRangeError,
        "InvalidTimestampError": InvalidTimestampError,
        "MealNutrition": MealNutrition,
        "MealRecord": MealRecord,
        "MealType": MealType,
        "MeasurementUnit": MeasurementUnit,
        "MetricIdentifier": MetricIdentifier,
        "MoodCategory": MoodCategory,
        "PerceivedExertion": PerceivedExertion,
        "RecordId": RecordId,
        "RecordMetadata": RecordMetadata,
        "SleepQuality": SleepQuality,
        "SleepRecord": SleepRecord,
        "SleepStageDurations": SleepStageDurations,
        "SubjectiveScore": SubjectiveScore,
        "SubjectiveWellnessCheckIn": SubjectiveWellnessCheckIn,
        "TimeRange": TimeRange,
        "WellnessCategory": WellnessCategory,
        "WorkoutRecord": WorkoutRecord,
        "WorkoutType": WorkoutType,
    }

    assert domain.__all__ == list(expected_exports)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
