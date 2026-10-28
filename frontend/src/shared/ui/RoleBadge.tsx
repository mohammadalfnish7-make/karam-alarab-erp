interface RoleBadgeProps {
  name: string
  label?: string
}

export function RoleBadge({ name, label }: RoleBadgeProps) {
  return (
    <span className="inline-flex rounded-md bg-[var(--color-wash)] px-2 py-0.5 text-xs font-medium text-[var(--color-primary)]">
      {label ?? name}
    </span>
  )
}
