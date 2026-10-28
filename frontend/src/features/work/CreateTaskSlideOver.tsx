import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { useSession } from '@/features/auth'
import { FollowersPicker } from '@/features/work/FollowersPicker'
import { useCreateTask, useTaskAssignees, useTaskTypes } from '@/features/work/hooks'
import type { TaskPriority } from '@/features/work/types'
import { isApiError } from '@/shared/api/http-client'
import { resolveLocale } from '@/shared/config/env'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PersonPicker } from '@/shared/ui/PersonPicker'
import { SlideOver } from '@/shared/ui/SlideOver'
import { TextField } from '@/shared/ui/TextField'

const PRIORITIES: TaskPriority[] = ['none', 'low', 'normal', 'high', 'urgent']

interface CreateTaskSlideOverProps {
  open: boolean
  onClose: () => void
}

export function CreateTaskSlideOver({ open, onClose }: CreateTaskSlideOverProps) {
  const { t } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { me } = useSession()
  const typesQuery = useTaskTypes(true)
  const assigneesQuery = useTaskAssignees(open)
  const create = useCreateTask()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [taskTypeId, setTaskTypeId] = useState('')
  const [assigneeUserId, setAssigneeUserId] = useState('')
  const [followerUserIds, setFollowerUserIds] = useState<string[]>([])
  const [dueOn, setDueOn] = useState('')
  const [priority, setPriority] = useState<TaskPriority>('normal')
  const [error, setError] = useState<string | null>(null)

  const types = typesQuery.data ?? []
  const assignees = assigneesQuery.data ?? []

  useEffect(() => {
    if (!open || assigneeUserId || !me?.id) {
      return
    }
    setAssigneeUserId(me.id)
  }, [open, me?.id, assigneeUserId])

  async function submit() {
    setError(null)
    if (!title.trim()) {
      setError(t('work.create.titleRequired'))
      return
    }
    if (!taskTypeId) {
      setError(t('work.create.typeRequired'))
      return
    }
    if (!assigneeUserId) {
      setError(t('work.create.assigneeRequired'))
      return
    }
    try {
      await create.mutateAsync({
        task_type_id: taskTypeId,
        title: title.trim(),
        description,
        assignee_user_id: assigneeUserId,
        due_on: dueOn || null,
        priority,
        follower_user_ids: followerUserIds.filter((id) => id !== assigneeUserId),
      })
      setTitle('')
      setDescription('')
      setDueOn('')
      setPriority('normal')
      setAssigneeUserId(me?.id ?? '')
      setFollowerUserIds([])
      onClose()
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message)
      } else {
        setError(t('work.create.failed'))
      }
    }
  }

  return (
    <SlideOver
      open={open}
      onClose={onClose}
      title={t('work.create.title')}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button disabled={create.isPending} onClick={() => void submit()}>
            {create.isPending ? t('work.create.saving') : t('work.create.submit')}
          </Button>
        </div>
      }
    >
      {error ? <Alert tone="error">{error}</Alert> : null}
      {types.length === 0 && !typesQuery.isLoading ? (
        <Alert tone="info">
          {t('work.create.noTypes')}{' '}
          <Link className="underline" to={`/${locale}/admin/workflows`}>
            {t('work.create.goWorkflows')}
          </Link>
        </Alert>
      ) : null}
      <div className="mt-3 flex flex-col gap-3">
        <TextField
          name="task-title"
          label={`${t('work.create.fieldTitle')} *`}
          value={title}
          autoComplete="off"
          onChange={(e) => setTitle(e.target.value)}
        />
        <label className="block text-sm">
          <span className="mb-1 block font-medium">
            {t('work.create.fieldType')}
            <span className="text-[var(--color-danger)]" aria-hidden>
              {' '}
              *
            </span>
          </span>
          <select
            className="w-full rounded-[10px] border border-[#E5E7EB] bg-[var(--color-surface)] px-3 py-2.5 outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--color-primary)_25%,transparent)]"
            value={taskTypeId}
            onChange={(e) => setTaskTypeId(e.target.value)}
          >
            <option value="">{t('work.create.pickType')}</option>
            {types.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
        </label>
        <PersonPicker
          mode="single"
          people={assignees}
          value={assigneeUserId || null}
          currentUserId={me?.id}
          preferIds={me?.id ? [me.id] : []}
          disabled={assigneesQuery.isLoading || create.isPending}
          required
          label={t('work.create.fieldAssignee')}
          placeholder={t('work.create.pickAssignee')}
          recentStorageKey="karam.work.recentAssignees"
          onChange={(userId) => {
            const next = userId ?? ''
            setAssigneeUserId(next)
            if (next) {
              setFollowerUserIds((prev) => prev.filter((id) => id !== next))
            }
          }}
        />
        <FollowersPicker
          users={assignees}
          selectedIds={followerUserIds}
          excludeIds={assigneeUserId ? [assigneeUserId] : []}
          disabled={assigneesQuery.isLoading || create.isPending}
          onToggle={(userId, checked) => {
            setFollowerUserIds((prev) =>
              checked ? [...prev, userId] : prev.filter((id) => id !== userId),
            )
          }}
        />
        <label className="block text-sm">
          <span className="mb-1 block font-medium">{t('work.create.fieldPriority')}</span>
          <select
            className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2"
            value={priority}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`work.priority.${p}`)}
              </option>
            ))}
          </select>
        </label>
        <TextField
          name="task-due"
          type="date"
          label={t('work.create.fieldDue')}
          value={dueOn}
          onChange={(e) => setDueOn(e.target.value)}
        />
        <label className="block text-sm">
          <span className="mb-1 block font-medium">{t('work.create.fieldDescription')}</span>
          <textarea
            className="min-h-24 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
      </div>
    </SlideOver>
  )
}
