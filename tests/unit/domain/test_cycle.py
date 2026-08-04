"""Tests for menstrual-cycle tracking domain types."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

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
    MeasurementUnit,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    MenstrualFlow,
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
    SymptomIntensity,
    TimeRange,
    WellnessCategory,
    WorkoutRecord,
    WorkoutType,
)

_DEFAULT_START_DATE = date(2026, 8, 1)


def _metadata(*, notes: str | None = "Synthetic cycle observation") -> RecordMetadata:
    """Return valid metadata containing only neutral synthetic test data."""
    return RecordMetadata(
        record_id=RecordId("cycle-record-1"),
        recorded_at=datetime(2026, 8, 1, 9, tzinfo=UTC),
        source=DataSource.MANUAL,
        notes=notes,
    )


def _symptom(
    symptom: CycleSymptom = CycleSymptom.CRAMPS,
    intensity: SymptomIntensity | None = None,
) -> CycleSymptomEntry:
    """Return a valid symptom entry."""
    return CycleSymptomEntry(symptom, intensity)


def _bleeding_record(
    *,
    metadata: RecordMetadata | None = None,
    flow: MenstrualFlow | object = MenstrualFlow.MODERATE,
    symptoms: tuple[CycleSymptomEntry, ...] | object = (),
) -> MenstrualBleedingRecord:
    """Build a bleeding observation while keeping setup concise."""
    return MenstrualBleedingRecord(
        metadata=metadata or _metadata(),
        flow=flow,  # type: ignore[arg-type]
        symptoms=symptoms,  # type: ignore[arg-type]
    )


def _cycle_record(
    *,
    metadata: RecordMetadata | None = None,
    start_date: date | object = _DEFAULT_START_DATE,
    end_date: date | object | None = None,
) -> MenstrualCycleRecord:
    """Build a user-supplied cycle range while keeping setup concise."""
    return MenstrualCycleRecord(
        metadata=metadata or _metadata(),
        start_date=start_date,  # type: ignore[arg-type]
        end_date=end_date,  # type: ignore[arg-type]
    )


def test_menstrual_flow_has_exact_stable_ordered_members() -> None:
    """Flow values expose the complete vendor-neutral serialized vocabulary."""
    expected = [
        ("SPOTTING", "spotting"),
        ("LIGHT", "light"),
        ("MODERATE", "moderate"),
        ("HEAVY", "heavy"),
    ]

    assert [(member.name, member.value) for member in MenstrualFlow] == expected
    assert len({member.value for member in MenstrualFlow}) == len(expected)
    assert all(str(member) == member.value for member in MenstrualFlow)
    assert not {"ABNORMAL", "NORMAL", "CONCERNING", "DANGEROUS"} & set(MenstrualFlow.__members__)


def test_cycle_symptom_has_exact_stable_ordered_members() -> None:
    """Symptoms expose the complete general non-diagnostic vocabulary."""
    expected = [
        ("CRAMPS", "cramps"),
        ("BLOATING", "bloating"),
        ("HEADACHE", "headache"),
        ("BACK_DISCOMFORT", "back_discomfort"),
        ("BREAST_TENDERNESS", "breast_tenderness"),
        ("FATIGUE", "fatigue"),
        ("MOOD_CHANGE", "mood_change"),
        ("NAUSEA", "nausea"),
        ("ACNE", "acne"),
        ("FOOD_CRAVING", "food_craving"),
        ("SLEEP_CHANGE", "sleep_change"),
        ("OTHER", "other"),
    ]

    assert [(member.name, member.value) for member in CycleSymptom] == expected
    assert len({member.value for member in CycleSymptom}) == len(expected)
    assert all(str(member) == member.value for member in CycleSymptom)
    assert not {"PREGNANCY", "INFERTILITY", "DEPRESSION", "ANXIETY"} & set(CycleSymptom.__members__)


def test_symptom_intensity_has_exact_stable_ordered_members() -> None:
    """Intensity exposes the complete user-selected serialized vocabulary."""
    expected = [("MILD", "mild"), ("MODERATE", "moderate"), ("STRONG", "strong")]

    assert [(member.name, member.value) for member in SymptomIntensity] == expected
    assert len({member.value for member in SymptomIntensity}) == len(expected)
    assert all(str(member) == member.value for member in SymptomIntensity)


def test_symptom_entry_accepts_no_intensity() -> None:
    """A controlled symptom alone forms a valid entry."""
    entry = _symptom(CycleSymptom.BLOATING)

    assert entry.symptom is CycleSymptom.BLOATING
    assert entry.intensity is None


@pytest.mark.parametrize("intensity", list(SymptomIntensity))
def test_symptom_entry_accepts_every_intensity(intensity: SymptomIntensity) -> None:
    """Every controlled intensity remains exactly supplied."""
    entry = _symptom(CycleSymptom.HEADACHE, intensity)

    assert entry.symptom is CycleSymptom.HEADACHE
    assert entry.intensity is intensity


def test_symptom_entry_has_value_equality_hashing_and_immutability() -> None:
    """Symptom entries are immutable, hashable values."""
    first = _symptom(CycleSymptom.FATIGUE, SymptomIntensity.MILD)
    same = _symptom(CycleSymptom.FATIGUE, SymptomIntensity.MILD)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.symptom = CycleSymptom.OTHER


@pytest.mark.parametrize(
    "symptom",
    ["cramps", DataSource.MANUAL, 1, True, None, {}, object()],
)
def test_symptom_entry_rejects_invalid_symptom(symptom: object) -> None:
    """Raw and unrelated values are not converted into symptoms."""
    with pytest.raises(DomainValidationError, match="symptom must be a CycleSymptom"):
        CycleSymptomEntry(symptom)  # type: ignore[arg-type]


@pytest.mark.parametrize("intensity", ["mild", DataSource.MANUAL, 1, True, {}, object()])
def test_symptom_entry_rejects_invalid_intensity(intensity: object) -> None:
    """Known intensity must already be a controlled intensity value."""
    with pytest.raises(DomainValidationError, match="intensity must be a SymptomIntensity"):
        CycleSymptomEntry(CycleSymptom.CRAMPS, intensity)  # type: ignore[arg-type]


def test_bleeding_record_accepts_metadata_and_flow_only() -> None:
    """Metadata and controlled flow form a valid observation."""
    record = _bleeding_record()

    assert record.flow is MenstrualFlow.MODERATE
    assert record.symptoms == ()


@pytest.mark.parametrize("flow", list(MenstrualFlow))
def test_bleeding_record_accepts_every_flow(flow: MenstrualFlow) -> None:
    """Every controlled flow description is accepted unchanged."""
    assert _bleeding_record(flow=flow).flow is flow


def test_bleeding_record_accepts_ordered_symptoms_with_optional_intensity() -> None:
    """Unique symptom entries with and without intensity retain exact order."""
    first = _symptom(CycleSymptom.BACK_DISCOMFORT)
    second = _symptom(CycleSymptom.FATIGUE, SymptomIntensity.STRONG)
    symptoms = (first, second)
    record = _bleeding_record(symptoms=symptoms)

    assert record.symptoms is symptoms
    assert record.symptoms == (first, second)
    assert record.symptoms[0] is first
    assert record.symptoms[1] is second


@pytest.mark.parametrize("notes", [None, "Synthetic note"])
def test_bleeding_record_preserves_metadata_and_optional_notes(notes: str | None) -> None:
    """Metadata supplies timestamp and optional notes without duplicate fields."""
    metadata = _metadata(notes=notes)
    record = _bleeding_record(metadata=metadata)

    assert record.metadata is metadata
    assert record.metadata.notes == notes
    assert not hasattr(record, "notes")
    assert not hasattr(record, "recorded_at")


def test_bleeding_record_has_value_equality_hashing_and_immutability() -> None:
    """Equivalent observations are immutable, hashable values."""
    first = _bleeding_record(symptoms=(_symptom(),))
    same = _bleeding_record(symptoms=(_symptom(),))

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.flow = MenstrualFlow.LIGHT


@pytest.mark.parametrize("metadata", [{}, "metadata", None, SubjectiveScore(5)])
def test_bleeding_record_rejects_invalid_metadata(metadata: object) -> None:
    """Mappings, text, None, and unrelated domain objects are not converted."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        MenstrualBleedingRecord(metadata, MenstrualFlow.LIGHT)  # type: ignore[arg-type]


