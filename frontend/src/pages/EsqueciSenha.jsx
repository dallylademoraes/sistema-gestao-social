import { useState } from 'react'
import { Link } from 'react-router-dom'
import { auth } from '../services/api'

export default function EsqueciSenha() {
  const [email, setEmail] = useState('')
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [mensagem, setMensagem] = useState('')
  const [resetUrl, setResetUrl] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')
    setMensagem('')
    setResetUrl('')
    setCarregando(true)
    try {
      const r = await auth.forgotPassword(email)
      setMensagem(r.data.message || 'Se o e-mail existir, enviaremos as instruções de redefinição.')
      if (r.data.reset_url) setResetUrl(r.data.reset_url)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível processar sua solicitação.')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark">ASAP</div>
          <div>
            <div className="auth-brand-title">Recuperar acesso</div>
            <div className="auth-brand-subtitle">Enviaremos instruções para redefinir sua senha</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} autoComplete="off">
          <div style={{ marginBottom: 16 }}>
            <label className="form-label">E-mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="form-input"
            />
          </div>

          {erro && <p className="form-error">{erro}</p>}
          {mensagem && <p style={{ color: 'var(--link)', fontSize: 13, marginBottom: 10 }}>{mensagem}</p>}
          {resetUrl && (
            <a className="btn-secondary" href={resetUrl} style={{ display: 'inline-flex', textDecoration: 'none', marginBottom: 10 }}>
              Abrir link de redefinição (ambiente local)
            </a>
          )}

          <button type="submit" disabled={carregando} className="form-submit">
            {carregando ? 'Enviando...' : 'Enviar link'}
          </button>
        </form>

        <div style={{ marginTop: 14 }}>
          <Link to="/login" style={{ color: 'var(--link)', fontSize: 13, fontWeight: 700, textDecoration: 'none' }}>
            Voltar ao login
          </Link>
        </div>
      </div>
    </div>
  )
}
