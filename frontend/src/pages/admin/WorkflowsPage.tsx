import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission } from '@/features/auth'
import {
  useCreateTaskType,
  useCreateWorkflow,
  useSetTaskTypeActive,
  useTaskTypes,
  useWorkflows,
} from '@/features/work/hooks'
import { isApiError } from '@/shared/api/http-client'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PageFrame } from '@/shared/ui/PageFrame'
import { SlideOver } from '@/shared/ui/SlideOver'
import { TextField } from '@/shared/ui/TextField'
import { StatusBadge } from '@/shared/ui/StatusBadge'

export function WorkflowsPage() {
  return (
    <RequirePermission permission={Permissions.workAdmin}>
      <WorkflowsInner />
    </RequirePermission>
  )
}

function WorkflowsInner() {
  const { t } = useTranslation()
  const workflowsQuery = useWorkflows()
  const typesQuery = useTaskTypes(false)
  const createWorkflow = useCreateWorkflow()
  const createType = useCreateTaskType()
  const setActive = useSetTaskTypeActive()

  const [wfOpen, setWfOpen] = useState(false)
  const [typeOpen, setTypeOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [wfName, setWfName] = useState('')
  const [statusLines, setStatusLines] = useState('todo,To do,1\ndoing,Doing,0\ndone,Done,0')
  const [transitionLines, setTransitionLines] = useState(
    'todo,doing,start\ndoing,done,finish',
  )

  const [typeKey, setTypeKey] = useState('')
  const [typeName, setTypeName] = useState('')
  const [typeWorkflowId, setTypeWorkflowId] = useState('')

  async function submitWorkflow() {
    setError(null)
    const statuses = statusLines
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split(',').map((p) => p.trim())
        const key = parts[0] ?? ''
        const name = parts[1] || key
        const initial = parts[2] ?? ''
        return {
          key,
          name,
          is_initial: initial === '1' || initial === 'true',
        }
      })
      .filter((s) => s.key)
    const transitions = transitionLines
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split(',').map((p) => p.trim())
        return {
          from_status_key: parts[0] ?? '',
          to_status_key: parts[1] ?? '',
          name: parts[2] || '',
        }
      })
      .filter((t) => t.from_status_key && t.to_status_key)
    try {
      await createWorkflow.mutateAsync({
        name: wfName.trim(),
        statuses,
        transitions,
      })
      setWfOpen(false)
      setWfName('')
    } catch (err) {
      if (isApiError(err)) setError(err.message)
      else setError(t('work.workflows.saveFailed'))
    }
  }

  async function submitType() {
    setError(null)
    try {
      await createType.mutateAsync({
        key: typeKey.trim(),
        name: typeName.trim(),
        workflow_id: typeWorkflowId,
      })
      setTypeOpen(false)
      setTypeKey('')
      setTypeName('')
    } catch (err) {
      if (isApiError(err)) setError(err.message)
      else setError(t('work.workflows.saveFailed'))
    }
  }

  return (
    <PageFrame
      title={t('work.workflows.title')}
      subtitle={t('work.workflows.subtitle')}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setWfOpen(true)}>
            {t('work.workflows.createWorkflow')}
          </Button>
          <Button onClick={() => setTypeOpen(true)}>{t('work.workflows.createType')}</Button>
        </div>
      }
    >
      {error ? <Alert tone="error">{error}</Alert> : null}

      <section className="mt-2">
        <h2 className="text-sm font-semibold">{t('work.workflows.workflowsHeading')}</h2>
        {workflowsQuery.isLoading ? (
          <p className="mt-2 text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
        ) : null}
        <ul className="mt-2 divide-y divide-[var(--color-border)] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]">
          {(workflowsQuery.data ?? []).map((wf) => (
            <li key={wf.id} className="px-3 py-2 text-sm font-medium">
              {wf.name}
            </li>
          ))}
          {workflowsQuery.isSuccess && workflowsQuery.data.length === 0 ? (
            <li className="px-3 py-3 text-sm text-[var(--color-muted)]">
              {t('work.workflows.emptyWorkflows')}
            </li>
          ) : null}
        </ul>
      </section>

      <section className="mt-6">
        <h2 className="text-sm font-semibold">{t('work.workflows.typesHeading')}</h2>
        <ul className="mt-2 divide-y divide-[var(--color-border)] rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]">
          {(typesQuery.data ?? []).map((type) => (
            <li
              key={type.id}
              className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium">
                  {type.name}{' '}
                  <span className="text-[var(--color-muted)]">({type.key})</span>
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge
                  active={type.isActive}
                  activeLabel={t('identity.users.active')}
                  inactiveLabel={t('identity.users.inactive')}
                />
                <Button
                  variant="secondary"
                  disabled={setActive.isPending}
                  onClick={() =>
                    void setActive.mutateAsync({
                      id: type.id,
                      isActive: !type.isActive,
                    })
                  }
                >
                  {type.isActive
                    ? t('work.workflows.deactivate')
                    : t('work.workflows.activate')}
                </Button>
              </div>
            </li>
          ))}
          {typesQuery.isSuccess && typesQuery.data.length === 0 ? (
            <li className="px-3 py-3 text-sm text-[var(--color-muted)]">
              {t('work.workflows.emptyTypes')}
            </li>
          ) : null}
        </ul>
      </section>

      <SlideOver
        open={wfOpen}
        onClose={() => setWfOpen(false)}
        title={t('work.workflows.createWorkflow')}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setWfOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              disabled={createWorkflow.isPending}
              onClick={() => void submitWorkflow()}
            >
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-3">
          <TextField
            name="wf-name"
            label={t('work.workflows.fieldName')}
            value={wfName}
            onChange={(e) => setWfName(e.target.value)}
          />
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t('work.workflows.fieldStatuses')}</span>
            <textarea
              className="min-h-28 w-full rounded-md border border-[var(--color-border)] px-3 py-2 font-mono text-xs"
              value={statusLines}
              onChange={(e) => setStatusLines(e.target.value)}
            />
            <span className="mt-1 block text-xs text-[var(--color-muted)]">
              {t('work.workflows.statusesHint')}
            </span>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">
              {t('work.workflows.fieldTransitions')}
            </span>
            <textarea
              className="min-h-24 w-full rounded-md border border-[var(--color-border)] px-3 py-2 font-mono text-xs"
              value={transitionLines}
              onChange={(e) => setTransitionLines(e.target.value)}
            />
            <span className="mt-1 block text-xs text-[var(--color-muted)]">
              {t('work.workflows.transitionsHint')}
            </span>
          </label>
        </div>
      </SlideOver>

      <SlideOver
        open={typeOpen}
        onClose={() => setTypeOpen(false)}
        title={t('work.workflows.createType')}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setTypeOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button disabled={createType.isPending} onClick={() => void submitType()}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-3">
          <TextField
            name="type-key"
            label={t('work.workflows.fieldKey')}
            value={typeKey}
            onChange={(e) => setTypeKey(e.target.value)}
          />
          <TextField
            name="type-name"
            label={t('work.workflows.fieldTypeName')}
            value={typeName}
            onChange={(e) => setTypeName(e.target.value)}
          />
          <label className="block text-sm">
            <span className="mb-1 block font-medium">{t('work.workflows.fieldWorkflow')}</span>
            <select
              className="w-full rounded-md border border-[var(--color-border)] px-3 py-2"
              value={typeWorkflowId}
              onChange={(e) => setTypeWorkflowId(e.target.value)}
            >
              <option value="">{t('work.workflows.pickWorkflow')}</option>
              {(workflowsQuery.data ?? []).map((wf) => (
                <option key={wf.id} value={wf.id}>
                  {wf.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </SlideOver>
    </PageFrame>
  )
}
