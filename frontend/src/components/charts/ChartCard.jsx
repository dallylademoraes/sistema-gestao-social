export default function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <div className={`chart-card ${className}`.trim()}>
      <div className="chart-card-header">
        <h2 className="chart-card-title">{title}</h2>
        {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
      </div>
      <div className="chart-card-body">{children}</div>
    </div>
  )
}
