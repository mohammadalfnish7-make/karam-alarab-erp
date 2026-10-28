import { parseApiError } from '@/shared/api/errors'
import { httpClient } from '@/shared/api/http-client'
import { env } from '@/shared/config/env'
import type {
  AuditEntry,
  CatalogFile,
  CreateTaskInput,
  CreateTaskTypeInput,
  CreateWorkflowInput,
  PageTasks,
  PatchTaskInput,
  Task,
  TaskAssignee,
  TaskType,
  WorkflowDetail,
  WorkflowSummary,
} from '@/features/work/types'

function buildUrl(path: string): string {
  const base = env.apiBaseUrl.replace(/\/$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}

async function uploadForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: 'POST',
    credentials: 'include',
    body: form,
  })
  const contentType = response.headers.get('Content-Type') ?? ''
  const payload: unknown = contentType.includes('application/json')
    ? await response.json()
    : null
  if (!response.ok) {
    throw parseApiError(response.status, payload)
  }
  return payload as T
}

function mapWorkflow(raw: {
  id: string
  name: string
  statuses: Array<{
    key: string
    name: string
    is_initial: boolean
    position: number
  }>
  transitions: Array<{
    from_status_key: string
    to_status_key: string
    name: string
  }>
}): WorkflowDetail {
  return {
    id: raw.id,
    name: raw.name,
    statuses: raw.statuses.map((s) => ({
      key: s.key,
      name: s.name,
      isInitial: s.is_initial,
      position: s.position,
    })),
    transitions: raw.transitions.map((t) => ({
      fromStatusKey: t.from_status_key,
      toStatusKey: t.to_status_key,
      name: t.name,
    })),
  }
}

