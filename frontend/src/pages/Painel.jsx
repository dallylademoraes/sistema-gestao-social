import { useEffect, useState } from 'react'
import { cadastros as api } from '../services/api'
import { Link } from 'react-router-dom'

function Metrica({ label, valor, cor }) {
  return (
    <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1rem 1.25rem' }}>
      <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, color: cor || 'var(--text-main)' }}>{valor}</div>
    </div>
  )
}

export default function Painel() {
  const [lista, setLista] = useState([])

  useEffect(() => {
    api.listar({ limit: 200 }).then((r) => setLista(r.data))
  }, [])

  const total = lista.length
  const ativos = lista.filter((c) => c.status === 'ativo').length
  const pendentes = lista.filter((c) => c.status === 'pendente').length
  const comEncam = lista.filter((c) => c.com_encaminhamento).length

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: '1.5rem' }}>Painel</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: '2rem' }}>
        <Metrica label="Total de cadastros" valor={total} />
        <Metrica label="Ativos" valor={ativos} cor="var(--metric-accent-1)" />
        <Metrica label="Pendentes" valor={pendentes} cor="var(--metric-accent-2)" />
        <Metrica label="Com encaminhamento" valor={comEncam} cor="var(--metric-accent-3)" />
      </div>

      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: 15, fontWeight: 500 }}>Pendentes de aprovação</h2>
          <Link to="/cadastros?status=pendente" style={{ fontSize: 13, color: 'var(--link)', textDecoration: 'none', fontWeight: 700 }}>Ver todos</Link>
        </div>
        {lista.filter((c) => c.status === 'pendente').length === 0 ? (
          <p style={{ fontSize: 14, color: 'var(--text-soft)' }}>Nenhum cadastro pendente.</p>
        ) : (
          lista.filter((c) => c.status === 'pendente').slice(0, 5).map((c) => (
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
