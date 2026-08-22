from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    HydrationRecord,
    RecordId,
    SleepRecord,
    SubjectiveWellnessCheckIn,
)
from lifelenz.ingestion import (
    CsvImportRecordType,
    WellnessCsvParser,
    wellness_record_identity,
)


@pytest.mark.parametrize(
    ("record_type", "content", "expected_type"),
    [
        (
            CsvImportRecordType.SLEEP,
            "recorded_at,start,end,sleep_minutes,awake_minutes,quality,interruption_count,notes\n"
            "2026-08-20T07:00:00+05:30,2026-08-19T23:00:00+05:30,"
            "2026-08-20T07:00:00+05:30,430,50,good,2,Synthetic sleep\n",
            SleepRecord,
        ),
        (
            CsvImportRecordType.DAILY_ACTIVITY,
            "recorded_at,activity_date,steps,distance_value,distance_unit,active_minutes,"
            "active_calories_kcal\n"
            "2026-08-20T20:00:00+05:30,2026-08-20,8000,2500,meters,45,320\n",
            DailyActivityRecord,
        ),
        (
            CsvImportRecordType.HYDRATION,
            "recorded_at,volume_value,volume_unit,beverage_type,caffeine_milligrams\n"
            "2026-08-20T10:00:00+05:30,0.5,liters,water,0\n",
            HydrationRecord,
        ),
        (
            CsvImportRecordType.DAILY_NUTRITION,
            "recorded_at,nutrition_date,calories_kcal,protein_grams,meal_count\n"
            "2026-08-20T22:00:00+05:30,2026-08-20,2100,75,3\n",
            DailyNutritionRecord,
        ),
        (
            CsvImportRecordType.BODY_MEASUREMENT,
            "recorded_at,weight_value,weight_unit,height_value,height_unit,body_fat_percent\n"
            "2026-08-20T08:00:00+05:30,72500,grams,175,centimeters,18.5\n",
            BodyMeasurementRecord,
        ),
        (
            CsvImportRecordType.SUBJECTIVE_CHECK_IN,
            "recorded_at,mood_score,energy_score,stress_score,motivation_score,mood_category,tags\n"
            "2026-08-20T18:00:00+05:30,7,6,4,8,high,calm;focused\n",
            SubjectiveWellnessCheckIn,
        ),
    ],
)
def test_csv_v1_parses_supported_mvp_records(
    record_type: CsvImportRecordType,
    content: str,
    expected_type: type[object],
) -> None:
    result = WellnessCsvParser().parse(
        schema_version=1,
        record_type=record_type,
        content=content,
    )

    assert result.total_rows == 1
    assert result.valid_rows == 1
    assert result.invalid_rows == 0
    assert result.issues == ()
    record = result.records[0].record
    assert type(record) is expected_type
    assert record.metadata.source is DataSource.CSV_IMPORT


def test_csv_v1_normalizes_supported_units() -> None:
    parser = WellnessCsvParser()
    activity = (
        parser.parse(
            schema_version=1,
            record_type=CsvImportRecordType.DAILY_ACTIVITY,
            content=(
                "recorded_at,activity_date,distance_value,distance_unit\n"
                "2026-08-20T20:00:00+05:30,2026-08-20,2500,meters\n"
            ),
        )
        .records[0]
        .record
    )
    hydration = (
        parser.parse(
            schema_version=1,
            record_type=CsvImportRecordType.HYDRATION,
            content=(
                "recorded_at,volume_value,volume_unit\n2026-08-20T10:00:00+05:30,0.75,liters\n"
            ),
        )
        .records[0]
        .record
    )
    body = (
        parser.parse(
            schema_version=1,
            record_type=CsvImportRecordType.BODY_MEASUREMENT,
            content=(
                "recorded_at,weight_value,weight_unit,height_value,height_unit\n"
                "2026-08-20T08:00:00+05:30,72500,grams,175,centimeters\n"
            ),
        )
        .records[0]
        .record
    )

    assert isinstance(activity, DailyActivityRecord)
    assert activity.distance_kilometers == 2.5
    assert isinstance(hydration, HydrationRecord)
    assert hydration.volume_milliliters == 750.0
    assert isinstance(body, BodyMeasurementRecord)
    assert body.weight_kilograms == 72.5
    assert body.height_meters == 1.75


def test_csv_v1_reports_actionable_row_errors_without_discarding_valid_rows() -> None:
    result = WellnessCsvParser().parse(
        schema_version=1,
        record_type=CsvImportRecordType.HYDRATION,
        content=(
            "recorded_at,volume_value,volume_unit\n"
            "2026-08-20T10:00:00+05:30,500,milliliters\n"
            "2026-08-20T11:00:00,250,milliliters\n"
            "2026-08-20T12:00:00+05:30,1,gallons\n"
        ),
    )

    assert result.total_rows == 3
    assert result.valid_rows == 1
    assert result.invalid_rows == 2
    assert [(issue.row_number, issue.field, issue.code) for issue in result.issues] == [
        (3, "recorded_at", "invalid_value"),
        (4, "volume_unit", "invalid_value"),
    ]


def test_csv_v1_rejects_unknown_headers_and_unsupported_schema_versions() -> None:
    parser = WellnessCsvParser()
    unknown = parser.parse(
        schema_version=1,
        record_type=CsvImportRecordType.HYDRATION,
        content="recorded_at,volume_value,typo\n2026-08-20T10:00:00+05:30,500,x\n",
    )
    unsupported = parser.parse(
        schema_version=2,
        record_type=CsvImportRecordType.HYDRATION,
        content="recorded_at,volume_value\n2026-08-20T10:00:00+05:30,500\n",
    )

    assert unknown.records == ()
    assert [(issue.field, issue.code) for issue in unknown.issues] == [("typo", "unknown_header")]
    assert unsupported.issues[0].code == "unsupported_schema_version"


def test_duplicate_identity_ignores_generated_id_source_and_equivalent_offsets() -> None:
    record = (
        WellnessCsvParser()
        .parse(
            schema_version=1,
            record_type=CsvImportRecordType.HYDRATION,
            content=(
                "recorded_at,volume_value,notes\n2026-08-20T10:00:00+05:30,500,Synthetic note\n"
            ),
        )
        .records[0]
        .record
    )
    assert isinstance(record, HydrationRecord)

    equivalent_metadata = replace(
        record.metadata,
        record_id=RecordId.generate(),
        recorded_at=datetime(2026, 8, 20, 4, 30, tzinfo=UTC),
        source=DataSource.MANUAL,
    )
    equivalent = replace(record, metadata=equivalent_metadata)
    different_time = replace(
        record,
        metadata=replace(
            equivalent_metadata,
            recorded_at=equivalent_metadata.recorded_at + timedelta(minutes=1),
        ),
    )

    assert wellness_record_identity(record) == wellness_record_identity(equivalent)
    assert wellness_record_identity(record) != wellness_record_identity(different_time)
