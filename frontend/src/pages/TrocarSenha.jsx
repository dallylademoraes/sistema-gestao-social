import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function TrocarSenha() {
  const { trocarSenha, logout } = useAuth()
  const navigate = useNavigate()
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [erro, setErro] = useState('')
  const [carregando, setCarregando] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErro('')

    if (novaSenha.length < 8) {
      setErro('A nova senha precisa ter no mínimo 8 caracteres.')
      return
    }
    if (novaSenha !== confirmacao) {
      setErro('A confirmação de senha não confere.')
      return
    }

    setCarregando(true)
    try {
      await trocarSenha(senhaAtual, novaSenha)
      navigate('/')
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível alterar a senha.')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="centered-form-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <div>
            <div className="auth-brand-title">Trocar senha</div>
            <div className="auth-brand-subtitle">Defina uma senha permanente para continuar</div>
          </div>
        </div>

        <form onSubmit={submit}>
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">Senha temporária</label>
            <input
              className="form-input"
              type="password"
              value={senhaAtual}
              onChange={(e) => setSenhaAtual(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label className="form-label">Nova senha</label>
            <input
              className="form-input"
              type="password"
              value={novaSenha}
              onChange={(e) => setNovaSenha(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>

          <div style={{ marginBottom: 18 }}>
            <label className="form-label">Confirmar nova senha</label>
            <input
              className="form-input"
              type="password"
              value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>

          {erro && (
            <div
              role="alert"
              style={{
                marginBottom: 16,
                padding: '10px 12px',
                borderRadius: 10,
                border: '1px solid var(--danger)',
                background: 'rgba(192, 57, 43, 0.08)',
                color: 'var(--text-main)',
                fontSize: 13,
              }}
            >
              {erro}
            </div>
          )}

          <button type="submit" className="form-submit" disabled={carregando}>
            {carregando ? 'Salvando...' : 'Salvar nova senha'}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={logout}
            style={{ width: '100%', marginTop: 10 }}
          >
            Sair
          </button>
        </form>
      </div>
    </div>
  )
}