export const workApi = {
  listTasks(
    params: {
      page?: number
      pageSize?: number
      assigneeUserId?: string
      statusKey?: string
      taskTypeId?: string
      priority?: string
      dueOnFrom?: string
      dueOnTo?: string
      q?: string
    },
    signal?: AbortSignal,
  ): Promise<PageTasks> {
    const qs = new URLSearchParams()
    qs.set('page', String(params.page ?? 1))
    qs.set('pageSize', String(params.pageSize ?? 50))
    if (params.assigneeUserId) qs.set('assigneeUserId', params.assigneeUserId)
    if (params.statusKey) qs.set('statusKey', params.statusKey)
    if (params.taskTypeId) qs.set('taskTypeId', params.taskTypeId)
    if (params.priority) qs.set('priority', params.priority)
    if (params.dueOnFrom) qs.set('dueOnFrom', params.dueOnFrom)
    if (params.dueOnTo) qs.set('dueOnTo', params.dueOnTo)
    if (params.q?.trim()) qs.set('q', params.q.trim())
    return httpClient<PageTasks>(`/tasks?${qs.toString()}`, { signal })
  },

  getTask(id: string, signal?: AbortSignal): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}`, { signal })
  },

  createTask(body: CreateTaskInput, signal?: AbortSignal): Promise<Task> {
    return httpClient<Task>('/tasks', { method: 'POST', body, signal })
  },

  addFollower(
    id: string,
    followerUserId: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/followers`, {
      method: 'POST',
      body: { follower_user_id: followerUserId },
      signal,
    })
  },

  removeFollower(
    id: string,
    followerUserId: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/followers/${followerUserId}`, {
      method: 'DELETE',
      signal,
    })
  },

  remindAssignee(
    id: string,
    message = '',
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/reminders`, {
      method: 'POST',
      body: { message },
      signal,
    })
  },

  patchTask(id: string, body: PatchTaskInput, signal?: AbortSignal): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}`, { method: 'PATCH', body, signal })
  },

  transitionTask(
    id: string,
    toStatusKey: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/transitions`, {
      method: 'POST',
      body: { to_status_key: toStatusKey },
      signal,
    })
  },

  addStep(id: string, title: string, signal?: AbortSignal): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/steps`, {
      method: 'POST',
      body: { title },
      signal,
    })
  },

  completeStep(
    id: string,
    stepId: string,
    isDone: boolean,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/steps/${stepId}`, {
      method: 'PATCH',
      body: { is_done: isDone },
      signal,
    })
  },

  renameStep(
    id: string,
    stepId: string,
    title: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/steps/${stepId}`, {
      method: 'PUT',
      body: { title },
      signal,
    })
  },

  deleteStep(id: string, stepId: string, signal?: AbortSignal): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/steps/${stepId}`, {
      method: 'DELETE',
      signal,
    })
  },

  addComment(id: string, body: string, signal?: AbortSignal): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/comments`, {
      method: 'POST',
      body: { body },
      signal,
    })
  },

  addEntityLink(
    id: string,
    entityType: string,
    entityId: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/entity-links`, {
      method: 'POST',
      body: { entity_type: entityType, entity_id: entityId },
      signal,
    })
  },

  removeEntityLink(
    id: string,
    entityType: string,
    entityId: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(
      `/tasks/${id}/entity-links/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
      { method: 'DELETE', signal },
    )
  },

  removeAttachment(
    id: string,
    attachmentId: string,
    signal?: AbortSignal,
  ): Promise<Task> {
    return httpClient<Task>(`/tasks/${id}/attachments/${attachmentId}`, {
      method: 'DELETE',
      signal,
    })
  },

  uploadAttachment(id: string, file: File): Promise<Task> {
    const form = new FormData()
    form.append('file', file)
    return uploadForm<Task>(`/tasks/${id}/attachments`, form)
  },

  listWorkflows(signal?: AbortSignal): Promise<WorkflowSummary[]> {
    return httpClient<WorkflowSummary[]>('/workflows', { signal })
  },

  async getWorkflow(id: string, signal?: AbortSignal): Promise<WorkflowDetail> {
    const raw = await httpClient<{
      id: string
      name: string
      statuses: Array<{
        key: string
        name: string
        is_initial: boolean
        position: number
      }>
      transitions: Array<{
        from_status_key: string
        to_status_key: string
        name: string
      }>
    }>(`/workflows/${id}`, { signal })
    return mapWorkflow(raw)
  },

  async createWorkflow(
    body: CreateWorkflowInput,
    signal?: AbortSignal,
  ): Promise<WorkflowDetail> {
    const raw = await httpClient<{
      id: string
      name: string
      statuses: Array<{
        key: string
        name: string
        is_initial: boolean
        position: number
      }>
      transitions: Array<{
        from_status_key: string
        to_status_key: string
        name: string
      }>
    }>('/workflows', { method: 'POST', body, signal })
    return mapWorkflow(raw)
  },

  listTaskTypes(
    activeOnly = false,
    signal?: AbortSignal,
  ): Promise<TaskType[]> {
    const qs = activeOnly ? '?activeOnly=true' : ''
    return httpClient<TaskType[]>(`/task-types${qs}`, { signal })
  },

  listAssignees(signal?: AbortSignal): Promise<TaskAssignee[]> {
    return httpClient<TaskAssignee[]>('/task-assignees', { signal })
  },

  createTaskType(body: CreateTaskTypeInput, signal?: AbortSignal): Promise<TaskType> {
    return httpClient<TaskType>('/task-types', { method: 'POST', body, signal })
  },

  setTaskTypeActive(
    id: string,
    isActive: boolean,
    signal?: AbortSignal,
  ): Promise<TaskType> {
    return httpClient<TaskType>(`/task-types/${id}`, {
      method: 'PATCH',
      body: { is_active: isActive },
      signal,
    })
  },

  listAuditEntries(
    entity: string,
    entityId: string,
    signal?: AbortSignal,
  ): Promise<{ data: AuditEntry[] }> {
    const qs = new URLSearchParams({ entity, entityId })
    return httpClient<{ data: AuditEntry[] }>(`/audit-entries?${qs}`, { signal })
  },

  searchFiles(
    name: string,
    signal?: AbortSignal,
  ): Promise<{ data: CatalogFile[]; total: number }> {
    const qs = new URLSearchParams({ name, page: '1', pageSize: '25' })
    return httpClient<{ data: CatalogFile[]; total: number }>(
      `/files?${qs}`,
      { signal },
    )
  },

  getFile(id: string, signal?: AbortSignal): Promise<CatalogFile> {
    return httpClient<CatalogFile>(`/files/${id}`, { signal })
  },

  uploadCatalogFile(
    file: File,
    ownerContext = '',
    ownerId = '',
  ): Promise<CatalogFile> {
    const form = new FormData()
    form.append('file', file)
    form.append('owner_context', ownerContext)
    form.append('owner_id', ownerId)
    return uploadForm<CatalogFile>('/files', form)
  },

  fileContentUrl(fileId: string): string {
    return buildUrl(`/files/${fileId}/content`)
  },
}
