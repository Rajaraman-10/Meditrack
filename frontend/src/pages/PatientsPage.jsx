import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { createPatient, fetchPatients, updatePatient } from '../api/patients'
import { getApiError } from '../utils/apiError'

const emptyPatient = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  phone: '',
  date_of_birth: '',
  gender: '',
  blood_group: '',
}

function PatientsPage() {
  const { user } = useAuth()
  const isClinicStaff = user.role === 'admin' || user.role === 'receptionist'
  const [patients, setPatients] = useState([])
  const [form, setForm] = useState(emptyPatient)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [createdPatientNumber, setCreatedPatientNumber] = useState('')
  const [error, setError] = useState('')

  const loadPatients = useCallback(async () => {
    try {
      setPatients(await fetchPatients())
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load patient records.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let current = true
    fetchPatients()
      .then((data) => {
        if (current) setPatients(data)
      })
      .catch((requestError) => {
        if (current) setError(getApiError(requestError, 'Could not load patient records.'))
      })
      .finally(() => {
        if (current) setLoading(false)
      })
    return () => {
      current = false
    }
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    setCreatedPatientNumber('')
    try {
      const details = { ...form }
      if (!details.date_of_birth) delete details.date_of_birth
      const createdPatient = await createPatient(details)
      setForm(emptyPatient)
      setMessage('Patient registered successfully.')
      setCreatedPatientNumber(createdPatient.patient_number)
      await loadPatients()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not register patient.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleProfileUpdate(event) {
    event.preventDefault()
    const patient = patients[0]
    if (!patient) return
    setSaving(true)
    setError('')
    setMessage('')
    const data = new FormData(event.currentTarget)
    try {
      await updatePatient(patient.id, {
        phone: data.get('phone'),
        address: data.get('address'),
        date_of_birth: data.get('date_of_birth') || null,
        gender: data.get('gender'),
        blood_group: data.get('blood_group'),
        emergency_contact_name: data.get('emergency_contact_name'),
        emergency_contact_phone: data.get('emergency_contact_phone'),
      })
      setMessage('Profile saved.')
      await loadPatients()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not update the profile.'))
    } finally {
      setSaving(false)
    }
  }

  function changeField(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{isClinicStaff ? 'PATIENT MANAGEMENT' : 'YOUR HEALTH PROFILE'}</p>
          <h1>{isClinicStaff ? 'Patients' : 'My patient profile'}</h1>
        </div>
        <span className="count-pill">{patients.length} {patients.length === 1 ? 'record' : 'records'}</span>
      </div>

      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && (
        <p className="success-notice" role="status">
          {message}
          {createdPatientNumber && <> Patient Number: <strong>{createdPatientNumber}</strong> — share it with the patient.</>}
        </p>
      )}

      {isClinicStaff && (
        <form className="panel workspace-panel" onSubmit={handleCreate}>
          <div className="section-heading">
            <div><p className="eyebrow">RECEPTION WORKFLOW</p><h2>Register a patient</h2></div>
          </div>
          <div className="form-grid">
            <label>First name<input name="first_name" required value={form.first_name} onChange={changeField} /></label>
            <label>Last name<input name="last_name" required value={form.last_name} onChange={changeField} /></label>
            <label>Email<input name="email" type="email" required value={form.email} onChange={changeField} /></label>
            <label>Temporary password<input name="password" type="password" minLength="8" required value={form.password} onChange={changeField} /></label>
            <label>Phone<input name="phone" value={form.phone} onChange={changeField} /></label>
            <label>Date of birth<input name="date_of_birth" type="date" value={form.date_of_birth} onChange={changeField} /></label>
                <label>Gender<input name="gender" value={form.gender} onChange={changeField} /></label>
                <label>Blood group<input name="blood_group" maxLength="3" value={form.blood_group} onChange={changeField} /></label>
          </div>
          <button className="primary-button form-submit" disabled={saving}>{saving ? 'Saving…' : 'Register patient'}</button>
        </form>
      )}

      {!isClinicStaff && patients[0] && (
        <form className="panel workspace-panel" onSubmit={handleProfileUpdate}>
          <p className="auth-intro">Your login email and account role are protected and cannot be changed here.</p>
          <div className="form-grid">
            <label>Email<input value={patients[0].email} readOnly /></label>
            <label>Date of birth<input name="date_of_birth" type="date" defaultValue={patients[0].date_of_birth || ''} /></label>
            <label>Gender<input name="gender" defaultValue={patients[0].gender || ''} /></label>
            <label>Blood group<input name="blood_group" maxLength="3" defaultValue={patients[0].blood_group || ''} /></label>
            <label>Phone<input name="phone" defaultValue={patients[0].phone} /></label>
            <label>Address<input name="address" defaultValue={patients[0].address} /></label>
            <label>Emergency contact<input name="emergency_contact_name" defaultValue={patients[0].emergency_contact_name} /></label>
            <label>Emergency phone<input name="emergency_contact_phone" defaultValue={patients[0].emergency_contact_phone} /></label>
          </div>
          <button className="primary-button form-submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
        </form>
      )}

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">RECORDS</p><h2>{isClinicStaff ? 'Patient directory' : 'Account details'}</h2></div></div>
        {loading ? <p className="empty-state">Loading patient records…</p> : patients.length === 0 ? <p className="empty-state">No patient profile is linked to this account yet.</p> : (
          <div className="table-wrap">
            <table>
            <thead><tr><th>Patient Number</th><th>Patient</th><th>Email</th><th>Phone</th><th>Date of birth</th></tr></thead>
            <tbody>{patients.map((patient) => <tr key={patient.id}><td><strong>{patient.patient_number}</strong></td><td>{patient.first_name} {patient.last_name}</td><td>{patient.email}</td><td>{patient.phone || '—'}</td><td>{patient.date_of_birth || '—'}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  )
}

export default PatientsPage
