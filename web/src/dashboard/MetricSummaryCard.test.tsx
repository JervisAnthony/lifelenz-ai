import { render, screen } from '@testing-library/react';

import type { MetricWellnessSummary } from '../api/types';
import { wellnessSummary } from '../test/resourceFixtures';
import { MetricSummaryCard } from './MetricSummaryCard';

describe('MetricSummaryCard', () => {
  it('visualizes the real baseline range and mathematical trend without health judgment', () => {
    render(<MetricSummaryCard summary={wellnessSummary.metrics[0]} />);

    expect(
      screen.getByRole('heading', { name: 'Water intake' }),
    ).toBeInTheDocument();
    expect(screen.getByText('2 samples')).toBeInTheDocument();
    expect(
      screen.getByRole('img', {
        name: /Observed range 250 mL to 500 mL.*Mean 375 mL.*Median 375 mL/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('Increasing')).toBeInTheDocument();
    expect(screen.getByText('+250 mL')).toBeInTheDocument();
    expect(screen.getByText('+100%')).toBeInTheDocument();
    expect(screen.getAllByText('375 mL').length).toBeGreaterThanOrEqual(2);
    expect(
      screen.queryByText(/healthy|unhealthy|improving|worsening/i),
    ).not.toBeInTheDocument();
  });

  it('keeps a one-sample baseline useful without inventing a trend', () => {
    const summary: MetricWellnessSummary = {
      ...wellnessSummary.metrics[0],
      baseline: {
        ...wellnessSummary.metrics[0].baseline,
        sample_count: 1,
        mean: 500,
        median: 500,
        minimum: 500,
        maximum: 500,
        population_standard_deviation: 0,
      },
      trend: null,
    };

    render(<MetricSummaryCard summary={summary} />);

    expect(screen.getByText('1 sample')).toBeInTheDocument();
    expect(
      screen.getByRole('img', {
        name: /Observed range 500 mL to 500 mL.*Mean 500 mL.*Median 500 mL/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('No recent direction is available from this summary yet.'),
    ).toBeInTheDocument();
    expect(screen.queryByText('Absolute change')).not.toBeInTheDocument();
  });
});
