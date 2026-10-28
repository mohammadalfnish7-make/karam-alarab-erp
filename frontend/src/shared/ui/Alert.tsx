import type { ReactNode } from 'react'

type AlertTone = 'success' | 'error' | 'info'

interface AlertProps {
  tone?: AlertTone
  children: ReactNode
  role?: 'status' | 'alert'
}

const tones: Record<AlertTone, string> = {
  success: 'border-[var(--color-success)] bg-[color-mix(in_srgb,var(--color-success)_12%,white)] text-[var(--color-success)]',
  error: 'border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_10%,white)] text-[var(--color-danger)]',
  info: 'border-[var(--color-primary)] bg-[var(--color-wash)] text-[var(--color-text)]',
}

export function Alert({ tone = 'info', children, role = 'status' }: AlertProps) {
  return (
    <div
      role={role}
      className={`rounded-md border px-3 py-2 text-sm ${tones[tone]}`}
    >
      {children}
    </div>
  )
}
