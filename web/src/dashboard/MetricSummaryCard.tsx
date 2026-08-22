import type { MetricWellnessSummary } from '../api/types';
import {
  formatMeasurement,
  formatObservationDate,
  formatPercentageChange,
  formatSignedMeasurement,
  metricLabels,
  rangePosition,
  trendLabels,
} from './metricPresentation';

export function MetricSummaryCard({
  summary,
}: {
  summary: MetricWellnessSummary;
}) {
  const { baseline, trend, unit } = summary;
  const meanPosition = rangePosition(
    baseline.mean,
    baseline.minimum,
    baseline.maximum,
  );
  const medianPosition = rangePosition(
    baseline.median,
    baseline.minimum,
    baseline.maximum,
  );
  const rangeLabel = [
    `Observed range ${formatMeasurement(baseline.minimum, unit)} to ${formatMeasurement(baseline.maximum, unit)}.`,
    `Mean ${formatMeasurement(baseline.mean, unit)}.`,
    `Median ${formatMeasurement(baseline.median, unit)}.`,
  ].join(' ');

  return (
    <article className="metric-card">
      <div className="metric-card__heading">
        <h3>{metricLabels[summary.metric]}</h3>
        <span>
          {baseline.sample_count} {baseline.sample_count === 1 ? 'sample' : 'samples'}
        </span>
      </div>

      <p className="metric-card__average">
        <span>Recent average</span>
        <strong>{formatMeasurement(baseline.mean, unit)}</strong>
      </p>

      <div className="metric-card__visual">
        <div className="metric-card__visual-heading">
          <span>Observed range</span>
          <span>Mean + median markers</span>
        </div>
        <div className="metric-card__range-plot" role="img" aria-label={rangeLabel}>
          <div className="metric-card__range-track" aria-hidden="true">
            <span
              className="metric-card__range-marker metric-card__range-marker--mean"
              style={{ left: `${meanPosition}%` }}
            />
            <span
              className="metric-card__range-marker metric-card__range-marker--median"
              style={{ left: `${medianPosition}%` }}
            />
          </div>
          <div className="metric-card__range-labels" aria-hidden="true">
            <span>{formatMeasurement(baseline.minimum, unit)}</span>
            <span>{formatMeasurement(baseline.maximum, unit)}</span>
          </div>
        </div>
        <div className="metric-card__legend" aria-hidden="true">
          <span><i className="metric-card__legend-dot metric-card__legend-dot--mean" />Mean</span>
          <span><i className="metric-card__legend-dot metric-card__legend-dot--median" />Median</span>
        </div>
      </div>

      <dl className="metric-card__stats">
        <div>
          <dt>Median</dt>
          <dd>{formatMeasurement(baseline.median, unit)}</dd>
        </div>
        <div>
          <dt>Minimum</dt>
          <dd>{formatMeasurement(baseline.minimum, unit)}</dd>
        </div>
        <div>
          <dt>Maximum</dt>
          <dd>{formatMeasurement(baseline.maximum, unit)}</dd>
        </div>
        <div>
          <dt>Spread</dt>
          <dd>
            {formatMeasurement(baseline.population_standard_deviation, unit)}
          </dd>
        </div>
      </dl>

      {trend ? (
        <section className="metric-card__trend" aria-label="Mathematical trend details">
          <div className="metric-card__trend-heading">
            <span>Recent direction</span>
            <strong>{trendLabels[trend.direction]}</strong>
          </div>
          <p className="metric-card__trend-values">
            <span>{formatMeasurement(trend.first_value, unit)}</span>
            <span aria-hidden="true">→</span>
            <span>{formatMeasurement(trend.last_value, unit)}</span>
          </p>
          <dl className="metric-card__trend-stats">
            <div>
              <dt>Absolute change</dt>
              <dd>{formatSignedMeasurement(trend.absolute_change, unit)}</dd>
            </div>
            <div>
              <dt>Relative change</dt>
              <dd>{formatPercentageChange(trend.percentage_change)}</dd>
            </div>
          </dl>
          <p className="metric-card__observed-window">
            Observed {formatObservationDate(trend.first_observed_at)} to{' '}
            {formatObservationDate(trend.last_observed_at)}.
          </p>
        </section>
      ) : (
        <p className="metric-card__trend-empty">
          No recent direction is available from this summary yet.
        </p>
      )}
    </article>
  );
}
