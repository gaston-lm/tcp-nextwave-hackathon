import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './overrides.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const API_REQUEST_OPTIONS = {
  headers: { 'ngrok-skip-browser-warning': '1' },
}

const severityColors = {
  urgent: 'magenta',
  high: 'cyan',
  medium: 'violet',
  low: 'gray',
}

const severityHexColors = {
  urgent: '#db1686',
  high: '#00bfc6',
  medium: '#915ee9',
  low: '#c9c9d0',
}

const scopeLabels = {
  provider: 'Provider',
  country: 'Country',
  payment_method: 'Payment method',
  issuing_bank: 'Issuing bank',
  merchant: 'Merchant',
}

function formatDateTime(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

function formatApprovalRateDrop(value) {
  if (value == null) return '—'
  const percent = Math.abs(value) <= 1 ? value * 100 : value
  return `${percent.toFixed(percent < 10 ? 1 : 0)}%`
}

function formatImpact(value) {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)
}

function incidentRingGradient(incidents, total) {
  if (!total) return '#e2e2e7'

  let position = 0
  const segments = incidents.map(({ severity, count }) => {
    const start = position
    position += (count / total) * 100
    return `${severityHexColors[severity]} ${start}% ${position}%`
  })
  return `conic-gradient(${segments.join(', ')})`
}

function TransactionTrend({ trend }) {
  const days = trend?.days || []
  if (!days.length) return <p className="trend-empty">Loading transaction activity…</p>

  const chartWidth = 960
  const chartHeight = 244
  const padding = { top: 24, right: 24, bottom: 34, left: 48 }
  const max = Math.max(...days.flatMap(day => [day.attempts, day.failed]), 1)
  const x = index => padding.left + (index * (chartWidth - padding.left - padding.right)) / Math.max(days.length - 1, 1)
  const y = value => padding.top + (chartHeight - padding.top - padding.bottom) * (1 - value / max)
  const formatThousands = value => String(Number((value / 1000).toFixed(1)))

  return <>
    <div className="transaction-chart-meta">
      <span><i className="failure-key" /> Failed transactions</span>
      <span><i className="total-key" /> Total transactions</span>
      <span className="thousands-note">Values in thousands</span>
    </div>
    <div className="transaction-chart-scroll">
      <svg className="transaction-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Twelve hour transaction and failure counts">
        {[0, .5, 1].map(fraction => <g key={fraction}><line className="chart-grid" x1={padding.left} x2={chartWidth - padding.right} y1={y(max * fraction)} y2={y(max * fraction)} /><text className="chart-axis-label" x={padding.left - 9} y={y(max * fraction) + 4}>{formatThousands(max * fraction)}</text></g>)}
        {days.slice(0, -1).map((day, index) => <line key={`total-${day.date}`} className="total-segment" x1={x(index)} y1={y(day.attempts)} x2={x(index + 1)} y2={y(days[index + 1].attempts)} />)}
        {days.slice(0, -1).map((day, index) => <line key={day.date} className="failure-segment" x1={x(index)} y1={y(day.failed)} x2={x(index + 1)} y2={y(days[index + 1].failed)} />)}
        {days.map((day, index) => <g key={day.date}><circle className="total-dot" cx={x(index)} cy={y(day.attempts)} r="5" /><text className="chart-value total-value" x={x(index)} y={y(day.attempts) - 11}>{formatThousands(day.attempts)}</text><circle className="failure-dot" cx={x(index)} cy={y(day.failed)} r="5" /><text className="chart-value" x={x(index)} y={y(day.failed) - 11}>{formatThousands(day.failed)}</text><text className="chart-label" x={x(index)} y={chartHeight - 9}>{day.label}</text></g>)}
      </svg>
    </div>
  </>
}

