export interface LoginFieldErrors {
  email?: string
  password?: string
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Client-side UX checks only. FastAPI DTOs remain authoritative. */
export function validateLoginFields(
  email: string,
  password: string,
  messages: {
    emailRequired: string
    emailInvalid: string
    passwordRequired: string
  },
): LoginFieldErrors {
  const errors: LoginFieldErrors = {}
  const trimmed = email.trim()
  if (!trimmed) {
    errors.email = messages.emailRequired
  } else if (!EMAIL_PATTERN.test(trimmed)) {
    errors.email = messages.emailInvalid
  }
  if (!password) {
    errors.password = messages.passwordRequired
  }
  return errors
}
