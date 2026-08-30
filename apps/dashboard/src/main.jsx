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

function App() {
  const [issues, setIssues] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [todayMetrics, setTodayMetrics] = useState(null)
  const [weeklyMetrics, setWeeklyMetrics] = useState(null)
  const [activeIncidentTab, setActiveIncidentTab] = useState('unread')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/incidents`, API_REQUEST_OPTIONS)
      .then(response => response.ok ? response.json() : Promise.reject(response))
      .then(data => {
        const apiIssues = data.map(issue => ({
          id: issue.key,
          title: issue.title,
          level: issue.severity[0].toUpperCase() + issue.severity.slice(1),
          time: `Since ${new Date(issue.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
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
          time: `Since ${new Date(updated.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
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
        </button>) : <p>{loadError || `No ${activeIncidentTab} incidents detected today.`}</p>}</div>
      </aside>

      <article className="detail panel">{selected ? <>
        <div className="detail-top"><div><p className="eyebrow">INCIDENT {selected.id}</p><h2>{selected.title}</h2></div><button className="quiet incident-read-action" onClick={setIncidentReadStatus}>{selected.isRead ? 'Mark as unread' : 'Mark as read'}</button></div>
        <div className="meta"><span className="badge urgent">{selected.level}</span><span>{selected.time}</span><span>Last seen just now</span></div>
        <div className="divider" />
        <div className="facts"><div><span>Estimated impact</span><strong>{estimatedImpact == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2 }).format(estimatedImpact)}</strong></div><div><span>Approval rate dropped</span><strong className="accent">{detail?.approvalRateDrop == null ? '—' : `${detail.approvalRateDrop}%`}</strong></div><div><span>Affected transactions</span><strong>{affectedTransactions == null ? '—' : affectedTransactions.toLocaleString()}</strong></div></div>
        <section className="next overview-card"><p className="eyebrow">OVERVIEW</p><h3>{overview}</h3><p>Incident data and its operational state are loaded from the Control Tower API.</p></section>
        <section className="insight actions-taken"><p className="eyebrow">AGENT ACTIONS TAKEN</p><h3>{action || 'No agent actions recorded yet.'}</h3><p>{action ? 'The action has been recorded and the incident remains under active observation.' : 'The API has not returned an action for this incident.'}</p></section>
      </> : <div className="detail-top"><div><p className="eyebrow">API STATUS</p><h2>{loadError ? 'Unable to load incidents' : 'Loading incidents…'}</h2><p>{loadError || 'Waiting for the Control Tower API response.'}</p></div></div>}</article>
    </section>
  </main>
}

createRoot(document.getElementById('root')).render(<App />)
