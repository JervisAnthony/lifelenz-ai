export function LoadingScreen({ label = 'Loading' }: { label?: string }) {
  return (
    <main className="loading-screen" aria-busy="true" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p>{label}…</p>
    </main>
  );
}
