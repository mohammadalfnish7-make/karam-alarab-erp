import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { identityApi } from '@/features/identity/api'
import { identityKeys } from '@/features/identity/keys'
import { sessionKeys } from '@/features/auth/session-keys'

export function useRoles() {
  return useQuery({
    queryKey: identityKeys.roles(),
    queryFn: ({ signal }) => identityApi.listRoles(signal),
  })
}

export function usePermissionsCatalog() {
  return useQuery({
    queryKey: identityKeys.permissions(),
    queryFn: ({ signal }) => identityApi.listPermissions(signal),
  })
}

export function useSetRolePermissions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ roleName, permissions }: { roleName: string; permissions: string[] }) =>
      identityApi.setRolePermissions(roleName, permissions),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: identityKeys.all })
      await queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}

export function useRegisterPermissions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (permissions: string[]) => identityApi.registerPermissions(permissions),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: identityKeys.permissions() })
      await queryClient.invalidateQueries({ queryKey: identityKeys.roles() })
    },
  })
}
