import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import vi from './locales/vi.json'
import zh from './locales/zh.json'

// Get saved language from localStorage, or default to English ('en')
const savedLocale = localStorage.getItem('app_lang') || 'en'

export const i18n = createI18n({
  legacy: false, // Use Composition API
  locale: savedLocale,
  fallbackLocale: 'en', // Fallback to English if string is missing
  messages: {
    en,
    vi,
    zh
  }
})

// Helper to change language globally and persist it
export function setLanguage(lang) {
  i18n.global.locale.value = lang
  localStorage.setItem('app_lang', lang)
  document.documentElement.setAttribute('lang', lang)
}
