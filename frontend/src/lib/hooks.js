import { useState, useEffect, useCallback } from 'react'

// ── Theme Hook ─────────────────────────────────────────────────────────────────
export function useTheme() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('wrd_theme') || 'dark'
  })
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('wrd_theme', theme)
  }, [theme])
  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  return [theme, toggle]
}

// ── Toast Hook ─────────────────────────────────────────────────────────────────
let toastId = 0
export function useToasts() {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts(t => t.filter(x => x.id !== id))
  }, [])

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastId
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), duration)
    return id
  }, [])

  return [toasts, addToast, removeToast]
}

// ── URL Search Params Hook ─────────────────────────────────────────────────────
export function useURLParams() {
  const getParams = useCallback(() => new URLSearchParams(window.location.search), [])

  const setParam = useCallback((key, value) => {
    const params = getParams()
    if (value) params.set(key, value)
    else params.delete(key)
    const str = params.toString()
    window.history.replaceState({}, '', str ? `?${str}` : window.location.pathname)
  }, [getParams])

  const getParam = useCallback((key, def = '') => getParams().get(key) || def, [getParams])

  return { setParam, getParam }
}

/** True on small touch viewports — used to lighten the WebGL background. */
export function useIsMobile(breakpoint = 768) {
  const [mobile, setMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth < breakpoint)
  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < breakpoint)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [breakpoint])
  return mobile
}