function App() {
  const [issues, setIssues] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [todayMetrics, setTodayMetrics] = useState(null)
  const [weeklyMetrics, setWeeklyMetrics] = useState(null)
  const [transactionTrend, setTransactionTrend] = useState(null)
  const [activeIncidentTab, setActiveIncidentTab] = useState('unread')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/incidents`, API_REQUEST_OPTIONS)
      .then(response => response.ok ? response.json() : Promise.reject(response))
      .then(data => {
        const apiIssues = data.map(issue => ({
          id: issue.key,
          title: issue.title,
          level: issue.severity[0].toUpperCase() + issue.severity.slice(1),
          time: `Detected ${formatDateTime(issue.createdAt)}`,
          volume: `${issue.affectedTransactions.toLocaleString()} affected`,
          ...issue,
        }))
        if (apiIssues.length) {
          setIssues(apiIssues)
          setSelected(apiIssues[0])
          setLoadError(null)
        } else {
          setLoadError('The API returned no incidents.')
        }
      })
      .catch(() => {
        setIssues([])
        setSelected(null)
        setLoadError('Unable to load incidents from the Control Tower API.')
      })
  }, [])

  useEffect(() => {
    const loadTrend = () => fetch(`${API_BASE_URL}/api/dashboard/transaction-trend`, API_REQUEST_OPTIONS)
      .then(response => response.ok ? response.json() : Promise.reject(response))
      .then(setTransactionTrend)
      .catch(() => setTransactionTrend(null))
    loadTrend()
    const poll = window.setInterval(loadTrend, 5000)
    return () => window.clearInterval(poll)
  }, [])

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE_URL}/api/dashboard/incidents-today`, API_REQUEST_OPTIONS)
        .then(response => response.ok ? response.json() : Promise.reject(response)),
      fetch(`${API_BASE_URL}/api/dashboard/incidents-this-week`, API_REQUEST_OPTIONS)
        .then(response => response.ok ? response.json() : Promise.reject(response)),
    ])
      .then(([today, week]) => {
        setTodayMetrics(today)
        setWeeklyMetrics(week)
      })
      .catch(() => {
        setTodayMetrics(null)
        setWeeklyMetrics(null)
      })
  }, [])

  useEffect(() => {
    if (!selected) {
      setDetail(null)
      return
    }

    fetch(`${API_BASE_URL}/api/incidents/${selected.id}`, API_REQUEST_OPTIONS)
      .then(response => response.ok ? response.json() : Promise.reject(response))
      .then(setDetail)
      .catch(() => setDetail(null))
  }, [selected?.id])

  const action = detail?.agentAction
  const overview = detail?.overview || selected?.overview || 'No overview returned by the API.'
  const estimatedImpact = detail?.estimatedImpact ?? selected?.estimatedImpact
  const affectedTransactions = detail?.affectedTransactions ?? selected?.affectedTransactions
  const weekDays = weeklyMetrics?.days || []
  const maxWeeklyCount = Math.max(...weekDays.map(day => day.count), 1)
  const unreadIncidents = issues.filter(incident => !incident.isRead)
  const readIncidents = issues.filter(incident => incident.isRead)
  const tabIncidents = activeIncidentTab === 'unread' ? unreadIncidents : readIncidents
  const todayIncidentKeys = todayMetrics?.byIncidentKey || []
  const ringGradient = incidentRingGradient(todayIncidentKeys, todayMetrics?.total || 0)
  const incidentScope = Object.entries(detail?.dimensionSignatures ?? selected?.dimensionSignatures ?? {})
    .filter(([, value]) => value)

  const setIncidentReadStatus = () => {
    if (!selected) return

    const isRead = !selected.isRead
    fetch(`${API_BASE_URL}/api/incidents/${selected.id}/read`, {
      ...API_REQUEST_OPTIONS,
      method: 'PATCH',
      headers: { ...API_REQUEST_OPTIONS.headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_read: isRead }),
    })
      .then(response => response.ok ? response.json() : Promise.reject(response))
      .then(updated => {
        const updatedIncident = {
          id: updated.key,
          title: updated.title,
          level: updated.severity[0].toUpperCase() + updated.severity.slice(1),
          time: `Detected ${formatDateTime(updated.createdAt)}`,
          volume: `${updated.affectedTransactions.toLocaleString()} affected`,
          ...updated,
        }
        setIssues(current => current.map(incident => incident.id === updatedIncident.id ? updatedIncident : incident))
        setSelected(updatedIncident)
        setDetail(updated)
        setActiveIncidentTab(isRead ? 'read' : 'unread')
      })
      .catch(() => setLoadError('Unable to update the incident read status.'))
  }

  return <main className="shell">
    <header>
      <div>
        <p className="eyebrow">PAYMENT OPERATIONS</p>
        <h1>Control tower</h1>
      </div>
    </header>

    <section className="panel transaction-trend-panel">
      <div className="panel-heading"><div><p className="eyebrow">LIVE ACTIVITY · LAST 12 HOURS</p><h2>Failed transactions</h2></div></div>
      <TransactionTrend trend={transactionTrend} />
    </section>

    <section className="overview">
      <article className="panel anomalies">
        <div className="panel-heading"><div><p className="eyebrow">TODAY</p><h2>Incidents found</h2></div></div>
        <div className="anomaly-content">
          <div className="ring" style={{ background: ringGradient }}><div><strong>{todayMetrics?.total ?? '—'}</strong><span>detected</span></div></div>
          <ul className="legend">{todayMetrics ? todayIncidentKeys.length ? todayIncidentKeys.map(({ incidentKey, severity }) => <li key={incidentKey}><i className={`dot ${severityColors[severity]}`} /> {incidentKey} <b>{severity}</b></li>) : <li>No incidents detected today.</li> : <li>Loading incident metrics…</li>}</ul>
        </div>
      </article>

      <article className="panel chart-panel">
        <div className="panel-heading"><div><p className="eyebrow">THIS WEEK</p><h2>Detected incidents</h2></div><span className="trend">{weeklyMetrics?.total ?? '—'} total</span></div>
        <div className="chart">{weekDays.length ? weekDays.map(day => <div className="bar-wrap" key={day.date}><div className="bar" style={{ height: `${(day.count / maxWeeklyCount) * 100}%` }} /><span>{day.label}</span><small>{day.count}</small></div>) : <p>Loading weekly incident data…</p>}</div>
      </article>
    </section>

    <section className="workspace">
      <aside className="issue-list panel">
        <div className="panel-heading"><div><p className="eyebrow">INCIDENTS FOUND</p><h2>All incidents</h2></div></div>
        <div className="incident-tabs"><button className={`quiet incident-tab ${activeIncidentTab === 'unread' ? 'active' : ''}`} onClick={() => setActiveIncidentTab('unread')}>Unread ({unreadIncidents.length})</button><button className={`quiet incident-tab ${activeIncidentTab === 'read' ? 'active' : ''}`} onClick={() => setActiveIncidentTab('read')}>Read ({readIncidents.length})</button></div>
        <div className="issues">{tabIncidents.length ? tabIncidents.map(issue => <button className={`issue ${selected?.id === issue.id ? 'selected' : ''}`} key={issue.id} onClick={() => setSelected(issue)}>
          <div><span className={`badge ${issue.level.toLowerCase()}`}>{issue.level}</span><span className="issue-id">{issue.id}</span></div>
          <strong>{issue.title}</strong><small>{issue.time} · {issue.volume}</small>
        </button>) : <p>{loadError || `No ${activeIncidentTab} incidents found.`}</p>}</div>
      </aside>

      <article className="detail panel">{selected ? <>
        <div className="detail-top"><div><p className="eyebrow">INCIDENT {selected.id}</p><h2>{selected.title}</h2></div><button className="quiet incident-read-action" onClick={setIncidentReadStatus}>{selected.isRead ? 'Mark as unread' : 'Mark as read'}</button></div>
        <div className="meta"><span className={`badge ${selected.severity}`}>{selected.level}</span><span className="status">{selected.status}</span><span>Detected {formatDateTime(selected.createdAt)}</span><span>Last seen {formatDateTime(detail?.lastSeenAt ?? selected.lastSeenAt)}</span></div>
        <div className="divider" />
        <div className="facts"><div><span>Estimated impact</span><strong>{formatImpact(estimatedImpact)}</strong></div><div><span>Approval rate dropped</span><strong className="accent">{formatApprovalRateDrop(detail?.approvalRateDrop ?? selected.approvalRateDrop)}</strong></div><div><span>Affected transactions</span><strong>{affectedTransactions == null ? '—' : affectedTransactions.toLocaleString()}</strong></div></div>
        <section className="scope"><p className="eyebrow">AFFECTED SCOPE</p><div className="scope-values">{incidentScope.length ? incidentScope.map(([key, value]) => <span key={key}><b>{scopeLabels[key] ?? key}</b>{value}</span>) : <span>No scope returned by the API.</span>}</div></section>
        <section className="next overview-card"><p className="eyebrow">OVERVIEW</p><h3>{overview}</h3><p>Incident data and its operational state are loaded from the Control Tower API.</p></section>
        <section className="insight actions-taken"><p className="eyebrow">RELATED CONTEXT</p><h3>{action || 'No agent action recorded.'}</h3><p>{(detail?.relatedIncidentIds ?? selected.relatedIncidentIds ?? []).length ? `Related incidents: ${(detail?.relatedIncidentIds ?? selected.relatedIncidentIds).join(', ')}.` : 'No related incidents recorded.'} {(detail?.relatedDeploymentIds ?? selected.relatedDeploymentIds ?? []).length ? `Related deployments: ${(detail?.relatedDeploymentIds ?? selected.relatedDeploymentIds).join(', ')}.` : 'No related deployments recorded.'}</p></section>
      </> : <div className="detail-top"><div><p className="eyebrow">API STATUS</p><h2>{loadError ? 'Unable to load incidents' : 'Loading incidents…'}</h2><p>{loadError || 'Waiting for the Control Tower API response.'}</p></div></div>}</article>
    </section>
  </main>
}

createRoot(document.getElementById('root')).render(<App />)
