import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission } from '@/features/auth'
import {
  RoleChecklist,
  useCreateUser,
  useRoles,
  useUpdateUser,
  useUsers,
  validateCreateUser,
} from '@/features/identity'
import { isApiError } from '@/shared/api/http-client'
import type { User } from '@/shared/api/types'
import { initialsFromEmail } from '@/shared/lib/initials'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Pagination } from '@/shared/ui/Pagination'
import { RoleBadge } from '@/shared/ui/RoleBadge'
import { SlideOver } from '@/shared/ui/SlideOver'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { TextField } from '@/shared/ui/TextField'

const PAGE_SIZE = 25

export function UsersPage() {
  return (
    <RequirePermission permission={Permissions.identityRead}>
      <UsersPageInner />
    </RequirePermission>
  )
}

function UsersPageInner() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page') ?? '1') || 1)
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)

  const usersQuery = useUsers(page, PAGE_SIZE)
  const rolesQuery = useRoles()

  const filtered = useMemo(() => {
    const rows = usersQuery.data?.data ?? []
    const q = search.trim().toLowerCase()
    return rows.filter((u) => {
      if (!showInactive && !u.is_active) {
        return false
      }
      if (q && !u.email.toLowerCase().includes(q)) {
        return false
      }
      return true
    })
  }, [usersQuery.data?.data, search, showInactive])

  const total = usersQuery.data?.total ?? 0
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const to = Math.min(page * PAGE_SIZE, total)

  return (
    <PageFrame
      title={t('identity.users.title')}
      subtitle={t('identity.users.subtitle')}
      actions={
        <RequirePermission permission={Permissions.identityUpdate} hide>
          <Button onClick={() => setCreateOpen(true)}>{t('identity.users.create')}</Button>
        </RequirePermission>
      }
      toolbar={
        <>
          <TextField
            name="user-search"
            compact
            label={t('identity.users.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('identity.users.searchPlaceholder')}
            className="w-72"
          />
          <label className="flex items-center gap-2 text-sm text-[var(--color-text)]">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            {t('identity.users.showInactive')}
          </label>
        </>
      }
    >

      {usersQuery.isLoading ? (
        <p className="mt-8 text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}

      {usersQuery.isError ? (
        <div className="mt-8">
          <Alert tone="error" role="alert">
            {t('identity.users.loadError')}
          </Alert>
          <Button className="mt-3" variant="secondary" onClick={() => void usersQuery.refetch()}>
            {t('common.retry')}
          </Button>
        </div>
      ) : null}

      {!usersQuery.isLoading && !usersQuery.isError && filtered.length === 0 ? (
        <div className="mt-16 flex flex-col items-center text-center">
          <p className="text-lg font-semibold text-[var(--color-text)]">
            {t('identity.users.emptyTitle')}
          </p>
          <p className="mt-1 text-sm text-[var(--color-muted)]">{t('identity.users.emptyBody')}</p>
          <RequirePermission permission={Permissions.identityUpdate} hide>
            <Button className="mt-4" onClick={() => setCreateOpen(true)}>
              {t('identity.users.create')}
            </Button>
          </RequirePermission>
        </div>
      ) : null}

      {filtered.length > 0 ? (
        <div className="overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full table-fixed text-left text-sm">
            <thead className="border-b border-[var(--color-border)] bg-[var(--color-wash)] text-xs uppercase tracking-wide text-[var(--color-muted)]">
              <tr>
                <th className="w-[38%] px-3 py-2 font-medium">{t('identity.users.colEmail')}</th>
                <th className="w-[28%] px-3 py-2 font-medium">{t('identity.users.colRoles')}</th>
                <th className="w-[16%] px-3 py-2 font-medium">{t('identity.users.colStatus')}</th>
                <th className="w-[18%] px-3 py-2 text-right font-medium">{t('identity.users.colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((user) => (
                <tr key={user.id} className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-wash)]">
                  <td className="px-3 py-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <span
                        aria-hidden
                        className="inline-flex size-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-wash)] text-[11px] font-semibold text-[var(--color-primary)]"
                      >
                        {initialsFromEmail(user.email)}
                      </span>
                      <span className="truncate font-medium text-[var(--color-text)]">{user.email}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <RoleBadge
                          key={role}
                          name={role}
                          label={t(`identity.roleLabels.${role}`, { defaultValue: role })}
                        />
                      ))}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <StatusBadge
                      active={user.is_active}
                      activeLabel={t('identity.users.active')}
                      inactiveLabel={t('identity.users.inactive')}
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    <RequirePermission permission={Permissions.identityUpdate} hide>
                      <Button variant="ghost" onClick={() => setEditing(user)}>
                        {t('identity.users.edit')}
                      </Button>
                    </RequirePermission>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {total > 0 ? (
        <div className="mt-4">
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            summary={t('identity.users.showing', { from, to, total })}
            prevLabel={t('common.prev')}
            nextLabel={t('common.next')}
            onPageChange={(next) => {
              const nextParams = new URLSearchParams(params)
              nextParams.set('page', String(next))
              setParams(nextParams)
            }}
          />
        </div>
      ) : null}

      <CreateUserPanel
        open={createOpen}
        roles={rolesQuery.data ?? []}
        onClose={() => setCreateOpen(false)}
      />
      <EditUserPanel
        user={editing}
        roles={rolesQuery.data ?? []}
        onClose={() => setEditing(null)}
      />
    </PageFrame>
  )
}

function CreateUserPanel({
  open,
  roles,
  onClose,
}: {
  open: boolean
  roles: { name: string; is_superuser: boolean; permissions: string[] }[]
  onClose: () => void
}) {
  const { t } = useTranslation()
  const create = useCreateUser()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRoles, setSelectedRoles] = useState<string[]>(['operations'])
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string
    password?: string
    roles?: string
  }>({})
  const [formError, setFormError] = useState<string | null>(null)

  function reset(): void {
    setEmail('')
    setPassword('')
    setSelectedRoles(['operations'])
    setFieldErrors({})
    setFormError(null)
  }

  async function onSubmit(): Promise<void> {
    setFormError(null)
    const errors = validateCreateUser(email, password, selectedRoles, {
      emailRequired: t('identity.users.emailRequired'),
      emailInvalid: t('identity.users.emailInvalid'),
      passwordRequired: t('identity.users.passwordRequired'),
      passwordTooShort: t('identity.users.passwordTooShort'),
      rolesRequired: t('identity.users.rolesRequired'),
    })
    setFieldErrors(errors)
    if (errors.email || errors.password || errors.roles) {
      return
    }
    try {
      await create.mutateAsync({
        email: email.trim(),
        password,
        roles: selectedRoles,
      })
      reset()
      onClose()
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        setFieldErrors({ email: t('identity.users.emailExists') })
        return
      }
      setFormError(isApiError(error) ? error.message : t('identity.users.saveFailed'))
    }
  }

  return (
    <SlideOver
      open={open}
      title={t('identity.users.createTitle')}
      onClose={() => {
        reset()
        onClose()
      }}
      footer={
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              reset()
              onClose()
            }}
          >
            {t('common.cancel')}
          </Button>
          <Button disabled={create.isPending} onClick={() => void onSubmit()}>
            {create.isPending ? t('identity.users.saving') : t('identity.users.create')}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <TextField
          name="create-email"
          type="email"
          autoComplete="off"
          label={t('identity.users.email')}
          value={email}
          error={fieldErrors.email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={create.isPending}
        />
        <TextField
          name="create-password"
          type="password"
          autoComplete="new-password"
          label={t('identity.users.tempPassword')}
          value={password}
          error={fieldErrors.password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={create.isPending}
        />
        <p className="text-xs text-[var(--color-muted)]">{t('identity.users.passwordHint')}</p>
        <RoleChecklist
          roles={roles}
          selected={selectedRoles}
          onChange={setSelectedRoles}
          error={fieldErrors.roles}
          disabled={create.isPending}
        />
        {formError ? (
          <Alert tone="error" role="alert">
            {formError}
          </Alert>
        ) : null}
      </div>
    </SlideOver>
  )
}

