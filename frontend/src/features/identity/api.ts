import { httpClient } from '@/shared/api/http-client'
import type {
  ChangePasswordInput,
  CreateUserInput,
  PageUsers,
  Role,
  UpdateUserInput,
  User,
} from '@/shared/api/types'

export const identityApi = {
  async listUsers(
    page: number,
    pageSize: number,
    signal?: AbortSignal,
  ): Promise<PageUsers> {
    const qs = new URLSearchParams({
      page: String(page),
      pageSize: String(pageSize),
    })
    const raw = await httpClient<{
      data: PageUsers['data']
      page: number
      pageSize?: number
      page_size?: number
      total: number
    }>(`/users?${qs.toString()}`, { signal })
    return {
      data: raw.data,
      page: raw.page,
      pageSize: raw.pageSize ?? raw.page_size ?? pageSize,
      total: raw.total,
    }
  },

  createUser(body: CreateUserInput, signal?: AbortSignal): Promise<User> {
    return httpClient<User>('/users', { method: 'POST', body, signal })
  },

  updateUser(id: string, body: UpdateUserInput, signal?: AbortSignal): Promise<User> {
    return httpClient<User>(`/users/${id}`, { method: 'PATCH', body, signal })
  },

  listRoles(signal?: AbortSignal): Promise<Role[]> {
    return httpClient<Role[]>('/roles', { signal })
  },

  listPermissions(signal?: AbortSignal): Promise<string[]> {
    return httpClient<string[]>('/permissions', { signal })
  },

  setRolePermissions(
    roleName: string,
    permissions: string[],
    signal?: AbortSignal,
  ): Promise<void> {
    return httpClient<void>(`/roles/${encodeURIComponent(roleName)}/permissions`, {
      method: 'PUT',
      body: { permissions },
      signal,
    })
  },

  registerPermissions(permissions: string[], signal?: AbortSignal): Promise<string[]> {
    return httpClient<string[]>('/permissions/register', {
      method: 'POST',
      body: { permissions },
      signal,
    })
  },

  changeMyPassword(body: ChangePasswordInput, signal?: AbortSignal): Promise<void> {
    // Wrong current password is 401, but the session cookie is still valid.
    return httpClient<void>('/users/me/password', {
      method: 'PATCH',
      body,
      signal,
      notifyUnauthorized: false,
    })
  },
}
