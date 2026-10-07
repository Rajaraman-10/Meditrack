import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import {
  createAvailability,
  createDepartment,
  createDoctor,
  createReceptionist,
  createScheduleException,
  deleteAvailability,
  deleteScheduleException,
  fetchAvailability,
  fetchDepartments,
  fetchDoctors,
  fetchScheduleExceptions,
  updateDoctor,
  updateAvailability,
  updateScheduleException,
} from '../api/clinics'
import { getApiError } from '../utils/apiError'

const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function localDateValue(date = new Date()) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10)
}

function formatCalendarDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function getUpcomingScheduleDates(availability, exceptions) {
  const weeklyByDay = new Map()
  availability.filter((entry) => entry.is_active).forEach((entry) => {
    const windows = weeklyByDay.get(entry.weekday) || []
    windows.push(`${entry.start_time.slice(0, 5)}–${entry.end_time.slice(0, 5)}`)
    weeklyByDay.set(entry.weekday, windows)
  })
  const exceptionsByDate = new Map(exceptions.map((entry) => [entry.date, entry]))

  return Array.from({ length: 14 }, (_, offset) => {
    const date = new Date()
    date.setDate(date.getDate() + offset)
    const dateValue = localDateValue(date)
    const exception = exceptionsByDate.get(dateValue)
    if (exception) {
      return {
        date: dateValue,
        is_available: !exception.is_closed,
        hours: exception.is_closed
          ? ''
          : `${exception.start_time.slice(0, 5)}–${exception.end_time.slice(0, 5)}`,
        note: exception.note,
      }
    }
    const windows = weeklyByDay.get(date.getDay() === 0 ? 6 : date.getDay() - 1) || []
    return {
      date: dateValue,
      is_available: windows.length > 0,
      hours: windows.join(', '),
      note: '',
    }
  })
}

function ClinicPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'admin'
  const canManageSchedule = ['admin', 'receptionist', 'doctor'].includes(user.role)
  const [departments, setDepartments] = useState([])
  const [doctors, setDoctors] = useState([])
  const [availability, setAvailability] = useState([])
  const [exceptions, setExceptions] = useState([])
  const [selectedDoctorId, setSelectedDoctorId] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [departmentForm, setDepartmentForm] = useState({ name: '', description: '' })
  const [doctorForm, setDoctorForm] = useState({
    email: '', password: '', first_name: '', last_name: '', phone: '', department: '',
    license_number: '', specialization: '', consultation_fee: '500.00',
    slot_duration_minutes: '30',
  })
  const [editingDoctor, setEditingDoctor] = useState(null)
  const [doctorEditForm, setDoctorEditForm] = useState({})
  const [receptionistForm, setReceptionistForm] = useState({
    email: '', password: '', first_name: '', last_name: '',
  })
  const [scheduleForm, setScheduleForm] = useState({
    weekday: '0', start_time: '09:00', end_time: '17:00',
  })
  const [exceptionForm, setExceptionForm] = useState({
    date: '', note: '', is_closed: false, start_time: '09:00', end_time: '17:00',
  })
  const [editingAvailability, setEditingAvailability] = useState({})
  const [editingException, setEditingException] = useState(null)

  const manageableDoctors = useMemo(() => {
    if (user.role === 'doctor') {
      return doctors.filter((doctor) => doctor.email === user.email)
    }
    return doctors
  }, [doctors, user.email, user.role])

  const loadClinic = useCallback(async () => {
    try {
      const [departmentData, doctorData] = await Promise.all([
        fetchDepartments(),
        fetchDoctors(),
      ])
      setDepartments(departmentData)
      setDoctors(doctorData)
      const ownDoctor = user.role === 'doctor'
        ? doctorData.find((doctor) => doctor.email === user.email)
        : null
      const desiredId = ownDoctor?.id || selectedDoctorId || doctorData[0]?.id || ''
      setSelectedDoctorId(String(desiredId))
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load clinic information.'))
    } finally {
      setLoading(false)
    }
  }, [selectedDoctorId, user.email, user.role])

  const loadSchedule = useCallback(async (doctorId) => {
    if (!doctorId || !canManageSchedule) return
    try {
      const [availabilityData, exceptionData] = await Promise.all([
        fetchAvailability(doctorId),
        fetchScheduleExceptions(doctorId),
      ])
      setAvailability(availabilityData)
      setExceptions(exceptionData)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load the doctor schedule.'))
    }
  }, [canManageSchedule])

  useEffect(() => {
    let current = true
    Promise.all([fetchDepartments(), fetchDoctors()])
      .then(([departmentData, doctorData]) => {
        if (!current) return
        setDepartments(departmentData)
        setDoctors(doctorData)
        const ownDoctor = user.role === 'doctor'
          ? doctorData.find((doctor) => doctor.email === user.email)
          : null
        const desiredId = ownDoctor?.id || selectedDoctorId || doctorData[0]?.id || ''
        setSelectedDoctorId(String(desiredId))
      })
      .catch((requestError) => {
        if (current) setError(getApiError(requestError, 'Could not load clinic information.'))
      })
      .finally(() => {
        if (current) setLoading(false)
      })
    return () => {
      current = false
    }
  }, [selectedDoctorId, user.email, user.role])

  useEffect(() => {
    if (!selectedDoctorId || !canManageSchedule) return undefined
    let current = true
    Promise.all([
      fetchAvailability(selectedDoctorId),
      fetchScheduleExceptions(selectedDoctorId),
    ])
      .then(([availabilityData, exceptionData]) => {
        if (!current) return
        setAvailability(availabilityData)
        setExceptions(exceptionData)
      })
      .catch((requestError) => {
        if (current) setError(getApiError(requestError, 'Could not load the doctor schedule.'))
      })
    return () => {
      current = false
    }
  }, [canManageSchedule, selectedDoctorId])

  function updateForm(setter, event) {
    setter((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submitAction(action, successMessage) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(successMessage)
      await loadClinic()
      if (selectedDoctorId) await loadSchedule(selectedDoctorId)
    } catch (requestError) {
      setError(getApiError(requestError, 'The change could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDepartment(event) {
    event.preventDefault()
    await submitAction(
      () => createDepartment(departmentForm),
      'Department created.',
    )
    setDepartmentForm({ name: '', description: '' })
  }

  async function handleDoctor(event) {
    event.preventDefault()
    await submitAction(
      () => createDoctor({
        ...doctorForm,
        slot_duration_minutes: Number(doctorForm.slot_duration_minutes),
      }),
      'Doctor account created.',
    )
    setDoctorForm({
      email: '', password: '', first_name: '', last_name: '', phone: '', department: '',
      license_number: '', specialization: '', consultation_fee: '500.00',
      slot_duration_minutes: '30',
    })
  }

  function startEditDoctor(doctor) {
    setEditingDoctor(doctor.id)
    setDoctorEditForm({
      department: String(doctor.department),
      phone: doctor.phone || '',
      consultation_fee: doctor.consultation_fee,
      slot_duration_minutes: String(doctor.slot_duration_minutes),
      is_accepting_appointments: doctor.is_accepting_appointments,
    })
    setError('')
    setMessage('')
  }

  async function saveDoctor(event) {
    event.preventDefault()
    const doctorId = editingDoctor
    await submitAction(
      () => updateDoctor(doctorId, {
        ...doctorEditForm,
        slot_duration_minutes: Number(doctorEditForm.slot_duration_minutes),
      }),
      'Doctor profile updated.',
    )
    setEditingDoctor(null)
  }

  async function handleReceptionist(event) {
    event.preventDefault()
    await submitAction(
      () => createReceptionist(receptionistForm),
      'Receptionist account created.',
    )
    setReceptionistForm({ email: '', password: '', first_name: '', last_name: '' })
  }

  async function handleAvailability(event) {
    event.preventDefault()
    await submitAction(
      () => createAvailability({
        ...scheduleForm,
        doctor: Number(selectedDoctorId),
        weekday: Number(scheduleForm.weekday),
      }),
      'Weekly availability added.',
    )
  }

  async function saveAvailability(entry) {
    const edit = editingAvailability[entry.id]
    if (!edit) return
    await submitAction(
      () => updateAvailability(entry.id, {
        start_time: edit.start_time,
        end_time: edit.end_time,
      }),
      `${entry.weekday_label} hours updated.`,
    )
    setEditingAvailability((current) => {
      const next = { ...current }
      delete next[entry.id]
      return next
    })
  }

  async function removeAvailability(entry) {
    await submitAction(
      () => deleteAvailability(entry.id),
      `${entry.weekday_label} availability removed.`,
    )
  }

  async function handleException(event) {
    event.preventDefault()
    const exceptionDetails = {
      ...exceptionForm,
      doctor: Number(selectedDoctorId),
      start_time: exceptionForm.is_closed ? null : exceptionForm.start_time,
      end_time: exceptionForm.is_closed ? null : exceptionForm.end_time,
    }
    await submitAction(
      () => editingException
        ? updateScheduleException(editingException.id, exceptionDetails)
        : createScheduleException(exceptionDetails),
      editingException ? 'Date-specific availability updated.' : 'Date-specific availability added.',
    )
    setExceptionForm({ date: '', note: '', is_closed: false, start_time: '09:00', end_time: '17:00' })
    setEditingException(null)
  }

  function editException(entry) {
    setEditingException(entry)
    setExceptionForm({
      date: entry.date,
      note: entry.note || '',
      is_closed: entry.is_closed,
      start_time: entry.start_time?.slice(0, 5) || '09:00',
      end_time: entry.end_time?.slice(0, 5) || '17:00',
    })
  }

  async function removeException(entry) {
    await submitAction(
      () => deleteScheduleException(entry.id),
      `Date override for ${formatCalendarDate(entry.date)} removed.`,
    )
    if (editingException?.id === entry.id) {
      setEditingException(null)
      setExceptionForm({ date: '', note: '', is_closed: false, start_time: '09:00', end_time: '17:00' })
    }
  }

  if (loading) return <p className="route-message" role="status">Loading clinic information…</p>

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">CLINIC DIRECTORY</p><h1>Doctors & departments</h1></div>
        <span className="count-pill">{doctors.length} doctors</span>
      </div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}

      <section className="doctor-grid">
        {doctors.map((doctor) => (
          <article className="panel doctor-card" key={doctor.id}>
            <span className="doctor-avatar">{(doctor.first_name || doctor.email).slice(0, 1).toUpperCase()}</span>
            <div>
              <p className="eyebrow">{doctor.department_name}</p>
              <h2>Dr. {doctor.first_name} {doctor.last_name}</h2>
              <p>{doctor.specialization}</p>
              <span className="muted-copy">Consultation fee: ₹{doctor.consultation_fee}</span>
              {doctor.phone && <span className="muted-copy">Phone: {doctor.phone}</span>}
              <span className="muted-copy">{doctor.slot_duration_minutes}-minute appointments</span>
              {isAdmin && <button className="text-button" type="button" onClick={() => startEditDoctor(doctor)}>Edit doctor</button>}
              {isAdmin && editingDoctor === doctor.id && (
                <form className="staff-inline-form" onSubmit={saveDoctor}>
                  <label>Department<select required value={doctorEditForm.department} onChange={(event) => setDoctorEditForm({ ...doctorEditForm, department: event.target.value })}>{departments.filter((department) => department.is_active).map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
                  <label>Phone<input maxLength="32" value={doctorEditForm.phone} onChange={(event) => setDoctorEditForm({ ...doctorEditForm, phone: event.target.value })} /></label>
                  <label>Consultation fee<input required type="number" min="0" step="0.01" value={doctorEditForm.consultation_fee} onChange={(event) => setDoctorEditForm({ ...doctorEditForm, consultation_fee: event.target.value })} /></label>
                  <label>Slot duration<input required type="number" min="5" max="240" value={doctorEditForm.slot_duration_minutes} onChange={(event) => setDoctorEditForm({ ...doctorEditForm, slot_duration_minutes: event.target.value })} /></label>
                  <label>Accepting appointments<select value={doctorEditForm.is_accepting_appointments ? 'yes' : 'no'} onChange={(event) => setDoctorEditForm({ ...doctorEditForm, is_accepting_appointments: event.target.value === 'yes' })}><option value="yes">Active</option><option value="no">Inactive</option></select></label>
                  <button className="primary-button" disabled={saving}>Save doctor</button>
                  <button className="text-button" type="button" onClick={() => setEditingDoctor(null)}>Cancel</button>
                </form>
              )}
            </div>
          </article>
        ))}
        {doctors.length === 0 && <p className="empty-state">No doctors have been added yet.</p>}
      </section>

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">CLINIC DIRECTORY</p><h2>Departments</h2></div></div>
        {departments.length === 0
          ? <p className="empty-state">No active departments are available.</p>
          : (
            <div className="department-management-list">
              {departments.map((department) => (
                <article className="department-management-card" key={department.id}>
                  <p className="eyebrow">{department.code}</p>
                  <h3>{department.name}</h3>
                  {department.description && <p>{department.description}</p>}
                </article>
              ))}
            </div>
          )}
      </section>

      {isAdmin && (
        <div className="management-grid">
          <form className="panel workspace-panel" onSubmit={handleDepartment}>
            <div className="section-heading"><div><p className="eyebrow">ADMIN</p><h2>Add department</h2></div></div>
            <div className="form-grid">
              <label>Name<input name="name" required value={departmentForm.name} onChange={(event) => updateForm(setDepartmentForm, event)} /></label>
              <label>Description<input name="description" value={departmentForm.description} onChange={(event) => updateForm(setDepartmentForm, event)} /></label>
            </div>
            <button className="primary-button form-submit" disabled={saving}>Create department</button>
          </form>

          <form className="panel workspace-panel" onSubmit={handleReceptionist}>
            <div className="section-heading"><div><p className="eyebrow">ADMIN</p><h2>Add receptionist</h2></div></div>
            <div className="form-grid">
              <label>First name<input name="first_name" required value={receptionistForm.first_name} onChange={(event) => updateForm(setReceptionistForm, event)} /></label>
              <label>Last name<input name="last_name" required value={receptionistForm.last_name} onChange={(event) => updateForm(setReceptionistForm, event)} /></label>
              <label>Email<input name="email" type="email" required value={receptionistForm.email} onChange={(event) => updateForm(setReceptionistForm, event)} /></label>
              <label>Temporary password<input name="password" type="password" minLength="8" required value={receptionistForm.password} onChange={(event) => updateForm(setReceptionistForm, event)} /></label>
            </div>
            <button className="primary-button form-submit" disabled={saving}>Create receptionist account</button>
          </form>

          <form className="panel workspace-panel" onSubmit={handleDoctor}>
            <div className="section-heading"><div><p className="eyebrow">ADMIN</p><h2>Add doctor</h2></div></div>
            <div className="form-grid">
              <label>First name<input name="first_name" required value={doctorForm.first_name} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Last name<input name="last_name" required value={doctorForm.last_name} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Email<input name="email" type="email" required value={doctorForm.email} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Phone<input name="phone" maxLength="32" value={doctorForm.phone} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Temporary password<input name="password" type="password" minLength="8" required value={doctorForm.password} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Department<select name="department" required value={doctorForm.department} onChange={(event) => updateForm(setDoctorForm, event)}><option value="">Choose a department</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
              <label>Medical license<input name="license_number" required value={doctorForm.license_number} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Specialization<input name="specialization" required value={doctorForm.specialization} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Consultation fee<input name="consultation_fee" type="number" min="0" step="0.01" required value={doctorForm.consultation_fee} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
              <label>Appointment length (minutes)<input name="slot_duration_minutes" type="number" min="5" max="240" required value={doctorForm.slot_duration_minutes} onChange={(event) => updateForm(setDoctorForm, event)} /></label>
            </div>
            <button className="primary-button form-submit" disabled={saving}>Create doctor account</button>
          </form>
        </div>
      )}

      {canManageSchedule && manageableDoctors.length > 0 && (
        <section className="panel workspace-panel">
          <div className="section-heading">
            <div><p className="eyebrow">{user.role === 'doctor' ? 'MY SCHEDULE' : 'SCHEDULE MANAGEMENT'}</p><h2>{user.role === 'doctor' ? 'My availability' : 'Weekly availability'}</h2></div>
            {user.role !== 'doctor' && (
              <select aria-label="Select doctor" value={selectedDoctorId} onChange={(event) => setSelectedDoctorId(event.target.value)}>
                {manageableDoctors.map((doctor) => <option value={doctor.id} key={doctor.id}>Dr. {doctor.first_name} {doctor.last_name}</option>)}
              </select>
            )}
          </div>
          <form onSubmit={handleAvailability}>
            <div className="form-grid">
              <label>Weekday<select name="weekday" value={scheduleForm.weekday} onChange={(event) => updateForm(setScheduleForm, event)}>{weekdays.map((day, index) => <option value={index} key={day}>{day}</option>)}</select></label>
              <label>Starts<input name="start_time" type="time" required value={scheduleForm.start_time} onChange={(event) => updateForm(setScheduleForm, event)} /></label>
              <label>Ends<input name="end_time" type="time" required value={scheduleForm.end_time} onChange={(event) => updateForm(setScheduleForm, event)} /></label>
            </div>
            <button className="primary-button form-submit" disabled={saving}>Add hours</button>
          </form>
          {(availability.length > 0 || exceptions.length > 0) && (
            <div className="compact-list weekly-availability-list">
              {availability.map((entry) => {
                const edit = editingAvailability[entry.id]
                return (
                  <div className="weekly-availability-row" key={entry.id}>
                    <strong>{entry.weekday_label}</strong>
                    {edit ? (
                      <div className="weekly-availability-edit">
                        <label>Starts<input type="time" value={edit.start_time} onChange={(event) => setEditingAvailability((current) => ({ ...current, [entry.id]: { ...current[entry.id], start_time: event.target.value } }))} /></label>
                        <label>Ends<input type="time" value={edit.end_time} onChange={(event) => setEditingAvailability((current) => ({ ...current, [entry.id]: { ...current[entry.id], end_time: event.target.value } }))} /></label>
                        <button className="text-button" type="button" disabled={saving} onClick={() => saveAvailability(entry)}>Save</button>
                        <button className="text-button" type="button" onClick={() => setEditingAvailability((current) => { const next = { ...current }; delete next[entry.id]; return next })}>Cancel</button>
                      </div>
                    ) : (
                      <>
                        <span>{entry.start_time.slice(0, 5)}–{entry.end_time.slice(0, 5)}{!entry.is_active ? ' · Inactive' : ''}</span>
                        <div className="schedule-row-actions">
                          <button className="text-button" type="button" onClick={() => setEditingAvailability((current) => ({ ...current, [entry.id]: { start_time: entry.start_time.slice(0, 5), end_time: entry.end_time.slice(0, 5) } }))}>Edit time</button>
                          <button className="text-button schedule-delete-button" type="button" disabled={saving} onClick={() => removeAvailability(entry)}>Remove</button>
                        </div>
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {availability.length > 0 && (
            <div className="availability-date-preview">
              <h3>Upcoming dates</h3>
              <p className="muted-copy">These dates use your weekly hours unless a date-specific override is listed below.</p>
              <div className="availability-date-grid">
                {getUpcomingScheduleDates(availability, exceptions).map((entry) => (
                  <article className={`availability-date-card${entry.is_available ? '' : ' availability-date-closed'}`} key={entry.date}>
                    <strong>{formatCalendarDate(entry.date)}</strong>
                    <span>{entry.hours || 'Not available'}</span>
                    {entry.note && <small>{entry.note}</small>}
                  </article>
                ))}
              </div>
            </div>
          )}

          <form className="exception-form" onSubmit={handleException}>
            <div className="section-heading"><div><p className="eyebrow">DATE-SPECIFIC SCHEDULE</p><h2>{editingException ? 'Edit date override' : 'Add or change a date'}</h2></div></div>
            <div className="form-grid">
              <label>Date<input type="date" required min={localDateValue()} value={exceptionForm.date} onChange={(event) => setExceptionForm({ ...exceptionForm, date: event.target.value })} /></label>
              <label>Availability
                <select value={exceptionForm.is_closed ? 'closed' : 'open'} onChange={(event) => setExceptionForm({ ...exceptionForm, is_closed: event.target.value === 'closed' })}>
                  <option value="open">Available during these hours</option>
                  <option value="closed">Unavailable all day</option>
                </select>
              </label>
              {!exceptionForm.is_closed && <>
                <label>Starts<input name="start_time" type="time" required value={exceptionForm.start_time} onChange={(event) => setExceptionForm({ ...exceptionForm, start_time: event.target.value })} /></label>
                <label>Ends<input name="end_time" type="time" required value={exceptionForm.end_time} onChange={(event) => setExceptionForm({ ...exceptionForm, end_time: event.target.value })} /></label>
              </>}
              <label>Note<input value={exceptionForm.note} onChange={(event) => setExceptionForm({ ...exceptionForm, note: event.target.value })} /></label>
            </div>
            <button className="secondary-button form-submit" disabled={saving}>{editingException ? 'Save date override' : 'Save date availability'}</button>
            {editingException && <button className="text-button" type="button" onClick={() => { setEditingException(null); setExceptionForm({ date: '', note: '', is_closed: false, start_time: '09:00', end_time: '17:00' }) }}>Cancel edit</button>}
          </form>
          {exceptions.length > 0 && <div className="compact-list">{exceptions.map((entry) => (
            <div className="schedule-exception-row" key={entry.id}>
              <strong>{formatCalendarDate(entry.date)}</strong>
              <span>{entry.is_closed ? 'Unavailable all day' : `${entry.start_time.slice(0, 5)}–${entry.end_time.slice(0, 5)}`}{entry.note ? ` · ${entry.note}` : ''}</span>
              <div className="schedule-row-actions">
                <button className="text-button" type="button" onClick={() => editException(entry)}>Edit</button>
                <button className="text-button schedule-delete-button" type="button" disabled={saving} onClick={() => removeException(entry)}>Remove</button>
              </div>
            </div>
          ))}</div>}
        </section>
      )}
    </section>
  )
}

export default ClinicPage
