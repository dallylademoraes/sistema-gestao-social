import { useEffect, useMemo, useState } from 'react'
import { cadastros as api } from '../services/api'
import { Link } from 'react-router-dom'
import ChartCard from '../components/charts/ChartCard'
import BarChart from '../components/charts/BarChart'
import DonutChart from '../components/charts/DonutChart'
import {
  statusDistribuicao,
  cadastrosPorMes,
  termosLgpd,
  topCidades,
  pcdDistribuicao,
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
  const [lista, setLista] = useState([])
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    setCarregando(true)
    api.listar({ limit: 500 })
      .then((r) => setLista(r.data))
      .finally(() => setCarregando(false))
  }, [])

  const stats = useMemo(() => {
    const porStatus = statusDistribuicao(lista).map((d) => ({
      ...d,
      color: CORES_STATUS[d.label] || undefined,
    }))
    return {
      porStatus,
      porMes: cadastrosPorMes(lista),
      termos: termosLgpd(lista),
      cidades: topCidades(lista),
      pcd: pcdDistribuicao(lista),
    }
  }, [lista])

  const total = lista.length
  const ativos = lista.filter((c) => c.status === 'ativo').length
  const pendentes = lista.filter((c) => c.status === 'pendente').length
  const comEncam = lista.filter((c) => c.com_encaminhamento).length
  const pendentesLista = lista.filter((c) => c.status === 'pendente')

  return (
    <div className="painel-page">
      <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: '1.5rem' }}>Painel</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: '1.5rem' }}>
        <Metrica label="Total de cadastros" valor={carregando ? '…' : total} />
        <Metrica label="Ativos" valor={carregando ? '…' : ativos} cor="var(--metric-accent-1)" />
        <Metrica label="Pendentes" valor={carregando ? '…' : pendentes} cor="var(--metric-accent-2)" />
        <Metrica label="Com encaminhamento" valor={carregando ? '…' : comEncam} cor="var(--metric-accent-3)" />
      </div>

      {!carregando && lista.length > 0 && (
        <div className="painel-charts-grid">
          <ChartCard title="Cadastros por status" subtitle="Distribuição atual na base">
            <BarChart data={stats.porStatus} height={220} />
          </ChartCard>

          <ChartCard title="Novos cadastros" subtitle="Últimos 6 meses">
            <BarChart data={stats.porMes} height={220} />
          </ChartCard>

          <ChartCard title="Termos LGPD" subtitle="Documentação dos termos gerados">
            <DonutChart data={stats.termos} />
          </ChartCard>

          <ChartCard title="PCD" subtitle="Pessoas com deficiência declarada">
            <DonutChart data={stats.pcd} size={150} />
          </ChartCard>

          <ChartCard title="Principais cidades" subtitle="Top 5 com mais cadastros" className="chart-card--wide">
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
