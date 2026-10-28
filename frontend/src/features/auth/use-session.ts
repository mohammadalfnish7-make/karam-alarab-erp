import { useQuery } from '@tanstack/react-query'

import { authApi } from '@/features/auth/api'
import { sessionKeys } from '@/features/auth/session-keys'
import type { Me } from '@/shared/api/types'

export interface SessionState {
  me: Me | null | undefined
  isAuthenticated: boolean
  isLoading: boolean
  isError: boolean
  error: unknown
  refetch: () => void
}

/**
 * Single source of session truth. Login/logout invalidate `sessionKeys.me()`.
 * Do not mirror `me` into React context or localStorage.
 */
export function useSession(): SessionState {
  const query = useQuery({
    queryKey: sessionKeys.me(),
    queryFn: ({ signal }) => authApi.me(signal),
    retry: false,
    staleTime: 60_000,
  })

  return {
    me: query.data,
    isAuthenticated: Boolean(query.data),
    isLoading: query.isPending,
    isError: query.isError,
    error: query.error,
    refetch: () => {
      void query.refetch()
    },
  }
}
