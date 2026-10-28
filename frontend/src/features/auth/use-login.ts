import { useMutation, useQueryClient } from '@tanstack/react-query'

import { authApi } from '@/features/auth/api'
import { sessionKeys } from '@/features/auth/session-keys'
import type { LoginRequest, Me } from '@/shared/api/types'

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: LoginRequest) => authApi.login(body),
    onSuccess: (me: Me) => {
      queryClient.setQueryData(sessionKeys.me(), me)
    },
  })
}
