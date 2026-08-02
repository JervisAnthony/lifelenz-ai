"""Tests for the foundational wellness taxonomy."""

import operator
from enum import StrEnum
from types import MappingProxyType

import pytest

from lifelenz import domain
from lifelenz.domain import (
    ConfidenceLevel,
    DataSource,
    InsightSeverity,
    MeasurementUnit,
    MetricIdentifier,
    WellnessCategory,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC, METRICS_BY_CATEGORY


def test_enum_members_are_complete_and_unique() -> None:
    """Every controlled type exposes exactly its expected, non-aliased members."""
    expected_names = {
        WellnessCategory: (
            "SLEEP",
            "ACTIVITY",
            "HYDRATION",
            "NUTRITION",
            "BODY",
            "MOOD",
            "ENERGY",
            "STRESS",
            "RECOVERY",
        ),
        MetricIdentifier: (
            "SLEEP_DURATION",
            "TIME_IN_BED",
            "SLEEP_EFFICIENCY",
            "STEPS",
            "DISTANCE",
            "ACTIVE_MINUTES",
            "ACTIVE_CALORIES",
            "WATER_INTAKE",
            "CALORIES",
            "PROTEIN",
            "CARBOHYDRATES",
            "FAT",
            "FIBRE",
            "WEIGHT",
            "HEIGHT",
            "BMI",
            "BODY_FAT",
            "MOOD_SCORE",
            "ENERGY_SCORE",
            "STRESS_SCORE",
            "RECOVERY_SCORE",
        ),
        MeasurementUnit: (
            "MINUTES",
            "HOURS",
            "METERS",
            "KILOMETERS",
            "GRAMS",
            "KILOGRAMS",
            "KILOGRAMS_PER_SQUARE_METER",
            "MILLILITERS",
            "LITERS",
            "KCAL",
            "PERCENT",
            "COUNT",
            "SCORE",
        ),
        DataSource: ("MANUAL", "CSV_IMPORT", "APP_IMPORT", "API_IMPORT"),
        ConfidenceLevel: ("LOW", "MEDIUM", "HIGH"),
        InsightSeverity: ("INFO", "NOTICE", "WARNING"),
    }

    for enum_type, names in expected_names.items():
        members = list(enum_type)
        assert tuple(member.name for member in members) == names
        assert len(members) == len(names)
        assert len({member.value for member in members}) == len(members)


def test_enum_members_have_stable_string_representations() -> None:
    """String conversion returns the stable serialized value for every member."""
    enum_types: tuple[type[StrEnum], ...] = (
        WellnessCategory,
        MetricIdentifier,
        MeasurementUnit,
        DataSource,
        ConfidenceLevel,
        InsightSeverity,
    )

    for enum_type in enum_types:
        for member in enum_type:
            assert str(member) == member.value
            assert f"{member}" == member.value


def test_category_mapping_defines_expected_metric_groups() -> None:
    """Categories expose the intended metrics in deterministic order."""
    assert dict(METRICS_BY_CATEGORY) == {
        WellnessCategory.SLEEP: (
            MetricIdentifier.SLEEP_DURATION,
            MetricIdentifier.TIME_IN_BED,
            MetricIdentifier.SLEEP_EFFICIENCY,
        ),
        WellnessCategory.ACTIVITY: (
            MetricIdentifier.STEPS,
            MetricIdentifier.DISTANCE,
            MetricIdentifier.ACTIVE_MINUTES,
            MetricIdentifier.ACTIVE_CALORIES,
        ),
        WellnessCategory.HYDRATION: (MetricIdentifier.WATER_INTAKE,),
        WellnessCategory.NUTRITION: (
            MetricIdentifier.CALORIES,
            MetricIdentifier.PROTEIN,
            MetricIdentifier.CARBOHYDRATES,
            MetricIdentifier.FAT,
            MetricIdentifier.FIBRE,
        ),
        WellnessCategory.BODY: (
            MetricIdentifier.WEIGHT,
            MetricIdentifier.HEIGHT,
            MetricIdentifier.BMI,
            MetricIdentifier.BODY_FAT,
        ),
        WellnessCategory.MOOD: (MetricIdentifier.MOOD_SCORE,),
        WellnessCategory.ENERGY: (MetricIdentifier.ENERGY_SCORE,),
        WellnessCategory.STRESS: (MetricIdentifier.STRESS_SCORE,),
        WellnessCategory.RECOVERY: (MetricIdentifier.RECOVERY_SCORE,),
    }


def test_every_metric_belongs_to_exactly_one_nonempty_category() -> None:
    """The category relationship is exhaustive, exclusive, and nonempty."""
    categorized_metrics = [
        metric for category_metrics in METRICS_BY_CATEGORY.values() for metric in category_metrics
    ]

    assert set(METRICS_BY_CATEGORY) == set(WellnessCategory)
    assert all(METRICS_BY_CATEGORY[category] for category in WellnessCategory)
    assert len(categorized_metrics) == len(set(categorized_metrics))
    assert set(categorized_metrics) == set(MetricIdentifier)


def test_every_metric_has_the_expected_default_unit() -> None:
    """Default units are dimensionally appropriate and cover every metric."""
    assert dict(DEFAULT_UNIT_BY_METRIC) == {
        MetricIdentifier.SLEEP_DURATION: MeasurementUnit.HOURS,
        MetricIdentifier.TIME_IN_BED: MeasurementUnit.HOURS,
        MetricIdentifier.SLEEP_EFFICIENCY: MeasurementUnit.PERCENT,
        MetricIdentifier.STEPS: MeasurementUnit.COUNT,
        MetricIdentifier.DISTANCE: MeasurementUnit.KILOMETERS,
        MetricIdentifier.ACTIVE_MINUTES: MeasurementUnit.MINUTES,
        MetricIdentifier.ACTIVE_CALORIES: MeasurementUnit.KCAL,
        MetricIdentifier.WATER_INTAKE: MeasurementUnit.MILLILITERS,
        MetricIdentifier.CALORIES: MeasurementUnit.KCAL,
        MetricIdentifier.PROTEIN: MeasurementUnit.GRAMS,
        MetricIdentifier.CARBOHYDRATES: MeasurementUnit.GRAMS,
        MetricIdentifier.FAT: MeasurementUnit.GRAMS,
        MetricIdentifier.FIBRE: MeasurementUnit.GRAMS,
        MetricIdentifier.WEIGHT: MeasurementUnit.KILOGRAMS,
        MetricIdentifier.HEIGHT: MeasurementUnit.METERS,
        MetricIdentifier.BMI: MeasurementUnit.KILOGRAMS_PER_SQUARE_METER,
        MetricIdentifier.BODY_FAT: MeasurementUnit.PERCENT,
        MetricIdentifier.MOOD_SCORE: MeasurementUnit.SCORE,
        MetricIdentifier.ENERGY_SCORE: MeasurementUnit.SCORE,
        MetricIdentifier.STRESS_SCORE: MeasurementUnit.SCORE,
        MetricIdentifier.RECOVERY_SCORE: MeasurementUnit.SCORE,
    }
    assert set(DEFAULT_UNIT_BY_METRIC) == set(MetricIdentifier)


def test_relationship_mappings_are_immutable() -> None:
    """Neither relationship map nor its ordered category values can be modified."""
    assert isinstance(METRICS_BY_CATEGORY, MappingProxyType)
    assert isinstance(DEFAULT_UNIT_BY_METRIC, MappingProxyType)

    with pytest.raises(TypeError):
        operator.setitem(
            METRICS_BY_CATEGORY,
            WellnessCategory.SLEEP,
            (MetricIdentifier.SLEEP_DURATION,),
        )

    with pytest.raises(TypeError):
        operator.setitem(
            DEFAULT_UNIT_BY_METRIC,
            MetricIdentifier.SLEEP_DURATION,
            MeasurementUnit.MINUTES,
        )

    with pytest.raises(TypeError):
        operator.setitem(
            METRICS_BY_CATEGORY[WellnessCategory.SLEEP],
            0,
            MetricIdentifier.TIME_IN_BED,
        )


def test_domain_package_exports_only_public_taxonomy_types() -> None:
    """Consumers can import the controlled types from the domain package."""
    expected_exports = {
        "ConfidenceLevel": ConfidenceLevel,
        "DataSource": DataSource,
        "InsightSeverity": InsightSeverity,
        "MeasurementUnit": MeasurementUnit,
        "MetricIdentifier": MetricIdentifier,
        "WellnessCategory": WellnessCategory,
    }

    assert domain.__all__ == list(expected_exports)
    for name, expected_type in expected_exports.items():
        assert getattr(domain, name) is expected_type
