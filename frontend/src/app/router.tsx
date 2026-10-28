import { Navigate, Route, Routes, useParams } from 'react-router'

import { LocaleLayout } from '@/app/LocaleLayout'
import { RequireAuth } from '@/features/auth'
import { LoginPage } from '@/pages/auth/LoginPage'
import { AppShell } from '@/pages/shell/AppShell'
import { HomePage } from '@/pages/shell/HomePage'
import { env, resolveLocale } from '@/shared/config/env'

function ProtectedLocaleRoutes() {
  const { locale: localeParam } = useParams()
  return <RequireAuth locale={resolveLocale(localeParam)} />
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to={`/${env.defaultLocale}`} replace />} />
      <Route path="/:locale" element={<LocaleLayout />}>
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedLocaleRoutes />}>
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to=".." replace />} />
      </Route>
      <Route path="*" element={<Navigate to={`/${env.defaultLocale}`} replace />} />
    </Routes>
  )
}
