import { Link } from 'react-router-dom';

export function Brand({ to = '/' }: { to?: string }) {
  return (
    <Link className="brand" to={to} aria-label="LifeLenz home">
      <span className="brand__mark" aria-hidden="true">
        L
      </span>
      <span>LifeLenz</span>
    </Link>
  );
}
