import { NavLink, Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'

const linkStyle = (ativo) => ({
  display: 'block',
  padding: '8px 12px',
  borderRadius: 8,
  fontSize: 14,
  color: ativo ? 'var(--nav-active-text)' : 'var(--nav-text)',
  background: ativo ? 'var(--nav-active-bg)' : 'transparent',
  textDecoration: 'none',
  fontWeight: ativo ? 700 : 500,
})

export default function Layout() {
  const { usuario, logout, carregando } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)
  const podeGerenciarUsuarios = usuario?.perfil === 'coordenadora'

  if (carregando) return null
  if (!usuario) return <Navigate to="/login" />

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ width: 232, background: 'var(--surface-elevated)', borderRight: '1px solid var(--border)', padding: '1.25rem 1rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '2rem' }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'linear-gradient(145deg, #2fb383 0%, #1f8a65 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 11 }}>
            ASAP
          </div>
          <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)' }}>Cadastros</span>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-soft)', marginBottom: 6, padding: '0 10px' }}>
              Operação
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <NavLink to="/" end style={({ isActive }) => linkStyle(isActive)}>Painel</NavLink>
              <NavLink to="/cadastros" style={({ isActive }) => linkStyle(isActive)}>Cadastros</NavLink>
              {podeCriarOuEditarCadastro && (
                <NavLink to="/cadastros/novo" style={({ isActive }) => linkStyle(isActive)}>Novo cadastro</NavLink>
              )}
            </div>
          </div>

          {podeGerenciarUsuarios && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-soft)', marginBottom: 6, padding: '0 10px' }}>
                Administração
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <NavLink to="/usuarios" style={({ isActive }) => linkStyle(isActive)}>Usuários</NavLink>
              </div>
            </div>
          )}
        </nav>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={toggleTheme}
            aria-label={`Alternar para modo ${isDark ? 'claro' : 'escuro'}`}
            aria-pressed={isDark}
            style={{ width: '100%', marginBottom: 12 }}
          >
            {isDark ? 'Modo claro' : 'Modo escuro'}
          </button>
          <div style={{ fontSize: 13, color: 'var(--text-main)', marginBottom: 4, fontWeight: 600 }}>{usuario.nome}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>{usuario.perfil}</div>
          <button
            onClick={logout}
            style={{ fontSize: 13, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontWeight: 600 }}
          >
            Sair
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: '2rem', overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
