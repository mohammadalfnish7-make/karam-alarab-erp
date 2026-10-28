import { Navigate, Outlet, useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'

import { useSession } from '@/features/auth/use-session'
import type { AppLocale } from '@/shared/config/env'

interface RequireAuthProps {
  locale: AppLocale
}

/** Route guard: anonymous users go to login with return path. */
export function RequireAuth({ locale }: RequireAuthProps) {
  const { isAuthenticated, isLoading } = useSession()
  const location = useLocation()
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-[var(--color-muted)]">
        {t('shell.loading')}
      </div>
    )
  }

  if (!isAuthenticated) {
    const returnTo = `${location.pathname}${location.search}`
    return (
      <Navigate
        to={`/${locale}/login`}
        replace
        state={{ returnTo }}
      />
    )
  }

  return <Outlet />
}
