import { Link } from 'react-router-dom';

import { Brand } from '../components/Brand';

export function NotFoundPage() {
  return (
    <main className="not-found">
      <Brand />
      <p className="eyebrow">404</p>
      <h1>This page is out of view.</h1>
      <p>The address may have changed, or the page may not exist yet.</p>
      <Link className="button button--primary" to="/">
        Return home
      </Link>
    </main>
  );
}
