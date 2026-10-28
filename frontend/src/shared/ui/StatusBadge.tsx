interface StatusBadgeProps {
  active: boolean
  activeLabel: string
  inactiveLabel: string
}

export function StatusBadge({ active, activeLabel, inactiveLabel }: StatusBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text)]">
      <span
        aria-hidden
        className={`inline-block size-2 rounded-full ${active ? 'bg-[var(--color-success)]' : 'bg-[var(--color-danger)]'}`}
      />
      {active ? activeLabel : inactiveLabel}
    </span>
  )
}
