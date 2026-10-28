import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission, hasPermission, useSession } from '@/features/auth'
import { workApi } from '@/features/work/api'
import { FollowersPicker } from '@/features/work/FollowersPicker'
import {
  useAddComment,
  useAddFollower,
  useAddStep,
  useCompleteStep,
  useDeleteStep,
  useLinkCatalogFile,
  useLinkedCatalogFiles,
  usePatchTask,
  useRemindAssignee,
  useRemoveAttachment,
  useRemoveFollower,
  useRenameStep,
  useTask,
  useUnlinkCatalogFile,
  useTaskAssignees,
  useTaskAudit,
  useTaskTypes,
  useTransitionTask,
  useUploadCatalogFile,
  useWorkflow,
} from '@/features/work/hooks'
import type { TaskPriority } from '@/features/work/types'
import { isApiError } from '@/shared/api/http-client'
import { env, resolveLocale } from '@/shared/config/env'
import { formatDubaiDateTime } from '@/shared/lib/dubai-time'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PageFrame } from '@/shared/ui/PageFrame'
import { TextField } from '@/shared/ui/TextField'

const PRIORITIES: TaskPriority[] = ['none', 'low', 'normal', 'high', 'urgent']

export function TaskDetailPage() {
  return (
    <RequirePermission permission={Permissions.workRead}>
      <TaskDetailInner />
    </RequirePermission>
  )
}

