/** Two-letter initials from an email local-part or display name. */
export function initialsFromEmail(email: string): string {
  const local = email.split('@')[0] ?? email
  const parts = local.split(/[._-]+/).filter(Boolean)
  if (parts.length >= 2) {
    const a = parts[0]?.[0] ?? ''
    const b = parts[1]?.[0] ?? ''
    return `${a}${b}`.toUpperCase()
  }
  return local.slice(0, 2).toUpperCase() || '?'
}
