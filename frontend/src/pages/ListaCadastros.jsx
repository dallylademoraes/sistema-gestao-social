import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { cadastros as api } from '../services/api'
import { useAuth } from '../hooks/useAuth'

const badge = {
  ativo: { background: 'var(--badge-active-bg)', color: 'var(--badge-active-text)' },
  pendente: { background: 'var(--badge-pending-bg)', color: 'var(--badge-pending-text)' },
  inativo: { background: 'var(--badge-inactive-bg)', color: 'var(--badge-inactive-text)' },
}

export default function ListaCadastros() {
  const { usuario } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [lista, setLista] = useState([])
  const [busca, setBusca] = useState(searchParams.get('busca') || '')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [pcd, setPcd] = useState(searchParams.get('pcd') || '')
  const [lgpd, setLgpd] = useState(searchParams.get('lgpd') || '')
  const [carregando, setCarregando] = useState(true)
  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)

  const sincronizarUrl = () => {
    const params = {}
    if (busca) params.busca = busca
    if (status) params.status = status
    if (pcd) params.pcd = pcd
    if (lgpd) params.lgpd = lgpd
    setSearchParams(params)
  }

  const carregar = () => {
    sincronizarUrl()
    setCarregando(true)
    api.listar({
      busca: busca || undefined,
      status: status || undefined,
      pcd: pcd || undefined,
      lgpd_concluido: lgpd || undefined,
    })
      .then((r) => setLista(r.data))
      .finally(() => setCarregando(false))
  }

  useEffect(() => { carregar() }, [status, pcd, lgpd])

  const handleBusca = (e) => {
    e.preventDefault()
    carregar()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500 }}>Cadastros</h1>
        {podeCriarOuEditarCadastro && (
          <Link to="/cadastros/novo" className="btn-primary" style={{ textDecoration: 'none' }}>
            + Novo
          </Link>
        )}
      </div>

      <form onSubmit={handleBusca} style={{ display: 'flex', gap: 8, marginBottom: '1rem', flexWrap: 'wrap' }}>
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por nome ou CPF..."
          style={{ flex: 1, minWidth: 200 }}
          className="form-input"
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="form-select" style={{ width: 'auto' }}>
          <option value="">Todos os status</option>
          <option value="ativo">Ativo</option>
          <option value="pendente">Pendente</option>
          <option value="inativo">Inativo</option>
        </select>
        <select value={pcd} onChange={(e) => setPcd(e.target.value)} className="form-select" style={{ width: 'auto' }}>
          <option value="">PCD</option>
          <option value="true">Sim</option>
          <option value="false">Não</option>
        </select>
        <select value={lgpd} onChange={(e) => setLgpd(e.target.value)} className="form-select" style={{ width: 'auto' }}>
          <option value="">LGPD</option>
          <option value="true">Concluído</option>
          <option value="false">Pendente</option>
        </select>
        <button type="submit" className="btn-secondary">
          Buscar
        </button>
      </form>

      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        {carregando ? (
          <p style={{ padding: '1.5rem', color: 'var(--text-soft)', fontSize: 14 }}>Carregando...</p>
        ) : lista.length === 0 ? (
          <p style={{ padding: '1.5rem', color: 'var(--text-soft)', fontSize: 14 }}>Nenhum cadastro encontrado.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--surface-subtle)' }}>
                {['Nome', 'CPF', 'Cidade/UF', 'Gênero', 'PCD', 'LGPD', 'Status LGPD', 'Status', ''].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, fontSize: 11, color: 'var(--text-soft)', borderBottom: '1px solid var(--border)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lista.map((c) => (
                <tr key={c.id} style={{ borderBottom: '1px solid var(--row-border)' }}>
                  <td style={{ padding: '11px 14px', fontWeight: 600 }}>{c.nome_social || c.nome}</td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>{c.cpf}</td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)' }}>{c.cidade}/{c.uf}</td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)' }}>{c.identidade_genero || '—'}</td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)' }}>{c.pcd ? 'Sim' : 'Não'}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{
                      background: c.lgpd_concluido ? 'var(--badge-active-bg)' : 'var(--badge-pending-bg)',
                      color: c.lgpd_concluido ? 'var(--badge-active-text)' : 'var(--badge-pending-text)',
                      padding: '3px 10px',
                      borderRadius: 999,
                      fontSize: 11,
                      fontWeight: 700,
                    }}>
                      {c.lgpd_concluido ? 'Ok' : 'Pendente'}
                    </span>
                  </td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)' }}>{c.status_lgpd || 'pendente'}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ ...badge[c.status], padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 500 }}>
                      {c.status}
                    </span>
                  </td>
                  <td style={{ padding: '11px 14px' }}>
                    <Link to={`/cadastros/${c.id}`} style={{ color: 'var(--link)', fontSize: 13, textDecoration: 'none', fontWeight: 700 }}>Ver</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
