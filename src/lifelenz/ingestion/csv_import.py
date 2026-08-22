"""Versioned CSV ingestion for supported LifeLenz wellness records."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum, StrEnum, unique
from math import isfinite
from typing import Any, Callable

from lifelenz.domain import (
    BeverageType,
    BodyMeasurementRecord,
    CheckInTag,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    DomainValidationError,
    HydrationRecord,
    MealNutrition,
    MoodCategory,
    RecordId,
    RecordMetadata,
    SleepQuality,
    SleepRecord,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    TimeRange,
)
from lifelenz.repositories import WellnessRecord

CSV_SCHEMA_VERSION = 1
MAX_CSV_BYTES = 1_000_000
MAX_CSV_ROWS = 5_000


@unique
class CsvImportRecordType(StrEnum):
    """Record categories supported by the first LifeLenz CSV schema."""

    SLEEP = "sleep"
    DAILY_ACTIVITY = "daily_activity"
    HYDRATION = "hydration"
    DAILY_NUTRITION = "daily_nutrition"
    BODY_MEASUREMENT = "body_measurement"
    SUBJECTIVE_CHECK_IN = "subjective_check_in"


@dataclass(frozen=True, slots=True)
class CsvImportIssue:
    """One actionable file- or row-level CSV validation problem."""

    row_number: int | None
    field: str | None
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ParsedCsvRecord:
    """A valid parsed record retaining its source CSV row number."""

    row_number: int
    record: WellnessRecord


@dataclass(frozen=True, slots=True)
class CsvParseResult:
    """Pure parsing result without persistence side effects."""

    schema_version: int
    record_type: CsvImportRecordType
    total_rows: int
    records: tuple[ParsedCsvRecord, ...]
    issues: tuple[CsvImportIssue, ...]

    @property
    def valid_rows(self) -> int:
        return len(self.records)

    @property
    def invalid_rows(self) -> int:
        return self.total_rows - self.valid_rows


@dataclass(frozen=True, slots=True)
class _CsvSchema:
    required_headers: frozenset[str]
    optional_headers: frozenset[str]
    builder: Callable[[dict[str, str], int], WellnessRecord]

    @property
    def allowed_headers(self) -> frozenset[str]:
        return self.required_headers | self.optional_headers


class _RowValueError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def _required(row: dict[str, str], field: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise _RowValueError(field, f"{field} is required")
    return value


def _optional(row: dict[str, str], field: str) -> str | None:
    value = row.get(field, "").strip()
    return value or None


def _parse_datetime(row: dict[str, str], field: str = "recorded_at") -> datetime:
    raw = _required(row, field)
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as error:
        raise _RowValueError(field, f"{field} must be an ISO 8601 timestamp") from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise _RowValueError(field, f"{field} must include a UTC offset")
    return value


def _parse_date(row: dict[str, str], field: str) -> date:
    raw = _required(row, field)
    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise _RowValueError(field, f"{field} must be an ISO 8601 date") from error


def _parse_float(
    row: dict[str, str],
    field: str,
    *,
    required: bool = False,
    default: float | None = None,
) -> float | None:
    raw = _required(row, field) if required else _optional(row, field)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as error:
        raise _RowValueError(field, f"{field} must be numeric") from error
    if not isfinite(value):
        raise _RowValueError(field, f"{field} must be finite")
    return value


def _parse_int(
    row: dict[str, str],
    field: str,
    *,
    required: bool = False,
    default: int | None = None,
) -> int | None:
    raw = _required(row, field) if required else _optional(row, field)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise _RowValueError(field, f"{field} must be an integer") from error


def _parse_enum[T: Enum](
    row: dict[str, str],
    field: str,
    enum_type: type[T],
    *,
    required: bool = False,
    default: T | None = None,
) -> T | None:
    raw = _required(row, field) if required else _optional(row, field)
    if raw is None:
        return default
    try:
        return enum_type(raw)
    except ValueError as error:
        allowed = ", ".join(str(member.value) for member in enum_type)
        raise _RowValueError(field, f"{field} must be one of: {allowed}") from error


def _metadata(row: dict[str, str]) -> RecordMetadata:
    return RecordMetadata(
        record_id=RecordId.generate(),
        recorded_at=_parse_datetime(row),
        source=DataSource.CSV_IMPORT,
        notes=_optional(row, "notes"),
    )


def _normalize_unit(
    value: float,
    unit: str | None,
    *,
    field: str,
    default_unit: str,
    factors: dict[str, float],
) -> float:
    resolved = unit or default_unit
    try:
        factor = factors[resolved]
    except KeyError as error:
        allowed = ", ".join(sorted(factors))
        raise _RowValueError(field, f"{field} must be one of: {allowed}") from error
    return value * factor


def _build_sleep(row: dict[str, str], _row_number: int) -> WellnessRecord:
    quality = _parse_enum(row, "quality", SleepQuality)
    interruption_count = _parse_int(row, "interruption_count")
    sleep_minutes = _parse_float(row, "sleep_minutes", required=True)
    awake_minutes = _parse_float(row, "awake_minutes", required=True)
    assert sleep_minutes is not None
    assert awake_minutes is not None
    return SleepRecord(
        metadata=_metadata(row),
        period=TimeRange(
            start=_parse_datetime(row, "start"),
            end=_parse_datetime(row, "end"),
        ),
        sleep_minutes=sleep_minutes,
        awake_minutes=awake_minutes,
        quality=quality,
        interruption_count=interruption_count,
    )


def _build_daily_activity(row: dict[str, str], _row_number: int) -> WellnessRecord:
    distance = _parse_float(row, "distance_value", default=0.0)
    assert distance is not None
    distance_kilometers = _normalize_unit(
        distance,
        _optional(row, "distance_unit"),
        field="distance_unit",
        default_unit="kilometers",
        factors={"kilometers": 1.0, "meters": 0.001},
    )
    return DailyActivityRecord(
        metadata=_metadata(row),
        activity_date=_parse_date(row, "activity_date"),
        steps=_parse_int(row, "steps", default=0) or 0,
        distance_kilometers=distance_kilometers,
        active_minutes=_parse_float(row, "active_minutes", default=0.0) or 0.0,
        active_calories_kcal=_parse_float(row, "active_calories_kcal", default=0.0) or 0.0,
    )


def _build_hydration(row: dict[str, str], _row_number: int) -> WellnessRecord:
    volume = _parse_float(row, "volume_value", required=True)
    assert volume is not None
    volume_milliliters = _normalize_unit(
        volume,
        _optional(row, "volume_unit"),
        field="volume_unit",
        default_unit="milliliters",
        factors={"liters": 1000.0, "milliliters": 1.0},
    )
    beverage_type = _parse_enum(
        row,
        "beverage_type",
        BeverageType,
        default=BeverageType.WATER,
    )
    assert beverage_type is not None
    return HydrationRecord(
        metadata=_metadata(row),
        volume_milliliters=volume_milliliters,
        beverage_type=beverage_type,
        caffeine_milligrams=_parse_float(row, "caffeine_milligrams"),
    )


def _build_daily_nutrition(row: dict[str, str], _row_number: int) -> WellnessRecord:
    nutrition = MealNutrition(
        calories_kcal=_parse_float(row, "calories_kcal"),
        protein_grams=_parse_float(row, "protein_grams"),
        carbohydrates_grams=_parse_float(row, "carbohydrates_grams"),
        fat_grams=_parse_float(row, "fat_grams"),
        fibre_grams=_parse_float(row, "fibre_grams"),
    )
    return DailyNutritionRecord(
        metadata=_metadata(row),
        nutrition_date=_parse_date(row, "nutrition_date"),
        nutrition=nutrition,
        meal_count=_parse_int(row, "meal_count"),
    )


def _build_body_measurement(row: dict[str, str], _row_number: int) -> WellnessRecord:
    weight = _parse_float(row, "weight_value", required=True)
    assert weight is not None
    weight_kilograms = _normalize_unit(
        weight,
        _optional(row, "weight_unit"),
        field="weight_unit",
        default_unit="kilograms",
        factors={"grams": 0.001, "kilograms": 1.0},
    )

    height_value = _parse_float(row, "height_value")
    height_meters = None
    if height_value is not None:
        height_meters = _normalize_unit(
            height_value,
            _optional(row, "height_unit"),
            field="height_unit",
            default_unit="meters",
            factors={"centimeters": 0.01, "meters": 1.0},
        )
    elif _optional(row, "height_unit") is not None:
        raise _RowValueError("height_unit", "height_unit requires height_value")

    return BodyMeasurementRecord(
        metadata=_metadata(row),
        weight_kilograms=weight_kilograms,
        height_meters=height_meters,
        body_fat_percent=_parse_float(row, "body_fat_percent"),
        waist_circumference_centimeters=_parse_float(
            row,
            "waist_circumference_centimeters",
        ),
    )


def _build_subjective_check_in(row: dict[str, str], _row_number: int) -> WellnessRecord:
    tags_raw = _optional(row, "tags")
    tags: tuple[CheckInTag, ...] = ()
    if tags_raw:
        parsed_tags: list[CheckInTag] = []
        for raw_tag in tags_raw.split(";"):
            normalized = raw_tag.strip()
            if not normalized:
                continue
            try:
                parsed_tags.append(CheckInTag(normalized))
            except ValueError as error:
                raise _RowValueError("tags", f"unsupported check-in tag: {normalized}") from error
        tags = tuple(parsed_tags)

    mood = _parse_int(row, "mood_score", required=True)
    energy = _parse_int(row, "energy_score", required=True)
    stress = _parse_int(row, "stress_score", required=True)
    assert mood is not None
    assert energy is not None
    assert stress is not None
    motivation = _parse_int(row, "motivation_score")
    mood_category = _parse_enum(row, "mood_category", MoodCategory)

    return SubjectiveWellnessCheckIn(
        metadata=_metadata(row),
        mood_score=SubjectiveScore(mood),
        energy_score=SubjectiveScore(energy),
        stress_score=SubjectiveScore(stress),
        motivation_score=SubjectiveScore(motivation) if motivation is not None else None,
        mood_category=mood_category,
        tags=tags,
    )


_COMMON = frozenset({"recorded_at"})
_NOTES = frozenset({"notes"})
_SCHEMAS: dict[CsvImportRecordType, _CsvSchema] = {
    CsvImportRecordType.SLEEP: _CsvSchema(
        required_headers=_COMMON | {"start", "end", "sleep_minutes", "awake_minutes"},
        optional_headers=_NOTES | {"quality", "interruption_count"},
        builder=_build_sleep,
    ),
    CsvImportRecordType.DAILY_ACTIVITY: _CsvSchema(
        required_headers=_COMMON | {"activity_date"},
        optional_headers=_NOTES
        | {
            "steps",
            "distance_value",
            "distance_unit",
            "active_minutes",
            "active_calories_kcal",
        },
        builder=_build_daily_activity,
    ),
    CsvImportRecordType.HYDRATION: _CsvSchema(
        required_headers=_COMMON | {"volume_value"},
        optional_headers=_NOTES
        | {"volume_unit", "beverage_type", "caffeine_milligrams"},
        builder=_build_hydration,
    ),
    CsvImportRecordType.DAILY_NUTRITION: _CsvSchema(
        required_headers=_COMMON | {"nutrition_date"},
        optional_headers=_NOTES
        | {
            "calories_kcal",
            "protein_grams",
            "carbohydrates_grams",
            "fat_grams",
            "fibre_grams",
            "meal_count",
        },
        builder=_build_daily_nutrition,
    ),
    CsvImportRecordType.BODY_MEASUREMENT: _CsvSchema(
        required_headers=_COMMON | {"weight_value"},
        optional_headers=_NOTES
        | {
            "weight_unit",
            "height_value",
            "height_unit",
            "body_fat_percent",
            "waist_circumference_centimeters",
        },
        builder=_build_body_measurement,
    ),
    CsvImportRecordType.SUBJECTIVE_CHECK_IN: _CsvSchema(
        required_headers=_COMMON | {"mood_score", "energy_score", "stress_score"},
        optional_headers=_NOTES | {"motivation_score", "mood_category", "tags"},
        builder=_build_subjective_check_in,
    ),
}


class WellnessCsvParser:
    """Parse one versioned CSV document into validated domain records."""

    def parse(
        self,
        *,
        schema_version: int,
        record_type: CsvImportRecordType,
        content: str,
    ) -> CsvParseResult:
        if schema_version != CSV_SCHEMA_VERSION:
            return CsvParseResult(
                schema_version=schema_version,
                record_type=record_type,
                total_rows=0,
                records=(),
                issues=(
                    CsvImportIssue(
                        row_number=None,
                        field="schema_version",
                        code="unsupported_schema_version",
                        message=f"supported CSV schema version is {CSV_SCHEMA_VERSION}",
                    ),
                ),
            )
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        if len(content.encode("utf-8")) > MAX_CSV_BYTES:
            return CsvParseResult(
                schema_version=schema_version,
                record_type=record_type,
                total_rows=0,
                records=(),
                issues=(
                    CsvImportIssue(
                        row_number=None,
                        field=None,
                        code="file_too_large",
                        message=f"CSV content must not exceed {MAX_CSV_BYTES} UTF-8 bytes",
                    ),
                ),
            )

        schema = _SCHEMAS[record_type]
        normalized_content = content.lstrip("\ufeff")
        try:
            reader = csv.DictReader(io.StringIO(normalized_content, newline=""))
            raw_headers = reader.fieldnames
        except csv.Error as error:
            return self._file_error(schema_version, record_type, "invalid_csv", str(error))
        if raw_headers is None:
            return self._file_error(
                schema_version,
                record_type,
                "missing_header",
                "CSV content must contain a header row",
            )

        headers = tuple(header.strip() for header in raw_headers)
        if len(headers) != len(set(headers)):
            return self._file_error(
                schema_version,
                record_type,
                "duplicate_header",
                "CSV header names must be unique",
            )
        missing = sorted(schema.required_headers - set(headers))
        unknown = sorted(set(headers) - schema.allowed_headers)
        header_issues = tuple(
            CsvImportIssue(None, field, "missing_header", f"required header is missing: {field}")
            for field in missing
        ) + tuple(
            CsvImportIssue(None, field, "unknown_header", f"unsupported header: {field}")
            for field in unknown
        )
        if header_issues:
            return CsvParseResult(schema_version, record_type, 0, (), header_issues)

        entries: list[ParsedCsvRecord] = []
        issues: list[CsvImportIssue] = []
        total_rows = 0
        try:
            for raw_row in reader:
                row_number = reader.line_num
                if total_rows >= MAX_CSV_ROWS:
                    issues.append(
                        CsvImportIssue(
                            row_number=None,
                            field=None,
                            code="too_many_rows",
                            message=f"CSV content must not exceed {MAX_CSV_ROWS} data rows",
                        )
                    )
                    break
                if None in raw_row:
                    total_rows += 1
                    issues.append(
                        CsvImportIssue(
                            row_number=row_number,
                            field=None,
                            code="column_count_mismatch",
                            message="row contains more columns than the header",
                        )
                    )
                    continue
                row = {
                    header.strip(): (value or "").strip()
                    for header, value in raw_row.items()
                    if header is not None
                }
                if not any(row.values()):
                    continue
                total_rows += 1
                try:
                    record = schema.builder(row, row_number)
                except _RowValueError as error:
                    issues.append(
                        CsvImportIssue(
                            row_number=row_number,
                            field=error.field,
                            code="invalid_value",
                            message=str(error),
                        )
                    )
                except DomainValidationError as error:
                    issues.append(
                        CsvImportIssue(
                            row_number=row_number,
                            field=None,
                            code="domain_validation_error",
                            message=str(error),
                        )
                    )
                else:
                    entries.append(ParsedCsvRecord(row_number=row_number, record=record))
        except csv.Error as error:
            issues.append(
                CsvImportIssue(
                    row_number=reader.line_num or None,
                    field=None,
                    code="invalid_csv",
                    message=str(error),
                )
            )

        return CsvParseResult(
            schema_version=schema_version,
            record_type=record_type,
            total_rows=total_rows,
            records=tuple(entries),
            issues=tuple(issues),
        )

    @staticmethod
    def _file_error(
        schema_version: int,
        record_type: CsvImportRecordType,
        code: str,
        message: str,
    ) -> CsvParseResult:
        return CsvParseResult(
            schema_version=schema_version,
            record_type=record_type,
            total_rows=0,
            records=(),
            issues=(CsvImportIssue(None, None, code, message),),
        )


def wellness_record_identity(record: WellnessRecord) -> tuple[Any, ...]:
    """Return a deterministic semantic identity used for exact duplicate detection.

    Generated record identifiers and source provenance are deliberately excluded.
    Aware timestamps compare by absolute instant, so equivalent UTC offsets match.
    Notes and all record-specific values remain part of the identity.
    """

    return (type(record).__name__, _canonical_value(record))


def _canonical_value(value: Any) -> Any:
    if isinstance(value, RecordMetadata):
        return (
            "metadata",
            value.recorded_at.astimezone(UTC).isoformat(),
            value.notes,
        )
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return tuple(
            (field.name, _canonical_value(getattr(value, field.name)))
            for field in fields(value)
            if field.name not in {"record_id", "source"}
        )
    if isinstance(value, tuple):
        return tuple(_canonical_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_canonical_value(item) for item in value)
    return value
