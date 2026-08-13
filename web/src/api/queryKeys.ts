export const queryKeys = {
  currentUser: ['auth', 'current-user'] as const,
  profile: ['profile'] as const,
  summary: ['summary'] as const,
  records: ['records'] as const,
  record: (recordId: string) => ['record', recordId] as const,
};
