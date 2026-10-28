import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Permissions, RequirePermission } from '@/features/auth'
import {
  PermissionChecklist,
  usePermissionsCatalog,
  useRegisterPermissions,
  useRoles,
  useSetRolePermissions,
  validatePermissionName,
} from '@/features/identity'
import { isApiError } from '@/shared/api/http-client'
import type { Role } from '@/shared/api/types'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog'
import { PageFrame } from '@/shared/ui/PageFrame'
import { RoleBadge } from '@/shared/ui/RoleBadge'
import { SlideOver } from '@/shared/ui/SlideOver'
import { TextField } from '@/shared/ui/TextField'

export function RolesPage() {
  return (
    <RequirePermission permission={Permissions.identityRead}>
      <RolesPageInner />
    </RequirePermission>
  )
}

function RolesPageInner() {
  const { t } = useTranslation()
  const rolesQuery = useRoles()
  const permsQuery = usePermissionsCatalog()
  const [editing, setEditing] = useState<Role | null>(null)
  const [registerOpen, setRegisterOpen] = useState(false)

  return (
    <PageFrame
      title={t('identity.roles.title')}
      subtitle={t('identity.roles.subtitle')}
      actions={
        <RequirePermission permission={Permissions.identityUpdate} hide>
          <Button variant="secondary" onClick={() => setRegisterOpen(true)}>
            {t('identity.roles.registerPermission')}
          </Button>
        </RequirePermission>
      }
    >

      {rolesQuery.isLoading ? (
        <p className="mt-8 text-sm text-[var(--color-muted)]">{t('shell.loading')}</p>
      ) : null}

      {rolesQuery.isError ? (
        <div className="mt-8">
          <Alert tone="error" role="alert">
            {t('identity.roles.loadError')}
          </Alert>
          <Button className="mt-3" variant="secondary" onClick={() => void rolesQuery.refetch()}>
            {t('common.retry')}
          </Button>
        </div>
      ) : null}

      {rolesQuery.data && rolesQuery.data.length > 0 ? (
        <div className="overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full table-fixed text-left text-sm">
            <thead className="border-b border-[var(--color-border)] bg-[var(--color-wash)] text-xs uppercase tracking-wide text-[var(--color-muted)]">
              <tr>
                <th className="w-[16%] px-3 py-2 font-medium">{t('identity.roles.colName')}</th>
                <th className="w-[12%] px-3 py-2 font-medium">{t('identity.roles.colSuperuser')}</th>
                <th className="w-[12%] px-3 py-2 font-medium">{t('identity.roles.colCount')}</th>
                <th className="w-[36%] px-3 py-2 font-medium">{t('identity.roles.colDescription')}</th>
                <th className="w-[24%] px-3 py-2 text-right font-medium">{t('identity.users.colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {rolesQuery.data.map((role) => (
                <tr key={role.name} className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-wash)]">
                  <td className="px-3 py-2">
                    <RoleBadge
                      name={role.name}
                      label={t(`identity.roleLabels.${role.name}`, { defaultValue: role.name })}
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {role.is_superuser ? t('common.yes') : t('common.no')}
                  </td>
                  <td className="px-3 py-2">{role.permissions.length}</td>
                  <td className="truncate px-3 py-2 text-[var(--color-muted)]">
                    {t(`identity.roleDescriptions.${role.name}`, { defaultValue: '—' })}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    <RequirePermission permission={Permissions.identityUpdate} hide>
                      <Button variant="ghost" onClick={() => setEditing(role)}>
                        {t('identity.roles.editPermissions')}
                      </Button>
                    </RequirePermission>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <EditPermissionsPanel
        role={editing}
        catalog={permsQuery.data ?? []}
        onClose={() => setEditing(null)}
      />
      <RegisterPermissionDialog open={registerOpen} onClose={() => setRegisterOpen(false)} />
    </PageFrame>
  )
}

function EditPermissionsPanel({
  role,
  catalog,
  onClose,
}: {
  role: Role | null
  catalog: string[]
  onClose: () => void
}) {
  const { t } = useTranslation()
  const save = useSetRolePermissions()
  const [selected, setSelected] = useState<string[]>([])
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (role) {
      setSelected([...role.permissions])
      setFormError(null)
      setConfirmOpen(false)
    }
  }, [role])

  async function apply(): Promise<void> {
    if (!role) {
      return
    }
    setFormError(null)
    try {
      await save.mutateAsync({ roleName: role.name, permissions: selected })
      setConfirmOpen(false)
      onClose()
    } catch (error) {
      setFormError(isApiError(error) ? error.message : t('identity.roles.saveFailed'))
    }
  }

  return (
    <>
      <SlideOver
        open={Boolean(role)}
        title={
          role
            ? t('identity.roles.editTitle', {
                role: t(`identity.roleLabels.${role.name}`, { defaultValue: role.name }),
              })
            : t('identity.roles.editPermissions')
        }
        onClose={onClose}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button disabled={save.isPending} onClick={() => setConfirmOpen(true)}>
              {t('common.save')}
            </Button>
          </div>
        }
      >
        {role ? (
          <div className="flex flex-col gap-4">
            {role.is_superuser ? (
              <Alert tone="info">{t('identity.roles.superuserHint')}</Alert>
            ) : null}
            <PermissionChecklist
              permissions={catalog}
              selected={selected}
              onChange={setSelected}
              disabled={save.isPending}
            />
            {formError ? (
              <Alert tone="error" role="alert">
                {formError}
              </Alert>
            ) : null}
          </div>
        ) : null}
      </SlideOver>

      <ConfirmDialog
        open={confirmOpen}
        title={t('identity.roles.confirmTitle')}
        body={t('identity.roles.confirmBody', {
          role: role
            ? t(`identity.roleLabels.${role.name}`, { defaultValue: role.name })
            : '',
        })}
        confirmLabel={t('identity.roles.confirmAction')}
        cancelLabel={t('common.cancel')}
        danger
        busy={save.isPending}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => void apply()}
      />
    </>
  )
}