@pytest.mark.parametrize("flow", ["light", DataSource.MANUAL, 1, True, None, {}, object()])
def test_bleeding_record_rejects_invalid_flow(flow: object) -> None:
    """Raw and unrelated values are not converted into flow descriptions."""
    with pytest.raises(DomainValidationError, match="flow must be a MenstrualFlow"):
        _bleeding_record(flow=flow)


@pytest.mark.parametrize(
    "symptoms",
    [[_symptom()], {_symptom()}, "cramps", {"symptom": _symptom()}],
)
def test_bleeding_record_rejects_non_tuple_symptom_collections(symptoms: object) -> None:
    """Lists, sets, strings, and mappings are not converted into tuples."""
    with pytest.raises(DomainValidationError, match="symptoms must be a tuple"):
        _bleeding_record(symptoms=symptoms)


@pytest.mark.parametrize("entry", [CycleSymptom.CRAMPS, "cramps", DataSource.MANUAL, object()])
def test_bleeding_record_rejects_invalid_tuple_entries(entry: object) -> None:
    """Every tuple member must already be a symptom-entry value object."""
    with pytest.raises(DomainValidationError, match="every symptom must be a CycleSymptomEntry"):
        _bleeding_record(symptoms=(entry,))


@pytest.mark.parametrize(
    "symptoms",
    [
        (_symptom(CycleSymptom.CRAMPS), _symptom(CycleSymptom.CRAMPS)),
        (
            _symptom(CycleSymptom.CRAMPS, SymptomIntensity.MILD),
            _symptom(CycleSymptom.CRAMPS, SymptomIntensity.STRONG),
        ),
    ],
)
def test_bleeding_record_rejects_duplicate_symptom_types(
    symptoms: tuple[CycleSymptomEntry, ...],
) -> None:
    """A symptom type may appear only once regardless of intensity."""
    with pytest.raises(DomainValidationError, match="duplicate symptom types"):
        _bleeding_record(symptoms=symptoms)


