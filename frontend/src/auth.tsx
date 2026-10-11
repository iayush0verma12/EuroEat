import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken } from './api'

export type User = {
  username: string
  full_name: string
  email: string
  home_city: string
  diet: string
  orders: number
  settings: Record<string, any>
}

type AuthCtx = {
  user: User | null
  loading: boolean
  login: (u: string, p: string, remember?: boolean) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
  setUser: (u: User) => void
}

const Ctx = createContext<AuthCtx>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!getToken())

  const refresh = useCallback(async () => {
    if (!getToken()) return
    try {
      setUser(await api<User>('/me'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const login = async (username: string, password: string, remember = true) => {
    const res = await api<{ token: string; user: User }>('/auth/login', { body: { username, password } })
    setToken(res.token, remember)
    setUser(res.user)
  }

  const logout = () => {
    setToken(null)
    setUser(null)
  }

  return <Ctx.Provider value={{ user, loading, login, logout, refresh, setUser }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
