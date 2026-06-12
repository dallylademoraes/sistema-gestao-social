import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import BarChart from '../components/charts/BarChart'
import ChartCard from '../components/charts/ChartCard'
import DonutChart from '../components/charts/DonutChart'
import api, { cadastros } from '../services/api'
import { baixarBlob, baixarGraficoPng } from '../utils/exportCsv'
import {
    cadastrosPorMes,
    corRacaDistribuicao,
    encaminhamentoDistribuicao,
    faixaEtariaDistribuicao,
    identidadeGeneroDistribuicao,
    pcdDistribuicao,
    rendaDistribuicao,
    statusDistribuicao,
    topCidades,
} from '../utils/painelStats'

function Metrica({ label, valor, cor }) {
  return (
    <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1rem 1.25rem' }}>
      <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, color: cor || 'var(--text-main)' }}>{valor}</div>
    </div>
  )
}

const CORES_STATUS = {
  Ativos: 'var(--metric-accent-1)',
  Pendentes: 'var(--metric-accent-2)',
  Inativos: 'var(--text-soft)',
}

export default function Painel() {
  const location = useLocation()
  const painelParams = { limit: 500 }
  const [lista, setLista] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [exportando, setExportando] = useState('')
  const [erro, setErro] = useState('')
  const [comparativo, setComparativo] = useState(null)

  const carregar = useCallback(() => {
    setErro('')
    // Verifica cache antes de iniciar carregamento
    const cached = cadastros.listarCached(painelParams)
    if (!cached) setCarregando(true)
    
    return Promise.all([
      cadastros.listarCached(painelParams),
      api.get('/cadastros/relatorio/comparativo').catch(() => null),
    ])
      .then(([r, relatorio]) => {
        setLista(Array.isArray(r.data) ? r.data : [])
        if (relatorio?.data) setComparativo(relatorio.data)
      })
      .catch(() => {
        setLista([])
        setErro('Não foi possível carregar os dados do painel.')
      })
      .finally(() => setCarregando(false))
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar, location.key])

  const stats = useMemo(() => {
    const porStatus = statusDistribuicao(lista).map((d) => ({
      ...d,
      color: CORES_STATUS[d.label] || undefined,
    }))
    return {
      porStatus,
      porMes: cadastrosPorMes(lista),
      cidades: topCidades(lista),
      pcd: pcdDistribuicao(lista),
      genero: identidadeGeneroDistribuicao(lista),
      corRaca: corRacaDistribuicao(lista),
      renda: rendaDistribuicao(lista),
      faixaEtaria: faixaEtariaDistribuicao(lista),
      encaminhamentos: encaminhamentoDistribuicao(lista),
    }
  }, [lista])

  const total = lista.length
  const ativos = lista.filter((c) => c.status === 'ativo').length
  const pendentes = lista.filter((c) => c.status === 'pendente').length
  const comEncam = lista.filter((c) => c.com_encaminhamento).length
  const pendentesLista = lista.filter((c) => c.status === 'pendente')

  const exportarCadastros = async () => {
      setExportando('cadastros')
      try {
        const blob = await cadastros.exportarCadastrosXlsx()
        baixarBlob(blob, 'cadastros_asap.xlsx')
      } finally {
        setExportando('')
      }
    }

  const exportarResumoGraficos = async () => {
    setExportando('graficos')
    try {
      const blob = await cadastros.exportarGraficosXlsx()
      baixarBlob(blob, 'resumo_graficos_asap.xlsx')
    } finally {
      setExportando('')
    }
  }

  const exportarComparativoPdf = async () => {
    setExportando('comparativo')
    try {
      const blob = await api.get('/cadastros/export/comparativo.pdf', { responseType: 'blob' }).then(r => r.data)
      baixarBlob(blob, 'relatorio_comparativo_mensal_asap.pdf')
    } finally {
      setExportando('')
    }
  }

  const variacaoLabel = (valor) => {
    if (typeof valor !== 'number') return '0%'
    const sinal = valor > 0 ? '+' : ''
    return `${sinal}${valor}%`
  }

  const acaoPngGrafico = (titulo, data) => (
    <button
      type="button"
      className="btn-compact"
      onClick={() => baixarGraficoPng(titulo, data)}
      style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', padding: '6px 8px', cursor: 'pointer' }}
    >
      PNG
    </button>
  )
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