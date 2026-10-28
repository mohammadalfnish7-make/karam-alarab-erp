import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import { env, type AppLocale } from '@/shared/config/env'
import en from '@/shared/i18n/locales/en.json'
import ru from '@/shared/i18n/locales/ru.json'

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ru: { translation: ru },
  },
  lng: env.defaultLocale,
  fallbackLng: env.defaultLocale,
  interpolation: { escapeValue: false },
})

export function syncDocumentLocale(locale: AppLocale): void {
  document.documentElement.lang = locale
  document.documentElement.dir = 'ltr'
}

export { i18n }
