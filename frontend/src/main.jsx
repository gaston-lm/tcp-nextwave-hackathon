import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './overrides.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const API_REQUEST_OPTIONS = {
  headers: { 'ngrok-skip-browser-warning': '1' },
}

const bars = [22, 68, 56, 31, 48, 19, 27]

function App() {
  const [issues, setIssues] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadError, setLoadError] = useState(null)

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

  return <main className="shell">
    <header>
      <div>
        <p className="eyebrow">PAYMENT OPERATIONS</p>
        <h1>Control tower</h1>
      </div>
    </header>

    <section className="overview">
      <article className="panel anomalies">
        <div className="panel-heading"><div><p className="eyebrow">TODAY</p><h2>Issues found</h2></div><button className="quiet">View all</button></div>
        <div className="anomaly-content">
          <div className="ring"><div><strong>12</strong><span>active</span></div></div>
          <ul className="legend">
            <li><i className="dot magenta" /> Provider down <b>4</b></li>
            <li><i className="dot cyan" /> Bank disruption <b>3</b></li>
            <li><i className="dot violet" /> Decline-code spike <b>3</b></li>
            <li><i className="dot gray" /> Country issue <b>2</b></li>
          </ul>
        </div>
      </article>

      <article className="panel chart-panel">
        <div className="panel-heading"><div><p className="eyebrow">THIS WEEK</p><h2>Detected incidents</h2></div><span className="trend">+18.4%</span></div>
        <div className="chart">{bars.map((bar, index) => <div className="bar-wrap" key={index}><div className="bar" style={{ height: `${bar}%` }} /><span>{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][index]}</span></div>)}</div>
      </article>
    </section>

    <section className="workspace">
      <aside className="issue-list panel">
        <div className="panel-heading"><div><p className="eyebrow">ISSUES FOUND</p><h2>Prioritized queue</h2></div><span className="count">{issues.length}</span></div>
        <div className="issues">{issues.length ? issues.map(issue => <button className={`issue ${selected?.id === issue.id ? 'selected' : ''}`} key={issue.id} onClick={() => setSelected(issue)}>
          <div><span className={`badge ${issue.level.toLowerCase()}`}>{issue.level}</span><span className="issue-id">{issue.id}</span></div>
          <strong>{issue.title}</strong><small>{issue.time} · {issue.volume}</small>
        </button>) : <p>{loadError || 'Loading incidents from the API…'}</p>}</div>
      </aside>

      <article className="detail panel">{selected ? <>
        <div className="detail-top"><div><p className="eyebrow">ISSUE {selected.id}</p><h2>{selected.title}</h2></div></div>
        <div className="meta"><span className="badge urgent">{selected.level}</span><span>{selected.time}</span><span>Last seen just now</span></div>
        <div className="divider" />
        <div className="facts"><div><span>Estimated impact</span><strong>{estimatedImpact == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2 }).format(estimatedImpact)}</strong></div><div><span>Approval rate dropped</span><strong className="accent">{detail?.approvalRateDrop == null ? '—' : `${detail.approvalRateDrop}%`}</strong></div><div><span>Affected transactions</span><strong>{affectedTransactions == null ? '—' : affectedTransactions.toLocaleString()}</strong></div></div>
        <section className="next overview-card"><p className="eyebrow">OVERVIEW</p><h3>{overview}</h3><p>Issue data and its operational state are loaded from the Control Tower API.</p></section>
        <section className="insight actions-taken"><p className="eyebrow">AGENT ACTIONS TAKEN</p><h3>{action || 'No agent actions recorded yet.'}</h3><p>{action ? 'The action has been recorded and the incident remains under active observation.' : 'The API has not returned an action for this incident.'}</p></section>
      </> : <div className="detail-top"><div><p className="eyebrow">API STATUS</p><h2>{loadError ? 'Unable to load incidents' : 'Loading incidents…'}</h2><p>{loadError || 'Waiting for the Control Tower API response.'}</p></div></div>}</article>
    </section>
  </main>
}

createRoot(document.getElementById('root')).render(<App />)
