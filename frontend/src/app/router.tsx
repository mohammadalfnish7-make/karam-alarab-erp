import { Navigate, Route, Routes, useParams } from 'react-router'

import { LocaleLayout } from '@/app/LocaleLayout'
import { RequireAuth } from '@/features/auth'
import { ChangePasswordPage } from '@/pages/account/ChangePasswordPage'
import { RolesPage } from '@/pages/admin/RolesPage'
import { UsersPage } from '@/pages/admin/UsersPage'
import { WorkflowsPage } from '@/pages/admin/WorkflowsPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { AppShell } from '@/pages/shell/AppShell'
import { HomePage } from '@/pages/shell/HomePage'
import { DueDatesPage } from '@/pages/work/DueDatesPage'
import { PrioritiesPage } from '@/pages/work/PrioritiesPage'
import { TaskDetailPage } from '@/pages/work/TaskDetailPage'
import { TasksBoardPage } from '@/pages/work/TasksBoardPage'
import { TasksCalendarPage } from '@/pages/work/TasksCalendarPage'
import { TasksListPage } from '@/pages/work/TasksListPage'
import { TasksTimelinePage } from '@/pages/work/TasksTimelinePage'
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
            <Route path="tasks" element={<TasksListPage />} />
            <Route path="tasks/board" element={<TasksBoardPage />} />
            <Route path="tasks/calendar" element={<TasksCalendarPage />} />
            <Route path="tasks/timeline" element={<TasksTimelinePage />} />
            <Route path="tasks/:taskId" element={<TaskDetailPage />} />
            <Route path="priorities" element={<PrioritiesPage />} />
            <Route path="due-dates" element={<DueDatesPage />} />
            <Route path="admin/users" element={<UsersPage />} />
            <Route path="admin/roles" element={<RolesPage />} />
            <Route path="admin/workflows" element={<WorkflowsPage />} />
            <Route path="account/password" element={<ChangePasswordPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to=".." replace />} />
      </Route>
      <Route path="*" element={<Navigate to={`/${env.defaultLocale}`} replace />} />
    </Routes>
  )
}
