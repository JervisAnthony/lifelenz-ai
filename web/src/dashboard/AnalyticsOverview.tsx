import type { WellnessSummary } from '../api/types';

export function AnalyticsOverview({ summary }: { summary: WellnessSummary }) {
  const metricsWithDirection = summary.metrics.filter(
    (metric) => metric.trend !== null,
  ).length;

  return (
    <section
      className="analytics-overview"
      aria-labelledby="analytics-overview-heading"
    >
      <div className="analytics-overview__heading">
        <div>
          <p className="eyebrow">Descriptive analytics</p>
          <h3 id="analytics-overview-heading">At a glance</h3>
        </div>
        <p>
          These counts describe the summary generated from your stored records.
          They are not a wellness score.
        </p>
      </div>
      <dl className="analytics-overview__stats">
        <div>
          <dt>Records summarized</dt>
          <dd>{summary.generated_from_record_count}</dd>
        </div>
        <div>
          <dt>Metrics available</dt>
          <dd>{summary.metrics.length}</dd>
        </div>
        <div>
          <dt>Metrics with direction</dt>
          <dd>{metricsWithDirection}</dd>
        </div>
      </dl>
      <p className="analytics-overview__note">
        A direction appears only when the summary API returns enough usable
        samples for that metric. Increasing, decreasing, and stable are
        mathematical descriptions.
      </p>
    </section>
  );
}
