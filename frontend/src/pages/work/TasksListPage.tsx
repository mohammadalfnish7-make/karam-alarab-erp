import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, hasPermission, useSession } from '@/features/auth'
import { CreateTaskSlideOver } from '@/features/work/CreateTaskSlideOver'
import { TaskViewTabs } from '@/features/work/TaskViewTabs'
import {
  useTaskAssignees,
  useTaskTypes,
  useTasks,
  useWorkflow,
} from '@/features/work/hooks'
import type { TaskPriority } from '@/features/work/types'
import { resolveLocale } from '@/shared/config/env'
import { formatDubaiDate, formatDubaiDateTime } from '@/shared/lib/dubai-time'
import { displayNameFromEmail } from '@/shared/lib/person-label'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Pagination } from '@/shared/ui/Pagination'

const PAGE_SIZE = 50
const PRIORITIES: TaskPriority[] = ['none', 'low', 'normal', 'high', 'urgent']

export function TasksListPage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <TasksListInner />
    </RequirePermission>
  )
}

function TasksListInner() {
  const { t, i18n } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const [params, setParams] = useSearchParams()
  const [createOpen, setCreateOpen] = useState(false)

  const canCreate = hasPermission(me, Permissions.workCreate)
  const canBrowseAll = hasPermission(me, Permissions.workAdmin) || Boolean(me?.is_superuser)

  // Admins default to all tasks; others stay on "mine".
  const scopeParam = params.get('scope')
  const scope =
    canBrowseAll && scopeParam !== 'mine'
      ? 'all'
      : 'mine'
  const page = Math.max(1, Number(params.get('page') ?? '1') || 1)
  const taskTypeId = params.get('type') || undefined
  const statusKey = params.get('status') || undefined
  const priority = params.get('priority') || undefined
  const dueOnFrom = params.get('dueFrom') || undefined
  const dueOnTo = params.get('dueTo') || undefined
  const assigneeFilter = params.get('assignee') || undefined
  const q = params.get('q')?.trim() || undefined
  const [qDraft, setQDraft] = useState(q ?? '')

  useEffect(() => {
    setQDraft(q ?? '')
  }, [q])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = qDraft.trim()
      setParams((prev) => {
        const current = prev.get('q')?.trim() ?? ''
        if (next === current) return prev
        const updated = new URLSearchParams(prev)
        if (next) updated.set('q', next)
        else updated.delete('q')
        updated.delete('page')
        return updated
      })
    }, 300)
    return () => window.clearTimeout(timer)
  }, [qDraft, setParams])

  const assigneeUserId =
    scope === 'mine' ? me?.id : assigneeFilter || undefined

  const typesQuery = useTaskTypes(false)
  const assigneesQuery = useTaskAssignees(canBrowseAll)
  const selectedType = typesQuery.data?.find((x) => x.id === taskTypeId)
  const workflowQuery = useWorkflow(selectedType?.workflowId)

  const tasksQuery = useTasks(
    {
      page,
      pageSize: PAGE_SIZE,
      assigneeUserId,
      taskTypeId,
      statusKey,
      priority,
      dueOnFrom,
      dueOnTo,
      q,
    },
    scope === 'mine' ? Boolean(me?.id) : true,
  )

  const assigneeLabel = useMemo(() => {
    const map = new Map<string, string>()
    for (const user of assigneesQuery.data ?? []) {
      const name = displayNameFromEmail(user.email)
      map.set(user.id, name ? `${name} (${user.email})` : user.email)
    }
    return (id: string | null) => {
      if (!id) return t('work.list.unassigned')
      return map.get(id) ?? id.slice(0, 8)
    }
  }, [assigneesQuery.data, t])

  const typeName = (id: string) =>
    typesQuery.data?.find((x) => x.id === id)?.name ?? id.slice(0, 8)

  function patchFilters(next: Record<string, string | null>): void {
    const updated = new URLSearchParams(params)
    for (const [key, value] of Object.entries(next)) {
      if (value === null || value === '') updated.delete(key)
      else updated.set(key, value)
    }
    if (!('page' in next)) updated.delete('page')
    setParams(updated)
  }

  const total = tasksQuery.data?.total ?? 0
  const rows = tasksQuery.data?.data ?? []
  const showAssigneeCol = scope === 'all'
  const title =
    scope === 'all' ? t('work.list.titleAll') : t('work.list.title')
  const subtitle =
    scope === 'all' ? t('work.list.subtitleAll') : t('work.list.subtitle')

  return (
    <PageFrame
      title={title}
      subtitle={subtitle}
      actions={
        canCreate ? (
          <Button onClick={() => setCreateOpen(true)}>{t('work.create.open')}</Button>
        ) : null
      }
      toolbar={
        <div className="flex w-full flex-col gap-3">
          <TaskViewTabs active="list" />
          <div className="flex flex-wrap items-end gap-3 rounded-[10px] border border-[#E5E7EB] bg-[var(--color-surface)] p-3">
            <label className="flex min-w-[16rem] flex-1 flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
              {t('work.list.filterSearch')}
              <input
                type="search"
                autoComplete="off"
                placeholder={t('work.list.searchPlaceholder')}
                className="min-h-10 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 text-sm text-[var(--color-text)] outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--color-primary)_25%,transparent)]"
                value={qDraft}
                onChange={(e) => setQDraft(e.target.value)}
              />
            </label>

            {canBrowseAll ? (
              <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
                {t('work.list.filterScope')}
                <select
                  className="min-h-10 min-w-[10rem] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                  value={scope}
                  onChange={(e) =>
                    patchFilters({
                      scope: e.target.value === 'mine' ? 'mine' : null,
                      assignee: null,
                    })
                  }
                >
                  <option value="mine">{t('work.list.scopeMine')}</option>
                  <option value="all">{t('work.list.scopeAll')}</option>
                </select>
              </label>
            ) : null}

            {scope === 'all' ? (
              <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
                {t('work.list.filterAssignee')}
                <select
                  className="min-h-10 min-w-[14rem] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                  value={assigneeFilter ?? ''}
                  onChange={(e) =>
                    patchFilters({ assignee: e.target.value || null })
                  }
                >
                  <option value="">{t('work.list.anyAssignee')}</option>
                  {(assigneesQuery.data ?? []).map((user) => (
                    <option key={user.id} value={user.id}>
                      {displayNameFromEmail(user.email) ?? user.email}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
              {t('work.list.filterType')}
              <select
                className="min-h-10 min-w-[12rem] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                value={taskTypeId ?? ''}
                onChange={(e) =>
                  patchFilters({
                    type: e.target.value || null,
                    status: null,
                  })
                }
              >
                <option value="">{t('work.list.anyType')}</option>
                {(typesQuery.data ?? []).map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
              {t('work.list.filterStatus')}
              <select
                className="min-h-10 min-w-[10rem] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                value={statusKey ?? ''}
                disabled={!selectedType}
                onChange={(e) =>
                  patchFilters({ status: e.target.value || null })
                }
              >
                <option value="">{t('work.list.anyStatus')}</option>
                {(workflowQuery.data?.statuses ?? []).map((status) => (
                  <option key={status.key} value={status.key}>
                    {status.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
              {t('work.list.filterPriority')}
              <select
                className="min-h-10 min-w-[8rem] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                value={priority ?? ''}
                onChange={(e) =>
                  patchFilters({ priority: e.target.value || null })
                }
              >
                <option value="">{t('work.list.anyPriority')}</option>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {t(`work.priority.${p}`)}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
              {t('work.list.filterDueFrom')}
              <input
                type="date"
                className="min-h-10 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                value={dueOnFrom ?? ''}
                onChange={(e) =>
                  patchFilters({ dueFrom: e.target.value || null })
                }
              />
            </label>

            <label className="flex flex-col gap-1 text-xs font-medium text-[var(--color-muted)]">
              {t('work.list.filterDueTo')}
              <input
                type="date"
                className="min-h-10 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
                value={dueOnTo ?? ''}
                onChange={(e) => patchFilters({ dueTo: e.target.value || null })}
              />
            </label>

            <Button
              variant="secondary"
              onClick={() =>
                setParams(
                  canBrowseAll && scope === 'mine'
                    ? new URLSearchParams({ scope: 'mine' })
                    : new URLSearchParams(),
                )
              }
            >
              {t('work.list.clearFilters')}
            </Button>
          </div>
        </div>
      }
    >
      {tasksQuery.isLoading ? (
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}
      {tasksQuery.isError ? (
        <Alert tone="error">{t('work.list.loadError')}</Alert>
      ) : null}
      {tasksQuery.isSuccess && rows.length === 0 ? (
        <div className="mt-8">
          <p className="text-sm font-semibold">{t('work.list.emptyTitle')}</p>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            {scope === 'all'
              ? t('work.list.emptyBodyAll')
              : t('work.list.emptyBody')}
          </p>
        </div>
      ) : null}
      {tasksQuery.isSuccess && rows.length > 0 ? (
        <div className="flex flex-col gap-3">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-xs uppercase tracking-wide text-[var(--color-muted)]">
                  <th className="px-2 py-2 font-semibold">{t('work.list.colReference')}</th>
                  <th className="px-2 py-2 font-semibold">{t('work.list.colTitle')}</th>
                  <th className="px-2 py-2 font-semibold">{t('work.list.colType')}</th>
                  {showAssigneeCol ? (
                    <th className="px-2 py-2 font-semibold">
                      {t('work.list.colAssignee')}
                    </th>
                  ) : null}
                  <th className="px-2 py-2 font-semibold">{t('work.list.colStatus')}</th>
                  <th className="px-2 py-2 font-semibold">{t('work.list.colPriority')}</th>
                  <th className="px-2 py-2 font-semibold">{t('work.list.colDue')}</th>
                  <th className="px-2 py-2 font-semibold">{t('work.list.colUpdated')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((task) => (
                  <tr
                    key={task.id}
                    className="border-b border-[var(--color-border)] hover:bg-[var(--color-wash)]"
                  >
                    <td className="whitespace-nowrap px-2 py-2 font-medium tabular-nums">
                      <Link
                        className="text-[var(--color-primary)] underline-offset-2 hover:underline"
                        to={`/${locale}/tasks/${task.id}`}
                      >
                        {task.reference || typeName(task.taskTypeId)}
                      </Link>
                    </td>
                    <td className="px-2 py-2">
                      <Link
                        className="font-medium text-[var(--color-text)] underline-offset-2 hover:underline"
                        to={`/${locale}/tasks/${task.id}`}
                      >
                        {task.title}
                      </Link>
                    </td>
                    <td className="px-2 py-2">{typeName(task.taskTypeId)}</td>
                    {showAssigneeCol ? (
                      <td className="px-2 py-2">
                        {assigneeLabel(task.assigneeUserId)}
                      </td>
                    ) : null}
                    <td className="px-2 py-2">
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          aria-hidden
                          className="size-2 rounded-full bg-[var(--color-primary)]"
                        />
                        {task.statusKey}
                      </span>
                    </td>
                    <td className="px-2 py-2">{t(`work.priority.${task.priority}`)}</td>
                    <td className="px-2 py-2">
                      {task.dueOn
                        ? formatDubaiDate(task.dueOn, i18n.language)
                        : t('work.list.noDue')}
                    </td>
                    <td className="px-2 py-2">
                      {formatDubaiDateTime(task.updatedAt, i18n.language)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={(next) =>
              patchFilters({ page: next <= 1 ? null : String(next) })
            }
            summary={t('work.list.pageSummary', {
              from: total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1,
              to: Math.min(page * PAGE_SIZE, total),
              total,
            })}
            prevLabel={t('common.prev')}
            nextLabel={t('common.next')}
          />
        </div>
      ) : null}
      <CreateTaskSlideOver open={createOpen} onClose={() => setCreateOpen(false)} />
    </PageFrame>
  )
}
