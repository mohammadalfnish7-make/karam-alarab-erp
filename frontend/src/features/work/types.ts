export type TaskPriority = 'none' | 'low' | 'normal' | 'high' | 'urgent'

export interface TaskStep {
  id: string
  title: string
  position: number
  isDone: boolean
}

export interface TaskComment {
  id: string
  authorUserId: string
  body: string
  createdAt: string
}

export interface TaskAttachment {
  id: string
  filename: string
  contentType: string
  sizeBytes: number
  createdAt: string
}

export interface TaskEntityLink {
  entityType: string
  entityId: string
}

export interface Task {
  id: string
  taskTypeId: string
  /** Human id like "collecting payment-12". */
  reference: string
  sequenceNumber: number
  statusKey: string
  title: string
  description: string
  assigneeUserId: string | null
  parentTaskId: string | null
  dueOn: string | null
  priority: TaskPriority
  createdBy: string
  createdAt: string
  updatedAt: string
  steps: TaskStep[]
  comments: TaskComment[]
  attachments: TaskAttachment[]
  entityLinks: TaskEntityLink[]
  followerUserIds: string[]
}

export interface PageTasks {
  data: Task[]
  page: number
  pageSize: number
  total: number
}

export interface WorkflowStatus {
  key: string
  name: string
  isInitial: boolean
  position: number
}

export interface WorkflowTransition {
  fromStatusKey: string
  toStatusKey: string
  name: string
}

export interface WorkflowSummary {
  id: string
  name: string
}

export interface WorkflowDetail extends WorkflowSummary {
  statuses: WorkflowStatus[]
  transitions: WorkflowTransition[]
}

export interface TaskType {
  id: string
  key: string
  name: string
  workflowId: string
  hierarchyLevel: string
  isActive: boolean
}

export interface CreateWorkflowInput {
  name: string
  statuses: Array<{ key: string; name: string; is_initial: boolean }>
  transitions: Array<{
    from_status_key: string
    to_status_key: string
    name?: string
  }>
}

export interface CreateTaskTypeInput {
  key: string
  name: string
  workflow_id: string
  hierarchy_level?: string
}

export interface CreateTaskInput {
  task_type_id: string
  title: string
  description?: string
  assignee_user_id?: string | null
  due_on?: string | null
  priority?: TaskPriority
  follower_user_ids?: string[]
}

export interface PatchTaskInput {
  due_on?: string | null
  priority?: TaskPriority
}

export interface AuditEntry {
  id: string
  occurredAt: string
  actor: string
  action: string
  entity: string
  entityId: string
  summary: string
  requestId: string
}

export interface TaskAssignee {
  id: string
  email: string
}

export interface CatalogFile {
  id: string
  displayName: string
  contentType: string
  sizeBytes: number
  sha256: string
  status: string
  uploadedBy: string
  ownerContext: string
  ownerId: string
  createdAt: string
}
