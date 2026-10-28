/**
 * Maps the FastAPI `{ error: { code, message, fields? } }` envelope.
 * Keep transport parsing here so features never parse Response JSON ad hoc.
 */

export interface ApiErrorBody {
  code: string
  message: string
  fields?: Record<string, string>
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.fields = body.fields ?? {}
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isForbidden(): boolean {
    return this.status === 403
  }

  get isRateLimited(): boolean {
    return this.status === 429
  }
}

interface ErrorEnvelope {
  error?: {
    code?: unknown
    message?: unknown
    fields?: unknown
  }
}

export function parseApiError(status: number, payload: unknown): ApiError {
  const envelope = payload as ErrorEnvelope | null
  const err = envelope?.error
  const code = typeof err?.code === 'string' ? err.code : 'unknown_error'
  const message =
    typeof err?.message === 'string' ? err.message : 'Something went wrong. Try again.'
  const fields =
    err?.fields && typeof err.fields === 'object' && !Array.isArray(err.fields)
      ? Object.fromEntries(
          Object.entries(err.fields as Record<string, unknown>).filter(
            (entry): entry is [string, string] => typeof entry[1] === 'string',
          ),
        )
      : {}
  return new ApiError(status, { code, message, fields })
}
