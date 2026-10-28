/** Human label from an email local-part when the API has no display name. */
export function displayNameFromEmail(email: string): string | null {
  const local = (email.split('@')[0] ?? '').trim()
  if (!local) return null
  const parts = local.split(/[._+-]+/).filter(Boolean)
  if (parts.length === 0) return null
  // Test-looking locals (dup.1793171550768) should not become fake names.
  const looksSynthetic = parts.some(
    (part) => /^\d+$/.test(part) || /\d{6,}/.test(part),
  )
  if (looksSynthetic) return null
  return parts
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
}

const AVATAR_TONES = [
  'bg-[#DBEAFE] text-[#1E40AF]',
  'bg-[#D1FAE5] text-[#065F46]',
  'bg-[#FEF3C7] text-[#92400E]',
  'bg-[#FFE4E6] text-[#9F1239]',
  'bg-[#E0E7FF] text-[#3730A3]',
  'bg-[#CCFBF1] text-[#115E59]',
] as const

/** Stable avatar color class from an id/email string. */
export function avatarTone(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i) * (i + 1)) % AVATAR_TONES.length
  }
  return AVATAR_TONES[hash] ?? AVATAR_TONES[0]
}
