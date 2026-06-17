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
    <div className="auth-page auth-page--decorated">
      <style>{`@keyframes orbitBlob{0%{transform:translate(0px,0px) scale(1)}12.5%{transform:translate(-80vw,0) scale(1.03)}25%{transform:translate(-80vw,60vh) scale(1)}37.5%{transform:translate(0,60vh) scale(0.98)}50%{transform:translate(80vw,60vh) scale(1.02)}62.5%{transform:translate(80vw,0) scale(1)}75%{transform:translate(0,-10vh) scale(1.01)}87.5%{transform:translate(-40vw,-10vh) scale(0.99)}100%{transform:translate(0px,0px) scale(1)} }
        @keyframes fadeInUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
        .auth-welcome{animation:fadeInUp 560ms ease both}
      `}</style>
      <div style={{ position: 'absolute', right: -40, top: -30, width: 360, height: 360, pointerEvents: 'none', opacity: 0.12, animation: 'orbitBlob 36s ease-in-out infinite', transformOrigin: '50% 50%' }} aria-hidden>
        <svg viewBox="0 0 600 600" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="g1" x1="0%" x2="100%" y1="0%" y2="100%" gradientUnits="userSpaceOnUse" gradientTransform="rotate(0 300 300)">
              <stop offset="0%" stopColor="#3ab789">
                <animate attributeName="offset" values="0%;12%;0%" dur="6s" repeatCount="indefinite" />
              </stop>
              <stop offset="100%" stopColor="#1f8a65">
                <animate attributeName="offset" values="100%;88%;100%" dur="6s" repeatCount="indefinite" />
              </stop>
              <animateTransform attributeName="gradientTransform" type="rotate" from="0 300 300" to="360 300 300" dur="20s" repeatCount="indefinite" />
            </linearGradient>
            <filter id="blur">
              <feGaussianBlur stdDeviation="30" />
            </filter>
          </defs>
          <g filter="url(#blur)" transform="translate(0 0)">
            <path d="M421.8,96.7C474,150,496,232,467,286c-29,54-114,86-176,106s-125,19-164-23S55,294,79,228s86-126,154-150S369,43,421.8,96.7Z" fill="url(#g1)">
              <animateTransform attributeName="transform" type="scale" values="1;1.02;1" dur="8s" repeatCount="indefinite" additive="sum" />
            </path>
          </g>
        </svg>
      </div>
      <div className="auth-welcome" style={{ marginBottom: 20, padding: '18px 0', maxWidth: 560 }}>
        <h1 style={{ margin: 0, fontSize: 28, color: 'var(--text-main)' }}>Bem-vindo ao Sistema de Gestão da ASAP</h1>
        <p style={{ marginTop: 6, color: 'var(--text-soft)', marginBottom: 6 }}>Acesse sua conta para gerenciar cadastros, assinaturas e relatórios.</p>
        <div style={{ height: 6, width: 140, borderRadius: 6, background: 'linear-gradient(90deg,#3ab789,#1f8a65)' }} aria-hidden />
      </div>
      <div className="auth-card">
        <div className="auth-brand">
          <div>
            <div className="auth-brand-title">Sistema de Gestão</div>
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
