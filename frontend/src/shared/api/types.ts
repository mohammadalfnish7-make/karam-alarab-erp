/**
 * Transport types aligned with backend `api/dto.py`.
 * Do not invent fields the API does not return.
 */

export interface LoginRequest {
  email: string
  password: string
}

export interface Me {
  id: string
  email: string
  is_active: boolean
  roles: string[]
  permissions: string[]
  is_superuser: boolean
}

export interface User {
  id: string
  email: string
  is_active: boolean
  roles: string[]
}

export interface PageUsers {
  data: User[]
  page: number
  pageSize: number
  total: number
}

export interface Role {
  name: string
  is_superuser: boolean
  permissions: string[]
}

export interface CreateUserInput {
  email: string
  password: string
  roles: string[]
}

export interface UpdateUserInput {
  roles?: string[]
  is_active?: boolean
}

export interface ChangePasswordInput {
  current_password: string
  new_password: string
}
