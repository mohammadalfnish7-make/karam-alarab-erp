import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, useSession } from '@/features/auth'

export function HomePage() {
  const { t } = useTranslation()
  const { me } = useSession()

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-[var(--color-text)]">
        {t('shell.home.title')}
      </h1>
      <p className="mt-2 text-sm text-[var(--color-muted)]">{t('shell.home.body')}</p>
      {me ? (
        <p className="mt-6 text-sm text-[var(--color-text)]" role="status">
          {t('auth.session.signedInAs', { email: me.email })}
        </p>
      ) : null}

      <div className="mt-8">
        <RequirePermission permission={Permissions.identityRead} hide>
          <p className="text-sm font-medium text-[var(--color-primary)]">
            {t('nav.admin')}
          </p>
        </RequirePermission>
      </div>
    </div>
  )
}
