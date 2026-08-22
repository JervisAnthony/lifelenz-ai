import type {
  HydrationRecordCreateRequest,
  SleepRecordCreateRequest,
  WellnessRecord,
  WorkoutRecordCreateRequest,
} from '../api/types';
import {
  bodyMeasurementRecord,
  dailyActivityRecord,
  dailyNutritionRecord,
  hydrationRecord,
  mealRecord,
  menstrualBleedingRecord,
  menstrualCycleRecord,
  workoutRecord,
} from '../test/resourceFixtures';
import {
  bodyMeasurementEditValue,
  checkInEditValue,
  dailyActivityEditValue,
  dailyNutritionEditValue,
  hydrationEditValue,
  mealEditValue,
  menstrualBleedingEditValue,
  menstrualCycleEditValue,
  prepareCorrectionRequest,
  sleepEditValue,
  workoutEditValue,
} from './recordEditing';

const sleepRecord: WellnessRecord = {
  record_type: 'sleep',
  metadata: {
    record_id: '11111111-1111-4111-8111-111111111111',
    recorded_at: '2026-08-14T08:15:00+05:30',
    source: 'app_import',
    notes: 'Synthetic sleep note',
  },
  data: {
    period: {
      start: '2026-08-13T23:30:00+05:30',
      end: '2026-08-14T07:30:00+05:30',
    },
    sleep_minutes: 430,
    awake_minutes: 50,
    quality: 'good',
    stages: {
      awake_minutes: 50,
      light_minutes: 210,
      deep_minutes: 100,
      rem_minutes: 120,
    },
    interruption_count: 0,
  },
};

const checkInRecord: WellnessRecord = {
  record_type: 'subjective_check_in',
  metadata: {
    record_id: '22222222-2222-4222-8222-222222222222',
    recorded_at: '2026-08-14T18:30:00+05:30',
    source: 'manual',
    notes: 'Synthetic check-in note',
  },
  data: {
    mood_score: 7,
    energy_score: 6,
    stress_score: 3,
    motivation_score: null,
    mood_category: 'high',
    tags: ['calm', 'focused'],
  },
};

describe('record correction preparation', () => {
  it('reconstructs all ten supported record types for their existing forms', () => {
    expect(sleepEditValue(sleepRecord)?.sleepMinutes).toBe('430');
    expect(dailyActivityEditValue(dailyActivityRecord)?.steps).toBe('4200');
    expect(workoutEditValue(workoutRecord)?.workoutType).toBe(
      'strength_training',
    );
    expect(hydrationEditValue(hydrationRecord)?.volume).toBe('350');
    expect(mealEditValue(mealRecord)?.mealType).toBe('lunch');
    expect(dailyNutritionEditValue(dailyNutritionRecord)?.mealCount).toBe('');
    expect(
      bodyMeasurementEditValue(bodyMeasurementRecord)?.bodyFatPercent,
    ).toBe('');
    expect(checkInEditValue(checkInRecord)?.tags).toEqual(['calm', 'focused']);
    expect(menstrualBleedingEditValue(menstrualBleedingRecord)?.flow).toBe(
      'light',
    );
    expect(menstrualCycleEditValue(menstrualCycleRecord)?.endDate).toBe('');
  });

  it('preserves explicit zero while keeping nullable values empty', () => {
    if (hydrationRecord.record_type !== 'hydration') {
      throw new Error('unexpected fixture type');
    }
    const importedHydration: WellnessRecord = {
      ...hydrationRecord,
      metadata: { ...hydrationRecord.metadata, source: 'csv_import' },
      data: {
        ...hydrationRecord.data,
        caffeine_milligrams: 0,
      },
    };
    expect(hydrationEditValue(importedHydration)?.caffeine).toBe('0');
    expect(workoutEditValue(workoutRecord)?.distanceKilometers).toBe('');
  });

  it('preserves source provenance when preparing a normal correction request', () => {
    if (hydrationRecord.record_type !== 'hydration') {
      throw new Error('unexpected fixture type');
    }
    const importedHydration: WellnessRecord = {
      ...hydrationRecord,
      metadata: { ...hydrationRecord.metadata, source: 'csv_import' },
    };
    const request: HydrationRecordCreateRequest = {
      record_type: 'hydration',
      metadata: {
        recorded_at: '2026-08-15T10:30:00+05:30',
        source: 'manual',
        notes: 'Corrected synthetic note',
      },
      data: {
        volume_milliliters: 475,
        beverage_type: 'water',
        caffeine_milligrams: null,
      },
    };

    const corrected = prepareCorrectionRequest(importedHydration, request);
    expect(corrected.metadata.source).toBe('csv_import');
    expect(corrected.metadata.recorded_at).toBe('2026-08-15T10:30:00+05:30');
  });

  it('preserves hidden sleep stages and metadata timestamp', () => {
    const request: SleepRecordCreateRequest = {
      record_type: 'sleep',
      metadata: {
        recorded_at: '2026-08-15T07:45:00+05:30',
        source: 'manual',
        notes: 'Corrected sleep note',
      },
      data: {
        period: {
          start: '2026-08-14T23:45:00+05:30',
          end: '2026-08-15T07:45:00+05:30',
        },
        sleep_minutes: 440,
        awake_minutes: 40,
        quality: 'very_good',
        stages: null,
        interruption_count: 0,
      },
    };

    const corrected = prepareCorrectionRequest(sleepRecord, request);
    expect(corrected.record_type).toBe('sleep');
    if (corrected.record_type !== 'sleep') throw new Error('unexpected type');
    expect(corrected.metadata.source).toBe('app_import');
    expect(corrected.metadata.recorded_at).toBe(
      sleepRecord.metadata.recorded_at,
    );
    expect(corrected.data.stages).toEqual(sleepRecord.data.stages);
  });

  it('preserves hidden workout metadata timestamp while allowing period correction', () => {
    if (workoutRecord.record_type !== 'workout') {
      throw new Error('unexpected fixture type');
    }
    const importedWorkout: WellnessRecord = {
      ...workoutRecord,
      metadata: { ...workoutRecord.metadata, source: 'api_import' },
    };
    const request: WorkoutRecordCreateRequest = {
      record_type: 'workout',
      metadata: {
        recorded_at: '2026-08-15T09:00:00+05:30',
        source: 'manual',
        notes: null,
      },
      data: {
        ...workoutRecord.data,
        period: {
          start: '2026-08-15T07:00:00+05:30',
          end: '2026-08-15T08:00:00+05:30',
        },
      },
    };

    const corrected = prepareCorrectionRequest(importedWorkout, request);
    expect(corrected.metadata.source).toBe('api_import');
    expect(corrected.metadata.recorded_at).toBe(
      importedWorkout.metadata.recorded_at,
    );
    if (corrected.record_type !== 'workout') {
      throw new Error('unexpected type');
    }
    expect(corrected.data.period.end).toBe('2026-08-15T08:00:00+05:30');
  });

  it('rejects changing a record discriminator during correction', () => {
    const request: HydrationRecordCreateRequest = {
      record_type: 'hydration',
      metadata: {
        recorded_at: '2026-08-15T10:30:00+05:30',
        source: 'manual',
        notes: null,
      },
      data: {
        volume_milliliters: 300,
        beverage_type: 'water',
        caffeine_milligrams: null,
      },
    };

    expect(() => prepareCorrectionRequest(mealRecord, request)).toThrow(
      'cannot change type',
    );
  });
});
