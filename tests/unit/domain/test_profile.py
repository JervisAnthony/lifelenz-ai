"""Tests for privacy-conscious wellness-profile domain types."""

from dataclasses import FrozenInstanceError, fields
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
    WellnessProfile,
    WorkoutRecord,
    WorkoutType,
)

_PROFILE_UUID = "123e4567-e89b-12d3-a456-426614174000"
_DEFAULT_PROFILE_ID = ProfileId(_PROFILE_UUID)


def _profile(
    *,
    profile_id: ProfileId | object = _DEFAULT_PROFILE_ID,
    time_zone: str | object = "UTC",
    display_name: str | object | None = None,
    measurement_system: MeasurementSystem | object = MeasurementSystem.METRIC,
    week_start: WeekStart | object = WeekStart.MONDAY,
    tracked_domains: tuple[TrackedWellnessDomain, ...] | object = (),
) -> WellnessProfile:
    """Build a wellness profile while keeping test setup concise."""
    return WellnessProfile(
        profile_id=profile_id,  # type: ignore[arg-type]
        time_zone=time_zone,  # type: ignore[arg-type]
        display_name=display_name,  # type: ignore[arg-type]
        measurement_system=measurement_system,  # type: ignore[arg-type]
        week_start=week_start,  # type: ignore[arg-type]
        tracked_domains=tracked_domains,  # type: ignore[arg-type]
    )


def test_profile_id_accepts_and_preserves_canonical_uuid_text() -> None:
    """A representative canonical UUID remains exactly supplied."""
    identifier = ProfileId(_PROFILE_UUID)

    assert identifier.value == _PROFILE_UUID
    assert str(identifier) == _PROFILE_UUID


def test_profile_id_accepts_uppercase_canonical_uuid_without_normalizing() -> None:
    """Canonical uppercase UUID text follows RecordId's preservation convention."""
    uppercase_value = _PROFILE_UUID.upper()
    identifier = ProfileId(uppercase_value)

    assert identifier.value == uppercase_value
    assert str(identifier) == uppercase_value


def test_profile_id_has_value_equality_hashing_and_immutability() -> None:
    """Profile identifiers are immutable, hashable values."""
    first = ProfileId(_PROFILE_UUID)
    same = ProfileId(_PROFILE_UUID)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.value = "00000000-0000-0000-0000-000000000000"


def test_profile_id_generate_returns_unique_uuid4_values() -> None:
    """Generated profile identifiers use standard unique UUID4 text."""
    first = ProfileId.generate()
    second = ProfileId.generate()

    assert UUID(first.value).version == 4
    assert str(UUID(first.value)) == first.value
    assert first != second


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "not-a-uuid",
        "{123e4567-e89b-12d3-a456-426614174000}",
        "123e4567e89b12d3a456426614174000",
        True,
        None,
        {},
        RecordId(_PROFILE_UUID),
        object(),
    ],
)
def test_profile_id_rejects_invalid_values(value: object) -> None:
    """Empty, noncanonical, non-UUID, and unrelated values are rejected."""
    with pytest.raises(InvalidIdentifierError, match="profile identifier"):
        ProfileId(value)  # type: ignore[arg-type]


def test_profile_id_is_semantically_distinct_from_record_id() -> None:
    """Equal text does not collapse profile and record identifier types."""
    assert ProfileId(_PROFILE_UUID) != RecordId(_PROFILE_UUID)
    assert not isinstance(ProfileId(_PROFILE_UUID), RecordId)


def test_measurement_system_has_exact_stable_ordered_members() -> None:
    """Measurement systems expose the complete presentation vocabulary."""
    expected = [("METRIC", "metric"), ("IMPERIAL", "imperial")]

    assert [(member.name, member.value) for member in MeasurementSystem] == expected
    assert len({member.value for member in MeasurementSystem}) == len(expected)
    assert all(str(member) == member.value for member in MeasurementSystem)


