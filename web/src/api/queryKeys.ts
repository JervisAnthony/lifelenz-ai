export const queryKeys = {
  currentUser: ['auth', 'current-user'] as const,
  profile: ['profile'] as const,
  summary: ['summary'] as const,
  records: ['records'] as const,
  record: (recordId: string) => ['record', recordId] as const,
  recordHistory: (
    recordType: string | null,
    start: string | null,
    end: string | null,
  ) => ['records', 'history', recordType, start, end] as const,
  goals: ['goals'] as const,
  goal: (goalId: string) => ['goal', goalId] as const,
};
