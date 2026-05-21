export default function ChartCard({ title, subtitle, children, className = '', actions = null }) {
  return (
    <div className={`chart-card ${className}`.trim()}>
      <div className="chart-card-header">
        <div>
          <h2 className="chart-card-title">{title}</h2>
          {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="chart-card-actions">{actions}</div>}
      </div>
      <div className="chart-card-body">{children}</div>
    </div>
  )
}
