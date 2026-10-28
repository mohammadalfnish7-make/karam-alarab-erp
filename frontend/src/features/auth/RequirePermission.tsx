import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { hasPermission } from '@/features/auth/permissions'
import { useSession } from '@/features/auth/use-session'

interface RequirePermissionProps {
  permission: string
  children: ReactNode
  /** When true, render nothing instead of the forbidden panel. */
  hide?: boolean
}

/** UX gate only — never a substitute for API authorization. */
export function RequirePermission({
  permission,
  children,
  hide = false,
}: RequirePermissionProps) {
  const { me, isLoading } = useSession()
  const { t } = useTranslation()

  if (isLoading) {
    return null
  }

  if (!hasPermission(me, permission)) {
    if (hide) {
      return null
    }
    return (
      <div
        role="status"
        className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-sm text-[var(--color-text)]"
      >
        <p className="font-semibold">{t('auth.forbidden.title')}</p>
        <p className="mt-1 text-[var(--color-muted)]">{t('auth.forbidden.body')}</p>
      </div>
    )
  }

  return children
}
