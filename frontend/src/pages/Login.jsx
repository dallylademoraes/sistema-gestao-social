import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [bloqueado, setBloqueado] = useState(false)
  const [segundosBloqueio, setSegundosBloqueio] = useState(0)
  const [carregando, setCarregando] = useState(false)

  useEffect(() => {
    if (!bloqueado || segundosBloqueio <= 0) return undefined

    const timer = window.setInterval(() => {
      setSegundosBloqueio((atual) => {
        if (atual <= 1) {
          window.clearInterval(timer)
          setBloqueado(false)
          setErro('')
          return 0
        }
        return atual - 1
      })
    }, 1000)

    return () => window.clearInterval(timer)
  }, [bloqueado, segundosBloqueio])

  const formatarTempo = (totalSegundos) => {
    const minutos = Math.floor(totalSegundos / 60)
    const segundos = totalSegundos % 60
    if (minutos <= 0) return `${segundos}s`
    return `${minutos}m ${String(segundos).padStart(2, '0')}s`
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')
    setBloqueado(false)
    setSegundosBloqueio(0)
    setCarregando(true)
    try {
      await login(email, senha)
      navigate('/')
    } catch (err) {
      if (err.response?.status === 429) {
        setBloqueado(true)
        const retryAfter = Number(err.response?.headers?.['retry-after'] || err.response?.headers?.['x-ratelimit-reset'] || 0)
        setSegundosBloqueio(Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : 900)
        setErro(err.response?.data?.detail || 'Muitas tentativas. Tente novamente mais tarde.')
      } else if (err.response?.status === 401) {
        setErro('E-mail ou senha incorretos.')
      } else {
        setErro('Não foi possível entrar agora.')
      }
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark">
            ASAP
          </div>
          <div>
            <div className="auth-brand-title">Sistema de Cadastro</div>
            <div className="auth-brand-subtitle">Acesso restrito</div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">E-mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="form-input"
            />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label className="form-label">Senha</label>
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
              className="form-input"
            />
            <div style={{ marginTop: 8, textAlign: 'right' }}>
              <Link to="/esqueci-senha" style={{ fontSize: 12, color: 'var(--link)', textDecoration: 'none', fontWeight: 700 }}>
                Esqueci minha senha
              </Link>
            </div>
          </div>
          {erro && (
            <div
              role="alert"
              style={{
                marginBottom: 16,
                padding: '10px 12px',
                borderRadius: 10,
                border: bloqueado ? '1px solid var(--badge-pending-text)' : '1px solid var(--danger)',
                background: bloqueado ? 'var(--badge-pending-bg)' : 'rgba(192, 57, 43, 0.08)',
                color: 'var(--text-main)',
                fontSize: 13,
                lineHeight: 1.45,
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 4 }}>
                {bloqueado ? 'Acesso temporariamente bloqueado' : 'Falha no acesso'}
              </div>
              <div>{erro}</div>
              {bloqueado && (
                <div style={{ marginTop: 6, color: 'var(--text-soft)', fontSize: 12 }}>
                  Bloqueio ativo por {formatarTempo(segundosBloqueio)}. Aguarde a liberação automática e tente novamente.
                </div>
              )}
            </div>
          )}
          <button
            type="submit"
            disabled={carregando || (bloqueado && segundosBloqueio > 0)}
            className="form-submit"
          >
            {carregando ? 'Entrando...' : bloqueado && segundosBloqueio > 0 ? `Bloqueado (${formatarTempo(segundosBloqueio)})` : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
