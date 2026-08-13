import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { ApiError } from '../api/client';
import { createProfile, getProfile, updateProfile } from '../api/profile';
import { queryKeys } from '../api/queryKeys';
import type { WellnessProfileRequest } from '../api/types';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';
import { LoadingScreen } from '../components/LoadingScreen';
import { ProfileForm } from '../profile/ProfileForm';

function defaultTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}

const emptyProfile: WellnessProfileRequest = {
  time_zone: defaultTimeZone(),
  display_name: null,
  measurement_system: 'metric',
  week_start: 'monday',
  tracked_domains: [],
};

function profileErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.kind === 'network') {
      return "We couldn't reach LifeLenz. Please try again.";
    }
    if (
      error.code === 'request_validation_error' ||
      error.code === 'domain_validation_error' ||
      error.code === 'application_validation_error'
    ) {
      return 'Please review your profile preferences and try again.';
    }
    if (error.code === 'profile_access_denied') {
      return 'We could not access this profile.';
    }
  }
  return 'We could not save your profile. Please try again.';
}

export function ProfilePage() {
  const { user, accessToken, refreshCurrentUser, handleSessionError } =
    useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const expectsProfile = Boolean(user?.profile_ids.length);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const profileQuery = useQuery({
    queryKey: queryKeys.profile,
    queryFn: async ({ signal }) => {
      try {
        return await getProfile(accessToken as string, signal);
      } catch (caughtError) {
        handleSessionError(caughtError);
        throw caughtError;
      }
    },
    enabled: Boolean(accessToken && expectsProfile),
    retry: false,
  });

  const profileMissing =
    profileQuery.error instanceof ApiError &&
    profileQuery.error.code === 'profile_not_configured';
  const isCreateMode = !expectsProfile || profileMissing;
  const mutation = useMutation({
    mutationFn: async (request: WellnessProfileRequest) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return isCreateMode
        ? createProfile(accessToken, request)
        : updateProfile(accessToken, request);
    },
    onSuccess: async (profile) => {
      queryClient.setQueryData(queryKeys.profile, profile);
      await refreshCurrentUser();
      setError(null);
      if (isCreateMode) {
        navigate('/app', { replace: true });
      } else {
        setMessage('Profile preferences saved.');
      }
    },
    onError: async (caughtError) => {
      if (handleSessionError(caughtError)) {
        return;
      }
      if (
        isCreateMode &&
        caughtError instanceof ApiError &&
        caughtError.code === 'profile_already_exists' &&
        accessToken
      ) {
        try {
          const profile = await queryClient.fetchQuery({
            queryKey: queryKeys.profile,
            queryFn: ({ signal }) => getProfile(accessToken, signal),
            staleTime: 0,
          });
          queryClient.setQueryData(queryKeys.profile, profile);
          await refreshCurrentUser();
          setError(null);
          setMessage('Your existing profile is ready to edit.');
          return;
        } catch (recoveryError) {
          handleSessionError(recoveryError);
        }
      }
      setError(profileErrorMessage(caughtError));
    },
  });

  useEffect(() => {
    document.title = isCreateMode
      ? 'Set up your profile | LifeLenz'
      : 'Profile | LifeLenz';
  }, [isCreateMode]);

  if (!isCreateMode && profileQuery.isPending) {
    return <LoadingScreen label="Loading your profile" />;
  }

  if (!isCreateMode && profileQuery.isError) {
    if (!profileMissing) {
      return (
        <section
          className="resource-error"
          aria-labelledby="profile-error-heading"
        >
          <Alert>{profileErrorMessage(profileQuery.error)}</Alert>
          <h1 id="profile-error-heading">Profile preferences</h1>
          <button
            className="button button--secondary"
            onClick={() => void profileQuery.refetch()}
          >
            Try again
          </button>
        </section>
      );
    }
  }

  const initialValue: WellnessProfileRequest =
    profileQuery.data ?? emptyProfile;

  return (
    <div className="profile-page">
      <header className="page-intro">
        <p className="eyebrow">
          {isCreateMode ? 'A simple first step' : 'Your preferences'}
        </p>
        <h1>
          {isCreateMode
            ? 'Set up your wellness profile'
            : 'Profile preferences'}
        </h1>
        <p>
          {isCreateMode
            ? 'Choose how LifeLenz should organize and present your everyday wellness data.'
            : 'Keep the way LifeLenz organizes your wellness space aligned with what matters to you.'}
        </p>
      </header>
      <ProfileForm
        key={profileQuery.data?.profile_id ?? 'create'}
        initialValue={initialValue}
        mode={isCreateMode ? 'create' : 'edit'}
        isSubmitting={mutation.isPending}
        error={error}
        success={message}
        onSubmit={async (request) => {
          setError(null);
          setMessage(null);
          await mutation.mutateAsync(request).catch(() => undefined);
        }}
      />
    </div>
  );
}
