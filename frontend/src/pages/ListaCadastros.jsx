import { useEffect, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { cadastros as api } from '../services/api'
import { baixarBlob } from '../utils/exportCsv'

const badge = {
  ativo: { background: 'var(--badge-active-bg)', color: 'var(--badge-active-text)' },
  pendente: { background: 'var(--badge-pending-bg)', color: 'var(--badge-pending-text)' },
  inativo: { background: 'var(--badge-inactive-bg)', color: 'var(--badge-inactive-text)' },
}

export default function ListaCadastros() {
  const { usuario } = useAuth()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [busca, setBusca] = useState(searchParams.get('busca') || '')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [pcd, setPcd] = useState(searchParams.get('pcd') || '')
  const [lgpd, setLgpd] = useState(searchParams.get('lgpd') || '')
  const paramsIniciais = {
    busca: searchParams.get('busca') || undefined,
    status: searchParams.get('status') || undefined,
    pcd: searchParams.get('pcd') || undefined,
    lgpd_concluido: searchParams.get('lgpd') || undefined,
  }
  const [lista, setLista] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [exportando, setExportando] = useState(false)
  const [erro, setErro] = useState('')
  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)

  const paramsDaTela = (valores = { busca, status, pcd, lgpd }) => {
    const params = {}
    if (valores.busca) params.busca = valores.busca
    if (valores.status) params.status = valores.status
    if (valores.pcd) params.pcd = valores.pcd
    if (valores.lgpd) params.lgpd = valores.lgpd
    return params
  }

  const paramsApi = (valores = { busca, status, pcd, lgpd }) => ({
    busca: valores.busca || undefined,
    status: valores.status || undefined,
    pcd: valores.pcd || undefined,
    lgpd_concluido: valores.lgpd || undefined,
    _ts: Date.now(),
  })

  const carregar = (valores = { busca, status, pcd, lgpd }) => {
    setErro('')
    const params = paramsApi(valores)
    setCarregando(true)
    api.listarCached(params)
      .then((r) => setLista(r.data))
      .catch(() => {
        setLista([])
        setErro('Não foi possível carregar os cadastros.')
      })
      .finally(() => setCarregando(false))
  }

  const atualizarFiltro = (campo, valor) => {
    const valores = { busca, status, pcd, lgpd, [campo]: valor }
    if (campo === 'status') setStatus(valor)
    if (campo === 'pcd') setPcd(valor)
    if (campo === 'lgpd') setLgpd(valor)
    setSearchParams(paramsDaTela(valores))
  }

  useEffect(() => {
    const valores = {
      busca: searchParams.get('busca') || '',
      status: searchParams.get('status') || '',
      pcd: searchParams.get('pcd') || '',
      lgpd: searchParams.get('lgpd') || '',
    }
    setBusca(valores.busca)
    setStatus(valores.status)
    setPcd(valores.pcd)
    setLgpd(valores.lgpd)
    carregar(valores)
  }, [location.key, searchParams])

  const handleBusca = (e) => {
    e.preventDefault()
    const valores = { busca, status, pcd, lgpd }
    setSearchParams(paramsDaTela(valores))
  }

  const paramsAtuais = () => ({
    busca: busca || undefined,
    status: status || undefined,
    pcd: pcd || undefined,
    lgpd_concluido: lgpd || undefined,
  })

  const exportarCadastros = async () => {
    setExportando(true)
    try {
      const blob = await api.exportarCadastrosXlsx(paramsAtuais())
      baixarBlob(blob, 'cadastros_asap.xlsx')
    } finally {
      setExportando(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500 }}>Cadastros</h1>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button type="button" className="btn-secondary" onClick={exportarCadastros} disabled={exportando}>
            {exportando ? 'Exportando...' : 'Exportar Excel'}
          </button>
          {podeCriarOuEditarCadastro && (
            <Link to="/cadastros/novo" className="btn-primary" style={{ textDecoration: 'none' }}>
              + Novo
            </Link>
          )}
        </div>
      </div>

      <form onSubmit={handleBusca} style={{ display: 'flex', gap: 8, marginBottom: '1rem', flexWrap: 'wrap' }}>
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por nome ou CPF..."
          style={{ flex: 1, minWidth: 200 }}
          className="form-input"
        />
        <select value={status} onChange={(e) => atualizarFiltro('status', e.target.value)} className="form-select" style={{ width: 'auto' }}>
          <option value="">Todos os status</option>
          <option value="ativo">Ativo</option>
          <option value="pendente">Pendente</option>
          <option value="inativo">Inativo</option>
        </select>
        <select value={pcd} onChange={(e) => atualizarFiltro('pcd', e.target.value)} className="form-select" style={{ width: 'auto' }}>
          <option value="">PCD</option>
          <option value="true">Sim</option>
          <option value="false">Não</option>
        </select>
        <select value={lgpd} onChange={(e) => atualizarFiltro('lgpd', e.target.value)} className="form-select" style={{ width: 'auto' }}>
          <option value="">Termos</option>
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
        ) : erro ? (
          <p style={{ padding: '1.5rem', color: 'var(--danger)', fontSize: 14 }}>{erro}</p>
        ) : lista.length === 0 ? (
          <p style={{ padding: '1.5rem', color: 'var(--text-soft)', fontSize: 14 }}>Nenhum cadastro encontrado.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--surface-subtle)' }}>
                {['Nome', 'CPF', 'Cidade/UF', 'Gênero', 'PCD', 'Termos', 'Status', ''].map((h) => (
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
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ ...badge[c.status], padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 500 }}>
                      {c.status}
                    </span>
                  </td>
                  <td style={{ padding: '11px 14px' }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <Link to={`/cadastros/${c.id}`} style={{ color: 'var(--link)', fontSize: 13, textDecoration: 'none', fontWeight: 700 }}>Ver</Link>
                      {!c.lgpd_concluido && podeCriarOuEditarCadastro && (
                        <Link to={`/cadastros/${c.id}/assinar`} style={{ color: 'var(--link)', fontSize: 13, textDecoration: 'none', fontWeight: 700 }}>Assinar</Link>
                      )}
                    </div>
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