function RegisterPermissionDialog({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const register = useRegisterPermissions()
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | undefined>()
  const [formError, setFormError] = useState<string | null>(null)

  if (!open) {
    return null
  }

  async function onSubmit(): Promise<void> {
    setFormError(null)
    const fieldError = validatePermissionName(value, {
      required: t('identity.roles.permissionRequired'),
      invalid: t('identity.roles.permissionInvalid'),
    })
    setError(fieldError)
    if (fieldError) {
      return
    }
    try {
      await register.mutateAsync([value.trim().toLowerCase()])
      setValue('')
      onClose()
    } catch (err) {
      setFormError(isApiError(err) ? err.message : t('identity.roles.saveFailed'))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-[color-mix(in_srgb,var(--color-text)_40%,transparent)]"
        aria-label="Dismiss"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('identity.roles.registerPermission')}
        className="relative z-10 w-full max-w-md rounded-lg bg-[var(--color-surface)] p-5 shadow-xl"
      >
        <h2 className="text-lg font-semibold">{t('identity.roles.registerPermission')}</h2>
        <p className="mt-1 text-sm text-[var(--color-muted)]">
          {t('identity.roles.registerHint')}
        </p>
        <div className="mt-4">
          <TextField
            name="permission-name"
            label={t('identity.roles.permissionName')}
            value={value}
            error={error}
            placeholder="work:export"
            onChange={(e) => setValue(e.target.value)}
            disabled={register.isPending}
          />
        </div>
        {formError ? (
          <div className="mt-3">
            <Alert tone="error" role="alert">
              {formError}
            </Alert>
          </div>
        ) : null}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button disabled={register.isPending} onClick={() => void onSubmit()}>
            {t('identity.roles.addPermission')}
          </Button>
        </div>
      </div>
    </div>
  )
}
