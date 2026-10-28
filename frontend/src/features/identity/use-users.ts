import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { identityApi } from '@/features/identity/api'
import { identityKeys } from '@/features/identity/keys'
import type { CreateUserInput, UpdateUserInput } from '@/shared/api/types'

export function useUsers(page: number, pageSize: number) {
  return useQuery({
    queryKey: identityKeys.users(page, pageSize),
    queryFn: ({ signal }) => identityApi.listUsers(page, pageSize, signal),
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateUserInput) => identityApi.createUser(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: identityKeys.all })
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdateUserInput }) =>
      identityApi.updateUser(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: identityKeys.all })
    },
  })
}
