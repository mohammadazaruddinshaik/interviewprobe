import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'interviewprobe-theme'
const THEME_CHANGE_EVENT = 'interviewprobe:theme-change'

function supportsMatchMedia() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
}

function getSystemTheme() {
  if (!supportsMatchMedia()) return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function readStoredTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : null
  } catch {
    return null
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

// A real, persisted light/dark theme — no backend involved. The saved
// preference (if any) always wins; otherwise the OS-level
// `prefers-color-scheme` decides on first visit. Any component that calls
// this hook stays in sync with every other one (e.g. the desktop navbar's
// toggle and the mobile menu's toggle) via a small same-tab event, since
// the browser's own `storage` event never fires in the tab that wrote it.
export function useTheme() {
  const [theme, setThemeState] = useState(() => readStoredTheme() ?? getSystemTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    const handleExternalChange = (event) => setThemeState(event.detail)
    window.addEventListener(THEME_CHANGE_EVENT, handleExternalChange)
    return () => window.removeEventListener(THEME_CHANGE_EVENT, handleExternalChange)
  }, [])

  useEffect(() => {
    if (!supportsMatchMedia()) return undefined
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handleSystemChange = (event) => {
      // Only follow the OS if the user has never explicitly chosen —
      // once they pick a theme here, it sticks until they change it again.
      if (readStoredTheme() === null) {
        setThemeState(event.matches ? 'dark' : 'light')
      }
    }
    media.addEventListener('change', handleSystemChange)
    return () => media.removeEventListener('change', handleSystemChange)
  }, [])

  const setTheme = useCallback((nextTheme) => {
    setThemeState(nextTheme)
    try {
      localStorage.setItem(STORAGE_KEY, nextTheme)
    } catch {
      // Private-browsing/storage-blocked: the theme still applies for this
      // page view, it just won't persist across a reload.
    }
    window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: nextTheme }))
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }, [theme, setTheme])

  return { theme, setTheme, toggleTheme }
}
