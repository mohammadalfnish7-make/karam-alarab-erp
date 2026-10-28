import type { ButtonHTMLAttributes } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--color-primary)] text-white hover:brightness-95 disabled:opacity-60',
  secondary:
    'border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--color-wash)] disabled:opacity-60',
  ghost:
    'bg-transparent text-[var(--color-text)] hover:bg-[var(--color-wash)] disabled:opacity-60',
}

export function Button({
  variant = 'primary',
  className = '',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-10 items-center justify-center rounded-md px-4 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] ${variants[variant]} ${className}`}
      {...props}
    />
  )
}
