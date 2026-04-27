import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { auth } from '../services/api'

export default function RedefinirSenha() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = useMemo(() => params.get('token') || '', [params])

  const [senha, setSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')
    setOk('')

    if (!token) {
      setErro('Link inválido. Solicite uma nova recuperação de senha.')
      return
    }

    if (senha.length < 8) {
      setErro('A nova senha precisa ter no mínimo 8 caracteres.')
      return
    }

    if (senha !== confirmacao) {
      setErro('A confirmação de senha não confere.')
      return
    }

    setCarregando(true)
    try {
      await auth.resetPassword(token, senha)
      setOk('Senha redefinida com sucesso. Você já pode entrar no sistema.')
      setTimeout(() => navigate('/login'), 1200)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível redefinir a senha.')
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
            <div className="auth-brand-title">Redefinir senha</div>
            <div className="auth-brand-subtitle">Escolha uma nova senha para sua conta</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} autoComplete="off">
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">Nova senha</label>
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
              autoComplete="new-password"
              className="form-input"
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label className="form-label">Confirmar nova senha</label>
            <input
              type="password"
              value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
              required
              autoComplete="new-password"
              className="form-input"
            />
          </div>

          {erro && <p className="form-error">{erro}</p>}
          {ok && <p style={{ color: 'var(--link)', fontSize: 13, marginBottom: 10 }}>{ok}</p>}

          <button type="submit" disabled={carregando} className="form-submit">
            {carregando ? 'Atualizando...' : 'Atualizar senha'}
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
