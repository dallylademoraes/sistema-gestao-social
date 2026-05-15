const CORES_PADRAO = [
  'var(--metric-accent-1)',
  'var(--metric-accent-2)',
  'var(--metric-accent-3)',
  '#6b9fd4',
  '#c47eb5',
]

export default function BarChart({ data, vertical = true, height = 200 }) {
  if (!data?.length) {
    return <p className="chart-empty">Sem dados para exibir.</p>
  }

  const max = Math.max(...data.map((d) => d.value), 1)

  if (vertical) {
    return (
      <div className="bar-chart bar-chart--vertical" style={{ height }}>
        <div className="bar-chart-bars">
          {data.map((item, i) => {
            const pct = (item.value / max) * 100
            const cor = item.color || CORES_PADRAO[i % CORES_PADRAO.length]
            return (
              <div key={item.label} className="bar-chart-col">
                <span className="bar-chart-value">{item.value}</span>
                <div
                  className="bar-chart-bar-wrap"
                  style={{ height: `calc(${height}px - 52px)` }}
                >
                  <div
                    className="bar-chart-bar"
                    style={{ height: `${pct}%`, background: cor }}
                    title={`${item.label}: ${item.value}`}
                  />
                </div>
                <span className="bar-chart-label">{item.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="bar-chart bar-chart--horizontal">
      {data.map((item, i) => {
        const pct = (item.value / max) * 100
        const cor = item.color || CORES_PADRAO[i % CORES_PADRAO.length]
        return (
          <div key={item.label} className="bar-chart-row">
            <span className="bar-chart-row-label" title={item.label}>
              {item.label}
            </span>
            <div className="bar-chart-row-track">
              <div
                className="bar-chart-row-fill"
                style={{ width: `${pct}%`, background: cor }}
              />
            </div>
            <span className="bar-chart-row-value">{item.value}</span>
          </div>
        )
      })}
    </div>
  )
}
