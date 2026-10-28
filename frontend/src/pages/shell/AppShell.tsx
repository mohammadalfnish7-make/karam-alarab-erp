import { Link, Outlet, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { useLogout, useSession } from '@/features/auth'
import { resolveLocale, type AppLocale } from '@/shared/config/env'
import { Button } from '@/shared/ui/Button'

export function AppShell() {
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { t } = useTranslation()
  const { me } = useSession()
  const logout = useLogout()
  const navigate = useNavigate()

  const otherLocale: AppLocale = locale === 'en' ? 'ru' : 'en'

  return (
    <div className="min-h-dvh bg-[var(--color-wash)] text-[var(--color-text)]">
      <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <div className="flex items-center gap-6">
            <p className="text-base font-semibold tracking-tight">
              {t('brand.name')}{' '}
              <span className="text-[var(--color-primary)]">{t('brand.product')}</span>
            </p>
            <nav aria-label="Main">
              <Link
                to={`/${locale}`}
                className="text-sm font-medium text-[var(--color-primary)]"
              >
                {t('nav.home')}
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              aria-label={t('nav.language')}
              onClick={() => {
                void navigate(`/${otherLocale}`)
              }}
            >
              {otherLocale.toUpperCase()}
            </Button>
            {me ? (
              <Button
                variant="secondary"
                disabled={logout.isPending}
                onClick={() => {
                  void logout.mutateAsync().then(() => {
                    void navigate(`/${locale}/login`, { replace: true })
                  })
                }}
              >
                {t('auth.logout')}
              </Button>
            ) : null}
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  )
}
