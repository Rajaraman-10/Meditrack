import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchAppointments, fetchQueue } from '../api/appointments'
import { fetchDashboard } from '../api/clinical'
import { searchDoctorPatient } from '../api/patients'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

function localDateValue() {
  const today = new Date()
  return new Date(today.getTime() - today.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10)
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function statusLabel(status) {
  return status.replaceAll('_', ' ')
}

function DoctorDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [queue, setQueue] = useState([])
  const [error, setError] = useState('')
  const [patientNumber, setPatientNumber] = useState('')
  const [searchError, setSearchError] = useState('')
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    let active = true
    const today = localDateValue()

    Promise.all([
      fetchDashboard(),
      fetchAppointments(today),
      fetchQueue(today),
    ])
      .then(([dashboardData, appointmentData, queueData]) => {
        if (!active) return
        setDashboard(dashboardData)
        setAppointments(appointmentData)
        setQueue(queueData)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load your doctor dashboard.'))
      })

    return () => {
      active = false
    }
  }, [])

  async function handlePatientSearch(event) {
    event.preventDefault()
    setSearchError('')
    setSearching(true)
    try {
      const patient = await searchDoctorPatient(patientNumber)
      navigate(`/doctor/patients/${patient.id}`)
    } catch (requestError) {
      setSearchError(getApiError(requestError, 'Could not find an accessible patient record.'))
    } finally {
      setSearching(false)
    }
  }

  if (error) return <p className="form-error notice" role="alert">{error}</p>
  if (!dashboard) return <p className="route-message" role="status">Loading your dashboard…</p>

  const waitingPatients = queue.filter((entry) => entry.status === 'waiting')
  const completedToday = appointments.filter((appointment) => appointment.status === 'completed').length
  const metrics = [
    { label: "Today's appointments", value: dashboard.totals.today_appointments, tone: 'teal' },
    { label: 'Waiting patients', value: waitingPatients.length, tone: 'amber' },
    { label: 'Completed today', value: completedToday, tone: 'blue' },
    { label: 'Upcoming follow-ups', value: dashboard.totals.follow_ups, tone: 'violet' },
  ]

  return (
    <section className="workspace-page doctor-dashboard">
      <div className="doctor-welcome">
        <div>
          <p className="eyebrow">DOCTOR WORKSPACE</p>
          <h1>Good day, Dr. {user.first_name || user.email}</h1>
          <p>Here’s your clinic at a glance. Focus on the next patient and the care they need.</p>
        </div>
        <Link className="primary-button doctor-primary-action" to="/appointments">View appointments</Link>
      </div>

      <div className="doctor-metric-grid">
        {metrics.map((metric) => (
          <article className={`panel doctor-metric-card metric-${metric.tone}`} key={metric.label}>
            <span className="doctor-metric-icon" aria-hidden="true" />
            <p>{metric.label}</p>
            <strong>{metric.value ?? 0}</strong>
          </article>
        ))}
      </div>

      <section className="panel workspace-panel doctor-patient-search">
        <div>
          <p className="eyebrow">PATIENT RECORDS</p>
          <h2>Search patient by Patient Number</h2>
          <p className="muted-copy">Search for patients with an appointment in your care.</p>
        </div>
        <form className="doctor-search-form" onSubmit={handlePatientSearch}>
          <label htmlFor="doctor-patient-number">Patient Number</label>
          <div className="doctor-search-controls">
            <input
              id="doctor-patient-number"
              autoComplete="off"
              placeholder="e.g. MED-000123"
              value={patientNumber}
              onChange={(event) => setPatientNumber(event.target.value)}
              required
            />
            <button className="primary-button" disabled={searching}>
              {searching ? 'Searching…' : 'Search records'}
            </button>
          </div>
          {searchError && <p className="form-error" role="alert">{searchError}</p>}
        </form>
      </section>

      <div className="doctor-dashboard-grid">
        <section className="panel workspace-panel doctor-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">YOUR SCHEDULE</p>
              <h2>Today’s appointments</h2>
            </div>
            <Link className="text-button" to="/appointments">All appointments</Link>
          </div>
          {appointments.length === 0 ? (
            <p className="empty-state">You have no appointments scheduled today.</p>
          ) : (
            <div className="doctor-appointment-list">
              {appointments.map((appointment) => (
                <article className="doctor-appointment-row" key={appointment.id}>
                  <time className="doctor-time">{formatTime(appointment.starts_at)}</time>
                  <span className="doctor-patient-avatar" aria-hidden="true">
                    {(appointment.patient_name || '?').slice(0, 1).toUpperCase()}
                  </span>
                  <div className="doctor-appointment-details">
                    <strong>{appointment.patient_name}</strong>
                    <span>{appointment.reason || 'General consultation'}</span>
                  </div>
                  <span className={`status-chip status-${appointment.status}`}>
                    {statusLabel(appointment.status)}
                  </span>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel workspace-panel doctor-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">READY FOR CARE</p>
              <h2>Waiting queue</h2>
            </div>
            <span className="doctor-queue-count">{waitingPatients.length} waiting</span>
          </div>
          {waitingPatients.length === 0 ? (
            <p className="empty-state">No patients are waiting right now.</p>
          ) : (
            <div className="doctor-queue-list">
              {waitingPatients.map((entry) => (
                <article className="doctor-queue-row" key={entry.id}>
                  <span className="doctor-queue-position">{entry.position}</span>
                  <div className="doctor-appointment-details">
                    <strong>{entry.patient_name}</strong>
                    <span>Checked in {formatTime(entry.checked_in_at)}</span>
                  </div>
                  <Link className="text-button" to="/consultations">Open</Link>
                </article>
              ))}
            </div>
          )}
          <Link className="doctor-section-link" to="/consultations">Go to consultations <span aria-hidden="true">→</span></Link>
        </section>
      </div>

      <section className="panel workspace-panel doctor-section doctor-followups">
        <div className="section-heading">
          <div>
            <p className="eyebrow">CONTINUITY OF CARE</p>
            <h2>Upcoming follow-ups</h2>
          </div>
          <Link className="text-button" to="/consultations">View consultations</Link>
        </div>
        {!dashboard.follow_up_list?.length ? (
          <p className="empty-state">No upcoming follow-ups are scheduled.</p>
        ) : (
          <div className="doctor-followup-list">
            {dashboard.follow_up_list.map((followUp, index) => (
              <article className="doctor-followup-row" key={`${followUp.date}-${followUp.patient}-${index}`}>
                <span className="doctor-followup-date">{formatDate(followUp.date)}</span>
                <strong>{followUp.patient}</strong>
                <span className="muted-copy">Follow-up visit</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

export default DoctorDashboardPage
