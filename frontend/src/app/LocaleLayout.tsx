import { useEffect } from 'react'
import { Navigate, Outlet, useParams } from 'react-router'

import { UnauthorizedBridge } from '@/app/UnauthorizedBridge'
import { env, isAppLocale, resolveLocale } from '@/shared/config/env'
import { i18n, syncDocumentLocale } from '@/shared/i18n'

export function LocaleLayout() {
  const { locale: localeParam } = useParams()
  const localeValid = Boolean(localeParam && isAppLocale(localeParam))
  const locale = resolveLocale(localeParam)

  useEffect(() => {
    if (!localeValid) {
      return
    }
    syncDocumentLocale(locale)
    if (i18n.language !== locale) {
      void i18n.changeLanguage(locale)
    }
  }, [locale, localeValid])

  if (!localeValid) {
    return <Navigate to={`/${env.defaultLocale}`} replace />
  }

  return (
    <>
      <UnauthorizedBridge />
      <Outlet />
    </>
  )
}
