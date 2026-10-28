import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, hasPermission, useSession } from '@/features/auth'
import { useMyTasks, usePatchTask } from '@/features/work/hooks'
import type { Task, TaskPriority } from '@/features/work/types'
import { isApiError } from '@/shared/api/http-client'
import { resolveLocale } from '@/shared/config/env'
import { formatDubaiDate } from '@/shared/lib/dubai-time'
import { Alert } from '@/shared/ui/Alert'
import { PageFrame } from '@/shared/ui/PageFrame'
import { useState } from 'react'

const ORDER: TaskPriority[] = ['urgent', 'high', 'normal', 'low', 'none']

export function PrioritiesPage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <PrioritiesInner />
    </RequirePermission>
  )
}

function PrioritiesInner() {
  const { t, i18n } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const tasksQuery = useMyTasks(me?.id)
  const patch = usePatchTask()
  const canUpdate = hasPermission(me, Permissions.workUpdate)
  const [error, setError] = useState<string | null>(null)

  const groups = ORDER.map((priority) => ({
    priority,
    tasks: (tasksQuery.data?.data ?? []).filter((task) => task.priority === priority),
  }))

  async function changePriority(task: Task, priority: TaskPriority) {
    setError(null)
    try {
      await patch.mutateAsync({ id: task.id, body: { priority } })
    } catch (err) {
      if (isApiError(err)) setError(err.message)
      else setError(t('work.detail.saveFailed'))
    }
  }

  return (
    <PageFrame title={t('work.priorities.title')} subtitle={t('work.priorities.subtitle')}>
      {error ? <Alert tone="error">{error}</Alert> : null}
      {tasksQuery.isLoading ? (
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}
      {tasksQuery.isError ? <Alert tone="error">{t('work.list.loadError')}</Alert> : null}
      <div className="space-y-6">
        {groups.map((group) => (
          <section key={group.priority}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-muted)]">
              {t(`work.priority.${group.priority}`)}
              <span className="ml-2 font-normal">({group.tasks.length})</span>
            </h2>
            {group.tasks.length === 0 ? (
              <p className="mt-1 text-sm text-[var(--color-muted)]">{t('work.priorities.empty')}</p>
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
                      <select
                        className="rounded-md border border-[var(--color-border)] px-2 py-1"
                        value={task.priority}
                        disabled={patch.isPending}
                        aria-label={t('work.priorities.change')}
                        onChange={(e) =>
                          void changePriority(task, e.target.value as TaskPriority)
                        }
                      >
                        {ORDER.map((p) => (
                          <option key={p} value={p}>
                            {t(`work.priority.${p}`)}
                          </option>
                        ))}
                      </select>
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