def test_bleeding_record_symptom_tuple_is_immutable() -> None:
    """Stored symptom order cannot be item-mutated or replaced."""
    record = _bleeding_record(symptoms=(_symptom(),))

    with pytest.raises(TypeError):
        record.symptoms[0] = _symptom(CycleSymptom.OTHER)  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        record.symptoms = ()


def test_cycle_record_accepts_start_date_only() -> None:
    """A user-supplied start date may define an open range."""
    record = _cycle_record()

    assert record.start_date is _DEFAULT_START_DATE
    assert record.end_date is None


@pytest.mark.parametrize(
    "end_date",
    [_DEFAULT_START_DATE, date(2026, 8, 5)],
)
def test_cycle_record_accepts_same_or_later_end_date(end_date: date) -> None:
    """Same-day and later user-supplied end dates remain exact."""
    record = _cycle_record(end_date=end_date)

    assert record.start_date is _DEFAULT_START_DATE
    assert record.end_date is end_date


@pytest.mark.parametrize("notes", [None, "Synthetic note"])
def test_cycle_record_preserves_metadata_dates_and_optional_notes(notes: str | None) -> None:
    """Metadata and exact date objects are preserved without duplicate fields."""
    metadata = _metadata(notes=notes)
    start_date = date(2026, 8, 2)
    end_date = date(2026, 8, 6)
    record = _cycle_record(metadata=metadata, start_date=start_date, end_date=end_date)

    assert record.metadata is metadata
    assert record.start_date is start_date
    assert record.end_date is end_date
    assert record.metadata.notes == notes
    assert not hasattr(record, "notes")


def test_cycle_record_has_value_equality_hashing_and_immutability() -> None:
    """Equivalent date ranges are immutable, hashable values."""
    first = _cycle_record(end_date=date(2026, 8, 5))
    same = _cycle_record(end_date=date(2026, 8, 5))

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.end_date = date(2026, 8, 6)


