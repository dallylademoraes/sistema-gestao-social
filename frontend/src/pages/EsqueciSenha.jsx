import { Link } from 'react-router-dom'

export default function EsqueciSenha() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark">ASAP</div>
          <div>
            <div className="auth-brand-title">Recuperar acesso</div>
            <div className="auth-brand-subtitle">Instruções para acesso</div>
          </div>
        </div>

        <div style={{ textAlign: 'center', margin: '20px 0', fontSize: '14px', lineHeight: '1.5' }}>
          <p>
            Para recuperar o seu acesso ou redefinir a sua senha, por favor, <strong>fale com a coordenadora</strong>.
          </p>
          <p style={{ marginTop: '10px' }}>
            Ela que cria os logins, então poderá redefinir a senha para você.
          </p>
        </div>

        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <Link to="/login" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-block' }}>
            Voltar ao login
          </Link>
        </div>
      </div>
    </div>
  )
}
