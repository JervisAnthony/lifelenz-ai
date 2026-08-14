import { recordEntryRegistry } from './recordEntryRegistry';

describe('recordEntryRegistry', () => {
  it('resolves the exact ten unique backend creation workflows with friendly labels', () => {
    const types = recordEntryRegistry.map((entry) => entry.type);
    expect(types).toEqual([
      'sleep',
      'daily_activity',
      'workout',
      'hydration',
      'meal',
      'daily_nutrition',
      'body_measurement',
      'subjective_check_in',
      'menstrual_bleeding',
      'menstrual_cycle',
    ]);
    expect(new Set(types).size).toBe(types.length);
    expect(
      recordEntryRegistry.every((entry) => !entry.label.includes('_')),
    ).toBe(true);
    expect(recordEntryRegistry.every((entry) => entry.Form)).toBe(true);
  });
});