function EditUserPanel({
  user,
  roles,
  onClose,
}: {
  user: User | null
  roles: { name: string; is_superuser: boolean; permissions: string[] }[]
  onClose: () => void
}) {
  const { t } = useTranslation()
  const update = useUpdateUser()
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [isActive, setIsActive] = useState(true)
  const [rolesError, setRolesError] = useState<string | undefined>()
  const [formError, setFormError] = useState<string | null>(null)

  const open = Boolean(user)

  useEffect(() => {
    if (!user) {
      return
    }
    setSelectedRoles([...user.roles])
    setIsActive(user.is_active)
    setRolesError(undefined)
    setFormError(null)
  }, [user])

  async function onSubmit(): Promise<void> {
    if (!user) {
      return
    }
    setFormError(null)
    if (selectedRoles.length === 0) {
      setRolesError(t('identity.users.rolesRequired'))
      return
    }
    setRolesError(undefined)
    try {
      await update.mutateAsync({
        id: user.id,
        body: { roles: selectedRoles, is_active: isActive },
      })
      onClose()
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        setFormError(t('identity.users.lastAdmin'))
        return
      }
      setFormError(isApiError(error) ? error.message : t('identity.users.saveFailed'))
    }
  }

  return (
    <SlideOver
      open={open}
      title={t('identity.users.editTitle')}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button disabled={update.isPending} onClick={() => void onSubmit()}>
            {update.isPending ? t('identity.users.saving') : t('common.save')}
          </Button>
        </div>
      }
    >
      {user ? (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <span
              aria-hidden
              className="inline-flex size-10 items-center justify-center rounded-full bg-[var(--color-wash)] text-sm font-semibold text-[var(--color-primary)]"
            >
              {initialsFromEmail(user.email)}
            </span>
            <div>
              <p className="font-medium text-[var(--color-text)]">{user.email}</p>
              <p className="text-xs text-[var(--color-muted)]">{user.id}</p>
            </div>
          </div>
          <RoleChecklist
            roles={roles}
            selected={selectedRoles}
            onChange={setSelectedRoles}
            error={rolesError}
            disabled={update.isPending}
          />
          <label className="flex items-center justify-between gap-3 text-sm text-[var(--color-text)]">
            <span>{t('identity.users.accountStatus')}</span>
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              disabled={update.isPending}
              aria-label={t('identity.users.accountStatus')}
            />
          </label>
          {formError ? (
            <Alert tone="error" role="alert">
              {formError}
            </Alert>
          ) : null}
        </div>
      ) : null}
    </SlideOver>
  )
}
