import { useCallback, useEffect, useState } from 'react'
import { fetchAppointments } from '../api/appointments'
import { addConsultationNote, completeConsultation, fetchConsultations, startConsultation, updateConsultation } from '../api/clinical'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

function ConsultationsPage() {
  const { user } = useAuth()
  const [consultations, setConsultations] = useState([])
  const [appointments, setAppointments] = useState([])
  const [drafts, setDrafts] = useState({})
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const getPageData = useCallback(() => {
    return Promise.all([
      fetchConsultations(),
      user.role === 'doctor' ? fetchAppointments() : Promise.resolve([]),
    ])
  }, [user.role])

  const load = useCallback(async () => {
    try {
      const [records, bookings] = await getPageData()
      setConsultations(records)
      setAppointments(bookings.filter((item) => item.status === 'checked_in'))
      setDrafts(Object.fromEntries(records.map((item) => [item.id, {
        diagnosis: item.diagnosis,
        clinical_notes: item.clinical_notes,
        follow_up_date: item.follow_up_date || '',
      }])))
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load consultations.'))
    }
  }, [getPageData])

  useEffect(() => {
    let active = true
    getPageData()
      .then(([records, bookings]) => {
        if (!active) return
        setConsultations(records)
        setAppointments(bookings.filter((item) => item.status === 'checked_in'))
        setDrafts(Object.fromEntries(records.map((item) => [item.id, {
          diagnosis: item.diagnosis,
          clinical_notes: item.clinical_notes,
          follow_up_date: item.follow_up_date || '',
        }])))
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load consultations.'))
      })
    return () => { active = false }
  }, [getPageData])

  async function run(action, success) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(success)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'The clinical record could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">CLINICAL CARE</p><h1>Consultations</h1></div><span className="count-pill">{consultations.length} records</span></div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}

      {user.role === 'doctor' && appointments.length > 0 && (
        <section className="panel workspace-panel">
          <div className="section-heading"><div><p className="eyebrow">CHECKED IN</p><h2>Ready to consult</h2></div></div>
          <div className="compact-list">{appointments.map((appointment) => <div key={appointment.id}><strong>{appointment.patient_name}</strong><button className="text-button" disabled={saving} onClick={() => run(() => startConsultation(appointment.id), 'Consultation started.')}>Start consultation</button></div>)}</div>
        </section>
      )}

      {consultations.length === 0 ? <section className="panel workspace-panel"><p className="empty-state">No consultation records are available.</p></section> : consultations.map((record) => (
        <article className="panel workspace-panel consultation-card" key={record.id}>
          <div className="section-heading"><div><p className="eyebrow">{record.status.replaceAll('_', ' ')}</p><h2>{user.role === 'patient' ? `Dr. ${record.doctor_name}` : record.patient_name}</h2></div><span className="muted-copy">{new Date(record.appointment_starts_at).toLocaleString()}</span></div>
          {user.role === 'doctor' && record.status === 'in_progress' ? (
            <>
              <label className="wide-label">Diagnosis<textarea value={drafts[record.id]?.diagnosis || ''} onChange={(event) => setDrafts({ ...drafts, [record.id]: { ...drafts[record.id], diagnosis: event.target.value } })} /></label>
              <label className="wide-label">Clinical notes<textarea rows="4" value={drafts[record.id]?.clinical_notes || ''} onChange={(event) => setDrafts({ ...drafts, [record.id]: { ...drafts[record.id], clinical_notes: event.target.value } })} /></label>
              <label className="wide-label">Follow-up date<input type="date" value={drafts[record.id]?.follow_up_date || ''} onChange={(event) => setDrafts({ ...drafts, [record.id]: { ...drafts[record.id], follow_up_date: event.target.value } })} /></label>
              <div className="inline-actions">
                <button className="primary-button" disabled={saving} onClick={() => run(() => updateConsultation(record.id, drafts[record.id]), 'Clinical notes saved.')}>Save notes</button>
                <button className="secondary-button" disabled={saving} onClick={() => run(async () => { await updateConsultation(record.id, drafts[record.id]); await completeConsultation(record.id) }, 'Consultation completed.')}>Complete consultation</button>
              </div>
              <form className="note-form" onSubmit={(event) => { event.preventDefault(); run(() => addConsultationNote(record.id, note), 'Consultation note added.'); setNote('') }}>
                <label className="wide-label">Additional note<textarea rows="2" value={note} onChange={(event) => setNote(event.target.value)} /></label>
                <button className="text-button" disabled={saving || !note.trim()}>Add note</button>
              </form>
            </>
          ) : (
            <>
              <p><strong>Diagnosis:</strong> {record.diagnosis || 'Not recorded'}</p>
              <p><strong>Clinical notes:</strong> {record.clinical_notes || 'No notes recorded.'}</p>
              {record.follow_up_date && <p><strong>Follow-up:</strong> {record.follow_up_date}</p>}
            </>
          )}
          {record.notes?.map((item) => <p className="clinical-note" key={item.id}>{item.body}<span> · {item.author_name}</span></p>)}
        </article>
      ))}
    </section>
  )
}

export default ConsultationsPage
