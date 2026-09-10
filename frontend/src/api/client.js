// HTTP client for the RetailIQ API.
//
// The base URL is empty by default so requests go to the same origin as the
// app: in development Vite proxies /api -> the local FastAPI server, and in
// production the platform rewrites /api to the deployed FastAPI function.
// VITE_API_BASE_URL overrides this when the API lives on another origin.

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const API_PREFIX = '/api/v1'

const ACCESS_KEY = 'retailiq-access-token'
const REFRESH_KEY = 'retailiq-refresh-token'

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

// --- token storage ---------------------------------------------------------

export const tokens = {
  get access() {
    try { return localStorage.getItem(ACCESS_KEY) } catch { return null }
  },
  get refresh() {
    try { return localStorage.getItem(REFRESH_KEY) } catch { return null }
  },
  set({ access_token, refresh_token }) {
    try {
      localStorage.setItem(ACCESS_KEY, access_token)
      if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
    } catch { /* storage unavailable (private mode) — session-only auth */ }
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
    } catch { /* ignore */ }
  },
}

let onUnauthorized = null
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

// --- core request ----------------------------------------------------------

async function request(path, { method = 'GET', body, timeoutMs = 60000, retry = true } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const access = tokens.access
  if (access) headers.Authorization = `Bearer ${access}`

  try {
    const response = await fetch(`${BASE_URL}${API_PREFIX}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })

    // One transparent refresh attempt before giving up on the session.
    if (response.status === 401 && retry && tokens.refresh) {
      const refreshed = await tryRefresh()
      if (refreshed) return request(path, { method, body, timeoutMs, retry: false })
    }

    if (response.status === 401) {
      tokens.clear()
      onUnauthorized?.()
      throw new ApiError('Session expired', 401)
    }

    if (!response.ok) {
      let detail
      try { detail = (await response.json())?.detail } catch { /* non-JSON body */ }
      throw new ApiError(
        typeof detail === 'string' ? detail : `${method} ${path} failed (${response.status})`,
        response.status,
        detail,
      )
    }

    if (response.status === 204) return null
    const type = response.headers.get('content-type') || ''
    return type.includes('application/json') ? response.json() : response.text()
  } catch (err) {
    if (err.name === 'AbortError') throw new ApiError(`Request to ${path} timed out`, 408)
    throw err
  } finally {
    clearTimeout(timer)
  }
}

async function tryRefresh() {
  try {
    const response = await fetch(`${BASE_URL}${API_PREFIX}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh }),
    })
    if (!response.ok) return false
    tokens.set(await response.json())
    return true
  } catch {
    return false
  }
}

export const apiGet = (path, opts) => request(path, { ...opts, method: 'GET' })
export const apiPost = (path, body, opts) => request(path, { ...opts, method: 'POST', body })
export const apiPatch = (path, body, opts) => request(path, { ...opts, method: 'PATCH', body })
export const apiPut = (path, body, opts) => request(path, { ...opts, method: 'PUT', body })
export const apiDelete = (path, opts) => request(path, { ...opts, method: 'DELETE' })

/** Absolute URL for a download link (adds the token as a query-free header is impossible). */
export async function downloadFile(path, filename) {
  const response = await fetch(`${BASE_URL}${API_PREFIX}${path}`, {
    headers: tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {},
  })
  if (!response.ok) throw new ApiError(`Download failed (${response.status})`, response.status)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const apiBaseUrl = `${BASE_URL}${API_PREFIX}`
