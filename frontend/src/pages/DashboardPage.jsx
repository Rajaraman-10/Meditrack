import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchDashboard } from '../api/clinical'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

const titles = {
  admin: 'Administration overview',
  doctor: 'Doctor dashboard',
  receptionist: 'Reception dashboard',
  patient: 'Your care at a glance',
}

function DashboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let current = true
    fetchDashboard()
      .then((result) => {
        if (current) setData(result)
      })
      .catch((requestError) => {
        if (current) setError(getApiError(requestError, 'Could not load the dashboard.'))
      })
    return () => {
      current = false
    }
  }, [])

  if (error) return <p className="form-error notice" role="alert">{error}</p>
  if (!data) return <p className="route-message" role="status">Loading dashboard…</p>

  const metrics = Object.entries(data.totals || {})

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">{user.role.toUpperCase()} DASHBOARD</p><h1>{titles[user.role]}</h1></div>
        <span className="count-pill"><span className="greeting-dot" /> Hello, {user.first_name || user.email}</span>
      </div>

      <div className="metric-grid">
        {metrics.map(([key, value]) => (
          <article className="panel metric-card" key={key}>
            <span>{key.replaceAll('_', ' ')}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      {data.appointment_trend && (
        <section className="panel workspace-panel chart-panel">
          <div className="section-heading"><div><p className="eyebrow">SIX-MONTH TREND</p><h2>Appointments and revenue</h2></div></div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.appointment_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e7eeeb" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="count" name="Appointments" stroke="#167d72" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-wrap revenue-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.revenue_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e7eeeb" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="amount" name="Paid revenue" stroke="#ba8b36" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {data.today_appointments && (
        <section className="panel workspace-panel">
          <div className="section-heading"><div><p className="eyebrow">TODAY</p><h2>Appointments</h2></div></div>
          {data.today_appointments.length === 0 ? <p className="empty-state">No appointments scheduled today.</p> : (
            <div className="compact-list">{data.today_appointments.map((item) => <div key={item.id}><strong>{item.patient}</strong><span>{new Date(item.starts_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} · {item.status.replaceAll('_', ' ')}</span></div>)}</div>
          )}
        </section>
      )}

      {data.upcoming && (
        <section className="panel workspace-panel">
          <div className="section-heading"><div><p className="eyebrow">YOUR CARE</p><h2>Upcoming appointments</h2></div></div>
          {data.upcoming.length === 0 ? <p className="empty-state">No upcoming appointments.</p> : (
            <div className="compact-list">{data.upcoming.map((item) => <div key={item.id}><strong>Dr. {item.doctor}</strong><span>{new Date(item.starts_at).toLocaleString()}</span></div>)}</div>
          )}
        </section>
      )}
    </section>
  )
}

export default DashboardPage
