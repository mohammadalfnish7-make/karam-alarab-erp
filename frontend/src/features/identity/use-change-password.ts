import { useMutation, useQueryClient } from '@tanstack/react-query'

import { identityApi } from '@/features/identity/api'
import { sessionKeys } from '@/features/auth/session-keys'
import type { ChangePasswordInput } from '@/shared/api/types'

export function useChangePassword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ChangePasswordInput) => identityApi.changeMyPassword(body),
    onSuccess: async () => {
      queryClient.setQueryData(sessionKeys.me(), null)
      await queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}
