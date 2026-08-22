import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ApiError } from '../api/client';
import { getProfile } from '../api/profile';
import { queryKeys } from '../api/queryKeys';
import { getWellnessSummary } from '../api/summary';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';
import { AnalyticsOverview } from '../dashboard/AnalyticsOverview';
import '../dashboard/dashboardAnalytics.css';
import { MetricSummaryCard } from '../dashboard/MetricSummaryCard';
import { domainLabel } from '../profile/profileOptions';

function isEmptySummary(error: unknown): boolean {
  return (
    error instanceof ApiError && error.code === 'wellness_summary_unavailable'
  );
}

export function DashboardPage() {
  const { user, accessToken, handleSessionError, refreshCurrentUser } =
    useAuth();
  const profileQuery = useQuery({
    queryKey: queryKeys.profile,
    queryFn: async ({ signal }) => {
      try {
        return await getProfile(accessToken as string, signal);
      } catch (error) {
        handleSessionError(error);
        if (
          error instanceof ApiError &&
          error.code === 'profile_not_configured'
        ) {
          void refreshCurrentUser();
        }
        throw error;
      }
    },
    enabled: Boolean(accessToken),
    retry: false,
  });
  const summaryQuery = useQuery({
    queryKey: queryKeys.summary,
    queryFn: async ({ signal }) => {
      try {
        return await getWellnessSummary(accessToken as string, signal);
      } catch (error) {
        handleSessionError(error);
        throw error;
      }
    },
    enabled: Boolean(accessToken && profileQuery.data),
    retry: false,
  });

  useEffect(() => {
    document.title = 'Home | LifeLenz';
  }, []);

  if (!user) {
    return null;
  }

  const displayName = profileQuery.data?.display_name;
  const summary = summaryQuery.data;
  const summaryIsEmpty = Boolean(
    (summary && summary.metrics.length === 0) ||
    isEmptySummary(summaryQuery.error),
  );

  return (
    <div className="dashboard">
      <section className="dashboard__welcome" aria-labelledby="dashboard-title">
        <div>
          <p className="eyebrow">Your LifeLenz space</p>
          <h1 id="dashboard-title">
            {displayName
              ? `Welcome, ${displayName}.`
              : 'Your wellness overview'}
          </h1>
          <p>
            A clear view of the preferences and recorded patterns LifeLenz can
            currently summarize.
          </p>
        </div>
        <div className="profile-status profile-status--ready">
          <span className="profile-status__dot" aria-hidden="true" />
          <div>
            <span className="profile-status__label">Wellness profile</span>
            <strong>Configured</strong>
          </div>
        </div>
      </section>

      <section
        className="dashboard__profile"
        aria-labelledby="profile-overview-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Profile overview</p>
            <h2 id="profile-overview-heading">What you’re tracking</h2>
          </div>
          <p>
            Preferences shape presentation; recorded summary values remain in
            canonical units.
          </p>
        </div>
        {profileQuery.isPending ? (
          <p className="inline-status" role="status">
            Loading profile preferences…
          </p>
        ) : profileQuery.isError ? (
          <div className="summary-error">
            <Alert>We could not load your profile preferences.</Alert>
            <button
              className="button button--secondary"
              onClick={() => void profileQuery.refetch()}
            >
              Try profile again
            </button>
          </div>
        ) : (
          <div className="profile-overview-card">
            <div>
              <span>Measurement preference</span>
              <strong>
                {profileQuery.data.measurement_system === 'metric'
                  ? 'Metric'
                  : 'Imperial'}
              </strong>
            </div>
            <div>
              <span>Week starts</span>
              <strong>
                {profileQuery.data.week_start === 'monday'
                  ? 'Monday'
                  : 'Sunday'}
              </strong>
            </div>
            <div className="profile-overview-card__domains">
              <span>
                Tracked areas ({profileQuery.data.tracked_domains.length})
              </span>
              {profileQuery.data.tracked_domains.length ? (
                <ul>
                  {profileQuery.data.tracked_domains.map((domain) => (
                    <li key={domain}>{domainLabel(domain)}</li>
                  ))}
                </ul>
              ) : (
                <strong>None selected yet</strong>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="dashboard__summary" aria-labelledby="summary-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Based on your records</p>
            <h2 id="summary-heading">Recent wellness summary</h2>
          </div>
          <p>
            Visuals describe your recorded values and mathematical direction;
            they do not judge health or recommend targets.
          </p>
        </div>
        {profileQuery.isError ? (
          <p className="inline-status">
            Your summary will be available after your profile preferences load.
          </p>
        ) : summaryQuery.isPending || !profileQuery.data ? (
          <p className="inline-status" role="status">
            Preparing your summary…
          </p>
        ) : summaryIsEmpty ? (
          <div className="dashboard-empty">
            <span aria-hidden="true">○</span>
            <div>
              <h3>Your wellness picture will appear here</h3>
              <p>
                Add records manually or import a supported CSV. LifeLenz will
                summarize usable metrics from the data you have recorded.
              </p>
              <div className="dashboard-empty__actions">
                <Link className="button button--primary" to="/app/records">
                  Add or review records
                </Link>
                <Link
                  className="button button--secondary"
                  to="/app/records/import"
                >
                  Import CSV
                </Link>
              </div>
            </div>
          </div>
        ) : summaryQuery.isError ? (
          <div className="summary-error">
            <Alert>
              We could not load your wellness summary. Your profile is still
              available.
            </Alert>
            <button
              className="button button--secondary"
              onClick={() => void summaryQuery.refetch()}
            >
              Try summary again
            </button>
          </div>
        ) : summary ? (
          <>
            <AnalyticsOverview summary={summary} />
            <p className="summary-source">
              Based on {summary.generated_from_record_count}{' '}
              {summary.generated_from_record_count === 1 ? 'record' : 'records'}
              . Baseline range markers show minimum, maximum, mean, and median;
              they are not a time-series chart.
            </p>
            <div className="metric-grid">
              {summary.metrics.map((metric) => (
                <MetricSummaryCard key={metric.metric} summary={metric} />
              ))}
            </div>
          </>
        ) : null}
      </section>

      <aside className="dashboard__next-step">
        <p className="eyebrow">Continue your record</p>
        <h2>Keep your overview grounded in your own data.</h2>
        <p>
          Add or import wellness records as they become available, and manage
          your own goals separately. LifeLenz does not turn these summaries into
          medical advice or recommended targets.
        </p>
        <div className="dashboard__next-step-actions">
          <Link className="button button--primary" to="/app/records">
            Open Records
          </Link>
          <Link className="button button--secondary" to="/app/goals">
            Manage goals
          </Link>
        </div>
      </aside>
    </div>
  );
}
