import { useTranslation } from 'react-i18next'

import type { Role } from '@/shared/api/types'

interface RoleChecklistProps {
  roles: Role[]
  selected: readonly string[]
  onChange: (next: string[]) => void
  error?: string
  disabled?: boolean
}

export function RoleChecklist({
  roles,
  selected,
  onChange,
  error,
  disabled,
}: RoleChecklistProps) {
  const { t } = useTranslation()

  function toggle(name: string): void {
    if (selected.includes(name)) {
      onChange(selected.filter((r) => r !== name))
    } else {
      onChange([...selected, name])
    }
  }

  return (
    <fieldset className="flex flex-col gap-2" disabled={disabled}>
      <legend className="text-sm font-medium text-[var(--color-text)]">
        {t('identity.users.roles')}
      </legend>
      <ul className="flex flex-col gap-2">
        {roles.map((role) => (
          <li key={role.name}>
            <label className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={selected.includes(role.name)}
                onChange={() => toggle(role.name)}
              />
              <span>
                <span className="font-medium text-[var(--color-text)]">
                  {t(`identity.roleLabels.${role.name}`, { defaultValue: role.name })}
                </span>
                <span className="mt-0.5 block text-[var(--color-muted)]">
                  {t(`identity.roleDescriptions.${role.name}`, {
                    defaultValue: role.is_superuser
                      ? t('identity.roles.superuserHint')
                      : '',
                  })}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      {error ? (
        <p role="alert" className="text-sm text-[var(--color-danger)]">
          {error}
        </p>
      ) : null}
    </fieldset>
  )
}
