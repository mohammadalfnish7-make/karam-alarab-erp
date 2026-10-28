import { useEffect, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { useLogin, useSession } from '@/features/auth'
import { isApiError } from '@/shared/api/http-client'
import { resolveLocale, type AppLocale } from '@/shared/config/env'
import { validateLoginFields } from '@/shared/lib/validate-login'
import { Button } from '@/shared/ui/Button'
import { TextField } from '@/shared/ui/TextField'

interface LoginLocationState {
  returnTo?: string
}

export function LoginPage() {
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading } = useSession()
  const login = useLogin()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>(
    {},
  )
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (i18n.language !== locale) {
      void i18n.changeLanguage(locale)
    }
  }, [i18n, locale])

  if (!isLoading && isAuthenticated) {
    const state = location.state as LoginLocationState | null
    return <Navigate to={state?.returnTo ?? `/${locale}`} replace />
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setFormError(null)
    const errors = validateLoginFields(email, password, {
      emailRequired: t('auth.login.emailRequired'),
      emailInvalid: t('auth.login.emailInvalid'),
      passwordRequired: t('auth.login.passwordRequired'),
    })
    setFieldErrors(errors)
    if (errors.email || errors.password) {
      return
    }

    try {
      await login.mutateAsync({ email: email.trim(), password })
      const state = location.state as LoginLocationState | null
      void navigate(state?.returnTo ?? `/${locale}`, { replace: true })
    } catch (error) {
      if (isApiError(error) && error.isRateLimited) {
        setFormError(t('auth.login.rateLimited'))
        return
      }
      setFormError(t('auth.login.failed'))
    }
  }

  const otherLocale: AppLocale = locale === 'en' ? 'ru' : 'en'

  return (
    <div className="flex min-h-dvh flex-col bg-[var(--color-wash)]">
      <header className="flex items-center justify-between px-6 py-4">
        <p className="text-lg font-semibold tracking-tight text-[var(--color-text)]">
          {t('brand.name')}{' '}
          <span className="font-medium text-[var(--color-primary)]">{t('brand.product')}</span>
        </p>
        <Button
          variant="ghost"
          onClick={() => {
            void navigate(`/${otherLocale}/login${location.search}`, {
              replace: true,
              state: location.state,
            })
          }}
        >
          {otherLocale.toUpperCase()}
        </Button>
      </header>

      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 pb-16">
        <h1 className="text-2xl font-semibold text-[var(--color-text)]">
          {t('auth.login.title')}
        </h1>
        <p className="mt-2 text-sm text-[var(--color-muted)]">{t('auth.login.subtitle')}</p>

        <form className="mt-8 flex flex-col gap-4" onSubmit={(e) => void onSubmit(e)} noValidate>
          <TextField
            name="email"
            type="email"
            autoComplete="username"
            label={t('auth.login.email')}
            value={email}
            error={fieldErrors.email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={login.isPending}
          />
          <TextField
            name="password"
            type="password"
            autoComplete="current-password"
            label={t('auth.login.password')}
            value={password}
            error={fieldErrors.password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={login.isPending}
          />

          {formError ? (
            <p role="alert" className="text-sm text-[var(--color-danger)]">
              {formError}
            </p>
          ) : null}

          <Button type="submit" disabled={login.isPending} className="mt-2 w-full">
            {login.isPending ? t('auth.login.submitting') : t('auth.login.submit')}
          </Button>
        </form>
      </main>
    </div>
  )
}