def test_week_start_has_exact_stable_ordered_members() -> None:
    """Week starts expose the complete grouping vocabulary."""
    expected = [("MONDAY", "monday"), ("SUNDAY", "sunday")]

    assert [(member.name, member.value) for member in WeekStart] == expected
    assert len({member.value for member in WeekStart}) == len(expected)
    assert all(str(member) == member.value for member in WeekStart)


def test_tracked_domain_has_exact_stable_ordered_members() -> None:
    """Tracked domains expose the complete feature-preference vocabulary."""
    expected = [
        ("SLEEP", "sleep"),
        ("ACTIVITY", "activity"),
        ("HYDRATION", "hydration"),
        ("NUTRITION", "nutrition"),
        ("BODY_MEASUREMENTS", "body_measurements"),
        ("SUBJECTIVE_CHECK_INS", "subjective_check_ins"),
        ("MENSTRUAL_CYCLE", "menstrual_cycle"),
    ]

    assert [(member.name, member.value) for member in TrackedWellnessDomain] == expected
    assert len({member.value for member in TrackedWellnessDomain}) == len(expected)
    assert all(str(member) == member.value for member in TrackedWellnessDomain)
    assert not {
        "MEDICAL",
        "MENTAL_HEALTH",
        "FERTILITY",
        "PREGNANCY",
        "DISEASE_MANAGEMENT",
    } & set(TrackedWellnessDomain.__members__)


def test_profile_accepts_required_fields_with_neutral_defaults() -> None:
    """Identifier and time zone form a profile with documented defaults."""
    profile = _profile()

    assert profile.profile_id is _DEFAULT_PROFILE_ID
    assert profile.time_zone == "UTC"
    assert profile.display_name is None
    assert profile.measurement_system is MeasurementSystem.METRIC
    assert profile.week_start is WeekStart.MONDAY
    assert profile.tracked_domains == ()


def test_profile_has_exact_privacy_conscious_field_set() -> None:
    """The profile stores only approved wellness preferences."""
    assert tuple(field.name for field in fields(WellnessProfile)) == (
        "profile_id",
        "time_zone",
        "display_name",
        "measurement_system",
        "week_start",
        "tracked_domains",
    )


@pytest.mark.parametrize(
    ("display_name", "expected"),
    [
        (None, None),
        ("", None),
        (" \t\n ", None),
        ("  River  ", "River"),
        ("River  Stone", "River  Stone"),
        ("\u041c\u0438\u0440\u0430 \u674e", "\u041c\u0438\u0440\u0430 \u674e"),
    ],
)
def test_profile_normalizes_optional_display_name(
    display_name: str | None,
    expected: str | None,
) -> None:
    """Blank names become None while non-empty Unicode text trims only edges."""
    assert _profile(display_name=display_name).display_name == expected


@pytest.mark.parametrize("measurement_system", list(MeasurementSystem))
def test_profile_accepts_every_measurement_system(
    measurement_system: MeasurementSystem,
) -> None:
    """Metric and imperial preferences remain controlled presentation values."""
    assert _profile(measurement_system=measurement_system).measurement_system is measurement_system


@pytest.mark.parametrize("week_start", list(WeekStart))
def test_profile_accepts_every_week_start(week_start: WeekStart) -> None:
    """Monday and Sunday grouping preferences remain exact."""
    assert _profile(week_start=week_start).week_start is week_start


@pytest.mark.parametrize(
    "tracked_domains",
    [
        (),
        (TrackedWellnessDomain.SLEEP,),
        (TrackedWellnessDomain.HYDRATION, TrackedWellnessDomain.SLEEP),
        tuple(TrackedWellnessDomain),
    ],
)
def test_profile_accepts_unique_ordered_tracked_domains(
    tracked_domains: tuple[TrackedWellnessDomain, ...],
) -> None:
    """Empty, partial, and complete capability selections retain exact order."""
    profile = _profile(tracked_domains=tracked_domains)

    assert profile.tracked_domains is tracked_domains
    assert profile.tracked_domains == tracked_domains


def test_profile_preserves_identifier_and_time_zone_exactly() -> None:
    """Validated identifier and time-zone preferences remain supplied objects."""
    identifier = ProfileId("AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA")
    profile = _profile(profile_id=identifier, time_zone="America/New_York")

    assert profile.profile_id is identifier
    assert profile.time_zone == "America/New_York"


