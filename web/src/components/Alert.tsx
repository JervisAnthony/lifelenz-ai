import type { ReactNode } from 'react';

interface AlertProps {
  children: ReactNode;
  tone?: 'error' | 'success' | 'info';
}

export function Alert({ children, tone = 'error' }: AlertProps) {
  return (
    <div
      className={`alert alert--${tone}`}
      role={tone === 'error' ? 'alert' : 'status'}
    >
      {children}
    </div>
  );
}
