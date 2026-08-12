import { Link } from 'react-router-dom';

import { Brand } from '../components/Brand';

const foundations = [
  {
    title: 'One thoughtful record',
    body: 'Bring everyday wellness information into one structured, private place.',
  },
  {
    title: 'Your own baseline',
    body: 'Understand changes relative to your patterns—not someone else’s averages.',
  },
  {
    title: 'Clear by design',
    body: 'See where an observation comes from, without diagnostic claims or hidden scoring.',
  },
];

export function LandingPage() {
  return (
    <div className="landing-page">
      <header className="site-header">
        <Brand />
        <nav aria-label="Account navigation">
          <Link className="text-link" to="/login">
            Sign in
          </Link>
          <Link className="button button--primary" to="/register">
            Create account
          </Link>
        </nav>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-heading">
          <div className="hero__copy">
            <p className="eyebrow">Everyday wellness, in context</p>
            <h1 id="hero-heading">
              Notice the patterns that make your days feel different.
            </h1>
            <p className="hero__lede">
              LifeLenz helps you organize your wellness information and
              understand personal patterns over time—with calm, transparent
              language.
            </p>
            <div className="hero__actions">
              <Link
                className="button button--primary button--large"
                to="/register"
              >
                Start your private space
              </Link>
              <Link
                className="button button--secondary button--large"
                to="/login"
              >
                I already have an account
              </Link>
            </div>
            <p className="hero__fine-print">
              For general wellness reflection. LifeLenz does not provide medical
              advice.
            </p>
          </div>
          <div className="hero__visual" aria-hidden="true">
            <div className="rhythm-card">
              <span className="rhythm-card__label">A gentler daily view</span>
              <div className="rhythm-card__line rhythm-card__line--one" />
              <div className="rhythm-card__line rhythm-card__line--two" />
              <div className="rhythm-card__line rhythm-card__line--three" />
              <div className="rhythm-card__footer">
                <span>Sleep</span>
                <span>Energy</span>
                <span>Movement</span>
              </div>
            </div>
          </div>
        </section>

        <section
          className="foundation-section"
          aria-labelledby="foundation-heading"
        >
          <p className="eyebrow">Built for perspective</p>
          <h2 id="foundation-heading">
            A foundation for understanding, not judgment.
          </h2>
          <div className="foundation-grid">
            {foundations.map((item, index) => (
              <article key={item.title}>
                <span className="foundation-grid__number">0{index + 1}</span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <span>LifeLenz</span>
        <span>Private, personal, non-diagnostic wellness reflection.</span>
      </footer>
    </div>
  );
}
