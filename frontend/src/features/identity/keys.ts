export const identityKeys = {
  all: ['identity'] as const,
  users: (page: number, pageSize: number) =>
    [...identityKeys.all, 'users', { page, pageSize }] as const,
  roles: () => [...identityKeys.all, 'roles'] as const,
  permissions: () => [...identityKeys.all, 'permissions'] as const,
}
