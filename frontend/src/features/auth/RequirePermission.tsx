import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { hasPermission } from '@/features/auth/permissions'
import { useSession } from '@/features/auth/use-session'
import { resolveLocale } from '@/shared/config/env'
import { Button } from '@/shared/ui/Button'

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
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const navigate = useNavigate()

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
        className="mx-auto mt-16 flex max-w-md flex-col items-center px-6 text-center"
      >
        <p className="text-lg font-semibold text-[var(--color-text)]">
          {t('auth.forbidden.title')}
        </p>
        <p className="mt-2 text-sm text-[var(--color-muted)]">{t('auth.forbidden.body')}</p>
        <Button className="mt-6" variant="secondary" onClick={() => void navigate(`/${locale}`)}>
          {t('auth.forbidden.goHome')}
        </Button>
      </div>
    )
  }

  return children
}
