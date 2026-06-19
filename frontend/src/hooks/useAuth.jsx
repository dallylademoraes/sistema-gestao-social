import { createContext, useContext, useEffect, useState } from 'react'
import { auth } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    // Attempt to load current user via cookie-based session.
    auth.me()
      .then((r) => setUsuario(r.data))
      .catch((err) => {
        if (err?.response?.status !== 401) {
          console.error('Falha ao carregar usuário autenticado', err)
        }
      })
      .finally(() => setCarregando(false))
  }, [])

  const login = async (email, senha) => {
    const loginResponse = await auth.login(email, senha)
    const me = await auth.me()
    setUsuario(me.data)
    return loginResponse.data
  }

  const trocarSenha = async (senhaAtual, novaSenha) => {
    await auth.changePassword(senhaAtual, novaSenha)
    const me = await auth.me()
    setUsuario(me.data)
  }

  const logout = () => {
    // Inform backend to clear HttpOnly cookie, then clear client state
    auth.logout().catch(() => {})
    setUsuario(null)
  }

  return (
    <AuthContext.Provider value={{ usuario, login, trocarSenha, logout, carregando }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
