import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '../api/client';
import {
  createWellnessGoal,
  deleteWellnessGoal,
  listWellnessGoals,
  updateWellnessGoal,
} from '../api/goals';
import { queryKeys } from '../api/queryKeys';
import type { WellnessGoal, WellnessGoalRequest } from '../api/types';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';
import { Button } from '../components/Button';
import { GoalForm } from '../goals/GoalForm';
import {
  directionLabel,
  metricDefinition,
  statusLabel,
  unitLabels,
} from '../goals/goalPresentation';

function goalErrorMessage(error: unknown, action: string): string {
  if (error instanceof ApiError) {
    if (error.kind === 'network') {
      return "We couldn't reach LifeLenz. Your changes are still available.";
    }
    if (error.code === 'goal_not_found') {
      return 'This goal is no longer available. Refresh the list and try again.';
    }
    if (
      error.code === 'request_validation_error' ||
      error.code === 'domain_validation_error' ||
      error.code === 'application_validation_error'
    ) {
      return `We couldn't ${action} this goal. Review the details and try again.`;
    }
  }
  return `We couldn't ${action} this goal. Please try again.`;
}

function goalName(goal: WellnessGoal): string {
  return goal.title ?? metricDefinition(goal.target.metric).label;
}

export function GoalsPage() {
  const { accessToken, handleSessionError, refreshCurrentUser } = useAuth();
  const queryClient = useQueryClient();
  const [createVersion, setCreateVersion] = useState(0);
  const [editingGoalId, setEditingGoalId] = useState<string | null>(null);
  const [confirmingGoalId, setConfirmingGoalId] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const goalsQuery = useQuery({
    queryKey: queryKeys.goals,
    queryFn: async ({ signal }) => {
      try {
        return await listWellnessGoals(accessToken as string, signal);
      } catch (caughtError) {
        handleSessionError(caughtError);
        if (
          caughtError instanceof ApiError &&
          caughtError.code === 'profile_not_configured'
        ) {
          void refreshCurrentUser();
        }
        throw caughtError;
      }
    },
    enabled: Boolean(accessToken),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (request: WellnessGoalRequest) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return createWellnessGoal(accessToken, request);
    },
    retry: false,
    onSuccess: async () => {
      setCreateError(null);
      setSuccess('Wellness goal created.');
      setCreateVersion((version) => version + 1);
      await queryClient.invalidateQueries({ queryKey: queryKeys.goals });
    },
    onError: (caughtError) => {
      if (!handleSessionError(caughtError)) {
        setSuccess(null);
        setCreateError(goalErrorMessage(caughtError, 'create'));
      }
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      goalId,
      request,
    }: {
      goalId: string;
      request: WellnessGoalRequest;
    }) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return updateWellnessGoal(accessToken, goalId, request);
    },
    retry: false,
    onSuccess: async () => {
      setEditError(null);
      setEditingGoalId(null);
      setSuccess('Wellness goal updated.');
      await queryClient.invalidateQueries({ queryKey: queryKeys.goals });
    },
    onError: (caughtError) => {
      if (!handleSessionError(caughtError)) {
        setSuccess(null);
        setEditError(goalErrorMessage(caughtError, 'update'));
        if (
          caughtError instanceof ApiError &&
          caughtError.code === 'goal_not_found'
        ) {
          void queryClient.invalidateQueries({ queryKey: queryKeys.goals });
        }
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (goalId: string) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return deleteWellnessGoal(accessToken, goalId);
    },
    retry: false,
    onSuccess: async () => {
      setDeleteError(null);
      setConfirmingGoalId(null);
      setSuccess('Wellness goal deleted.');
      await queryClient.invalidateQueries({ queryKey: queryKeys.goals });
    },
    onError: (caughtError) => {
      if (!handleSessionError(caughtError)) {
        setSuccess(null);
        setDeleteError(goalErrorMessage(caughtError, 'delete'));
        if (
          caughtError instanceof ApiError &&
          caughtError.code === 'goal_not_found'
        ) {
          void queryClient.invalidateQueries({ queryKey: queryKeys.goals });
        }
      }
    },
  });

  useEffect(() => {
    document.title = 'Goals | LifeLenz';
  }, []);

  return (
    <div className="goals-page">
      <header className="page-intro">
        <p className="eyebrow">Your intentions</p>
        <h1>Wellness goals</h1>
        <p>
          Record and manage goals you define, using canonical wellness metrics
          without recommendations or progress scoring.
        </p>
      </header>

      {success ? <Alert tone="success">{success}</Alert> : null}

      <section className="goal-create" aria-labelledby="create-goal-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">New goal</p>
            <h2 id="create-goal-heading">Create a wellness goal</h2>
          </div>
          <p>Select your own metric, target, direction, and lifecycle state.</p>
        </div>
        <div className="goal-form-card">
          <GoalForm
            key={createVersion}
            mode="create"
            isSaving={createMutation.isPending}
            error={createError}
            onSubmit={async (request) => {
              setCreateError(null);
              setSuccess(null);
              await createMutation.mutateAsync(request);
            }}
          />
        </div>
      </section>

      <section className="goals-list-section" aria-labelledby="goals-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Saved goals</p>
            <h2 id="goals-heading">Your goal list</h2>
          </div>
          <p>Goals appear in the deterministic order returned by the server.</p>
        </div>
        {goalsQuery.isPending ? (
          <p className="inline-status" role="status">
            Loading wellness goals…
          </p>
        ) : goalsQuery.isError ? (
          <div className="summary-error">
            <Alert>We could not load your wellness goals.</Alert>
            <Button
              variant="secondary"
              type="button"
              onClick={() => void goalsQuery.refetch()}
            >
              Try goals again
            </Button>
          </div>
        ) : goalsQuery.data.length === 0 ? (
          <div className="goals-empty">
            <h3>No wellness goals yet.</h3>
            <p>You can use LifeLenz without creating a goal.</p>
          </div>
        ) : (
          <div className="goal-list">
            {goalsQuery.data.map((goal, index) => {
              const metric = metricDefinition(goal.target.metric);
              const isEditing = editingGoalId === goal.goal_id;
              const isConfirming = confirmingGoalId === goal.goal_id;
              const headingId = `goal-heading-${index}`;
              return (
                <article
                  className="goal-card"
                  key={goal.goal_id}
                  aria-labelledby={headingId}
                >
                  <div className="goal-card__heading">
                    <div>
                      <span className="goal-card__status">
                        {statusLabel(goal.status)}
                      </span>
                      <h3 id={headingId}>{goalName(goal)}</h3>
                    </div>
                    {!isEditing ? (
                      <div className="goal-card__actions">
                        <Button
                          variant="quiet"
                          type="button"
                          onClick={() => {
                            setEditingGoalId(goal.goal_id);
                            setConfirmingGoalId(null);
                            setEditError(null);
                            setDeleteError(null);
                            setSuccess(null);
                          }}
                        >
                          Edit {goalName(goal)}
                        </Button>
                        <Button
                          className="button--danger"
                          variant="quiet"
                          type="button"
                          onClick={() => {
                            setConfirmingGoalId(goal.goal_id);
                            setEditingGoalId(null);
                            setDeleteError(null);
                            setEditError(null);
                            setSuccess(null);
                          }}
                        >
                          Delete {goalName(goal)}
                        </Button>
                      </div>
                    ) : null}
                  </div>

                  {isEditing ? (
                    <GoalForm
                      mode="edit"
                      initialValue={goal}
                      isSaving={updateMutation.isPending}
                      error={editError}
                      onCancel={() => {
                        setEditingGoalId(null);
                        setEditError(null);
                      }}
                      onSubmit={async (request) => {
                        setEditError(null);
                        setSuccess(null);
                        await updateMutation.mutateAsync({
                          goalId: goal.goal_id,
                          request,
                        });
                      }}
                    />
                  ) : (
                    <>
                      <dl className="goal-card__details">
                        <div>
                          <dt>Metric</dt>
                          <dd>{metric.label}</dd>
                        </div>
                        <div>
                          <dt>Direction</dt>
                          <dd>{directionLabel(goal.direction)}</dd>
                        </div>
                        <div>
                          <dt>Target</dt>
                          <dd>
                            {goal.target.value.toLocaleString()}{' '}
                            {unitLabels[goal.target.unit]}
                          </dd>
                        </div>
                        <div>
                          <dt>Status</dt>
                          <dd>{statusLabel(goal.status)}</dd>
                        </div>
                      </dl>
                      {goal.start_date || goal.target_date ? (
                        <p className="goal-card__dates">
                          Start: {goal.start_date ?? 'Not set'} · Target:{' '}
                          {goal.target_date ?? 'Not set'}
                        </p>
                      ) : null}
                      {goal.description ? (
                        <p className="goal-card__description">
                          {goal.description}
                        </p>
                      ) : null}
                    </>
                  )}

                  {isConfirming ? (
                    <div
                      className="goal-delete-confirmation"
                      role="group"
                      aria-label={`Delete ${goalName(goal)}`}
                    >
                      {deleteError ? <Alert>{deleteError}</Alert> : null}
                      <p>
                        Delete <strong>{goalName(goal)}</strong>? This removes
                        the goal from your profile.
                      </p>
                      <div>
                        <Button
                          variant="secondary"
                          type="button"
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            setConfirmingGoalId(null);
                            setDeleteError(null);
                          }}
                        >
                          Cancel delete
                        </Button>
                        <Button
                          className="button--danger"
                          type="button"
                          disabled={deleteMutation.isPending}
                          onClick={() => deleteMutation.mutate(goal.goal_id)}
                        >
                          {deleteMutation.isPending
                            ? 'Deleting…'
                            : 'Confirm delete'}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
