import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, hasPermission, useSession } from '@/features/auth'
import { TaskViewTabs } from '@/features/work/TaskViewTabs'
import {
  useTaskTypes,
  useTasksByType,
  useTransitionTask,
  useWorkflow,
} from '@/features/work/hooks'
import type { Task } from '@/features/work/types'
import { isApiError } from '@/shared/api/http-client'
import { resolveLocale } from '@/shared/config/env'
import { formatDubaiDate } from '@/shared/lib/dubai-time'
import { Alert } from '@/shared/ui/Alert'
import { PageFrame } from '@/shared/ui/PageFrame'

export function TasksBoardPage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <TasksBoardInner />
    </RequirePermission>
  )
}

function TasksBoardInner() {
  const { t, i18n } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const typesQuery = useTaskTypes(true)
  const [taskTypeId, setTaskTypeId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)

  useEffect(() => {
    const first = typesQuery.data?.[0]
    if (!taskTypeId && first) {
      setTaskTypeId(first.id)
    }
  }, [taskTypeId, typesQuery.data])

  const selectedType = typesQuery.data?.find((x) => x.id === taskTypeId)
  const workflowQuery = useWorkflow(selectedType?.workflowId)
  const tasksQuery = useTasksByType(me?.id, taskTypeId || undefined)
  const transition = useTransitionTask()
  const canTransition = hasPermission(me, Permissions.workTransition)

  const columns = useMemo(
    () => [...(workflowQuery.data?.statuses ?? [])].sort((a, b) => a.position - b.position),
    [workflowQuery.data?.statuses],
  )

  const byStatus = useMemo(() => {
    const map = new Map<string, Task[]>()
    for (const col of columns) {
      map.set(col.key, [])
    }
    for (const task of tasksQuery.data?.data ?? []) {
      const list = map.get(task.statusKey) ?? []
      list.push(task)
      map.set(task.statusKey, list)
    }
    return map
  }, [columns, tasksQuery.data?.data])

  async function onDrop(toStatusKey: string) {
    if (!draggingId || !canTransition) {
      setDraggingId(null)
      return
    }
    const task = tasksQuery.data?.data.find((x) => x.id === draggingId)
    setDraggingId(null)
    if (!task || task.statusKey === toStatusKey) {
      return
    }
    setError(null)
    try {
      await transition.mutateAsync({ id: task.id, toStatusKey })
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message)
      } else {
        setError(t('work.board.moveFailed'))
      }
    }
  }

  return (
    <PageFrame
      title={t('work.board.title')}
      subtitle={t('work.board.subtitle')}
      toolbar={
        <div className="flex w-full flex-wrap items-center gap-3">
          <TaskViewTabs active="board" />
          <label className="flex items-center gap-2 text-sm">
            <span className="text-[var(--color-muted)]">{t('work.board.taskType')}</span>
            <select
              className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1"
              value={taskTypeId}
              onChange={(e) => setTaskTypeId(e.target.value)}
            >
              {(typesQuery.data ?? []).map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      }
    >
      {error ? <Alert tone="error">{error}</Alert> : null}
      {!typesQuery.data?.length && !typesQuery.isLoading ? (
        <Alert tone="info">{t('work.board.noTypes')}</Alert>
      ) : null}
      {tasksQuery.isLoading || workflowQuery.isLoading ? (
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}
      {columns.length > 0 ? (
        <div className="mt-3 flex gap-3 overflow-x-auto pb-4">
          {columns.map((col) => (
            <section
              key={col.key}
              aria-label={col.name}
              className="flex w-64 shrink-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-wash)]"
              onDragOver={(e) => {
                e.preventDefault()
              }}
              onDrop={(e) => {
                e.preventDefault()
                void onDrop(col.key)
              }}
            >
              <header className="border-b border-[var(--color-border)] px-3 py-2 text-sm font-semibold">
                {col.name}
                <span className="ml-2 text-xs font-normal text-[var(--color-muted)]">
                  {byStatus.get(col.key)?.length ?? 0}
                </span>
              </header>
              <ul className="flex min-h-40 flex-col gap-2 p-2">
                {(byStatus.get(col.key) ?? []).map((task) => (
                  <li
                    key={task.id}
                    draggable={canTransition}
                    onDragStart={() => setDraggingId(task.id)}
                    onDragEnd={() => setDraggingId(null)}
                    className={[
                      'rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm',
                      canTransition ? 'cursor-grab active:cursor-grabbing' : '',
                      draggingId === task.id ? 'opacity-60' : '',
                    ].join(' ')}
                  >
                    <p className="text-xs font-medium text-[var(--color-primary)]">
                      {task.reference}
                    </p>
                    <Link
                      to={`/${locale}/tasks/${task.id}`}
                      className="font-medium text-[var(--color-text)] hover:text-[var(--color-primary)]"
                    >
                      {task.title}
                    </Link>
                    <p className="mt-1 text-xs text-[var(--color-muted)]">
                      {t(`work.priority.${task.priority}`)}
                      {task.dueOn
                        ? ` · ${formatDubaiDate(task.dueOn, i18n.language)}`
                        : ''}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : null}
    </PageFrame>
  )
}
