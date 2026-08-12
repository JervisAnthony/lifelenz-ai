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
    <main className="auth-page">
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
  );
}
