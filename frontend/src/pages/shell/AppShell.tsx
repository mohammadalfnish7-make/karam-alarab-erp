import { NavLink, Outlet, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, hasPermission, useLogout, useSession } from '@/features/auth'
import { resolveLocale, type AppLocale } from '@/shared/config/env'
import { initialsFromEmail } from '@/shared/lib/initials'
import { Button } from '@/shared/ui/Button'

function navClass({ isActive }: { isActive: boolean }): string {
  return [
    'block rounded-md px-3 py-2 text-sm font-medium',
    isActive
      ? 'bg-[color-mix(in_srgb,white_16%,transparent)] text-white'
      : 'text-white/80 hover:bg-[color-mix(in_srgb,white_10%,transparent)] hover:text-white',
  ].join(' ')
}

export function AppShell() {
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { t } = useTranslation()
  const { me } = useSession()
  const logout = useLogout()
  const navigate = useNavigate()
  const otherLocale: AppLocale = locale === 'en' ? 'ru' : 'en'
  const canAdmin = hasPermission(me, Permissions.identityRead)
  const canWork = hasPermission(me, Permissions.workRead)
  const canWorkAdmin = hasPermission(me, Permissions.workAdmin)

  return (
    <div className="flex min-h-dvh bg-[var(--color-canvas)] text-[var(--color-text)]">
      <aside className="flex w-56 shrink-0 flex-col bg-[#1a2332] text-white">
        <div className="border-b border-white/10 px-4 py-4">
          <p className="text-sm font-semibold tracking-tight">
            {t('brand.name')}
            <span className="mt-0.5 block text-xs font-medium text-[var(--color-primary)]">
              {t('brand.product')}
            </span>
          </p>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-2 py-4" aria-label="Main">
          <NavLink to={`/${locale}`} end className={navClass}>
            {t('nav.home')}
          </NavLink>

          {canWork ? (
            <div className="mt-3">
              <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-white/50">
                {t('nav.work')}
              </p>
              <NavLink to={`/${locale}/tasks`} className={navClass}>
                {t('nav.tasks')}
              </NavLink>
              <NavLink to={`/${locale}/priorities`} className={navClass}>
                {t('nav.priorities')}
              </NavLink>
              <NavLink to={`/${locale}/due-dates`} className={navClass}>
                {t('nav.dueDates')}
              </NavLink>
            </div>
          ) : null}

          {canAdmin || canWorkAdmin ? (
            <div className="mt-3">
              <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-white/50">
                {t('nav.admin')}
              </p>
              {canAdmin ? (
                <>
                  <NavLink to={`/${locale}/admin/users`} className={navClass}>
                    {t('nav.users')}
                  </NavLink>
                  <NavLink to={`/${locale}/admin/roles`} className={navClass}>
                    {t('nav.roles')}
                  </NavLink>
                </>
              ) : null}
              {canWorkAdmin ? (
                <NavLink to={`/${locale}/admin/workflows`} className={navClass}>
                  {t('nav.workflows')}
                </NavLink>
              ) : null}
            </div>
          ) : null}

          <div className="mt-3">
            <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-white/50">
              {t('nav.account')}
            </p>
            <NavLink to={`/${locale}/account/password`} className={navClass}>
              {t('nav.password')}
            </NavLink>
          </div>
        </nav>

        <div className="border-t border-white/10 px-3 py-3">
          {me ? (
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="inline-flex size-8 items-center justify-center rounded-full bg-white/15 text-xs font-semibold"
              >
                {initialsFromEmail(me.email)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium">{me.email}</p>
              </div>
            </div>
          ) : null}
          <div className="mt-3 flex gap-2">
            <Button
              variant="ghost"
              className="flex-1 text-white hover:bg-white/10"
              aria-label={t('nav.language')}
              onClick={() => {
                void navigate(`/${otherLocale}`)
              }}
            >
              {otherLocale.toUpperCase()}
            </Button>
            <Button
              variant="ghost"
              className="flex-1 text-white hover:bg-white/10"
              disabled={logout.isPending}
              onClick={() => {
                void logout.mutateAsync().then(() => {
                  void navigate(`/${locale}/login`, { replace: true })
                })
              }}
            >
              {t('auth.logout')}
            </Button>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
