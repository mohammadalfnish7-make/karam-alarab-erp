import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, useSession } from '@/features/auth'
import { TaskViewTabs } from '@/features/work/TaskViewTabs'
import { useMyTasks } from '@/features/work/hooks'
import type { Task } from '@/features/work/types'
import { resolveLocale } from '@/shared/config/env'
import { todayDubai } from '@/shared/lib/dubai-time'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PageFrame } from '@/shared/ui/PageFrame'

export function TasksCalendarPage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <TasksCalendarInner />
    </RequirePermission>
  )
}

function TasksCalendarInner() {
  const { t } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const tasksQuery = useMyTasks(me?.id)
  const today = todayDubai()
  const [cursor, setCursor] = useState(() => {
    const parts = today.split('-').map(Number)
    return { year: parts[0] ?? 2026, month: parts[1] ?? 1 }
  })

  const year = cursor.year
  const month = cursor.month
  const first = new Date(Date.UTC(year, month - 1, 1))
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate()
  const startWeekday = (first.getUTCDay() + 6) % 7 // Monday=0

  const byDay = useMemo(() => {
    const map = new Map<string, Task[]>()
    for (const task of tasksQuery.data?.data ?? []) {
      if (!task.dueOn) continue
      const list = map.get(task.dueOn) ?? []
      list.push(task)
      map.set(task.dueOn, list)
    }
    return map
  }, [tasksQuery.data?.data])

  function shiftMonth(delta: number) {
    const date = new Date(Date.UTC(year, month - 1 + delta, 1))
    setCursor({ year: date.getUTCFullYear(), month: date.getUTCMonth() + 1 })
  }

  const monthLabel = new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-GB', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(first)

  const cells: Array<{ key: string; day: number | null; dateKey: string | null }> = []
  for (let i = 0; i < startWeekday; i++) {
    cells.push({ key: `pad-${i}`, day: null, dateKey: null })
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const dateKey = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    cells.push({ key: dateKey, day, dateKey })
  }

  return (
    <PageFrame
      title={t('work.calendar.title')}
      subtitle={t('work.calendar.subtitle')}
      toolbar={
        <div className="flex w-full flex-wrap items-center gap-3">
          <TaskViewTabs active="calendar" />
          <div className="ml-auto flex items-center gap-2">
            <Button variant="secondary" onClick={() => shiftMonth(-1)}>
              {t('common.prev')}
            </Button>
            <span className="text-sm font-semibold">{monthLabel}</span>
            <Button variant="secondary" onClick={() => shiftMonth(1)}>
              {t('common.next')}
            </Button>
          </div>
        </div>
      }
    >
      {tasksQuery.isLoading ? (
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}
      {tasksQuery.isError ? <Alert tone="error">{t('work.list.loadError')}</Alert> : null}
      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-border)]">
        {['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map((d) => (
          <div
            key={d}
            className="bg-[var(--color-wash)] px-2 py-1 text-xs font-semibold uppercase text-[var(--color-muted)]"
          >
            {t(`work.calendar.${d}`)}
          </div>
        ))}
        {cells.map((cell) => {
          const tasks = cell.dateKey ? byDay.get(cell.dateKey) ?? [] : []
          return (
            <div
              key={cell.key}
              className={[
                'min-h-24 bg-[var(--color-surface)] p-2',
                cell.dateKey === today ? 'ring-2 ring-inset ring-[var(--color-primary)]' : '',
              ].join(' ')}
            >
              {cell.day ? (
                <p className="text-xs font-semibold text-[var(--color-muted)]">{cell.day}</p>
              ) : null}
              <ul className="mt-1 space-y-1">
                {tasks.map((task) => (
                  <li key={task.id}>
                    <Link
                      to={`/${locale}/tasks/${task.id}`}
                      className="block truncate rounded bg-[var(--color-wash)] px-1 py-0.5 text-xs font-medium text-[var(--color-text)] hover:text-[var(--color-primary)]"
                      title={task.title}
                    >
                      {task.reference || task.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </PageFrame>
  )
}
