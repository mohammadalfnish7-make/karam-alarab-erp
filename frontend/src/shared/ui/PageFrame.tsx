import type { ReactNode } from 'react'

interface PageFrameProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  toolbar?: ReactNode
  children: ReactNode
}

/** Standard ERP page: title bar, optional filter toolbar, full-width work area. */
export function PageFrame({ title, subtitle, actions, toolbar, children }: PageFrameProps) {
  return (
    <div className="flex min-h-full flex-col bg-[var(--color-canvas)]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[var(--color-text)]">{title}</h1>
          {subtitle ? (
            <p className="mt-0.5 text-xs text-[var(--color-muted)]">{subtitle}</p>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </header>
      {toolbar ? (
        <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-2">
          {toolbar}
        </div>
      ) : null}
      <div className="flex-1 px-5 py-4">{children}</div>
    </div>
  )
}
