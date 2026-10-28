export const workKeys = {
  all: ['work'] as const,
  tasks: (filters: Record<string, string | number | undefined>) =>
    [...workKeys.all, 'tasks', filters] as const,
  task: (id: string) => [...workKeys.all, 'task', id] as const,
  workflows: () => [...workKeys.all, 'workflows'] as const,
  workflow: (id: string) => [...workKeys.all, 'workflow', id] as const,
  taskTypes: (activeOnly: boolean) =>
    [...workKeys.all, 'taskTypes', activeOnly] as const,
  assignees: () => [...workKeys.all, 'assignees'] as const,
  audit: (entity: string, entityId: string) =>
    [...workKeys.all, 'audit', entity, entityId] as const,
  files: (name: string) => [...workKeys.all, 'files', name] as const,
  file: (id: string) => [...workKeys.all, 'file', id] as const,
}
