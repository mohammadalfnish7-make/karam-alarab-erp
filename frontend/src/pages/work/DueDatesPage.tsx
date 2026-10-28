import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, hasPermission, useSession } from '@/features/auth'
import { useMyTasks, usePatchTask } from '@/features/work/hooks'
import type { Task } from '@/features/work/types'
import { isApiError } from '@/shared/api/http-client'
import { resolveLocale } from '@/shared/config/env'
import { formatDubaiDate, todayDubai } from '@/shared/lib/dubai-time'
import { Alert } from '@/shared/ui/Alert'
import { PageFrame } from '@/shared/ui/PageFrame'
import { TextField } from '@/shared/ui/TextField'

export function DueDatesPage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <DueDatesInner />
    </RequirePermission>
  )
}

function DueDatesInner() {
  const { t, i18n } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const tasksQuery = useMyTasks(me?.id)
  const patch = usePatchTask()
  const canUpdate = hasPermission(me, Permissions.workUpdate)
  const [error, setError] = useState<string | null>(null)
  const today = todayDubai()

  const groups = useMemo(() => {
    const tasks = tasksQuery.data?.data ?? []
    const overdue: Task[] = []
    const upcoming: Task[] = []
    const none: Task[] = []
    for (const task of tasks) {
      if (!task.dueOn) {
        none.push(task)
      } else if (task.dueOn < today) {
        overdue.push(task)
      } else {
        upcoming.push(task)
      }
    }
    overdue.sort((a, b) => (a.dueOn ?? '').localeCompare(b.dueOn ?? ''))
    upcoming.sort((a, b) => (a.dueOn ?? '').localeCompare(b.dueOn ?? ''))
    return [
      { key: 'overdue', tasks: overdue },
      { key: 'upcoming', tasks: upcoming },
      { key: 'none', tasks: none },
    ] as const
  }, [tasksQuery.data?.data, today])

  async function changeDue(task: Task, dueOn: string | null) {
    setError(null)
    try {
      await patch.mutateAsync({ id: task.id, body: { due_on: dueOn } })
    } catch (err) {
      if (isApiError(err)) setError(err.message)
      else setError(t('work.detail.saveFailed'))
    }
  }

  return (
    <PageFrame title={t('work.dueDates.title')} subtitle={t('work.dueDates.subtitle')}>
      {error ? <Alert tone="error">{error}</Alert> : null}
      {tasksQuery.isLoading ? (
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}
      {tasksQuery.isError ? <Alert tone="error">{t('work.list.loadError')}</Alert> : null}
      <div className="space-y-6">
        {groups.map((group) => (
          <section key={group.key}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-muted)]">
              {t(`work.dueDates.${group.key}`)}
              <span className="ml-2 font-normal">({group.tasks.length})</span>
            </h2>
            {group.tasks.length === 0 ? (
              <p className="mt-1 text-sm text-[var(--color-muted)]">{t('work.dueDates.empty')}</p>
            ) : (
              <ul className="mt-2 divide-y divide-[var(--color-border)] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]">
                {group.tasks.map((task) => (
                  <li
                    key={task.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-sm"
                  >
                    <div>
                      <Link
                        to={`/${locale}/tasks/${task.id}`}
                        className="font-medium text-[var(--color-primary)] hover:underline"
                      >
                        {task.reference || task.title}
                      </Link>
                      <p className="text-xs text-[var(--color-muted)]">
                        {task.title}
                        {` · ${task.statusKey}`}
                        {task.dueOn
                          ? ` · ${formatDubaiDate(task.dueOn, i18n.language)}`
                          : ''}
                      </p>
                    </div>
                    {canUpdate ? (
                      <TextField
                        name={`due-${task.id}`}
                        compact
                        type="date"
                        label={t('work.dueDates.change')}
                        value={task.dueOn ?? ''}
                        disabled={patch.isPending}
                        onChange={(e) =>
                          void changeDue(task, e.target.value || null)
                        }
                        className="w-44"
                      />
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </PageFrame>
  )
}
