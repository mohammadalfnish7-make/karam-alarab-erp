/**
 * Auth transport types aligned with backend `api/dto.py`.
 * Replace / extend via `npm run gen:api` once OpenAPI generation is wired.
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
