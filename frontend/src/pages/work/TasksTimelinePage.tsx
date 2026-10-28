import { useMemo } from 'react'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, useSession } from '@/features/auth'
import { TaskViewTabs } from '@/features/work/TaskViewTabs'
import { useMyTasks } from '@/features/work/hooks'
import { resolveLocale } from '@/shared/config/env'
import { formatDubaiDate, todayDubai } from '@/shared/lib/dubai-time'
import { Alert } from '@/shared/ui/Alert'
import { PageFrame } from '@/shared/ui/PageFrame'

export function TasksTimelinePage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <TasksTimelineInner />
    </RequirePermission>
  )
}

function TasksTimelineInner() {
  const { t, i18n } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const tasksQuery = useMyTasks(me?.id)
  const today = todayDubai()

  const { scheduled, unscheduled, rangeStart, rangeEnd } = useMemo(() => {
    const all = tasksQuery.data?.data ?? []
    const withDue = all.filter((task) => Boolean(task.dueOn))
    const withoutDue = all.filter((task) => !task.dueOn)
    const dates = withDue.flatMap((task) => [
      task.createdAt.slice(0, 10),
      task.dueOn!,
    ])
    dates.push(today)
    const sorted = [...dates].sort()
    return {
      scheduled: withDue,
      unscheduled: withoutDue,
      rangeStart: sorted[0] ?? today,
      rangeEnd: sorted[sorted.length - 1] ?? today,
    }
  }, [tasksQuery.data?.data, today])

  const startMs = Date.parse(`${rangeStart}T00:00:00Z`)
  const endMs = Date.parse(`${rangeEnd}T00:00:00Z`)
  const span = Math.max(endMs - startMs, 86_400_000)

  function barStyle(createdAt: string, dueOn: string) {
    const leftMs = Date.parse(`${createdAt.slice(0, 10)}T00:00:00Z`)
    const rightMs = Date.parse(`${dueOn}T00:00:00Z`)
    const left = ((leftMs - startMs) / span) * 100
    const width = Math.max(((rightMs - leftMs) / span) * 100, 2)
    return { left: `${left}%`, width: `${width}%` }
  }

  return (
    <PageFrame
      title={t('work.timeline.title')}
      subtitle={t('work.timeline.subtitle')}
      toolbar={<TaskViewTabs active="timeline" />}
    >
      {tasksQuery.isLoading ? (
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}
      {tasksQuery.isError ? <Alert tone="error">{t('work.list.loadError')}</Alert> : null}
      {scheduled.length === 0 && unscheduled.length === 0 && tasksQuery.isSuccess ? (
        <p className="text-sm text-[var(--color-muted)]">{t('work.list.emptyBody')}</p>
      ) : null}
      <ul className="space-y-3">
        {scheduled.map((task) => (
          <li key={task.id} className="grid grid-cols-[12rem_1fr] items-center gap-3">
            <Link
              to={`/${locale}/tasks/${task.id}`}
              className="truncate text-sm font-medium text-[var(--color-primary)] hover:underline"
              title={task.title}
            >
              {task.reference || task.title}
            </Link>
            <div className="relative h-8 rounded bg-[var(--color-wash)]">
              <div
                className="absolute top-1.5 h-5 rounded bg-[var(--color-primary)]/80"
                style={barStyle(task.createdAt, task.dueOn!)}
                title={`${formatDubaiDate(task.createdAt.slice(0, 10), i18n.language)} → ${formatDubaiDate(task.dueOn, i18n.language)}`}
              />
            </div>
          </li>
        ))}
      </ul>
      {unscheduled.length > 0 ? (
        <div className="mt-8">
          <h2 className="text-sm font-semibold">{t('work.timeline.unscheduled')}</h2>
          <ul className="mt-2 space-y-1">
            {unscheduled.map((task) => (
              <li key={task.id}>
                <Link
                  to={`/${locale}/tasks/${task.id}`}
                  className="text-sm text-[var(--color-primary)] hover:underline"
                  title={task.title}
                >
                  {task.reference || task.title}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </PageFrame>
  )
}
