# LifeLenz CSV schema v1

LifeLenz CSV schema version `1` is the first deliberate structured-data import contract.
It supports six MVP wellness-record categories whose domain contracts are already stable:

- Sleep (`sleep`)
- Daily Activity (`daily_activity`)
- Hydration (`hydration`)
- Daily Nutrition (`daily_nutrition`)
- Body Measurement (`body_measurement`)
- Subjective Wellness Check-In (`subjective_check_in`)

Meal events, individual workouts, menstrual bleeding observations, and menstrual-cycle ranges are
not part of CSV v1. Their manual record workflows remain available, and later CSV schema versions
may add them without changing the meaning of version 1.

## File rules

A request identifies the record type separately from the CSV content. Every file therefore contains
rows for exactly one supported record type.

- UTF-8 text only
- Maximum encoded size: 1,000,000 bytes
- Maximum data rows: 5,000
- The first non-BOM row is the header
- Header names are exact, case-sensitive schema identifiers
- Unknown headers are rejected rather than ignored
- Required headers must be present
- Optional headers may be omitted entirely
- Blank data rows are ignored
- Timestamps must be ISO 8601 values with an explicit UTC offset
- Dates use ISO `YYYY-MM-DD`
- Empty optional cells remain unknown rather than being invented
- Imported records receive `csv_import` provenance

The parser validates the complete document before a commit-mode request persists any row. If any
row has a validation issue, commit mode writes zero records. Validation mode never writes records.

## Duplicate identity

CSV v1 duplicate detection uses semantic domain content rather than generated record IDs. Two
records are duplicates when they have the same concrete record type and equal validated content
after normalization, excluding:

- generated `record_id`
- source provenance

Aware timestamps compare by absolute instant, so equivalent offsets identify the same timestamp.
Notes remain part of duplicate identity. Duplicate rows are skipped and reported separately from
validation errors. A duplicate may match either an existing owned record or an earlier row in the
same CSV file.

## Sleep

Required headers:

- `recorded_at`
- `start`
- `end`
- `sleep_minutes`
- `awake_minutes`

Optional headers:

- `quality`: `very_poor`, `poor`, `fair`, `good`, `very_good`
- `interruption_count`
- `notes`

CSV v1 does not import detailed sleep-stage durations. Existing domain validation remains
authoritative for period and duration relationships.

## Daily Activity

Required headers:

- `recorded_at`
- `activity_date`

Optional headers:

- `steps` (default `0`)
- `distance_value` (default `0`)
- `distance_unit`: `kilometers` (default) or `meters`
- `active_minutes` (default `0`)
- `active_calories_kcal` (default `0`)
- `notes`

Distance is normalized to canonical kilometers before persistence.

## Hydration

Required headers:

- `recorded_at`
- `volume_value`

Optional headers:

- `volume_unit`: `milliliters` (default) or `liters`
- `beverage_type`: `water` (default), `sparkling_water`, `tea`, `coffee`, `juice`, `milk`,
  `sports_drink`, `other`
- `caffeine_milligrams`
- `notes`

Volume is normalized to canonical milliliters before persistence.

## Daily Nutrition

Required headers:

- `recorded_at`
- `nutrition_date`

Optional headers:

- `calories_kcal`
- `protein_grams`
- `carbohydrates_grams`
- `fat_grams`
- `fibre_grams`
- `meal_count`
- `notes`

At least one nutrition measurement must be supplied because that is an existing domain invariant.
No nutrient total is inferred from another value.

## Body Measurement

Required headers:

- `recorded_at`
- `weight_value`

Optional headers:

- `weight_unit`: `kilograms` (default) or `grams`
- `height_value`
- `height_unit`: `meters` (default) or `centimeters`
- `body_fat_percent`
- `waist_circumference_centimeters`
- `notes`

Weight and height are normalized to canonical kilograms and meters. BMI is not imported or
classified; the existing domain property may derive it only when height is known.

## Subjective Wellness Check-In

Required headers:

- `recorded_at`
- `mood_score`
- `energy_score`
- `stress_score`

Optional headers:

- `motivation_score`
- `mood_category`: `very_low`, `low`, `neutral`, `high`, `very_high`
- `tags`: semicolon-separated values from the existing controlled check-in tag vocabulary
- `notes`

Scores remain user-reported values from 1 through 10. They are not medical assessments or health
classifications.

## API workflow

Authenticated clients use `POST /api/v1/imports/csv` with JSON containing:

- `schema_version`: currently `1`
- `record_type`: one of the six supported CSV v1 record types
- `mode`: `validate` or `commit`
- `content`: CSV text

The response contains only counts, row-level issues, and duplicate row metadata. It does not echo
wellness row payloads. Profile ownership is derived from the authenticated account; clients cannot
choose a profile identifier.

CSV v1 is a general-wellness data-ingestion format. It performs no diagnosis, target comparison,
health scoring, recommendation generation, or medical interpretation.
