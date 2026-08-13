import type { MetricWellnessSummary } from '../api/types';
import {
  formatMeasurement,
  metricLabels,
  trendLabels,
} from './metricPresentation';

export function MetricSummaryCard({
  summary,
}: {
  summary: MetricWellnessSummary;
}) {
  return (
    <article className="metric-card">
      <div className="metric-card__heading">
        <h3>{metricLabels[summary.metric]}</h3>
        <span>{summary.baseline.sample_count} samples</span>
      </div>
      <p className="metric-card__average">
        <span>Recent average</span>
        <strong>
          {formatMeasurement(summary.baseline.mean, summary.unit)}
        </strong>
      </p>
      <dl className="metric-card__range">
        <div>
          <dt>Minimum</dt>
          <dd>{formatMeasurement(summary.baseline.minimum, summary.unit)}</dd>
        </div>
        <div>
          <dt>Maximum</dt>
          <dd>{formatMeasurement(summary.baseline.maximum, summary.unit)}</dd>
        </div>
        <div>
          <dt>Recent direction</dt>
          <dd>
            {summary.trend
              ? trendLabels[summary.trend.direction]
              : 'Not available yet'}
          </dd>
        </div>
      </dl>
    </article>
  );
}
