import { describe, expect, it } from 'vitest'

import { initialsFromEmail } from '@/shared/lib/initials'

describe('initialsFromEmail', () => {
  it('uses first letters of dotted local part', () => {
    expect(initialsFromEmail('jane.doe@karam-alarab.com')).toBe('JD')
  })

  it('falls back to first two characters', () => {
    expect(initialsFromEmail('ops@karam-alarab.com')).toBe('OP')
  })

  it('handles empty-ish local part', () => {
    expect(initialsFromEmail('@x.com')).toBe('?')
  })
})
