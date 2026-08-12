import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'quiet';
}

export function Button({
  className = '',
  variant = 'primary',
  ...props
}: ButtonProps) {
  return (
    <button
      className={`button button--${variant} ${className}`.trim()}
      {...props}
    />
  );
}
