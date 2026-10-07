import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import {
  checkInAppointment,
  createAppointment,
  fetchAppointments,
  fetchQueue,
  updateAppointment,
  updateQueueEntry,
} from '../api/appointments'
import { fetchDoctorSlots, fetchDoctors } from '../api/clinics'
import { fetchPatients } from '../api/patients'
import { getApiError } from '../utils/apiError'

function localDateValue() {
  const today = new Date()
  return new Date(today.getTime() - today.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10)
}

const staffRoles = ['admin', 'receptionist']

function formatDateTime(value) {
  return new Date(value).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function AppointmentsPage() {
  const { user } = useAuth()
  const isClinicStaff = staffRoles.includes(user.role)
  const canCheckIn = isClinicStaff
  const [appointments, setAppointments] = useState([])
  const [queue, setQueue] = useState([])
  const [doctors, setDoctors] = useState([])
  const [patients, setPatients] = useState([])
  const [slots, setSlots] = useState([])
  const [selectedDoctor, setSelectedDoctor] = useState('')
  const [selectedPatient, setSelectedPatient] = useState('')
  const [selectedDate, setSelectedDate] = useState(localDateValue)
  const [rescheduleId, setRescheduleId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [slotsLoading, setSlotsLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const appointmentTitle = useMemo(() => {
    if (user.role === 'doctor') return "Today's appointments"
    if (isClinicStaff) return "Today's clinic appointments"
    return 'My appointment history'
  }, [isClinicStaff, user.role])

  const loadPage = useCallback(async () => {
    try {
      const appointmentDate = user.role === 'patient' ? undefined : selectedDate
      const requests = [
        fetchAppointments(appointmentDate),
        fetchDoctors(),
        fetchQueue(localDateValue()),
      ]
      if (isClinicStaff) requests.push(fetchPatients())
      const [appointmentData, doctorData, queueData, patientData = []] = await Promise.all(requests)
      setAppointments(appointmentData)
      setDoctors(doctorData)
      setQueue(queueData)
      setPatients(patientData)

      if (user.role === 'doctor') {
        const ownDoctor = doctorData.find((doctor) => doctor.email === user.email)
        setSelectedDoctor(String(ownDoctor?.id || ''))
      } else if (!selectedDoctor && doctorData[0]) {
        setSelectedDoctor(String(doctorData[0].id))
      }
      if (isClinicStaff && !selectedPatient && patientData[0]) {
        setSelectedPatient(String(patientData[0].id))
      }
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load appointments.'))
    } finally {
      setLoading(false)
    }
  }, [isClinicStaff, selectedDate, selectedDoctor, selectedPatient, user.email, user.role])

  useEffect(() => {
    let current = true
    const appointmentDate = user.role === 'patient' ? undefined : selectedDate
    const requests = [
      fetchAppointments(appointmentDate),
      fetchDoctors(),
      fetchQueue(localDateValue()),
    ]
    if (isClinicStaff) requests.push(fetchPatients())

    Promise.all(requests)
      .then(([appointmentData, doctorData, queueData, patientData = []]) => {
        if (!current) return
        setAppointments(appointmentData)
        setDoctors(doctorData)
        setQueue(queueData)
        setPatients(patientData)
        if (user.role === 'doctor') {
          const ownDoctor = doctorData.find((doctor) => doctor.email === user.email)
          setSelectedDoctor(String(ownDoctor?.id || ''))
        } else if (!selectedDoctor && doctorData[0]) {
          setSelectedDoctor(String(doctorData[0].id))
        }
        if (isClinicStaff && !selectedPatient && patientData[0]) {
          setSelectedPatient(String(patientData[0].id))
        }
      })
      .catch((requestError) => {
        if (current) setError(getApiError(requestError, 'Could not load appointments.'))
      })
      .finally(() => {
        if (current) setLoading(false)
      })

    return () => {
      current = false
    }
  }, [isClinicStaff, selectedDate, selectedDoctor, selectedPatient, user.email, user.role])

  useEffect(() => {
    let current = true
    if (!selectedDoctor || !selectedDate) return undefined
    fetchDoctorSlots(selectedDoctor, selectedDate)
      .then((data) => {
        if (current) setSlots(data.slots)
      })
      .catch((requestError) => {
        if (current) {
          setSlots([])
          setError(getApiError(requestError, 'Could not load available slots.'))
        }
      })
      .finally(() => {
        if (current) setSlotsLoading(false)
      })

    return () => {
      current = false
    }
  }, [selectedDoctor, selectedDate])

  async function refreshData() {
    await loadPage()
    if (selectedDoctor) {
      try {
        const data = await fetchDoctorSlots(selectedDoctor, selectedDate)
        setSlots(data.slots)
      } catch (requestError) {
        setError(getApiError(requestError, 'Could not refresh available slots.'))
      }
    }
  }

  function handleDoctorChange(event) {
    setSlots([])
    setSlotsLoading(Boolean(event.target.value))
    setSelectedDoctor(event.target.value)
  }

  function handleDateChange(event) {
    setSlots([])
    setSlotsLoading(Boolean(selectedDoctor))
    setSelectedDate(event.target.value)
  }

  async function handleSlot(slot) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      if (rescheduleId) {
        await updateAppointment(rescheduleId, {
          doctor: Number(selectedDoctor),
          starts_at: slot,
        })
        setRescheduleId(null)
        setMessage('Appointment rescheduled.')
      } else {
        const payload = {
          doctor: Number(selectedDoctor),
          starts_at: slot,
        }
        if (isClinicStaff) payload.patient = Number(selectedPatient)
        await createAppointment(payload)
        setMessage('Appointment booked.')
      }
      await refreshData()
    } catch (requestError) {
      setError(getApiError(requestError, 'The selected slot could not be booked.'))
      try {
        const data = await fetchDoctorSlots(selectedDoctor, selectedDate)
        setSlots(data.slots)
      } catch (refreshError) {
        setError(getApiError(refreshError, 'Booking failed and slots could not be refreshed.'))
      }
    } finally {
      setSaving(false)
    }
  }

  async function handleAppointmentAction(appointment, action) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      if (action === 'check-in') {
        const entry = await checkInAppointment(appointment.id)
        setMessage(`Patient checked in at queue position ${entry.position}.`)
      } else if (action === 'cancel') {
        await updateAppointment(appointment.id, { status: 'cancelled' })
        setMessage('Appointment cancelled.')
      } else if (action === 'confirm') {
        await updateAppointment(appointment.id, { status: 'confirmed' })
        setMessage('Appointment confirmed.')
      } else if (action === 'reschedule') {
        setRescheduleId(appointment.id)
        setSelectedDoctor(String(appointment.doctor))
        const date = appointment.starts_at.slice(0, 10)
        setSelectedDate(date)
        setMessage(`Choose a new slot for ${appointment.patient_name}.`)
      }
      await refreshData()
    } catch (requestError) {
      setError(getApiError(requestError, 'The appointment could not be updated.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleQueueAction(entry, nextStatus) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await updateQueueEntry(entry.id, { status: nextStatus })
      setMessage('Waiting queue updated.')
      await refreshData()
    } catch (requestError) {
      setError(getApiError(requestError, 'The queue could not be updated.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="route-message" role="status">Loading appointments…</p>

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">{isClinicStaff ? 'RECEPTION WORKFLOW' : user.role === 'doctor' ? 'DOCTOR WORKSPACE' : 'PATIENT SERVICES'}</p><h1>Appointments & queue</h1></div>
        <span className="count-pill">{appointments.length} appointments</span>
      </div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}

      {(user.role === 'patient' || isClinicStaff) && (
        <section className="panel workspace-panel">
          <div className="section-heading">
            <div><p className="eyebrow">{rescheduleId ? 'CHANGE BOOKING' : 'BOOKING'}</p><h2>{rescheduleId ? 'Choose a new appointment time' : 'Find an available time'}</h2></div>
            {rescheduleId && <button className="text-button" onClick={() => setRescheduleId(null)}>Stop rescheduling</button>}
          </div>
          <div className="form-grid booking-filters">
            {isClinicStaff && (
              <label>Patient<select value={selectedPatient} onChange={(event) => setSelectedPatient(event.target.value)}><option value="">Choose a patient</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.first_name} {patient.last_name} · {patient.email}</option>)}</select></label>
            )}
            <label>Doctor<select value={selectedDoctor} onChange={handleDoctorChange}><option value="">Choose a doctor</option>{doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>Dr. {doctor.first_name} {doctor.last_name} · {doctor.specialization}</option>)}</select></label>
            <label>Date<input type="date" value={selectedDate} onChange={handleDateChange} /></label>
          </div>
          <div className="slot-grid" aria-live="polite">
            {slotsLoading ? <p className="empty-state">Finding available times…</p> : slots.length === 0 ? <p className="empty-state">No available slots for this doctor and date.</p> : slots.map((slot) => (
              <button className="slot-button" disabled={saving || (isClinicStaff && !selectedPatient)} onClick={() => handleSlot(slot)} key={slot}>
                {new Date(slot).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
              </button>
            ))}
          </div>
          {slots.length > 0 && <p className="field-hint">Times shown in your browser’s local timezone. The API validates the clinic schedule again when booking.</p>}
        </section>
      )}

      <section className="panel workspace-panel">
        <div className="section-heading">
          <div><p className="eyebrow">SCHEDULE</p><h2>{appointmentTitle}</h2></div>
          {user.role !== 'patient' && <label className="inline-date">Date<input type="date" value={selectedDate} onChange={handleDateChange} /></label>}
        </div>
        {appointments.length === 0 ? <p className="empty-state">No appointments to show for this date.</p> : (
          <div className="appointment-list">
            {appointments.map((appointment) => (
              <article className="appointment-row" key={appointment.id}>
                <div className="appointment-time">{formatDateTime(appointment.starts_at)}</div>
                <div className="appointment-main">
                  <strong>{user.role === 'patient' ? `Dr. ${appointment.doctor_name}` : appointment.patient_name}</strong>
                  <span>{user.role === 'patient' ? appointment.department_name : `Dr. ${appointment.doctor_name}`} · {appointment.status.replaceAll('_', ' ')}</span>
                </div>
                <div className="row-actions">
                  {canCheckIn && ['scheduled', 'confirmed'].includes(appointment.status) && (
                    <>
                      {appointment.status === 'scheduled' && <button className="text-button" disabled={saving} onClick={() => handleAppointmentAction(appointment, 'confirm')}>Confirm</button>}
                      {appointment.starts_at.slice(0, 10) === localDateValue() && <button className="text-button" disabled={saving} onClick={() => handleAppointmentAction(appointment, 'check-in')}>Check in</button>}
                      <button className="text-button" disabled={saving} onClick={() => handleAppointmentAction(appointment, 'reschedule')}>Reschedule</button>
                      <button className="text-button danger-text" disabled={saving} onClick={() => handleAppointmentAction(appointment, 'cancel')}>Cancel</button>
                    </>
                  )}
                  {user.role === 'patient' && ['scheduled', 'confirmed'].includes(appointment.status) && <button className="text-button danger-text" disabled={saving} onClick={() => handleAppointmentAction(appointment, 'cancel')}>Cancel</button>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel workspace-panel" id="queue">
        <div className="section-heading"><div><p className="eyebrow">LIVE WAITING ROOM</p><h2>Queue for {localDateValue()}</h2></div><span className="count-pill">{queue.filter((entry) => entry.status === 'waiting').length} waiting</span></div>
        {queue.length === 0 ? <p className="empty-state">No patients are in the waiting queue.</p> : (
          <div className="queue-list">
            {queue.map((entry) => (
              <div className="queue-row" key={entry.id}>
                <span className="queue-number">{String(entry.position).padStart(2, '0')}</span>
                <div className="appointment-main"><strong>{entry.patient_name}</strong><span>Dr. {entry.doctor_name} · {entry.status.replaceAll('_', ' ')}</span></div>
                {canCheckIn && entry.status === 'waiting' && <button className="text-button danger-text" disabled={saving} onClick={() => handleQueueAction(entry, 'left')}>Mark left</button>}
                {canCheckIn && entry.status === 'left' && <button className="text-button" disabled={saving} onClick={() => handleQueueAction(entry, 'waiting')}>Return to queue</button>}
              </div>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

export default AppointmentsPage
