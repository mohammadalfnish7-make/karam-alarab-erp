import { env } from '@/shared/config/env'
import { ApiError, parseApiError } from '@/shared/api/errors'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface HttpRequestOptions {
  method?: HttpMethod
  body?: unknown
  signal?: AbortSignal
  credentials?: RequestCredentials
  /**
   * When false, a 401 does not run the global unauthorized handler.
   * Use for the session probe (`GET /users/me`) where anonymous is expected.
   */
  notifyUnauthorized?: boolean
}

type UnauthorizedHandler = () => void

let onUnauthorized: UnauthorizedHandler | null = null

/** App layer registers once (clear session + redirect). */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler
}

function buildUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  const base = env.apiBaseUrl.replace(/\/$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}

/**
 * Single HTTP entry for the SPA. Always sends cookies; maps error envelopes.
 * Features call this (or feature api modules) — never raw fetch elsewhere.
 */
export async function httpClient<T>(
  path: string,
  options: HttpRequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    signal,
    credentials = 'include',
    notifyUnauthorized = true,
  } = options
  const headers = new Headers()
  if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(buildUrl(path), {
    method,
    credentials,
    headers,
    signal,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('Content-Type') ?? ''
  const isJson = contentType.includes('application/json')
  const payload: unknown = isJson ? await response.json() : null

  if (!response.ok) {
    const error = parseApiError(response.status, payload)
    if (error.isUnauthorized && notifyUnauthorized && onUnauthorized) {
      onUnauthorized()
    }
    throw error
  }

  return payload as T
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
