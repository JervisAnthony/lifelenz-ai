import { recordEntryRegistry } from './recordEntryRegistry';

describe('recordEntryRegistry', () => {
  it('exposes exactly the six implemented creation workflows', () => {
    expect(recordEntryRegistry.map((entry) => entry.type)).toEqual([
      'sleep',
      'hydration',
      'subjective_check_in',
      'daily_activity',
      'workout',
      'body_measurement',
    ]);
    expect(recordEntryRegistry.every((entry) => entry.Form)).toBe(true);
  });
});
