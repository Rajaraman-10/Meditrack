import { useEffect, useMemo, useState } from 'react'
import {
  fetchCurrentUser,
  loginUser,
  registerUser,
  revokeRefreshToken,
} from '../api/auth'
import AuthContext from './context'

function saveTokens(tokens) {
  sessionStorage.setItem('accessToken', tokens.access)
  sessionStorage.setItem('refreshToken', tokens.refresh)
}

function clearTokens() {
  sessionStorage.removeItem('accessToken')
  sessionStorage.removeItem('refreshToken')
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    const handleExpiredSession = () => {
      if (isMounted) {
        setUser(null)
      }
    }

    window.addEventListener('mediatrack:session-expired', handleExpiredSession)

    async function restoreSession() {
      if (!sessionStorage.getItem('refreshToken')) {
        setLoading(false)
        return
      }

      try {
        const currentUser = await fetchCurrentUser()
        if (isMounted) {
          setUser(currentUser)
        }
      } catch {
        clearTokens()
        if (isMounted) {
          setUser(null)
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    restoreSession()
    return () => {
      isMounted = false
      window.removeEventListener('mediatrack:session-expired', handleExpiredSession)
    }
  }, [])

  async function login(credentials) {
    const tokens = await loginUser(credentials)
    saveTokens(tokens)
    try {
      const currentUser = await fetchCurrentUser()
      setUser(currentUser)
      return currentUser
    } catch (error) {
      clearTokens()
      throw error
    }
  }

  async function register(details) {
    return registerUser(details)
  }

  async function logout() {
    const refreshToken = sessionStorage.getItem('refreshToken')
    try {
      if (refreshToken) {
        await revokeRefreshToken(refreshToken)
      }
    } finally {
      clearTokens()
      setUser(null)
    }
  }

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
