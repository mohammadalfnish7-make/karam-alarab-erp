import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'

import { sessionKeys } from '@/features/auth'
import { setUnauthorizedHandler } from '@/shared/api/http-client'
import { resolveLocale } from '@/shared/config/env'

/**
 * Wires the HTTP 401 handler once. Lives in the app layer so features
 * stay free of router coupling.
 */
export function UnauthorizedBridge() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { locale: localeParam } = useParams()
  const locale = resolveLocale(localeParam)

  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.setQueryData(sessionKeys.me(), null)
      void navigate(`/${locale}/login`, { replace: true })
    })
    return () => setUnauthorizedHandler(null)
  }, [locale, navigate, queryClient])

  return null
}
