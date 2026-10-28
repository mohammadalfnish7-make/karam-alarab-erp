const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export interface CreateUserFieldErrors {
  email?: string
  password?: string
  roles?: string
}

export interface ChangePasswordFieldErrors {
  current_password?: string
  new_password?: string
  confirm_password?: string
}

export function validateCreateUser(
  email: string,
  password: string,
  roles: readonly string[],
  messages: {
    emailRequired: string
    emailInvalid: string
    passwordRequired: string
    passwordTooShort: string
    rolesRequired: string
  },
): CreateUserFieldErrors {
  const errors: CreateUserFieldErrors = {}
  const trimmed = email.trim()
  if (!trimmed) {
    errors.email = messages.emailRequired
  } else if (!EMAIL_PATTERN.test(trimmed)) {
    errors.email = messages.emailInvalid
  }
  if (!password) {
    errors.password = messages.passwordRequired
  } else if (password.length < 12) {
    errors.password = messages.passwordTooShort
  }
  if (roles.length === 0) {
    errors.roles = messages.rolesRequired
  }
  return errors
}

export function validateChangePassword(
  current: string,
  next: string,
  confirm: string,
  messages: {
    currentRequired: string
    newRequired: string
    newTooShort: string
    confirmMismatch: string
  },
): ChangePasswordFieldErrors {
  const errors: ChangePasswordFieldErrors = {}
  if (!current) {
    errors.current_password = messages.currentRequired
  }
  if (!next) {
    errors.new_password = messages.newRequired
  } else if (next.length < 12) {
    errors.new_password = messages.newTooShort
  }
  if (next !== confirm) {
    errors.confirm_password = messages.confirmMismatch
  }
  return errors
}

export function validatePermissionName(
  value: string,
  messages: { required: string; invalid: string },
): string | undefined {
  const trimmed = value.trim().toLowerCase()
  if (!trimmed) {
    return messages.required
  }
  if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(trimmed)) {
    return messages.invalid
  }
  return undefined
}
