import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import { api, clearStoredToken, setStoredToken } from '../api'

export interface User {
  id: string
  username: string
  email: string | null
  display_name: string | null
  is_active: boolean
  is_system_admin: boolean
  role_id: number | null
}

interface AuthState {
  user: User | null
  multiUserEnabled: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    multiUserEnabled: false,
    isLoading: true,
  })

  const loadMe = useCallback(async () => {
    try {
      const data = await api.get<{ user: User; multi_user_enabled: boolean }>(
        '/core/auth/me',
      )
      setState({
        user: data.user,
        multiUserEnabled: data.multi_user_enabled,
        isLoading: false,
      })
    } catch {
      clearStoredToken()
      setState({ user: null, multiUserEnabled: false, isLoading: false })
    }
  }, [])

  useEffect(() => {
    loadMe()
  }, [loadMe])

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.post<{ token: string; user: User }>('/core/auth/login', {
      username,
      password,
    })
    setStoredToken(data.token)
    setState((s) => ({ ...s, user: data.user, isLoading: false }))
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/core/auth/logout', {})
    } finally {
      clearStoredToken()
      setState({ user: null, multiUserEnabled: false, isLoading: false })
    }
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
