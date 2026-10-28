import { httpClient, isApiError } from '@/shared/api/http-client'
import type { LoginRequest, Me } from '@/shared/api/types'

/** Infrastructure for IdentityAccess session endpoints. Swap implementation freely. */
export const authApi = {
  login(body: LoginRequest, signal?: AbortSignal): Promise<Me> {
    return httpClient<Me>('/sessions', { method: 'POST', body, signal })
  },

  /**
   * Session probe. Anonymous callers get `null` (not an exception),
   * so the UI can render login without a global 401 redirect loop.
   */
  async me(signal?: AbortSignal): Promise<Me | null> {
    try {
      return await httpClient<Me>('/users/me', {
        method: 'GET',
        signal,
        notifyUnauthorized: false,
      })
    } catch (error) {
      if (isApiError(error) && error.isUnauthorized) {
        return null
      }
      throw error
    }
  },

  logout(signal?: AbortSignal): Promise<void> {
    return httpClient<void>('/sessions/current', {
      method: 'DELETE',
      signal,
      notifyUnauthorized: false,
    })
  },
}
