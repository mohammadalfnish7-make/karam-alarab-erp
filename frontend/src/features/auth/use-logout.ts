import { useMutation, useQueryClient } from '@tanstack/react-query'

import { authApi } from '@/features/auth/api'
import { sessionKeys } from '@/features/auth/session-keys'

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: async () => {
      queryClient.setQueryData(sessionKeys.me(), null)
      await queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}
