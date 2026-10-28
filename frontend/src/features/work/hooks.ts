import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'

import { workApi } from '@/features/work/api'
import { workKeys } from '@/features/work/keys'
import type {
  CreateTaskInput,
  CreateTaskTypeInput,
  CreateWorkflowInput,
  PatchTaskInput,
  TaskPriority,
} from '@/features/work/types'

export interface TaskListFilters {
  page?: number
  pageSize?: number
  /** When set, only that assignee. When omitted, all assignees. */
  assigneeUserId?: string
  statusKey?: string
  taskTypeId?: string
  priority?: string
  dueOnFrom?: string
  dueOnTo?: string
  q?: string
}

/** Poll open task lists/detail so another user's edits appear without a manual refresh. */
const TASK_LIVE_REFETCH_MS = 5_000

export function useTasks(filters: TaskListFilters, enabled = true) {
  const page = filters.page ?? 1
  const pageSize = filters.pageSize ?? 50
  return useQuery({
    queryKey: workKeys.tasks({
      page,
      pageSize,
      assigneeUserId: filters.assigneeUserId ?? '',
      statusKey: filters.statusKey ?? '',
      taskTypeId: filters.taskTypeId ?? '',
      priority: filters.priority ?? '',
      dueOnFrom: filters.dueOnFrom ?? '',
      dueOnTo: filters.dueOnTo ?? '',
      q: filters.q ?? '',
    }),
    enabled,
    queryFn: ({ signal }) =>
      workApi.listTasks(
        {
          page,
          pageSize,
          assigneeUserId: filters.assigneeUserId,
          statusKey: filters.statusKey,
          taskTypeId: filters.taskTypeId,
          priority: filters.priority,
          dueOnFrom: filters.dueOnFrom,
          dueOnTo: filters.dueOnTo,
          q: filters.q,
        },
        signal,
      ),
    refetchInterval: enabled ? TASK_LIVE_REFETCH_MS : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  })
}

export function useMyTasks(assigneeUserId: string | undefined, pageSize = 100) {
  return useTasks(
    { page: 1, pageSize, assigneeUserId: assigneeUserId ?? undefined },
    Boolean(assigneeUserId),
  )
}

export function useTasksByType(
  assigneeUserId: string | undefined,
  taskTypeId: string | undefined,
) {
  const enabled = Boolean(assigneeUserId && taskTypeId)
  return useQuery({
    queryKey: workKeys.tasks({
      assigneeUserId: assigneeUserId ?? '',
      taskTypeId: taskTypeId ?? '',
    }),
    enabled,
    queryFn: ({ signal }) =>
      workApi.listTasks(
        {
          page: 1,
          pageSize: 100,
          assigneeUserId,
          taskTypeId,
        },
        signal,
      ),
    refetchInterval: enabled ? TASK_LIVE_REFETCH_MS : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  })
}

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: workKeys.task(taskId ?? ''),
    enabled: Boolean(taskId),
    queryFn: ({ signal }) => workApi.getTask(taskId!, signal),
    refetchInterval: TASK_LIVE_REFETCH_MS,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  })
}

export function useWorkflows() {
  return useQuery({
    queryKey: workKeys.workflows(),
    queryFn: ({ signal }) => workApi.listWorkflows(signal),
  })
}

export function useWorkflow(workflowId: string | undefined) {
  return useQuery({
    queryKey: workKeys.workflow(workflowId ?? ''),
    enabled: Boolean(workflowId),
    queryFn: ({ signal }) => workApi.getWorkflow(workflowId!, signal),
  })
}

export function useTaskTypes(activeOnly = false) {
  return useQuery({
    queryKey: workKeys.taskTypes(activeOnly),
    queryFn: ({ signal }) => workApi.listTaskTypes(activeOnly, signal),
  })
}

export function useTaskAssignees(enabled = true) {
  return useQuery({
    queryKey: workKeys.assignees(),
    enabled,
    queryFn: ({ signal }) => workApi.listAssignees(signal),
  })
}

export function useTaskAudit(taskId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: workKeys.audit('task', taskId ?? ''),
    enabled: Boolean(taskId) && enabled,
    queryFn: ({ signal }) => workApi.listAuditEntries('task', taskId!, signal),
    refetchInterval: enabled ? TASK_LIVE_REFETCH_MS : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateTaskInput) => workApi.createTask(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useAddFollower() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, followerUserId }: { id: string; followerUserId: string }) =>
      workApi.addFollower(id, followerUserId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useRemoveFollower() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, followerUserId }: { id: string; followerUserId: string }) =>
      workApi.removeFollower(id, followerUserId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useRemindAssignee() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, message }: { id: string; message?: string }) =>
      workApi.remindAssignee(id, message ?? ''),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function usePatchTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: PatchTaskInput }) =>
      workApi.patchTask(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useTransitionTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, toStatusKey }: { id: string; toStatusKey: string }) =>
      workApi.transitionTask(id, toStatusKey),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useAddComment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) =>
      workApi.addComment(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useAddStep() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      workApi.addStep(id, title),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useCompleteStep() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      stepId,
      isDone,
    }: {
      id: string
      stepId: string
      isDone: boolean
    }) => workApi.completeStep(id, stepId, isDone),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useRenameStep() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      stepId,
      title,
    }: {
      id: string
      stepId: string
      title: string
    }) => workApi.renameStep(id, stepId, title),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useDeleteStep() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, stepId }: { id: string; stepId: string }) =>
      workApi.deleteStep(id, stepId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useLinkCatalogFile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fileId }: { id: string; fileId: string }) =>
      workApi.addEntityLink(id, 'stored_file', fileId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useUnlinkCatalogFile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fileId }: { id: string; fileId: string }) =>
      workApi.removeEntityLink(id, 'stored_file', fileId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useRemoveAttachment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      attachmentId,
    }: {
      id: string
      attachmentId: string
    }) => workApi.removeAttachment(id, attachmentId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useUploadCatalogFile() {
  return useMutation({
    mutationFn: ({
      file,
      ownerContext,
      ownerId,
    }: {
      file: File
      ownerContext?: string
      ownerId?: string
    }) => workApi.uploadCatalogFile(file, ownerContext ?? '', ownerId ?? ''),
  })
}

/** Resolve catalog metadata for files linked on a task. */
export function useLinkedCatalogFiles(fileIds: string[], enabled = true) {
  return useQueries({
    queries: fileIds.map((id) => ({
      queryKey: workKeys.file(id),
      queryFn: ({ signal }: { signal: AbortSignal }) => workApi.getFile(id, signal),
      enabled: enabled && Boolean(id),
    })),
  })
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateWorkflowInput) => workApi.createWorkflow(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useCreateTaskType() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateTaskTypeInput) => workApi.createTaskType(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useSetTaskTypeActive() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      workApi.setTaskTypeActive(id, isActive),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workKeys.all })
    },
  })
}

export function useSetPriority() {
  const patch = usePatchTask()
  return {
    ...patch,
    mutateAsync: (args: { id: string; priority: TaskPriority }) =>
      patch.mutateAsync({ id: args.id, body: { priority: args.priority } }),
  }
}

export function useSetDueOn() {
  const patch = usePatchTask()
  return {
    ...patch,
    mutateAsync: (args: { id: string; dueOn: string | null }) =>
      patch.mutateAsync({ id: args.id, body: { due_on: args.dueOn } }),
  }
}