@pytest.mark.parametrize("metadata", [{}, "metadata", None, SubjectiveScore(5)])
def test_cycle_record_rejects_invalid_metadata(metadata: object) -> None:
    """Mappings, text, None, and unrelated domain objects are not converted."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        MenstrualCycleRecord(metadata, _DEFAULT_START_DATE)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "start_date",
    [datetime(2026, 8, 1, tzinfo=UTC), "2026-08-01", None, {}, True, object()],
)
def test_cycle_record_rejects_invalid_start_date(start_date: object) -> None:
    """Only an exact date is accepted without parsing or conversion."""
    with pytest.raises(DomainValidationError, match="start_date must be a plain date"):
        _cycle_record(start_date=start_date)


@pytest.mark.parametrize(
    "end_date",
    [datetime(2026, 8, 5, tzinfo=UTC), "2026-08-05", {}, True, object()],
)
def test_cycle_record_rejects_invalid_end_date(end_date: object) -> None:
    """Known end dates must be exact dates without parsing or conversion."""
    with pytest.raises(DomainValidationError, match="end_date must be a plain date or None"):
        _cycle_record(end_date=end_date)


def test_cycle_record_rejects_end_date_before_start_date() -> None:
    """A supplied end date cannot precede its supplied start date."""
    with pytest.raises(DomainValidationError, match="end_date must not precede start_date"):
        _cycle_record(start_date=date(2026, 8, 5), end_date=date(2026, 8, 4))


def test_cycle_record_has_no_arbitrary_duration_limit() -> None:
    """Long user-declared ranges are accepted without population thresholds."""
    record = _cycle_record(start_date=date(2020, 1, 1), end_date=date(2026, 8, 1))

    assert record.cycle_span_days == (date(2026, 8, 1) - date(2020, 1, 1)).days + 1


@pytest.mark.parametrize(
    ("end_date", "expected"),
    [(None, True), (_DEFAULT_START_DATE, False)],
)
def test_cycle_record_reports_ongoing_state(
    end_date: date | None,
    expected: bool,
) -> None:
    """Ongoing state reflects only absence of a user-supplied end date."""
    record = _cycle_record(end_date=end_date)

    assert record.is_ongoing is expected
    assert record.is_ongoing is expected


@pytest.mark.parametrize(
    ("start_date", "end_date", "expected"),
    [
        (_DEFAULT_START_DATE, None, None),
        (_DEFAULT_START_DATE, _DEFAULT_START_DATE, 1),
        (date(2026, 8, 1), date(2026, 8, 5), 5),
        (date(2026, 1, 30), date(2026, 2, 2), 4),
        (date(2028, 2, 28), date(2028, 3, 1), 3),
    ],
)
def test_cycle_span_days_is_inclusive_and_deterministic(
    start_date: date,
    end_date: date | None,
    expected: int | None,
) -> None:
    """Recorded spans use direct inclusive month and leap-day arithmetic."""
    record = _cycle_record(start_date=start_date, end_date=end_date)

    assert record.cycle_span_days == expected
    assert record.cycle_span_days == record.cycle_span_days


def test_cycle_record_exposes_no_prediction_or_regularity_properties() -> None:
    """Date ranges contain no predictions, averages, or classifications."""
    record = _cycle_record()

    for name in (
        "predicted_next_period",
        "average_cycle_length",
        "ovulation_date",
        "fertile_window",
        "irregular_cycle",
        "cycle_regularity",
        "medical_attention_required",
    ):
        assert not hasattr(record, name)


@pytest.mark.parametrize(
    ("symptoms", "expected_count", "expected_presence"),
    [
        ((), 0, False),
        ((_symptom(),), 1, True),
        ((_symptom(), _symptom(CycleSymptom.FATIGUE)), 2, True),
    ],
)
def test_bleeding_record_reports_symptom_count_and_presence(
    symptoms: tuple[CycleSymptomEntry, ...],
    expected_count: int,
    expected_presence: bool,
) -> None:
    """Derived symptom values reflect only the immutable supplied tuple."""
    record = _bleeding_record(symptoms=symptoms)

    assert record.symptom_count == expected_count
    assert record.has_symptoms is expected_presence
    assert record.symptom_count == record.symptom_count
    assert record.has_symptoms is record.has_symptoms


def test_bleeding_record_exposes_no_score_or_risk_properties() -> None:
    """Observations contain no flow score, symptom score, or risk output."""
    record = _bleeding_record()

    for name in ("flow_score", "symptom_score", "health_risk", "medical_attention_required"):
        assert not hasattr(record, name)


@pytest.mark.parametrize(
    ("record_factory", "field_name"),
    [
        (_bleeding_record, "metadata"),
        (_bleeding_record, "flow"),
        (_bleeding_record, "symptoms"),
        (_cycle_record, "metadata"),
        (_cycle_record, "start_date"),
        (_cycle_record, "end_date"),
    ],
)
def test_cycle_domain_records_are_immutable(record_factory: object, field_name: str) -> None:
    """Every stored field on both record types rejects reassignment."""
    record = record_factory()  # type: ignore[operator]

    with pytest.raises(FrozenInstanceError):
        setattr(record, field_name, None)


def test_domain_package_exposes_cycle_domain_api() -> None:
    """Public exports preserve every prior and cycle-domain type."""
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
        "MeasurementUnit": MeasurementUnit,
        "MenstrualBleedingRecord": MenstrualBleedingRecord,
        "MenstrualCycleRecord": MenstrualCycleRecord,
        "MenstrualFlow": MenstrualFlow,
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
        "SymptomIntensity": SymptomIntensity,
        "TimeRange": TimeRange,
        "WellnessCategory": WellnessCategory,
        "WorkoutRecord": WorkoutRecord,
        "WorkoutType": WorkoutType,
    }

    assert set(expected_exports) <= set(domain.__all__)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