def test_profile_has_value_equality_and_hashing() -> None:
    """Equivalent profiles are equal hashable values after name normalization."""
    first = _profile(display_name=" River ", tracked_domains=(TrackedWellnessDomain.SLEEP,))
    same = _profile(display_name="River", tracked_domains=(TrackedWellnessDomain.SLEEP,))

    assert first == same
    assert hash(first) == hash(same)


@pytest.mark.parametrize(
    "profile_id",
    [_PROFILE_UUID, RecordId(_PROFILE_UUID), {}, "not-an-id", None, SubjectiveScore(5)],
)
def test_profile_rejects_invalid_profile_identifier_objects(profile_id: object) -> None:
    """The parent boundary requires an explicitly constructed ProfileId."""
    with pytest.raises(DomainValidationError, match="profile_id must be a ProfileId"):
        _profile(profile_id=profile_id)


@pytest.mark.parametrize(
    "time_zone",
    [
        "UTC",
        "Asia/Kolkata",
        "Europe/Amsterdam",
        "America/New_York",
        "America/Argentina/Buenos_Aires",
    ],
)
def test_profile_accepts_structurally_valid_time_zones(time_zone: str) -> None:
    """Common and multi-segment identifiers validate without host lookup."""
    assert _profile(time_zone=time_zone).time_zone == time_zone


@pytest.mark.parametrize(
    "time_zone",
    [
        "",
        "   ",
        " Asia/Kolkata",
        "Asia/Kolkata ",
        "Asia/ Kolkata",
        "Asia/\tKolkata",
        "Asia/\nKolkata",
        "/Asia/Kolkata",
        "Asia/Kolkata/",
        "Asia//Kolkata",
        "Asia\\Kolkata",
        "Kolkata",
        "Asia/\x00Kolkata",
        True,
        5,
        None,
        {},
        object(),
    ],
)
def test_profile_rejects_invalid_time_zones(time_zone: object) -> None:
    """Invalid structures and non-string objects are rejected without lookup."""
    with pytest.raises(DomainValidationError, match="time_zone"):
        _profile(time_zone=time_zone)


@pytest.mark.parametrize("display_name", [True, 5, 5.5, {}, [], object()])
def test_profile_rejects_invalid_display_name_types(display_name: object) -> None:
    """Display names accept only strings or None without inference."""
    with pytest.raises(DomainValidationError, match="display_name"):
        _profile(display_name=display_name)


@pytest.mark.parametrize(
    "measurement_system",
    ["metric", DataSource.MANUAL, 1, True, None, {}, object()],
)
def test_profile_rejects_invalid_measurement_systems(measurement_system: object) -> None:
    """Raw and unrelated values are not converted into measurement systems."""
    with pytest.raises(DomainValidationError, match="measurement_system"):
        _profile(measurement_system=measurement_system)


@pytest.mark.parametrize(
    "week_start",
    ["monday", DataSource.MANUAL, 1, True, None, {}, object()],
)
def test_profile_rejects_invalid_week_starts(week_start: object) -> None:
    """Raw and unrelated values are not converted into week boundaries."""
    with pytest.raises(DomainValidationError, match="week_start"):
        _profile(week_start=week_start)


@pytest.mark.parametrize(
    "tracked_domains",
    [
        [TrackedWellnessDomain.SLEEP],
        {TrackedWellnessDomain.SLEEP},
        "sleep",
        {"domain": TrackedWellnessDomain.SLEEP},
    ],
)
def test_profile_rejects_non_tuple_tracked_domain_collections(
    tracked_domains: object,
) -> None:
    """Lists, sets, strings, and mappings are not converted into tuples."""
    with pytest.raises(DomainValidationError, match="tracked_domains must be a tuple"):
        _profile(tracked_domains=tracked_domains)


@pytest.mark.parametrize("tracked_domain", ["sleep", DataSource.MANUAL, object()])
def test_profile_rejects_invalid_values_inside_tracked_domain_tuple(
    tracked_domain: object,
) -> None:
    """Every tuple element must already be a controlled tracked-domain value."""
    with pytest.raises(DomainValidationError, match="every tracked domain"):
        _profile(tracked_domains=(tracked_domain,))


