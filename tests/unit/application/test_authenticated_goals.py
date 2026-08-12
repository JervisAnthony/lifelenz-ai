from unittest.mock import Mock

import pytest

from lifelenz.application import (
    ApplicationValidationError,
    AuthenticatedGoalService,
    AuthenticatedProfileService,
    GoalNotFoundError,
    GoalService,
)
from lifelenz.domain import (
    GoalDirection,
    GoalId,
    GoalStatus,
    GoalTarget,
    MeasurementUnit,
    MetricIdentifier,
    ProfileId,
    WellnessGoal,
    WellnessProfile,
)
from lifelenz.identity import UserId


def goal(profile_id: ProfileId | None = None) -> WellnessGoal:
    return WellnessGoal(
        GoalId.generate(),
        ProfileId.generate() if profile_id is None else profile_id,
        GoalTarget(MetricIdentifier.WATER_INTAKE, 2000, MeasurementUnit.MILLILITERS),
        GoalDirection.AT_LEAST,
        GoalStatus.ACTIVE,
    )


def orchestrator() -> tuple[AuthenticatedGoalService, Mock, Mock, WellnessProfile, UserId]:
    profiles = Mock(spec=AuthenticatedProfileService)
    goals = Mock(spec=GoalService)
    profile = WellnessProfile(ProfileId.generate(), "UTC")
    user = UserId.new()
    profiles.get_profile.return_value = profile
    return AuthenticatedGoalService(profiles, goals), profiles, goals, profile, user


def test_goal_operations_are_scoped_to_primary_profile() -> None:
    service, _, goals, profile, user = orchestrator()
    item = goal(profile.profile_id)
    goals.save_goal.return_value = item
    goals.list_goals_for_profile.return_value = (item,)

    assert service.create_goal(user, item) is item
    assert service.list_goals(user) == (item,)
    assert service.get_goal(user, item.goal_id) is item
    assert service.update_goal(user, item) is item
    assert service.remove_goal(user, item.goal_id) is None
    goals.save_goal.assert_called_with(item)
    goals.list_goals_for_profile.assert_called_with(profile.profile_id)
    goals.remove_goal.assert_called_once_with(item.goal_id)


def test_goal_missing_cross_profile_and_invalid_inputs_deny_without_enumeration() -> None:
    service, _, goals, profile, user = orchestrator()
    goals.list_goals_for_profile.return_value = ()
    with pytest.raises(GoalNotFoundError):
        service.get_goal(user, GoalId.generate())
    with pytest.raises(GoalNotFoundError):
        service.create_goal(user, goal())
    with pytest.raises(ApplicationValidationError):
        service.get_goal(user, ProfileId.generate())  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        service.create_goal(user, object())  # type: ignore[arg-type]
    existing = goal(profile.profile_id)
    goals.list_goals_for_profile.return_value = (existing,)
    reassigned = WellnessGoal(
        existing.goal_id,
        ProfileId.generate(),
        existing.target,
        existing.direction,
        existing.status,
    )
    with pytest.raises(GoalNotFoundError):
        service.update_goal(user, reassigned)


def test_authenticated_goal_constructor_requires_application_services() -> None:
    profiles = Mock(spec=AuthenticatedProfileService)
    goals = Mock(spec=GoalService)
    with pytest.raises(ApplicationValidationError):
        AuthenticatedGoalService(object(), goals)  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        AuthenticatedGoalService(profiles, object())  # type: ignore[arg-type]
