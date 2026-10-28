import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react'
import { useTranslation } from 'react-i18next'

import { initialsFromEmail } from '@/shared/lib/initials'
import { avatarTone, displayNameFromEmail } from '@/shared/lib/person-label'

const MAX_VISIBLE = 6
const ROW_PX = 48
const DEBOUNCE_MS = 200
const DEFAULT_RECENT_KEY = 'karam.people.recent'

export interface PersonOption {
  id: string
  email: string
  /** Optional display name; falls back to a derived email label. */
  name?: string | null
}

interface PersonPickerBaseProps {
  people: PersonOption[]
  excludeIds?: string[]
  disabled?: boolean
  label?: ReactNode
  hint?: string
  required?: boolean
  id?: string
  recentStorageKey?: string
  placeholder?: string
  searchPlaceholder?: string
  emptyLabel?: string
  /** Puts this person first under Suggested when present. */
  preferIds?: string[]
}

export interface SinglePersonPickerProps extends PersonPickerBaseProps {
  mode?: 'single'
  value: string | null
  onChange: (userId: string | null) => void
  clearable?: boolean
  /** When set, shows an “Assign to me” control beside the label. */
  currentUserId?: string
}

export interface MultiPersonPickerProps extends PersonPickerBaseProps {
  mode: 'multiple'
  value: string[]
  onToggle: (userId: string, selected: boolean) => void
  showSelectedCount?: boolean
  allowClearAll?: boolean
}

export type PersonPickerProps = SinglePersonPickerProps | MultiPersonPickerProps

function readRecentIds(key: string): string[] {
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed)
      ? parsed.filter((id): id is string => typeof id === 'string')
      : []
  } catch {
    return []
  }
}

function pushRecentId(key: string, userId: string): void {
  const next = [userId, ...readRecentIds(key).filter((id) => id !== userId)].slice(
    0,
    8,
  )
  try {
    sessionStorage.setItem(key, JSON.stringify(next))
  } catch {
    /* ignore quota */
  }
}

function personLabel(person: PersonOption): string {
  return person.name?.trim() || displayNameFromEmail(person.email) || person.email
}

function personMatches(person: PersonOption, q: string): boolean {
  const name = personLabel(person).toLowerCase()
  return person.email.toLowerCase().includes(q) || name.includes(q)
}

