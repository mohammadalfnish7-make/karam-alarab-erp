const DUBAI = 'Asia/Dubai'

/** Format a UTC ISO timestamp for display in Asia/Dubai. */
export function formatDubaiDateTime(
  iso: string,
  locale: string = 'en',
): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-GB', {
    timeZone: DUBAI,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/** Format a calendar date (YYYY-MM-DD) for display. */
export function formatDubaiDate(
  dueOn: string | null | undefined,
  locale: string = 'en',
): string {
  if (!dueOn) {
    return ''
  }
  const date = new Date(`${dueOn}T12:00:00Z`)
  if (Number.isNaN(date.getTime())) {
    return dueOn
  }
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-GB', {
    timeZone: DUBAI,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

/** Today's calendar date in Asia/Dubai as YYYY-MM-DD. */
export function todayDubai(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: DUBAI,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}
