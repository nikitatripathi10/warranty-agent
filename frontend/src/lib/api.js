const TOKEN_KEY = 'wrd_session_token'

export function getSessionToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setSessionToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token)
    }
  } catch {
    /* ignore storage errors */
  }
}

export function clearSessionToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore storage errors */
  }
}

/**
 * Wrapper around fetch() that attaches the signed JWT session token (if present)
 * as a Bearer header and includes credentials for same-origin HttpOnly cookies.
 */
export function apiFetch(url, options = {}) {
  const token = getSessionToken()
  const headers = new Headers(options.headers || {})
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return fetch(url, {
    credentials: 'include',
    ...options,
    headers,
  })
}

