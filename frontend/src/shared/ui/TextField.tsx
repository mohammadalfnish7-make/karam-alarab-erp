import type { InputHTMLAttributes } from 'react'

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function TextField({
  id,
  label,
  error,
  className = '',
  ...props
}: TextFieldProps) {
  const fieldId = id ?? props.name
  const errorId = fieldId ? `${fieldId}-error` : undefined

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={fieldId} className="text-sm font-medium text-[var(--color-text)]">
        {label}
      </label>
      <input
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className="min-h-10 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 text-sm text-[var(--color-text)] outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-wash)]"
        {...props}
      />
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-[var(--color-danger)]">
          {error}
        </p>
      ) : null}
    </div>
  )
}
