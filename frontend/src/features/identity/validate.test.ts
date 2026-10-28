import { describe, expect, it } from 'vitest'

import {
  validateChangePassword,
  validateCreateUser,
  validatePermissionName,
} from '@/features/identity/validate'

const createMsgs = {
  emailRequired: 'email required',
  emailInvalid: 'email invalid',
  passwordRequired: 'password required',
  passwordTooShort: 'password short',
  rolesRequired: 'roles required',
}

const passwordMsgs = {
  currentRequired: 'current required',
  newRequired: 'new required',
  newTooShort: 'new short',
  confirmMismatch: 'mismatch',
}

describe('validateCreateUser', () => {
  it('accepts a valid payload', () => {
    expect(
      validateCreateUser('ops@karam-alarab.com', 'password-1234', ['operations'], createMsgs),
    ).toEqual({})
  })

  it('rejects empty and invalid email', () => {
    expect(validateCreateUser('', 'password-1234', ['operations'], createMsgs).email).toBe(
      'email required',
    )
    expect(validateCreateUser('not-an-email', 'password-1234', ['operations'], createMsgs).email).toBe(
      'email invalid',
    )
  })

  it('rejects short password and empty roles', () => {
    const errors = validateCreateUser('a@b.co', 'short', [], createMsgs)
    expect(errors.password).toBe('password short')
    expect(errors.roles).toBe('roles required')
  })

  it('boundary: password length 11 vs 12', () => {
    expect(
      validateCreateUser('a@b.co', '12345678901', ['operations'], createMsgs).password,
    ).toBe('password short')
    expect(
      validateCreateUser('a@b.co', '123456789012', ['operations'], createMsgs).password,
    ).toBeUndefined()
  })
})

describe('validateChangePassword', () => {
  it('requires current and matching confirmation', () => {
    const errors = validateChangePassword('', 'password-1234', 'other-password', passwordMsgs)
    expect(errors.current_password).toBe('current required')
    expect(errors.confirm_password).toBe('mismatch')
  })

  it('accepts matching long passwords', () => {
    expect(
      validateChangePassword('old-password-12', 'new-password-12', 'new-password-12', passwordMsgs),
    ).toEqual({})
  })
})

describe('validatePermissionName', () => {
  it('accepts resource:action', () => {
    expect(
      validatePermissionName('work:export', { required: 'req', invalid: 'bad' }),
    ).toBeUndefined()
  })

  it('rejects empty and malformed names', () => {
    expect(validatePermissionName('  ', { required: 'req', invalid: 'bad' })).toBe('req')
    expect(validatePermissionName('no-colon', { required: 'req', invalid: 'bad' })).toBe('bad')
    expect(validatePermissionName('work:bad-char!', { required: 'req', invalid: 'bad' })).toBe(
      'bad',
    )
  })

  it('normalizes case so Work:Export is accepted', () => {
    expect(
      validatePermissionName('Work:Export', { required: 'req', invalid: 'bad' }),
    ).toBeUndefined()
  })
})
