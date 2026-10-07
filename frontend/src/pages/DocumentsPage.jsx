import { useCallback, useEffect, useState } from 'react'
import { downloadDocument, fetchDocuments, uploadDocument } from '../api/clinical'
import { fetchAppointments } from '../api/appointments'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

function DocumentsPage() {
  const { user } = useAuth()
  const [documents, setDocuments] = useState([])
  const [appointments, setAppointments] = useState([])
  const [form, setForm] = useState({ appointment: '', title: '', category: 'other', file: null })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const getPageData = useCallback(() => {
    return Promise.all([
      fetchDocuments(),
      ['doctor', 'admin', 'receptionist'].includes(user.role) ? fetchAppointments() : Promise.resolve([]),
    ])
  }, [user.role])

  const load = useCallback(async () => {
    try {
      const [records, bookings] = await getPageData()
      setDocuments(records)
      setAppointments(bookings)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load medical documents.'))
    }
  }, [getPageData])

  useEffect(() => {
    let active = true
    getPageData()
      .then(([records, bookings]) => {
        if (!active) return
        setDocuments(records)
        setAppointments(bookings)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load medical documents.'))
      })
    return () => { active = false }
  }, [getPageData])

  async function submit(event) {
    event.preventDefault()
    if (!form.file) return setError('Choose a file to upload.')
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const appointment = appointments.find((item) => String(item.id) === form.appointment)
      await uploadDocument(form.file, {
        title: form.title,
        category: form.category,
        ...(form.appointment ? { appointment: form.appointment } : {}),
        ...(user.role === 'admin' || user.role === 'receptionist' ? { patient: appointment?.patient } : {}),
      })
      setForm({ appointment: '', title: '', category: 'other', file: null })
      event.target.reset()
      setMessage('Medical document uploaded. Access is limited to authorized care-team members and the patient.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not upload the medical document.'))
    } finally {
      setSaving(false)
    }
  }

  async function download(record) {
    setError('')
    try {
      await downloadDocument(record.id, record.file_name)
    } catch (requestError) {
      setError(getApiError(requestError, 'The document could not be downloaded.'))
    }
  }

  const staff = user.role === 'admin' || user.role === 'receptionist'
  return (
    <section className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">PRIVATE PATIENT FILES</p><h1>Medical documents</h1></div><span className="count-pill">{documents.length} files</span></div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}
      <section className="panel workspace-panel"><div className="section-heading"><div><p className="eyebrow">SECURE UPLOAD</p><h2>Add a document</h2></div></div>
        <form onSubmit={submit}>
          <div className="form-grid">
            {(user.role === 'doctor' || staff) && <label>Appointment<select required={user.role === 'doctor' || staff} value={form.appointment} onChange={(event) => setForm({ ...form, appointment: event.target.value })}><option value="">Choose appointment</option>{appointments.map((item) => <option key={item.id} value={item.id}>{item.patient_name} · {new Date(item.starts_at).toLocaleDateString()}</option>)}</select></label>}
            <label>Document title<input required maxLength="180" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
            <label>Category<select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}><option value="other">Other</option><option value="lab_result">Lab result</option><option value="referral">Referral</option><option value="imaging">Imaging</option><option value="medical_record">Medical record</option></select></label>
            <label>File (PDF, JPG, PNG; max 10 MB)<input required type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setForm({ ...form, file: event.target.files?.[0] || null })} /></label>
          </div>
          <button className="primary-button form-submit" disabled={saving}>{saving ? 'Uploading…' : 'Upload document'}</button>
        </form>
      </section>
      <section className="panel workspace-panel"><div className="section-heading"><div><p className="eyebrow">AUTHORIZED RECORDS</p><h2>Available documents</h2></div></div>
        {documents.length === 0 ? <p className="empty-state">No medical documents are available to this account.</p> : <div className="compact-list">{documents.map((record) => <div key={record.id}><span><strong>{record.title}</strong><span>{record.category} · {new Date(record.uploaded_at).toLocaleDateString()}</span></span><button className="text-button" onClick={() => download(record)}>Download</button></div>)}</div>}
      </section>
    </section>
  )
}

export default DocumentsPage
