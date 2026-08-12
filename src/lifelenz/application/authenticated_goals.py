"""Account-scoped wellness-goal orchestration through primary profile ownership."""

from lifelenz.application.authenticated_profile import AuthenticatedProfileService
from lifelenz.application.exceptions import ApplicationValidationError, GoalNotFoundError
from lifelenz.application.services import GoalService
from lifelenz.domain import GoalId, WellnessGoal
from lifelenz.identity import UserId


class AuthenticatedGoalService:
    """Scope every goal operation to the authenticated user's primary profile."""

    def __init__(
        self,
        profile_service: AuthenticatedProfileService,
        goal_service: GoalService,
    ) -> None:
        if not isinstance(profile_service, AuthenticatedProfileService):
            raise ApplicationValidationError(
                "profile_service must be an AuthenticatedProfileService"
            )
        if not isinstance(goal_service, GoalService):
            raise ApplicationValidationError("goal_service must be a GoalService")
        self._profile_service = profile_service
        self._goal_service = goal_service

    def create_goal(self, user_id: UserId, goal: WellnessGoal) -> WellnessGoal:
        """Persist a goal only when its profile is the authenticated primary profile."""
        profile = self._profile_service.get_profile(user_id)
        validated_goal = self._require_goal(goal)
        if validated_goal.profile_id != profile.profile_id:
            raise GoalNotFoundError("goal was not found")
        return self._goal_service.save_goal(validated_goal)

    def list_goals(self, user_id: UserId) -> tuple[WellnessGoal, ...]:
        """Return the primary profile's deterministic goal tuple."""
        profile = self._profile_service.get_profile(user_id)
        return self._goal_service.list_goals_for_profile(profile.profile_id)

    def get_goal(self, user_id: UserId, goal_id: GoalId) -> WellnessGoal:
        """Find an exact goal inside the owned profile without global enumeration."""
        validated_id = self._require_goal_id(goal_id)
        for goal in self.list_goals(user_id):
            if goal.goal_id == validated_id:
                return goal
        raise GoalNotFoundError("goal was not found")

    def update_goal(self, user_id: UserId, goal: WellnessGoal) -> WellnessGoal:
        """Replace an owned goal while preserving its identifier and profile."""
        validated_goal = self._require_goal(goal)
        existing = self.get_goal(user_id, validated_goal.goal_id)
        if validated_goal.profile_id != existing.profile_id:
            raise GoalNotFoundError("goal was not found")
        return self._goal_service.save_goal(validated_goal)

    def remove_goal(self, user_id: UserId, goal_id: GoalId) -> None:
        """Remove a goal only after resolving it within the owned profile."""
        existing = self.get_goal(user_id, goal_id)
        self._goal_service.remove_goal(existing.goal_id)

    @staticmethod
    def _require_goal_id(goal_id: object) -> GoalId:
        if type(goal_id) is not GoalId:
            raise ApplicationValidationError("goal_id must be a GoalId")
        return goal_id

    @staticmethod
    def _require_goal(goal: object) -> WellnessGoal:
        if type(goal) is not WellnessGoal:
            raise ApplicationValidationError("goal must be a WellnessGoal")
        return goal
