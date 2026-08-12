import type { AuthContextValue } from '../auth/authContext';

export const currentUser = {
  user_id: '4d28698a-d090-4600-a9cc-ab957d43c926',
  email: 'person@example.com',
  is_active: true,
  profile_ids: [],
};

export function createAuthValue(
  overrides: Partial<AuthContextValue> = {},
): AuthContextValue {
  return {
    status: 'unauthenticated',
    user: null,
    notice: null,
    login: async () => currentUser,
    register: async (details) => ({
      user_id: currentUser.user_id,
      email: details.email,
      is_active: true,
    }),
    logout: () => undefined,
    clearNotice: () => undefined,
    ...overrides,
  };
}
