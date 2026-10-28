import { describe, expect, it } from 'vitest'

import { groupPermissions } from '@/shared/lib/group-permissions'

describe('groupPermissions', () => {
  it('groups by resource and sorts', () => {
    expect(
      groupPermissions(['work:update', 'work:read', 'identity_access:read', 'process:read']),
    ).toEqual({
      identity_access: ['identity_access:read'],
      process: ['process:read'],
      work: ['work:read', 'work:update'],
    })
  })

  it('handles empty list', () => {
    expect(groupPermissions([])).toEqual({})
  })
})
