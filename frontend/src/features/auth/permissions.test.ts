import { describe, expect, it } from 'vitest'

import { hasPermission } from '@/features/auth/permissions'
import type { Me } from '@/shared/api/types'

function me(partial: Partial<Me>): Me {
  return {
    id: '1',
    email: 'x@y.z',
    is_active: true,
    roles: [],
    permissions: [],
    is_superuser: false,
    ...partial,
  }
}

describe('hasPermission', () => {
  it('denies when signed out', () => {
    expect(hasPermission(null, 'work:read')).toBe(false)
    expect(hasPermission(undefined, 'work:read')).toBe(false)
  })

  it('allows superuser everything', () => {
    expect(hasPermission(me({ is_superuser: true }), 'identity_access:update')).toBe(true)
  })

  it('checks explicit grants', () => {
    const ops = me({ permissions: ['work:read'] })
    expect(hasPermission(ops, 'work:read')).toBe(true)
    expect(hasPermission(ops, 'identity_access:read')).toBe(false)
  })
})
