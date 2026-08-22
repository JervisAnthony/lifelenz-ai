import { render, screen, within } from '@testing-library/react';

import { wellnessSummary } from '../test/resourceFixtures';
import { AnalyticsOverview } from './AnalyticsOverview';

describe('AnalyticsOverview', () => {
  it('reports server-derived coverage counts without creating a score', () => {
    render(<AnalyticsOverview summary={wellnessSummary} />);

    const records = screen.getByText('Records summarized').closest('div');
    const metrics = screen.getByText('Metrics available').closest('div');
    const trends = screen.getByText('Metrics with direction').closest('div');

    expect(records).not.toBeNull();
    expect(metrics).not.toBeNull();
    expect(trends).not.toBeNull();
    expect(within(records as HTMLElement).getByText('2')).toBeInTheDocument();
    expect(within(metrics as HTMLElement).getByText('1')).toBeInTheDocument();
    expect(within(trends as HTMLElement).getByText('1')).toBeInTheDocument();
    expect(screen.getByText(/not a wellness score/i)).toBeInTheDocument();
  });
});
