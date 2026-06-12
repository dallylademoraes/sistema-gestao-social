const CORES_PADRAO = [
  'var(--metric-accent-1)',
  'var(--metric-accent-2)',
  'var(--metric-accent-3)',
  '#6b9fd4',
]

function arco(cx, cy, r, inicio, fim) {
  const rad = (deg) => (deg * Math.PI) / 180
  const x1 = cx + r * Math.cos(rad(inicio))
  const y1 = cy + r * Math.sin(rad(inicio))
  const x2 = cx + r * Math.cos(rad(fim))
  const y2 = cy + r * Math.sin(rad(fim))
  const grande = fim - inicio > 180 ? 1 : 0
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${grande} 1 ${x2} ${y2} Z`
}

export default function DonutChart({ data, size = 168 }) {
  if (!data?.length) {
    return <p className="chart-empty">Sem dados para exibir.</p>
  }

  const total = data.reduce((s, d) => s + d.value, 0) || 1
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.38
  let angulo = -90

  const fatias = data.map((item, i) => {
    const sweep = (item.value / total) * 360
    const inicio = angulo
    const fim = angulo + sweep
    angulo = fim
    const cor = item.color || CORES_PADRAO[i % CORES_PADRAO.length]
    return { ...item, path: arco(cx, cy, r, inicio, fim), cor, pct: Math.round((item.value / total) * 100) }
  })

  return (
    <div className="donut-chart">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Gráfico de rosca">
        {fatias.map((f) => (
          <path key={f.label} d={f.path} fill={f.cor} stroke="var(--surface-card)" strokeWidth="2" />
        ))}
        <circle cx={cx} cy={cy} r={r * 0.52} fill="var(--surface-card)" />
        <text x={cx} y={cy - 4} textAnchor="middle" className="donut-chart-total" fontSize="22" fontWeight="700" fill="var(--text-main)">
          {total}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="10" fill="var(--text-soft)">
          total
        </text>
      </svg>
      <ul className="donut-chart-legend">
        {fatias.map((f) => (
          <li key={f.label}>
            <span className="donut-chart-swatch" style={{ background: f.cor }} />
            <span className="donut-chart-legend-label">{f.label}</span>
            <span className="donut-chart-legend-value">
              {f.value} ({f.pct}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
