import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { useChangePassword, validateChangePassword } from '@/features/identity'
import { isApiError } from '@/shared/api/http-client'
import { resolveLocale } from '@/shared/config/env'
import { Alert } from '@/shared/ui/Alert'
import { Button } from '@/shared/ui/Button'
import { PageFrame } from '@/shared/ui/PageFrame'
import { TextField } from '@/shared/ui/TextField'

export function ChangePasswordPage() {
  const { t } = useTranslation()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const navigate = useNavigate()
  const change = useChangePassword()

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{
    current_password?: string
    new_password?: string
    confirm_password?: string
  }>({})
  const [formError, setFormError] = useState<string | null>(null)

  async function onSubmit(event: FormEvent): Promise<void> {
    event.preventDefault()
    setFormError(null)
    const errors = validateChangePassword(current, next, confirm, {
      currentRequired: t('identity.password.currentRequired'),
      newRequired: t('identity.password.newRequired'),
      newTooShort: t('identity.password.newTooShort'),
      confirmMismatch: t('identity.password.confirmMismatch'),
    })
    setFieldErrors(errors)
    if (errors.current_password || errors.new_password || errors.confirm_password) {
      return
    }
    try {
      await change.mutateAsync({
        current_password: current,
        new_password: next,
      })
      void navigate(`/${locale}/login`, { replace: true })
    } catch (error) {
      if (isApiError(error) && error.status === 401) {
        setFieldErrors({ current_password: t('identity.password.currentWrong') })
        return
      }
      setFormError(isApiError(error) ? error.message : t('identity.password.failed'))
    }
  }

  return (
    <PageFrame title={t('identity.password.title')} subtitle={t('identity.password.subtitle')}>
      <div className="grid max-w-4xl gap-4 lg:grid-cols-[minmax(0,28rem)_1fr]">
        <form
          className="flex flex-col gap-4 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
          onSubmit={(e) => void onSubmit(e)}
          noValidate
        >
          <TextField
            name="current-password"
            type="password"
            autoComplete="current-password"
            label={t('identity.password.current')}
            value={current}
            error={fieldErrors.current_password}
            onChange={(e) => setCurrent(e.target.value)}
            disabled={change.isPending}
          />
          <TextField
            name="new-password"
            type="password"
            autoComplete="new-password"
            label={t('identity.password.new')}
            value={next}
            error={fieldErrors.new_password}
            onChange={(e) => setNext(e.target.value)}
            disabled={change.isPending}
          />
          <p className="text-xs text-[var(--color-muted)]">{t('identity.password.hint')}</p>
          <TextField
            name="confirm-password"
            type="password"
            autoComplete="new-password"
            label={t('identity.password.confirm')}
            value={confirm}
            error={fieldErrors.confirm_password}
            onChange={(e) => setConfirm(e.target.value)}
            disabled={change.isPending}
          />
          {formError ? (
            <Alert tone="error" role="alert">
              {formError}
            </Alert>
          ) : null}
          <Button type="submit" disabled={change.isPending} className="self-start">
            {change.isPending ? t('identity.password.saving') : t('identity.password.submit')}
          </Button>
        </form>

        <Alert tone="info">{t('identity.password.sessionNote')}</Alert>
      </div>
    </PageFrame>
  )
}
