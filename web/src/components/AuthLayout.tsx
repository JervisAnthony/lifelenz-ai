import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { Brand } from './Brand';

interface AuthLayoutProps {
  title: string;
  intro: string;
  children: ReactNode;
  alternateText: string;
  alternateLink: string;
  alternateLabel: string;
}

export function AuthLayout({
  title,
  intro,
  children,
  alternateText,
  alternateLink,
  alternateLabel,
}: AuthLayoutProps) {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <main id="main-content" className="auth-page" tabIndex={-1}>
        <div className="auth-page__brand">
          <Brand />
        </div>
        <section className="auth-card" aria-labelledby="auth-title">
          <p className="eyebrow">Your private wellness space</p>
          <h1 id="auth-title">{title}</h1>
          <p className="auth-card__intro">{intro}</p>
          {children}
          <p className="auth-card__alternate">
            {alternateText} <Link to={alternateLink}>{alternateLabel}</Link>
          </p>
        </section>
      </main>
    </>
  );
}
