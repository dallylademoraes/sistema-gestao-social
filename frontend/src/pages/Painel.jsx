import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import BarChart from '../components/charts/BarChart'
import ChartCard from '../components/charts/ChartCard'
import DonutChart from '../components/charts/DonutChart'
import { cadastros as api } from '../services/api'
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
  const [lista, setLista] = useState(() => api.getCachedList(painelParams) || [])
  const [carregando, setCarregando] = useState(() => !api.getCachedList(painelParams))
  const [exportando, setExportando] = useState('')
  const [erro, setErro] = useState('')

  const carregar = useCallback(() => {
    setErro('')
    const cached = api.getCachedList(painelParams)
    if (!cached) setCarregando(true)
    return api.listarCached(painelParams)
      .then((r) => {
        setLista(Array.isArray(r.data) ? r.data : [])
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

  useEffect(() => {
    const recarregarSeVisivel = () => {
      if (!document.hidden) carregar()
    }
    window.addEventListener('focus', recarregarSeVisivel)
    window.addEventListener('pageshow', recarregarSeVisivel)
    return () => {
      window.removeEventListener('focus', recarregarSeVisivel)
      window.removeEventListener('pageshow', recarregarSeVisivel)
    }
  }, [carregar])

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
      const blob = await api.exportarCadastrosXlsx()
      baixarBlob(blob, 'cadastros_asap.xlsx')
    } finally {
      setExportando('')
    }
  }

  const exportarResumoGraficos = async () => {
    setExportando('graficos')
    try {
      const blob = await api.exportarGraficosXlsx()
      baixarBlob(blob, 'resumo_graficos_asap.xlsx')
    } finally {
      setExportando('')
    }
  }

  const acaoPngGrafico = (titulo, data) => (
    <button
      type="button"
      className="btn-compact"
      onClick={() => baixarGraficoPng(titulo, data)}
      title="Baixar PNG"
      style={{
        background: 'transparent',
        border: 'none',
        color: 'var(--text-muted)',
        padding: '6px 8px',
        fontSize: 12,
        cursor: 'pointer',
      }}
    >
      PNG
    </button>
  )

  return (
    <div className="painel-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, margin: 0 }}>Painel</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '6px 0 0' }}>Exporte a base e os resumos para montar relatórios no Excel.</p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button type="button" className="btn-compact" onClick={exportarResumoGraficos} disabled={Boolean(exportando)}>
            {exportando === 'graficos' ? 'Exportando...' : 'Exportar gráficos (Excel)'}
          </button>
          <button type="button" className="btn-compact" onClick={exportarCadastros} disabled={Boolean(exportando)}>
            {exportando === 'cadastros' ? 'Exportando...' : 'Exportar cadastros (Excel)'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: '1.5rem' }}>
        <Metrica label="Total de cadastros" valor={carregando ? '…' : total} />
        <Metrica label="Ativos" valor={carregando ? '…' : ativos} cor="var(--metric-accent-1)" />
        <Metrica label="Pendentes" valor={carregando ? '…' : pendentes} cor="var(--metric-accent-2)" />
        <Metrica label="Com encaminhamento" valor={carregando ? '…' : comEncam} cor="var(--metric-accent-3)" />
      </div>

      {erro && (
        <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1rem', color: 'var(--danger)', fontSize: 14, marginBottom: '1.5rem' }}>
          {erro}
        </div>
      )}

      {!carregando && lista.length > 0 && (
        <div className="painel-charts-grid">
          <ChartCard title="Cadastros por status" subtitle="Distribuição atual na base" actions={acaoPngGrafico('Cadastros por status', stats.porStatus)}>
            <BarChart data={stats.porStatus} height={220} />
          </ChartCard>

          <ChartCard title="Novos cadastros" subtitle="Últimos 6 meses" actions={acaoPngGrafico('Novos cadastros', stats.porMes)}>
            <BarChart data={stats.porMes} height={220} />
          </ChartCard>

          <ChartCard title="Faixa etária" subtitle="Perfil etário das pessoas atendidas" actions={acaoPngGrafico('Faixa etária', stats.faixaEtaria)}>
            <BarChart data={stats.faixaEtaria} height={220} />
          </ChartCard>

          <ChartCard title="PCD" subtitle="Pessoas com deficiência declarada" actions={acaoPngGrafico('PCD', stats.pcd)}>
            <DonutChart data={stats.pcd} size={150} />
          </ChartCard>

          <ChartCard title="Encaminhamentos" subtitle="Demandas com encaminhamento registrado" actions={acaoPngGrafico('Encaminhamentos', stats.encaminhamentos)}>
            <DonutChart data={stats.encaminhamentos} size={150} />
          </ChartCard>

          <ChartCard title="Renda média" subtitle="Distribuição socioeconômica declarada" actions={acaoPngGrafico('Renda média', stats.renda)}>
            <BarChart data={stats.renda} vertical={false} />
          </ChartCard>

          <ChartCard title="Cor/raça" subtitle="Autodeclaração registrada no cadastro" actions={acaoPngGrafico('Cor raça', stats.corRaca)}>
            <BarChart data={stats.corRaca} vertical={false} />
          </ChartCard>

          <ChartCard title="Identidade de gênero" subtitle="Top categorias informadas" actions={acaoPngGrafico('Identidade de gênero', stats.genero)}>
            <BarChart data={stats.genero} vertical={false} />
          </ChartCard>

          <ChartCard title="Principais cidades" subtitle="Top 5 com mais cadastros" className="chart-card--wide" actions={acaoPngGrafico('Principais cidades', stats.cidades)}>
            <BarChart data={stats.cidades} vertical={false} />
          </ChartCard>
        </div>
      )}

      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.25rem', marginTop: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: 15, fontWeight: 500 }}>Pendentes de aprovação</h2>
          <Link to="/cadastros?status=pendente" style={{ fontSize: 13, color: 'var(--link)', textDecoration: 'none', fontWeight: 700 }}>Ver todos</Link>
        </div>
        {carregando ? (
          <p style={{ fontSize: 14, color: 'var(--text-soft)' }}>Carregando…</p>
        ) : pendentesLista.length === 0 ? (
          <p style={{ fontSize: 14, color: 'var(--text-soft)' }}>Nenhum cadastro pendente.</p>
        ) : (
          pendentesLista.slice(0, 5).map((c) => (
            <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--row-border)' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{c.nome}</div>
                <div style={{ fontSize: 12, color: 'var(--text-soft)' }}>{c.cidade}/{c.uf} · {c.cpf}</div>
              </div>
              <Link to={`/cadastros/${c.id}`} style={{ fontSize: 13, color: 'var(--link)', textDecoration: 'none', fontWeight: 700 }}>Ver</Link>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
