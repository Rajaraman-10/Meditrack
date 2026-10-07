import { useEffect, useState } from 'react'
import { fetchAuditLogs } from '../api/clinical'
import { getApiError } from '../utils/apiError'

function AuditPage() {
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchAuditLogs()
      .then((records) => { if (active) setLogs(records) })
      .catch((requestError) => { if (active) setError(getApiError(requestError, 'Could not load activity logs.')) })
    return () => { active = false }
  }, [])

  return (
    <section className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">ADMIN ONLY</p><h1>Activity log</h1></div><span className="count-pill">{logs.length} events</span></div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      <section className="panel workspace-panel"><div className="section-heading"><div><p className="eyebrow">RECENT SYSTEM EVENTS</p><h2>Audit trail</h2></div></div>
        {logs.length === 0 ? <p className="empty-state">No activity has been recorded.</p> : <div className="table-wrap"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Record</th></tr></thead><tbody>{logs.map((item) => <tr key={item.id}><td>{new Date(item.occurred_at).toLocaleString()}</td><td>{item.actor_email || 'System'}</td><td>{item.action.replaceAll('_', ' ')}</td><td>{item.object_type} #{item.object_id}</td></tr>)}</tbody></table></div>}
      </section>
      <p className="muted-copy">This view is access-restricted to administrators. Audit events support accountability; they should not be edited through the application.</p>
    </section>
  )
}

export default AuditPage