function TaskDetailInner() {
  const { t, i18n } = useTranslation()
  const { locale: localeParam, taskId } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const taskQuery = useTask(taskId)
  const typesQuery = useTaskTypes(false)
  const task = taskQuery.data
  const type = typesQuery.data?.find((x) => x.id === task?.taskTypeId)
  const workflowQuery = useWorkflow(type?.workflowId)
  const canTransition = hasPermission(me, Permissions.workTransition)
  const canUpdate = hasPermission(me, Permissions.workUpdate)
  const canAttach = hasPermission(me, Permissions.workAttach)
  const canReadAudit = hasPermission(me, Permissions.processRead)
  const canReadFiles = hasPermission(me, Permissions.filesRead)
  const canWriteFiles = hasPermission(me, Permissions.filesWrite)
  const isCreator = Boolean(me?.id && task?.createdBy && me.id === task.createdBy)
  const canManageSteps =
    isCreator || hasPermission(me, Permissions.workAdmin)
  const auditQuery = useTaskAudit(taskId, canReadAudit)

  const transition = useTransitionTask()
  const patch = usePatchTask()
  const addComment = useAddComment()
  const addStep = useAddStep()
  const completeStep = useCompleteStep()
  const renameStep = useRenameStep()
  const deleteStep = useDeleteStep()
  const linkFile = useLinkCatalogFile()
  const unlinkFile = useUnlinkCatalogFile()
  const removeAttachment = useRemoveAttachment()
  const uploadFile = useUploadCatalogFile()
  const assigneesQuery = useTaskAssignees(true)
  const addFollower = useAddFollower()
  const removeFollower = useRemoveFollower()
  const remind = useRemindAssignee()

  const [comment, setComment] = useState('')
  const [stepTitle, setStepTitle] = useState('')
  const [editingStepId, setEditingStepId] = useState<string | null>(null)
  const [editingStepTitle, setEditingStepTitle] = useState('')
  const [fileSearch, setFileSearch] = useState('')
  const [fileSearchTried, setFileSearchTried] = useState(false)
  const [reminderNote, setReminderNote] = useState('')
  const [searchHits, setSearchHits] = useState<
    Array<{ id: string; displayName: string }>
  >([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const seenUpdatedAt = useRef<string | null>(null)
  const localSaveAt = useRef(0)

  const followerIds = task?.followerUserIds ?? []
  const isFollower = Boolean(me?.id && followerIds.includes(me.id))

  useEffect(() => {
    if (!task?.updatedAt) return
    if (seenUpdatedAt.current === null) {
      seenUpdatedAt.current = task.updatedAt
      return
    }
    if (seenUpdatedAt.current === task.updatedAt) return
    seenUpdatedAt.current = task.updatedAt
    // Skip banner right after our own save (invalidate will bump updatedAt).
    if (Date.now() - localSaveAt.current < 4_000) return
    setNotice((prev) => prev ?? t('work.detail.remoteUpdated'))
  }, [task?.updatedAt, t])

  const nextStatuses = useMemo(() => {
    if (!task || !workflowQuery.data) return []
    const edges = workflowQuery.data.transitions.filter(
      (edge) => edge.fromStatusKey === task.statusKey,
    )
    return edges.map((edge) => {
      const status = workflowQuery.data.statuses.find((s) => s.key === edge.toStatusKey)
      return { key: edge.toStatusKey, name: status?.name ?? edge.toStatusKey }
    })
  }, [task, workflowQuery.data])

  const catalogLinks =
    task?.entityLinks.filter((link) => link.entityType === 'stored_file') ?? []
  const catalogFileIds = catalogLinks.map((link) => link.entityId)
  const linkedFilesQuery = useLinkedCatalogFiles(catalogFileIds, canReadFiles)
  const linkedFilesById = useMemo(() => {
    const map = new Map<string, { displayName: string }>()
    for (const result of linkedFilesQuery) {
      if (result.data) map.set(result.data.id, result.data)
    }
    return map
  }, [linkedFilesQuery])

  async function run(action: () => Promise<unknown>, okMessage?: string) {
    setError(null)
    setNotice(null)
    try {
      await action()
      localSaveAt.current = Date.now()
      if (okMessage) setNotice(okMessage)
    } catch (err) {
      if (isApiError(err)) setError(err.message)
      else setError(t('work.detail.saveFailed'))
    }
  }

  if (taskQuery.isLoading) {
    return (
      <PageFrame title={t('work.detail.title')}>
        <p className="text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      </PageFrame>
    )
  }

  if (taskQuery.isError || !task) {
    return (
      <PageFrame title={t('work.detail.title')}>
        <Alert tone="error">{t('work.detail.loadError')}</Alert>
        <Link className="mt-3 inline-block text-sm underline" to={`/${locale}/tasks`}>
          {t('work.detail.back')}
        </Link>
      </PageFrame>
    )
  }

  return (
    <PageFrame
      title={task.reference || task.title}
      subtitle={task.reference ? task.title : (type?.name ?? t('work.detail.title'))}
      actions={
        <Link to={`/${locale}/tasks`}>
          <Button variant="secondary">{t('work.detail.back')}</Button>
        </Link>
      }
    >
      {error ? <Alert tone="error">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      <section className="mt-2 grid gap-4 lg:grid-cols-2">
        <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-sm">
            <span className="text-[var(--color-muted)]">{t('work.list.colStatus')}: </span>
            <span className="inline-flex items-center gap-1.5 font-medium">
              <span aria-hidden className="size-2 rounded-full bg-[var(--color-primary)]" />
              {workflowQuery.data?.statuses.find((s) => s.key === task.statusKey)?.name ??
                task.statusKey}
            </span>
          </p>
          {canTransition && nextStatuses.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {nextStatuses.map((status) => (
                <Button
                  key={status.key}
                  variant="secondary"
                  disabled={transition.isPending}
                  onClick={() =>
                    void run(() =>
                      transition.mutateAsync({ id: task.id, toStatusKey: status.key }),
                    )
                  }
                >
                  {status.name}
                </Button>
              ))}
            </div>
          ) : null}
          <label className="block text-sm">
            <span className="mb-1 block text-[var(--color-muted)]">
              {t('work.list.colPriority')}
            </span>
            <select
              className="rounded-md border border-[var(--color-border)] px-2 py-1"
              value={task.priority}
              disabled={!canUpdate || patch.isPending}
              onChange={(e) =>
                void run(() =>
                  patch.mutateAsync({
                    id: task.id,
                    body: { priority: e.target.value as TaskPriority },
                  }),
                )
              }
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {t(`work.priority.${p}`)}
                </option>
              ))}
            </select>
          </label>
          <TextField
            name="detail-due"
            type="date"
            label={t('work.list.colDue')}
            value={task.dueOn ?? ''}
            disabled={!canUpdate || patch.isPending}
            onChange={(e) =>
              void run(() =>
                patch.mutateAsync({
                  id: task.id,
                  body: { due_on: e.target.value || null },
                }),
              )
            }
          />
          {task.description ? (
            <p className="whitespace-pre-wrap text-sm">{task.description}</p>
          ) : null}

          <div className="border-t border-[var(--color-border)] pt-3">
            <FollowersPicker
              users={assigneesQuery.data ?? []}
              selectedIds={followerIds}
              excludeIds={task.assigneeUserId ? [task.assigneeUserId] : []}
              disabled={
                !canUpdate || addFollower.isPending || removeFollower.isPending
              }
              onToggle={(userId, checked) => {
                if (!canUpdate) return
                void run(() =>
                  checked
                    ? addFollower.mutateAsync({
                        id: task.id,
                        followerUserId: userId,
                      })
                    : removeFollower.mutateAsync({
                        id: task.id,
                        followerUserId: userId,
                      }),
                )
              }}
            />
            {isFollower ? (
              <div className="mt-3 flex flex-col gap-2">
                <TextField
                  name="reminder-note"
                  compact
                  label={t('work.detail.reminderNote')}
                  value={reminderNote}
                  onChange={(e) => setReminderNote(e.target.value)}
                  placeholder={t('work.detail.reminderPlaceholder')}
                />
                <Button
                  disabled={remind.isPending}
                  onClick={() =>
                    void run(
                      async () => {
                        await remind.mutateAsync({
                          id: task.id,
                          message: reminderNote,
                        })
                        setReminderNote('')
                      },
                      t('work.detail.reminderSent'),
                    )
                  }
                >
                  {t('work.detail.remind')}
                </Button>
              </div>
            ) : null}
          </div>
        </div>

        <div className="space-y-4">
          <section className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <h2 className="text-sm font-semibold">{t('work.detail.steps')}</h2>
            <p className="mt-1 text-xs text-[var(--color-muted)]">
              {t('work.detail.stepsHint')}
            </p>
            <ul className="mt-2 space-y-2">
              {task.steps.map((step) => {
                const isEditing = editingStepId === step.id
                return (
                  <li key={step.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={step.isDone}
                      disabled={!canUpdate || completeStep.isPending}
                      onChange={(e) =>
                        void run(() =>
                          completeStep.mutateAsync({
                            id: task.id,
                            stepId: step.id,
                            isDone: e.target.checked,
                          }),
                        )
                      }
                    />
                    {isEditing ? (
                      <>
                        <input
                          className="min-h-9 min-w-[12rem] flex-1 rounded-md border border-[var(--color-border)] px-2 text-sm"
                          value={editingStepTitle}
                          autoFocus
                          onChange={(e) => setEditingStepTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Escape') {
                              setEditingStepId(null)
                              return
                            }
                            if (e.key !== 'Enter') return
                            e.preventDefault()
                            if (!editingStepTitle.trim()) return
                            void run(async () => {
                              await renameStep.mutateAsync({
                                id: task.id,
                                stepId: step.id,
                                title: editingStepTitle.trim(),
                              })
                              setEditingStepId(null)
                            })
                          }}
                        />
                        <Button
                          variant="secondary"
                          disabled={renameStep.isPending}
                          onClick={() => {
                            if (!editingStepTitle.trim()) return
                            void run(async () => {
                              await renameStep.mutateAsync({
                                id: task.id,
                                stepId: step.id,
                                title: editingStepTitle.trim(),
                              })
                              setEditingStepId(null)
                            })
                          }}
                        >
                          {t('common.save')}
                        </Button>
                        <Button
                          variant="secondary"
                          onClick={() => setEditingStepId(null)}
                        >
                          {t('common.cancel')}
                        </Button>
                      </>
                    ) : (
                      <>
                        <span
                          className={[
                            'min-w-0 flex-1',
                            step.isDone
                              ? 'text-[var(--color-muted)] line-through'
                              : '',
                          ].join(' ')}
                        >
                          {step.title}
                        </span>
                        {canManageSteps ? (
                          <span className="ml-auto flex shrink-0 items-center gap-3">
                            <button
                              type="button"
                              className="text-xs font-semibold text-[var(--color-primary)] hover:underline"
                              onClick={() => {
                                setEditingStepId(step.id)
                                setEditingStepTitle(step.title)
                              }}
                            >
                              {t('work.detail.editStep')}
                            </button>
                            <button
                              type="button"
                              className="text-xs font-semibold text-[var(--color-danger)] hover:underline"
                              disabled={deleteStep.isPending}
                              onClick={() => {
                                if (
                                  !window.confirm(
                                    t('work.detail.deleteStepConfirm', {
                                      title: step.title,
                                    }),
                                  )
                                ) {
                                  return
                                }
                                void run(() =>
                                  deleteStep.mutateAsync({
                                    id: task.id,
                                    stepId: step.id,
                                  }),
                                )
                              }}
                            >
                              {t('work.detail.deleteStep')}
                            </button>
                          </span>
                        ) : null}
                      </>
                    )}
                  </li>
                )
              })}
              {task.steps.length === 0 ? (
                <li className="text-sm text-[var(--color-muted)]">
                  {t('work.detail.noSteps')}
                </li>
              ) : null}
            </ul>
            {canManageSteps ? (
              <div className="mt-3 flex gap-2">
                <TextField
                  name="new-step"
                  compact
                  label={t('work.detail.stepPlaceholder')}
                  value={stepTitle}
                  onChange={(e) => setStepTitle(e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="secondary"
                  disabled={addStep.isPending}
                  onClick={() => {
                    if (!stepTitle.trim()) return
                    void run(async () => {
                      await addStep.mutateAsync({ id: task.id, title: stepTitle.trim() })
                      setStepTitle('')
                    })
                  }}
                >
                  {t('work.detail.addStep')}
                </Button>
              </div>
            ) : null}
          </section>

          <section className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <h2 className="text-sm font-semibold">{t('work.detail.comments')}</h2>
            <ul className="mt-2 space-y-2">
              {task.comments.map((c) => (
                <li key={c.id} className="text-sm">
                  <p>{c.body}</p>
                  <p className="text-xs text-[var(--color-muted)]">
                    {formatDubaiDateTime(c.createdAt, i18n.language)}
                  </p>
                </li>
              ))}
            </ul>
            {canUpdate ? (
              <div className="mt-3 flex flex-col gap-2">
                <textarea
                  className="min-h-20 w-full rounded-md border border-[var(--color-border)] px-3 py-2 text-sm"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder={t('work.detail.commentPlaceholder')}
                />
                <Button
                  disabled={addComment.isPending}
                  onClick={() => {
                    if (!comment.trim()) return
                    void run(async () => {
                      await addComment.mutateAsync({ id: task.id, body: comment.trim() })
                      setComment('')
                    })
                  }}
                >
                  {t('work.detail.addComment')}
                </Button>
              </div>
            ) : null}
          </section>
        </div>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <h2 className="text-sm font-semibold">{t('work.detail.attachments')}</h2>
          <ul className="mt-2 space-y-2 text-sm">
            {task.attachments.map((att) => (
              <li key={att.id} className="flex flex-wrap items-center gap-2">
                <a
                  className="font-medium text-[var(--color-primary)] hover:underline"
                  href={`${env.apiBaseUrl}/tasks/${task.id}/attachments/${att.id}`}
                >
                  {att.filename}
                </a>
                {canAttach ? (
                  <button
                    type="button"
                    className="text-xs text-[var(--color-muted)] underline hover:text-[var(--color-danger)]"
                    disabled={removeAttachment.isPending}
                    onClick={() => {
                      if (
                        !window.confirm(
                          t('work.detail.removeAttachmentConfirm', {
                            name: att.filename,
                          }),
                        )
                      ) {
                        return
                      }
                      void run(
                        () =>
                          removeAttachment.mutateAsync({
                            id: task.id,
                            attachmentId: att.id,
                          }),
                        t('work.detail.attachmentRemoved'),
                      )
                    }}
                  >
                    {t('work.detail.removeAttachment')}
                  </button>
                ) : null}
              </li>
            ))}
            {catalogLinks.map((link) => {
              const meta = linkedFilesById.get(link.entityId)
              const label = meta?.displayName ?? `${link.entityId.slice(0, 8)}…`
              return (
                <li key={`catalog-${link.entityId}`} className="flex flex-wrap items-center gap-2">
                  <a
                    className="font-medium text-[var(--color-primary)] hover:underline"
                    href={workApi.fileContentUrl(link.entityId)}
                  >
                    {label}
                  </a>
                  <span className="rounded bg-[var(--color-wash)] px-1.5 py-0.5 text-[11px] text-[var(--color-muted)]">
                    {t('work.detail.catalogBadge')}
                  </span>
                  {canUpdate ? (
                    <button
                      type="button"
                      className="text-xs text-[var(--color-muted)] underline hover:text-[var(--color-danger)]"
                      disabled={unlinkFile.isPending}
                      onClick={() => {
                        void run(
                          () =>
                            unlinkFile.mutateAsync({
                              id: task.id,
                              fileId: link.entityId,
                            }),
                          t('work.detail.fileUnlinked'),
                        )
                      }}
                    >
                      {t('work.detail.unlink')}
                    </button>
                  ) : null}
                </li>
              )
            })}
            {task.attachments.length === 0 && catalogLinks.length === 0 ? (
              <li className="text-[var(--color-muted)]">{t('work.detail.noAttachments')}</li>
            ) : null}
          </ul>
        </div>

        <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <h2 className="text-sm font-semibold">{t('work.detail.catalog')}</h2>
          <p className="mt-1 text-xs text-[var(--color-muted)]">
            {t('work.detail.catalogHint')}
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {catalogLinks.map((link) => {
              const meta = linkedFilesById.get(link.entityId)
              const label = meta?.displayName ?? `${link.entityId.slice(0, 8)}…`
              return (
                <li
                  key={link.entityId}
                  className="flex flex-wrap items-center gap-2"
                >
                  <a
                    className="text-[var(--color-primary)] hover:underline"
                    href={workApi.fileContentUrl(link.entityId)}
                  >
                    {label}
                  </a>
                  {canUpdate ? (
                    <button
                      type="button"
                      className="text-xs text-[var(--color-muted)] underline hover:text-[var(--color-danger)]"
                      disabled={unlinkFile.isPending}
                      onClick={() => {
                        void run(
                          () =>
                            unlinkFile.mutateAsync({
                              id: task.id,
                              fileId: link.entityId,
                            }),
                          t('work.detail.fileUnlinked'),
                        )
                      }}
                    >
                      {t('work.detail.unlink')}
                    </button>
                  ) : null}
                </li>
              )
            })}
            {catalogLinks.length === 0 ? (
              <li className="text-[var(--color-muted)]">{t('work.detail.noCatalog')}</li>
            ) : null}
          </ul>
          {canReadFiles ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <TextField
                name="file-search"
                compact
                label={t('work.detail.searchFiles')}
                value={fileSearch}
                onChange={(e) => {
                  setFileSearch(e.target.value)
                  if (!e.target.value.trim()) setSearchHits([])
                }}
                onKeyDown={(e) => {
                  if (e.key !== 'Enter') return
                  e.preventDefault()
                  if (!fileSearch.trim()) return
                  void run(async () => {
                    const result = await workApi.searchFiles(fileSearch.trim())
                    setSearchHits(
                      result.data.map((f) => ({
                        id: f.id,
                        displayName: f.displayName,
                      })),
                    )
                    setFileSearchTried(true)
                  })
                }}
                className="w-48"
              />
              <Button
                variant="secondary"
                onClick={() => {
                  if (!fileSearch.trim()) return
                  void run(async () => {
                    const result = await workApi.searchFiles(fileSearch.trim())
                    setSearchHits(
                      result.data.map((f) => ({
                        id: f.id,
                        displayName: f.displayName,
                      })),
                    )
                    setFileSearchTried(true)
                  })
                }}
              >
                {t('work.detail.search')}
              </Button>
              {canWriteFiles ? (
                <label className="inline-flex cursor-pointer items-center rounded-md border border-[var(--color-border)] px-3 text-sm font-semibold">
                  {t('work.detail.upload')}
                  <input
                    type="file"
                    className="sr-only"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      e.target.value = ''
                      if (!file) return
                      void run(async () => {
                        const stored = await uploadFile.mutateAsync({
                          file,
                          ownerContext: 'work',
                          ownerId: task.id,
                        })
                        await linkFile.mutateAsync({ id: task.id, fileId: stored.id })
                      }, t('work.detail.fileLinked'))
                    }}
                  />
                </label>
              ) : null}
            </div>
          ) : null}
          {searchHits.length > 0 ? (
            <ul className="mt-2 space-y-1">
              {searchHits.map((hit) => (
                <li key={hit.id} className="flex items-center justify-between gap-2 text-sm">
                  <span>{hit.displayName}</span>
                  {canUpdate ? (
                    <Button
                      variant="secondary"
                      onClick={() =>
                        void run(
                          () => linkFile.mutateAsync({ id: task.id, fileId: hit.id }),
                          t('work.detail.fileLinked'),
                        )
                      }
                    >
                      {t('work.detail.link')}
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : fileSearchTried && fileSearch.trim() ? (
            <p className="mt-2 text-sm text-[var(--color-muted)]">
              {t('work.detail.noFileSearchHits', { query: fileSearch.trim() })}
            </p>
          ) : null}
        </div>
      </section>

      {canReadAudit ? (
        <section className="mt-4 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <h2 className="text-sm font-semibold">{t('work.detail.activity')}</h2>
          {auditQuery.isLoading ? (
            <p className="mt-2 text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
          ) : null}
          <ul className="mt-2 space-y-2">
            {(auditQuery.data?.data ?? []).map((entry) => (
              <li key={entry.id} className="text-sm">
                <p>{entry.summary || entry.action}</p>
                <p className="text-xs text-[var(--color-muted)]">
                  {entry.actor} · {formatDubaiDateTime(entry.occurredAt, i18n.language)}
                </p>
              </li>
            ))}
            {auditQuery.isSuccess && auditQuery.data.data.length === 0 ? (
              <li className="text-sm text-[var(--color-muted)]">{t('work.detail.noActivity')}</li>
            ) : null}
          </ul>
        </section>
      ) : null}
    </PageFrame>
  )
}