def test_profile_rejects_duplicate_tracked_domains() -> None:
    """The same capability cannot appear more than once."""
    with pytest.raises(DomainValidationError, match="must not contain duplicates"):
        _profile(
            tracked_domains=(
                TrackedWellnessDomain.SLEEP,
                TrackedWellnessDomain.SLEEP,
            )
        )


def test_profile_tracked_domain_tuple_is_immutable() -> None:
    """Stored capability order cannot be item-mutated or replaced."""
    profile = _profile(tracked_domains=(TrackedWellnessDomain.HYDRATION,))

    with pytest.raises(TypeError):
        profile.tracked_domains[0] = TrackedWellnessDomain.SLEEP  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        profile.tracked_domains = ()


@pytest.mark.parametrize(
    "field_name",
    [
        "profile_id",
        "time_zone",
        "display_name",
        "measurement_system",
        "week_start",
        "tracked_domains",
    ],
)
def test_wellness_profile_is_immutable(field_name: str) -> None:
    """Every stored profile field rejects reassignment."""
    profile = _profile()

    with pytest.raises(FrozenInstanceError):
        setattr(profile, field_name, None)


@pytest.mark.parametrize(
    ("display_name", "expected"),
    [(None, False), ("River", True)],
)
def test_profile_reports_display_name_presence(
    display_name: str | None,
    expected: bool,
) -> None:
    """Display-name presence reflects the normalized optional value."""
    profile = _profile(display_name=display_name)

    assert profile.has_display_name is expected
    assert profile.has_display_name is expected


@pytest.mark.parametrize(
    ("tracked_domains", "expected"),
    [
        ((), 0),
        ((TrackedWellnessDomain.SLEEP,), 1),
        ((TrackedWellnessDomain.SLEEP, TrackedWellnessDomain.ACTIVITY), 2),
    ],
)
def test_profile_reports_tracked_domain_count(
    tracked_domains: tuple[TrackedWellnessDomain, ...],
    expected: int,
) -> None:
    """Tracked-domain count directly reflects the immutable tuple length."""
    profile = _profile(tracked_domains=tracked_domains)

    assert profile.tracked_domain_count == expected
    assert profile.tracked_domain_count == profile.tracked_domain_count


def test_profile_tracks_reports_selected_and_unselected_domains() -> None:
    """Membership checking reflects only explicitly selected capabilities."""
    profile = _profile(
        tracked_domains=(TrackedWellnessDomain.HYDRATION, TrackedWellnessDomain.SLEEP)
    )

    assert profile.tracks(TrackedWellnessDomain.HYDRATION) is True
    assert profile.tracks(TrackedWellnessDomain.ACTIVITY) is False
    assert profile.tracks(TrackedWellnessDomain.HYDRATION) is True


@pytest.mark.parametrize("tracked_domain", ["sleep", DataSource.MANUAL, object()])
def test_profile_tracks_rejects_invalid_domain_objects(tracked_domain: object) -> None:
    """Membership checks require an existing controlled domain object."""
    with pytest.raises(DomainValidationError, match="domain must be a TrackedWellnessDomain"):
        _profile().tracks(tracked_domain)  # type: ignore[arg-type]


def test_profile_exposes_no_completeness_health_or_recommendation_properties() -> None:
    """Profiles contain no scoring, risk, recommendation, or automatic enabling output."""
    profile = _profile()

    for name in (
        "profile_completeness_score",
        "health_profile_score",
        "health_risk",
        "recommended_domains",
        "recommendation",
        "default_goals",
    ):
        assert not hasattr(profile, name)


def test_domain_package_exposes_profile_domain_api() -> None:
    """Public exports preserve every prior and profile-domain type."""
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
        "WellnessProfile": WellnessProfile,
        "WorkoutRecord": WorkoutRecord,
        "WorkoutType": WorkoutType,
    }

    assert set(expected_exports) <= set(domain.__all__)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
