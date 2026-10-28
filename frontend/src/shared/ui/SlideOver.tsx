import { useEffect, type ReactNode } from 'react'

import { Button } from '@/shared/ui/Button'

interface SlideOverProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

export function SlideOver({ open, title, onClose, children, footer }: SlideOverProps) {
  useEffect(() => {
    if (!open) {
      return
    }
    function onKey(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="presentation">
      <button
        type="button"
        aria-label="Close panel"
        className="absolute inset-0 bg-[color-mix(in_srgb,var(--color-text)_35%,transparent)]"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative z-10 flex h-full w-full max-w-md flex-col bg-[var(--color-surface)] shadow-xl"
      >
        <header className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
          <h2 className="text-lg font-semibold text-[var(--color-text)]">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close">
            ×
          </Button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer ? (
          <footer className="border-t border-[var(--color-border)] px-5 py-4">{footer}</footer>
        ) : null}
      </aside>
    </div>
  )
}
