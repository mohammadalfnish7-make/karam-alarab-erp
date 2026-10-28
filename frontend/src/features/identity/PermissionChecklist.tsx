import { groupPermissions } from '@/shared/lib/group-permissions'

interface PermissionChecklistProps {
  permissions: readonly string[]
  selected: readonly string[]
  onChange: (next: string[]) => void
  disabled?: boolean
}

export function PermissionChecklist({
  permissions,
  selected,
  onChange,
  disabled,
}: PermissionChecklistProps) {
  const groups = groupPermissions(permissions)

  function toggle(name: string): void {
    if (selected.includes(name)) {
      onChange(selected.filter((p) => p !== name))
    } else {
      onChange([...selected, name])
    }
  }

  function toggleGroup(names: string[]): void {
    const allOn = names.every((n) => selected.includes(n))
    if (allOn) {
      onChange(selected.filter((p) => !names.includes(p)))
    } else {
      onChange([...new Set([...selected, ...names])])
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {Object.entries(groups).map(([resource, names]) => (
        <details key={resource} open className="rounded-md border border-[var(--color-border)] p-3">
          <summary className="cursor-pointer text-sm font-semibold text-[var(--color-text)]">
            <label className="inline-flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <input
                type="checkbox"
                disabled={disabled}
                checked={names.every((n) => selected.includes(n))}
                onChange={() => toggleGroup(names)}
              />
              {resource}
            </label>
          </summary>
          <ul className="mt-2 flex flex-col gap-1.5 pl-1">
            {names.map((name) => (
              <li key={name}>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--color-text)]">
                  <input
                    type="checkbox"
                    disabled={disabled}
                    checked={selected.includes(name)}
                    onChange={() => toggle(name)}
                  />
                  <code className="text-xs">{name}</code>
                </label>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  )
}
