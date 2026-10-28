import type { Me } from '@/shared/api/types'

/** UX-only checks. The API still enforces every permission. */
export function hasPermission(me: Me | null | undefined, permission: string): boolean {
  if (!me) {
    return false
  }
  if (me.is_superuser) {
    return true
  }
  return me.permissions.includes(permission)
}

export function hasAnyPermission(
  me: Me | null | undefined,
  permissions: readonly string[],
): boolean {
  return permissions.some((p) => hasPermission(me, p))
}

/** Known IdentityAccess permission names (mirror backend seed). */
export const Permissions = {
  identityRead: 'identity_access:read',
  identityUpdate: 'identity_access:update',
  processRead: 'process:read',
} as const
