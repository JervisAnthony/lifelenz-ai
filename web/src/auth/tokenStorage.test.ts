import { tokenStorage } from './tokenStorage';

describe('tokenStorage', () => {
  it('returns null when no access token exists', () => {
    expect(tokenStorage.get()).toBeNull();
  });

  it('stores the access token in session storage', () => {
    tokenStorage.set('temporary-token');

    expect(tokenStorage.get()).toBe('temporary-token');
    expect(window.localStorage.length).toBe(0);
  });

  it('clears the stored access token', () => {
    tokenStorage.set('temporary-token');
    tokenStorage.clear();

    expect(tokenStorage.get()).toBeNull();
  });
});
