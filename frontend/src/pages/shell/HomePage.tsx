import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, hasPermission, useSession } from '@/features/auth'
import { resolveLocale } from '@/shared/config/env'
import { PageFrame } from '@/shared/ui/PageFrame'

export function HomePage() {
  const { t } = useTranslation()
  const { me } = useSession()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const canAdmin = hasPermission(me, Permissions.identityRead)
  const canWork = hasPermission(me, Permissions.workRead)
  const canWorkAdmin = hasPermission(me, Permissions.workAdmin)

  const modules = [
    canWork
      ? { to: `/${locale}/tasks`, title: t('nav.tasks'), body: t('work.list.subtitle') }
      : null,
    canWork
      ? {
          to: `/${locale}/priorities`,
          title: t('nav.priorities'),
          body: t('work.priorities.subtitle'),
        }
      : null,
    canWork
      ? {
          to: `/${locale}/due-dates`,
          title: t('nav.dueDates'),
          body: t('work.dueDates.subtitle'),
        }
      : null,
    canWorkAdmin
      ? {
          to: `/${locale}/admin/workflows`,
          title: t('nav.workflows'),
          body: t('work.workflows.subtitle'),
        }
      : null,
    canAdmin
      ? { to: `/${locale}/admin/users`, title: t('nav.users'), body: t('identity.users.subtitle') }
      : null,
    canAdmin
      ? { to: `/${locale}/admin/roles`, title: t('nav.roles'), body: t('identity.roles.subtitle') }
      : null,
    { to: `/${locale}/account/password`, title: t('nav.password'), body: t('identity.password.subtitle') },
  ].filter((item): item is { to: string; title: string; body: string } => item !== null)

  return (
    <PageFrame title={t('shell.home.title')} subtitle={t('shell.home.body')}>
      {me ? (
        <p className="mb-4 text-sm text-[var(--color-text)]" role="status">
          {t('auth.session.signedInAs', { email: me.email })}
        </p>
      ) : null}
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {modules.map((item) => (
          <li key={item.to}>
            <Link
              to={item.to}
              className="block h-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)]"
            >
              <span className="text-sm font-semibold text-[var(--color-text)]">{item.title}</span>
              <span className="mt-1 block text-xs text-[var(--color-muted)]">{item.body}</span>
            </Link>
          </li>
        ))}
      </ul>
    </PageFrame>
  )
}
