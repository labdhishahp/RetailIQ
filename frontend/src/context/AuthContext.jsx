import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { setUnauthorizedHandler, tokens } from '../api/client'
import { getMe, login as loginRequest } from '../api/retail'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore the session on load if a stored token is still valid.
  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (!tokens.access) {
        setLoading(false)
        return
      }
      try {
        const me = await getMe()
        if (!cancelled) setUser(me)
      } catch {
        tokens.clear()
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    restore()
    return () => { cancelled = true }
  }, [])

  // A 401 anywhere in the app drops the session rather than leaving a
  // half-authenticated UI on screen.
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
    return () => setUnauthorizedHandler(null)
  }, [])

  const login = useCallback(async (email, password) => {
    const issued = await loginRequest(email, password)
    tokens.set(issued)
    const me = await getMe()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    tokens.clear()
    setUser(null)
  }, [])

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    canWrite: ['manager', 'admin'].includes(user?.role),
    isAdmin: user?.role === 'admin',
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
