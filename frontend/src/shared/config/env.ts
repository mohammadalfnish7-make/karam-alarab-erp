/**
 * Runtime config for the SPA.
 * Dev uses the Vite `/api` proxy so cookies stay same-site.
 * Production can point at an absolute API origin via VITE_API_BASE_URL.
 */
export const env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api',
  defaultLocale: 'en' as const,
  supportedLocales: ['en', 'ru'] as const,
}

export type AppLocale = (typeof env.supportedLocales)[number]

export function isAppLocale(value: string): value is AppLocale {
  return (env.supportedLocales as readonly string[]).includes(value)
}

export function resolveLocale(value: string | undefined): AppLocale {
  if (value && isAppLocale(value)) {
    return value
  }
  return env.defaultLocale
}
