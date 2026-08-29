import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './overrides.css'

const fallbackIssues = [
  { id: 'INC-2048', title: 'Mercado Pago declines transfers from AR', level: 'Urgent', time: 'Since 15:30', volume: '1,284 affected' },
  { id: 'INC-2047', title: 'Naranja X transfer latency elevated', level: 'High', time: 'Since 10:15', volume: '642 affected' },
  { id: 'INC-2046', title: 'Brazilian card authorization dip', level: 'Medium', time: 'Since 08:40', volume: '318 affected' },
]

const bars = [22, 68, 56, 31, 48, 19, 27]

function App() {
  const [issues, setIssues] = useState(fallbackIssues)
  const [selected, setSelected] = useState(fallbackIssues[0])
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/incidents')
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
        }
      })
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    fetch(`http://127.0.0.1:8000/api/incidents/${selected.id}`)
      .then(response => response.ok ? response.json() : Promise.reject(response))
      .then(setDetail)
      .catch(() => setDetail(null))
  }, [selected.id])

  const action = detail?.agentAction
  const overview = detail?.overview || selected.overview || 'Authorization declines are 4.6× above the expected baseline.'
  const estimatedImpact = detail?.estimatedImpact ?? selected.estimatedImpact ?? 5120000
  const affectedTransactions = detail?.affectedTransactions ?? selected.affectedTransactions ?? 1284

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
        <div className="issues">{issues.map(issue => <button className={`issue ${selected.id === issue.id ? 'selected' : ''}`} key={issue.id} onClick={() => setSelected(issue)}>
          <div><span className={`badge ${issue.level.toLowerCase()}`}>{issue.level}</span><span className="issue-id">{issue.id}</span></div>
          <strong>{issue.title}</strong><small>{issue.time} · {issue.volume}</small>
        </button>)}</div>
      </aside>

      <article className="detail panel">
        <div className="detail-top"><div><p className="eyebrow">ISSUE {selected.id}</p><h2>{selected.title}</h2></div></div>
        <div className="meta"><span className="badge urgent">{selected.level}</span><span>{selected.time}</span><span>Last seen just now</span></div>
        <div className="divider" />
        <div className="facts"><div><span>Estimated impact</span><strong>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2 }).format(estimatedImpact)}</strong></div><div><span>Approval rate dropped</span><strong className="accent">{detail?.approvalRateDrop ?? 18.7}%</strong></div><div><span>Affected transactions</span><strong>{affectedTransactions.toLocaleString()}</strong></div></div>
        <section className="next overview-card"><p className="eyebrow">OVERVIEW</p><h3>{overview}</h3><p>Issue data and its operational state are loaded from the Control Tower API.</p></section>
        <section className="insight actions-taken"><p className="eyebrow">AGENT ACTIONS TAKEN</p><h3>{action || 'No agent actions recorded yet.'}</h3><p>{action ? 'The action has been recorded and the incident remains under active observation.' : 'The API has not returned an action for this incident.'}</p></section>
      </article>
    </section>
  </main>
}

createRoot(document.getElementById('root')).render(<App />)
