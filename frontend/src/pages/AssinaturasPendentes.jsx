import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { cadastros as api } from '../services/api'
import { useAuth } from '../hooks/useAuth'

export default function AssinaturasPendentes() {
  const { usuario } = useAuth()
  const location = useLocation()
  const listaParams = { lgpd_concluido: false, limit: 100 }
  const [lista, setLista] = useState(() => api.getCachedList(listaParams) || [])
  const [carregando, setCarregando] = useState(() => !api.getCachedList(listaParams))
  const [erro, setErro] = useState('')
  const podeAssinar = ['coordenadora', 'assistente'].includes(usuario?.perfil)

  const carregar = () => {
    setErro('')
    const cached = api.getCachedList(listaParams)
    if (cached) {
      setLista(cached)
      setCarregando(false)
    } else {
      setCarregando(true)
    }
    api.listarCached(listaParams)
      .then((r) => setLista(r.data))
      .catch(() => {
        setLista([])
        setErro('Não foi possível carregar as assinaturas pendentes.')
      })
      .finally(() => setCarregando(false))
  }

  useEffect(() => {
    carregar()
    const timer = setInterval(carregar, 8000)
    return () => clearInterval(timer)
  }, [location.key])

  if (!podeAssinar) {
    return (
      <div className="centered-form-shell">
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Sem permissão</h1>
        <p style={{ color: 'var(--text-muted)' }}>Seu perfil não pode coletar assinaturas.</p>
      </div>
    )
  }

  return (
    <div className="centered-form-shell">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Assinaturas pendentes</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '6px 0 0' }}>Abra esta tela no tablet e toque no cadastro da pessoa atendida.</p>
        </div>
        <button type="button" className="btn-secondary" onClick={carregar}>Atualizar</button>
      </div>

      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        {carregando ? (
          <p style={{ padding: '1.25rem', color: 'var(--text-soft)', fontSize: 14 }}>Carregando...</p>
        ) : erro ? (
          <p style={{ padding: '1.25rem', color: 'var(--danger)', fontSize: 14 }}>{erro}</p>
        ) : lista.length === 0 ? (
          <p style={{ padding: '1.25rem', color: 'var(--text-soft)', fontSize: 14 }}>Nenhuma assinatura pendente.</p>
        ) : (
          <div>
            {lista.map((c) => (
              <Link
                key={c.id}
                to={`/cadastros/${c.id}/assinar`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 12,
                  padding: '16px 18px',
                  borderBottom: '1px solid var(--row-border)',
                  textDecoration: 'none',
                  color: 'var(--text-main)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>{c.nome_social || c.nome}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 3 }}>CPF {c.cpf} · {c.telefone}</div>
                </div>
                <span className="btn-primary" style={{ whiteSpace: 'nowrap' }}>Assinar</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