export function PersonPicker(props: PersonPickerProps) {
  const { t } = useTranslation()
  const isMulti = props.mode === 'multiple'
  const recentKey = props.recentStorageKey ?? DEFAULT_RECENT_KEY
  const excludeIds = props.excludeIds ?? []
  const disabled = props.disabled ?? false
  const autoId = useId()
  const searchId = props.id ?? `person-picker-${autoId}`
  const rootRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const [recentIds, setRecentIds] = useState(() => readRecentIds(recentKey))

  const selectedIds = isMulti
    ? props.value
    : props.value
      ? [props.value]
      : []

  useEffect(() => {
    if (query === debouncedQuery) {
      setSearching(false)
      return
    }
    setSearching(true)
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query)
      setSearching(false)
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [query, debouncedQuery])

  useEffect(() => {
    function onPointerDown(event: MouseEvent): void {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [])

  useEffect(() => {
    if (open && !isMulti) {
      window.setTimeout(() => searchRef.current?.focus(), 0)
    }
  }, [open, isMulti])

  const byId = useMemo(() => {
    const map = new Map<string, PersonOption>()
    for (const person of props.people) map.set(person.id, person)
    return map
  }, [props.people])

  const excluded = useMemo(() => new Set(excludeIds), [excludeIds])

  const available = useMemo(
    () => props.people.filter((person) => !excluded.has(person.id)),
    [props.people, excluded],
  )

  const selectedPeople = useMemo(
    () =>
      selectedIds
        .map((id) => byId.get(id))
        .filter((person): person is PersonOption => Boolean(person)),
    [selectedIds, byId],
  )

  const preferSet = useMemo(
    () => new Set(props.preferIds ?? []),
    [props.preferIds],
  )

  const results = useMemo(() => {
    const q = debouncedQuery.trim().toLowerCase()
    const pool = isMulti
      ? available.filter((person) => !selectedIds.includes(person.id))
      : available
    const matches = q ? pool.filter((person) => personMatches(person, q)) : pool
    const recentSet = new Set(recentIds)
    return [...matches]
      .sort((a, b) => {
        const aPref = preferSet.has(a.id) ? 0 : 1
        const bPref = preferSet.has(b.id) ? 0 : 1
        if (aPref !== bPref) return aPref - bPref
        const aRecent = recentSet.has(a.id) ? 0 : 1
        const bRecent = recentSet.has(b.id) ? 0 : 1
        if (aRecent !== bRecent) return aRecent - bRecent
        return personLabel(a).localeCompare(personLabel(b))
      })
      .slice(0, 40)
  }, [
    available,
    selectedIds,
    debouncedQuery,
    recentIds,
    isMulti,
    preferSet,
  ])

  useEffect(() => {
    setHighlight(0)
  }, [debouncedQuery, open, results.length])

  useEffect(() => {
    if (!open) return
    const el = listRef.current?.querySelector<HTMLElement>(
      `[data-person-index="${highlight}"]`,
    )
    el?.scrollIntoView({ block: 'nearest' })
  }, [highlight, open])

  const showDropdown = open && !disabled
  const showResults =
    showDropdown &&
    (isMulti
      ? debouncedQuery.trim().length > 0 ||
        results.length > 0 ||
        available.length === 0
      : true)

  function remember(userId: string): void {
    pushRecentId(recentKey, userId)
    setRecentIds(readRecentIds(recentKey))
  }

  function selectPerson(userId: string): void {
    if (disabled) return
    if (props.mode === 'multiple') {
      props.onToggle(userId, true)
      remember(userId)
      setQuery('')
      setDebouncedQuery('')
      return
    }
    props.onChange(userId)
    remember(userId)
    setOpen(false)
    setQuery('')
    setDebouncedQuery('')
  }

  function removePerson(userId: string): void {
    if (disabled) return
    if (props.mode === 'multiple') {
      props.onToggle(userId, false)
      return
    }
    props.onChange(null)
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      return
    }
    if (!showResults || results.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlight((i) => Math.min(i + 1, results.length - 1))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlight((i) => Math.max(i - 1, 0))
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      const person = results[highlight]
      if (person) selectPerson(person.id)
    }
  }

  const selectedSingle = !isMulti ? selectedPeople[0] : undefined
  const placeholder =
    props.placeholder ?? t('peoplePicker.placeholder')
  const searchPlaceholder =
    props.searchPlaceholder ?? t('peoplePicker.searchPlaceholder')
  const emptyLabel = props.emptyLabel ?? t('peoplePicker.empty')

  return (
    <div ref={rootRef} className="block text-sm">
      {props.label ||
      props.hint ||
      (!isMulti && props.currentUserId) ? (
        <div className="mb-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            {props.label ? (
              <p className="text-[15px] font-semibold text-[var(--color-text)]">
                {props.label}
                {props.required ? (
                  <span className="text-[var(--color-danger)]" aria-hidden>
                    {' '}
                    *
                  </span>
                ) : null}
              </p>
            ) : (
              <span />
            )}
            {'currentUserId' in props && props.currentUserId && !disabled ? (
              <button
                type="button"
                className="text-xs font-medium text-[var(--color-primary)] hover:underline"
                onClick={() => {
                  const meId =
                    'currentUserId' in props ? props.currentUserId : undefined
                  if (meId) selectPerson(meId)
                }}
              >
                {t('peoplePicker.assignToMe')}
              </button>
            ) : null}
          </div>
          {props.hint ? (
            <p className="mt-1 text-[13px] leading-snug text-[var(--color-muted)]">
              {props.hint}
            </p>
          ) : null}
        </div>
      ) : null}

      {isMulti ? (
        <>
          {(props.showSelectedCount ?? true) ? (
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-[var(--color-muted)]">
                {t('peoplePicker.selectedCount', { count: selectedIds.length })}
              </span>
              {(props.allowClearAll ?? true) && selectedIds.length > 0 ? (
                <button
                  type="button"
                  className="text-xs font-medium text-[var(--color-primary)] hover:underline"
                  disabled={disabled}
                  onClick={() => {
                    for (const id of [...selectedIds]) removePerson(id)
                  }}
                >
                  {t('peoplePicker.clearAll')}
                </button>
              ) : null}
            </div>
          ) : null}
          {selectedPeople.length > 0 ? (
            <ul className="mb-3 flex flex-wrap gap-2">
              {selectedPeople.map((person) => {
                const name = personLabel(person)
                return (
                  <li key={person.id}>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-[#EEF2FF] py-1 pr-1.5 pl-1 text-[13px] font-medium text-[#3730A3]">
                      <PersonAvatar person={person} size="sm" />
                      <span className="max-w-[10rem] truncate">{name}</span>
                      <button
                        type="button"
                        aria-label={t('peoplePicker.removeChip', { name })}
                        disabled={disabled}
                        className="grid size-6 place-items-center rounded-full text-[#3730A3] hover:bg-white/70"
                        onClick={() => removePerson(person.id)}
                      >
                        ×
                      </button>
                    </span>
                  </li>
                )
              })}
            </ul>
          ) : null}
        </>
      ) : null}

      <div className="relative">
        {!isMulti ? (
          <button
            type="button"
            id={searchId}
            disabled={disabled}
            aria-haspopup="listbox"
            aria-expanded={open}
            className="flex min-h-11 w-full items-center gap-3 rounded-[10px] border border-[#E5E7EB] bg-[var(--color-surface)] px-3 py-2 text-left outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--color-primary)_25%,transparent)] disabled:opacity-60"
            onClick={() => setOpen((v) => !v)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                setOpen(true)
              }
            }}
          >
            {selectedSingle ? (
              <>
                <PersonAvatar person={selectedSingle} size="md" />
                <span className="min-w-0 flex-1">
                  {displayNameFromEmail(selectedSingle.email) ||
                  selectedSingle.name ? (
                    <>
                      <span className="block truncate text-sm font-medium text-[var(--color-text)]">
                        {personLabel(selectedSingle)}
                      </span>
                      <span className="block truncate text-xs text-[var(--color-muted)]">
                        {selectedSingle.email}
                      </span>
                    </>
                  ) : (
                    <span className="block truncate text-sm font-medium text-[var(--color-text)]">
                      {selectedSingle.email}
                    </span>
                  )}
                </span>
              </>
            ) : (
              <span className="flex-1 text-sm text-[var(--color-muted)]">
                {placeholder}
              </span>
            )}
            <ChevronIcon open={open} />
          </button>
        ) : (
          <>
            <label className="sr-only" htmlFor={searchId}>
              {searchPlaceholder}
            </label>
            <div className="relative">
              <span
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[var(--color-muted)]"
              >
                <SearchIcon />
              </span>
              <input
                ref={searchRef}
                id={searchId}
                type="search"
                autoComplete="off"
                disabled={disabled}
                value={query}
                placeholder={searchPlaceholder}
                className="min-h-11 w-full rounded-[10px] border border-[#E5E7EB] bg-[var(--color-surface)] py-2.5 pr-10 pl-10 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--color-primary)_25%,transparent)]"
                onFocus={() => setOpen(true)}
                onChange={(e) => {
                  setQuery(e.target.value)
                  setOpen(true)
                }}
                onKeyDown={onSearchKeyDown}
              />
              <SearchTrailing
                searching={searching}
                query={query}
                clearLabel={t('peoplePicker.clearSearch')}
                onClear={() => {
                  setQuery('')
                  setDebouncedQuery('')
                  setSearching(false)
                  setOpen(true)
                  searchRef.current?.focus()
                }}
              />
            </div>
          </>
        )}

        {showResults ? (
          <div
            className={[
              'absolute z-30 w-full overflow-hidden rounded-[10px] border border-[#E5E7EB] bg-[var(--color-surface)] shadow-[0_8px_24px_rgba(15,23,42,0.08)]',
              isMulti ? 'mt-2' : 'mt-1.5',
            ].join(' ')}
            role="listbox"
            aria-label={
              typeof props.label === 'string'
                ? props.label
                : t('peoplePicker.placeholder')
            }
          >
            {!isMulti ? (
              <div className="relative border-b border-[#E5E7EB] p-2">
                <span
                  aria-hidden
                  className="pointer-events-none absolute top-1/2 left-5 -translate-y-1/2 text-[var(--color-muted)]"
                >
                  <SearchIcon />
                </span>
                <input
                  ref={searchRef}
                  type="search"
                  autoComplete="off"
                  value={query}
                  placeholder={searchPlaceholder}
                  className="min-h-10 w-full rounded-lg border border-[#E5E7EB] bg-[var(--color-surface)] py-2 pr-9 pl-9 text-sm outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--color-primary)_25%,transparent)]"
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={onSearchKeyDown}
                />
                <SearchTrailing
                  searching={searching}
                  query={query}
                  clearLabel={t('peoplePicker.clearSearch')}
                  onClear={() => {
                    setQuery('')
                    setDebouncedQuery('')
                    setSearching(false)
                    searchRef.current?.focus()
                  }}
                />
              </div>
            ) : null}

            {!debouncedQuery.trim() && results.length > 0 ? (
              <p className="border-b border-[#E5E7EB] px-3 py-2 text-[11px] font-semibold tracking-wide text-[var(--color-muted)] uppercase">
                {t('peoplePicker.suggested')}
              </p>
            ) : null}

            <div className="relative">
              <div
                className="person-picker-scroll overflow-y-auto"
                style={{ maxHeight: MAX_VISIBLE * ROW_PX }}
              >
                {results.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-[var(--color-muted)]">
                    {available.length === 0
                      ? emptyLabel
                      : debouncedQuery.trim()
                        ? t('peoplePicker.noMatchQuery', {
                            query: debouncedQuery.trim(),
                          })
                        : t('peoplePicker.noMatch')}
                  </p>
                ) : (
                  <ul ref={listRef}>
                    {results.map((person, index) => {
                      const selected = selectedIds.includes(person.id)
                      const name = displayNameFromEmail(person.email) || person.name
                      const active = index === highlight
                      return (
                        <li key={person.id}>
                          <button
                            type="button"
                            role="option"
                            data-person-index={index}
                            aria-selected={selected}
                            disabled={disabled}
                            className={[
                              'flex min-h-12 w-full items-center gap-3 px-3 py-2.5 text-left transition-colors',
                              selected || active
                                ? 'bg-[#EEF2FF]'
                                : 'hover:bg-[#F3F4F6]',
                            ].join(' ')}
                            onMouseEnter={() => setHighlight(index)}
                            onClick={() => {
                              if (isMulti && selected) {
                                removePerson(person.id)
                              } else {
                                selectPerson(person.id)
                              }
                            }}
                          >
                            <PersonAvatar person={person} size="md" />
                            <span className="min-w-0 flex-1">
                              {name ? (
                                <>
                                  <span className="block truncate text-sm font-medium text-[var(--color-text)]">
                                    {personLabel(person)}
                                  </span>
                                  <span className="block truncate text-xs text-[var(--color-muted)]">
                                    {person.email}
                                  </span>
                                </>
                              ) : (
                                <span className="block truncate text-sm font-medium text-[var(--color-text)]">
                                  {person.email}
                                </span>
                              )}
                            </span>
                            <span
                              aria-hidden
                              className={[
                                'grid size-5 shrink-0 place-items-center rounded-full border text-[11px] font-bold',
                                selected
                                  ? 'border-[#4338CA] bg-[#4338CA] text-white'
                                  : 'border-[#D1D5DB] bg-white text-transparent',
                              ].join(' ')}
                            >
                              ✓
                            </span>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
              {results.length > MAX_VISIBLE ? (
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-[var(--color-surface)] to-transparent"
                />
              ) : null}
            </div>

            {!isMulti &&
            'clearable' in props &&
            props.clearable &&
            props.value ? (
              <div className="border-t border-[#E5E7EB] p-2">
                <button
                  type="button"
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-[var(--color-muted)] hover:bg-[#F3F4F6]"
                  onClick={() => {
                    removePerson(props.value as string)
                    setOpen(false)
                  }}
                >
                  {t('peoplePicker.clearSelection')}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <style>{`
        .person-picker-scroll {
          scrollbar-width: thin;
          scrollbar-color: #D1D5DB transparent;
        }
        .person-picker-scroll::-webkit-scrollbar {
          width: 6px;
        }
        .person-picker-scroll::-webkit-scrollbar-thumb {
          background: #D1D5DB;
          border-radius: 999px;
        }
        .person-picker-scroll::-webkit-scrollbar-track {
          background: transparent;
        }
      `}</style>
    </div>
  )
}

function PersonAvatar({
  person,
  size,
}: {
  person: PersonOption
  size: 'sm' | 'md'
}) {
  const dim = size === 'sm' ? 'size-6 text-[10px]' : 'size-8 text-xs'
  return (
    <span
      aria-hidden
      className={`grid shrink-0 place-items-center rounded-full font-semibold ${dim} ${avatarTone(person.id)}`}
    >
      {initialsFromEmail(person.name?.trim() || person.email)}
    </span>
  )
}

function SearchTrailing({
  searching,
  query,
  clearLabel,
  onClear,
}: {
  searching: boolean
  query: string
  clearLabel: string
  onClear: () => void
}) {
  if (searching) {
    return (
      <span aria-hidden className="absolute top-1/2 right-3 -translate-y-1/2">
        <Spinner />
      </span>
    )
  }
  if (!query) return null
  return (
    <button
      type="button"
      aria-label={clearLabel}
      className="absolute top-1/2 right-2.5 grid size-7 -translate-y-1/2 place-items-center rounded-full text-[var(--color-muted)] hover:bg-[var(--color-wash)] hover:text-[var(--color-text)]"
      onClick={onClear}
    >
      ×
    </button>
  )
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <path
        d="M20 20l-3.5-3.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={[
        'shrink-0 text-[var(--color-muted)] transition-transform',
        open ? 'rotate-180' : '',
      ].join(' ')}
    >
      <path
        d="M6 9l6 6 6-6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function Spinner() {
  return (
    <span className="inline-block size-4 animate-spin rounded-full border-2 border-[var(--color-muted)] border-t-transparent" />
  )
}
