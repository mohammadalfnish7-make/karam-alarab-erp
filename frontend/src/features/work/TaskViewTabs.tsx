import { NavLink, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { resolveLocale } from '@/shared/config/env'

const views = ['list', 'board', 'calendar', 'timeline'] as const

export function TaskViewTabs({ active }: { active: (typeof views)[number] }) {
  const { t } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)

  const href = (view: (typeof views)[number]) => {
    if (view === 'list') return `/${locale}/tasks`
    return `/${locale}/tasks/${view}`
  }

  return (
    <div className="flex flex-wrap gap-1" role="tablist" aria-label={t('work.views.label')}>
      {views.map((view) => (
        <NavLink
          key={view}
          to={href(view)}
          role="tab"
          aria-selected={active === view}
          className={[
            'rounded-md px-3 py-1.5 text-sm font-medium',
            active === view
              ? 'bg-[var(--color-primary)] text-white'
              : 'text-[var(--color-text)] hover:bg-[var(--color-wash)]',
          ].join(' ')}
        >
          {t(`work.views.${view}`)}
        </NavLink>
      ))}
    </div>
  )
}
