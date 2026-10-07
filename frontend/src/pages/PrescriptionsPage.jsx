import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAppointments } from '../api/appointments'
import { createPrescription, fetchConsultations, fetchPrescriptions, searchMedicines, startConsultation } from '../api/clinical'
import { searchDoctorPatient } from '../api/patients'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

function ageFromDate(dateString) {
  if (!dateString) return null
  const [year, month, day] = dateString.split('-').map(Number)
  const today = new Date()
  return today.getFullYear() - year - (
    today.getMonth() + 1 < month
    || (today.getMonth() + 1 === month && today.getDate() < day)
      ? 1
      : 0
  )
}

function medicineLabel(medicine) {
  return medicine.name.toLocaleLowerCase().includes(medicine.strength.toLocaleLowerCase())
    ? medicine.name
    : `${medicine.name} ${medicine.strength}`
}

function newMedicineRow(key) {
  return {
    key,
    medicine: null,
    manualEntry: false,
    medication_name: '',
    strength: '',
    dosage: '',
    route: '',
    frequency: '',
    duration: '',
    food_timing: '',
    instructions: '',
  }
}

function MedicineEntry({ item, index, onChange, onRemove, canRemove, setError }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (query.trim().length < 2) return undefined

    let active = true
    const timer = window.setTimeout(async () => {
      setSearching(true)
      try {
        const matches = await searchMedicines(query.trim())
        if (active) setResults(matches)
      } catch (requestError) {
        if (active) setError(getApiError(requestError, 'Could not search the medicine catalog.'))
      } finally {
        if (active) setSearching(false)
      }
    }, 250)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [query, setError])

  function setDetail(field, value) {
    onChange(index, { [field]: value })
  }

  const selectedMedicine = item.medicine
  const fieldId = `medicine-search-${item.key}`

  return (
    <fieldset className="prescription-medicine-row">
      <legend>Medicine {index + 1}</legend>
      {!item.manualEntry ? (
        <div className="medicine-autocomplete">
          <label htmlFor={fieldId}>Medicine from catalog</label>
          <input
            id={fieldId}
            autoComplete="off"
            placeholder="Type a name or generic name"
            value={selectedMedicine ? medicineLabel(selectedMedicine) : query}
            onChange={(event) => {
              setQuery(event.target.value)
              setResults([])
              setSearching(false)
              onChange(index, { medicine: null })
            }}
            required={!selectedMedicine}
            aria-autocomplete="list"
            aria-expanded={results.length > 0}
          />
          {searching && <span className="medicine-search-status" role="status">Searching catalog…</span>}
          {results.length > 0 && !selectedMedicine && (
            <ul className="medicine-suggestions" role="listbox" aria-label="Medicine search results">
              {results.map((medicine) => (
                <li key={medicine.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected="false"
                    onClick={() => {
                      onChange(index, { medicine, route: medicine.route || '' })
                      setQuery('')
                      setResults([])
                    }}
                  >
                    <strong>{medicineLabel(medicine)}</strong>
                    <span>{[medicine.generic_name, medicine.dosage_form].filter(Boolean).join(' · ')}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {!searching && query.trim().length >= 2 && results.length === 0 && !selectedMedicine && (
            <span className="medicine-search-status" role="status">No catalog match found.</span>
          )}
          {selectedMedicine && (
            <button
              className="text-button medicine-change-button"
              type="button"
              onClick={() => {
                onChange(index, { medicine: null })
                setQuery('')
              }}
            >
              Choose a different medicine
            </button>
          )}
          {!selectedMedicine && (
            <button
              className="text-button medicine-change-button"
              type="button"
              onClick={() => {
                onChange(index, { manualEntry: true, medicine: null })
                setQuery('')
                setResults([])
              }}
            >
              Enter a medicine not in the catalog
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="form-grid prescription-item-fields manual-medicine-fields">
            <label>Medicine name<input required maxLength="180" value={item.medication_name} onChange={(event) => onChange(index, { medication_name: event.target.value })} /></label>
            <label>Strength<input required maxLength="100" placeholder="e.g. 250 mg" value={item.strength} onChange={(event) => onChange(index, { strength: event.target.value })} /></label>
          </div>
          <button
            className="text-button medicine-change-button"
            type="button"
            onClick={() => onChange(index, { manualEntry: false, medication_name: '', strength: '' })}
          >
            Choose from medicine catalog
          </button>
        </>
      )}
      <div className="form-grid prescription-item-fields">
        <label>Dosage<input required maxLength="180" placeholder="e.g. 1 tablet" value={item.dosage} onChange={(event) => setDetail('dosage', event.target.value)} /></label>
        <label>Route<input required maxLength="80" placeholder="e.g. oral" value={item.route} onChange={(event) => setDetail('route', event.target.value)} /></label>
        <label>Frequency<input required maxLength="180" placeholder="e.g. as prescribed" value={item.frequency} onChange={(event) => setDetail('frequency', event.target.value)} /></label>
        <label>Duration<input required maxLength="100" placeholder="e.g. 5 days" value={item.duration} onChange={(event) => setDetail('duration', event.target.value)} /></label>
        <label>Food timing
          <select required value={item.food_timing} onChange={(event) => setDetail('food_timing', event.target.value)}>
            <option value="">Select timing</option>
            <option value="before_food">Before food</option>
            <option value="after_food">After food</option>
            <option value="with_food">With food</option>
            <option value="any">Any time</option>
          </select>
        </label>
        <label>Medicine instructions<input maxLength="500" placeholder="Optional directions" value={item.instructions} onChange={(event) => setDetail('instructions', event.target.value)} /></label>
      </div>
      {canRemove && <button className="text-button medicine-remove-button" type="button" onClick={() => onRemove(item.key)}>Remove medicine</button>}
    </fieldset>
  )
}

function PrescriptionsPage() {
  const { user } = useAuth()
  const nextKey = useRef(2)
  const [prescriptions, setPrescriptions] = useState([])
  const [consultations, setConsultations] = useState([])
  const [checkedInAppointments, setCheckedInAppointments] = useState([])
  const [patientNumber, setPatientNumber] = useState('')
  const [patient, setPatient] = useState(null)
  const [consultation, setConsultation] = useState('')
  const [medicines, setMedicines] = useState([newMedicineRow(1)])
  const [instructions, setInstructions] = useState('')
  const [loading, setLoading] = useState(true)
  const [searchingPatient, setSearchingPatient] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    try {
      const [records, clinicalRecords, appointments] = await Promise.all([
        fetchPrescriptions(),
        user.role === 'doctor' ? fetchConsultations() : Promise.resolve([]),
        user.role === 'doctor' ? fetchAppointments() : Promise.resolve([]),
      ])
      setPrescriptions(records)
      setConsultations(clinicalRecords.filter(
        (item) => item.status === 'completed',
      ))
      setCheckedInAppointments(appointments.filter((item) => item.status === 'checked_in'))
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load prescriptions.'))
    } finally {
      setLoading(false)
    }
  }, [user.role])

  useEffect(() => {
    let active = true
    Promise.all([
      fetchPrescriptions(),
      user.role === 'doctor' ? fetchConsultations() : Promise.resolve([]),
      user.role === 'doctor' ? fetchAppointments() : Promise.resolve([]),
    ])
      .then(([records, clinicalRecords, appointments]) => {
        if (!active) return
        setPrescriptions(records)
        setConsultations(clinicalRecords.filter(
          (item) => item.status === 'completed',
        ))
        setCheckedInAppointments(appointments.filter((item) => item.status === 'checked_in'))
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load prescriptions.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [user.role])

  async function findPatient(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setPatient(null)
    setConsultation('')
    setSearchingPatient(true)
    try {
      const match = await searchDoctorPatient(patientNumber)
      setPatient(match)
      const eligibleConsultations = consultations.filter(
        (item) => item.patient_number === match.patient_number,
      )
      const readyAppointments = checkedInAppointments.filter(
        (item) => item.patient_number === match.patient_number,
      )
      if (eligibleConsultations.length === 0 && readyAppointments.length === 0) {
        setMessage('Patient confirmed. No consultation or checked-in appointment was found for this patient.')
      } else if (eligibleConsultations.length === 0) {
        setMessage('Patient confirmed. Start a consultation below to enable prescription entry.')
      }
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not find an accessible patient.'))
    } finally {
      setSearchingPatient(false)
    }
  }

  function changeMedicine(index, update) {
    setMedicines((current) => current.map(
      (item, itemIndex) => itemIndex === index ? { ...item, ...update } : item,
    ))
  }

  function addMedicine() {
    setMedicines((current) => [...current, newMedicineRow(nextKey.current++)])
  }

  async function beginConsultation(appointmentId) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const started = await startConsultation(appointmentId)
      setConsultations((current) => [started, ...current])
      setConsultation(String(started.id))
      setCheckedInAppointments((current) => current.filter((item) => item.id !== appointmentId))
      setMessage('Consultation started. You can now enter the prescription.')
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not start the consultation. Confirm the appointment is checked in.'))
    } finally {
      setSaving(false)
    }
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await createPrescription({
        consultation: Number(consultation),
        instructions,
        items: medicines.map((item) => ({
          ...(item.medicine ? { medicine: item.medicine.id } : {
            medication_name: item.medication_name,
            strength: item.strength,
          }),
          dosage: item.dosage,
          route: item.route,
          frequency: item.frequency,
          duration: item.duration,
          food_timing: item.food_timing,
          instructions: item.instructions,
        })),
      })
      setPatient(null)
      setPatientNumber('')
      setConsultation('')
      setMedicines([newMedicineRow(nextKey.current++)])
      setInstructions('')
      setMessage('Prescription issued. Billing must confirm payment before it is released to the patient portal.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not issue the prescription.'))
    } finally {
      setSaving(false)
    }
  }

  const patientConsultations = patient
    ? consultations.filter(
      (item) => item.patient_number === patient.patient_number,
    )
    : []
  const patientCheckedInAppointments = patient
    ? checkedInAppointments.filter((item) => item.patient_number === patient.patient_number)
    : []

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">MEDICATIONS</p><h1>{user.role === 'patient' ? 'My prescriptions' : 'Prescriptions'}</h1></div>
        <span className="count-pill">{prescriptions.length} records</span>
      </div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}

      {user.role === 'doctor' && (
        <section className="panel workspace-panel prescription-composer">
          <div className="section-heading">
            <div><p className="eyebrow">DOCTOR WORKFLOW</p><h2>Create prescription</h2></div>
          </div>
          <form className="patient-confirm-form" onSubmit={findPatient}>
            <label htmlFor="prescription-patient-number">Patient Number</label>
            <div className="doctor-search-controls">
              <input
                id="prescription-patient-number"
                autoComplete="off"
                placeholder="e.g. MED-000123"
                value={patientNumber}
                onChange={(event) => {
                  setPatientNumber(event.target.value)
                  setPatient(null)
                  setConsultation('')
                }}
                required
              />
              <button className="primary-button" disabled={searchingPatient || loading}>
                {searchingPatient ? 'Looking up…' : 'Find patient'}
              </button>
            </div>
          </form>

          {patient && (
            <div className="confirmed-patient-card" role="status">
              <p className="eyebrow">CONFIRM PATIENT BEFORE PRESCRIBING</p>
              <h3>{patient.first_name} {patient.last_name}</h3>
              <dl>
                <div><dt>Patient Number</dt><dd>{patient.patient_number}</dd></div>
                <div><dt>Age</dt><dd>{ageFromDate(patient.date_of_birth) ?? 'Not recorded'}</dd></div>
                <div><dt>Gender</dt><dd>{patient.gender || 'Not recorded'}</dd></div>
              </dl>
            </div>
          )}

          {patient && patientConsultations.length === 0 && patientCheckedInAppointments.length > 0 && (
            <div className="confirmed-patient-card">
              <p className="eyebrow">CHECKED-IN APPOINTMENT</p>
              <p className="muted-copy">Start this patient’s consultation before writing the prescription.</p>
              {patientCheckedInAppointments.map((appointment) => (
                <div className="checked-in-appointment-row" key={appointment.id}>
                  <strong>{new Date(appointment.starts_at).toLocaleString()}</strong>
                  <button
                    className="primary-button"
                    type="button"
                    disabled={saving}
                    onClick={() => beginConsultation(appointment.id)}
                  >
                    {saving ? 'Starting…' : 'Start consultation'}
                  </button>
                </div>
              ))}
            </div>
          )}

          {patient && patientConsultations.length === 0 && patientCheckedInAppointments.length === 0 && (
            <p className="empty-state">
              No active consultation or checked-in appointment is available for this patient.
              Ask reception to check in an appointment, then search again.
            </p>
          )}

          {patient && patientConsultations.length > 0 && (
            <form onSubmit={submit}>
              <label className="prescription-consultation-select">
                Consultation
                <select required value={consultation} onChange={(event) => setConsultation(event.target.value)}>
                  <option value="">Select this patient's consultation</option>
                  {patientConsultations.map((item) => (
                    <option value={item.id} key={item.id}>
                      {new Date(item.appointment_starts_at).toLocaleString()} · {item.status.replaceAll('_', ' ')}
                    </option>
                  ))}
                </select>
              </label>

              <div className="section-heading prescription-medicine-heading">
                <div><p className="eyebrow">PRESCRIPTION</p><h3>Medicines and directions</h3></div>
              </div>
              <div className="prescription-medicine-list">
                {medicines.map((item, index) => (
                  <MedicineEntry
                    key={item.key}
                    item={item}
                    index={index}
                    onChange={changeMedicine}
                    onRemove={(key) => setMedicines((current) => current.filter((row) => row.key !== key))}
                    canRemove={medicines.length > 1}
                    setError={setError}
                  />
                ))}
              </div>
              <button className="secondary-button" type="button" onClick={addMedicine}>+ Add another medicine</button>
              <label className="wide-label prescription-notes-label">
                Additional instructions and doctor’s notes
                <textarea rows="3" maxLength="4000" value={instructions} onChange={(event) => setInstructions(event.target.value)} />
              </label>
              <button className="primary-button form-submit" disabled={saving || !consultation || medicines.some((item) => !item.medicine && !(item.manualEntry && item.medication_name.trim() && item.strength.trim()))}>
                {saving ? 'Issuing…' : 'Issue prescription'}
              </button>
            </form>
          )}
        </section>
      )}

      {loading ? <section className="panel workspace-panel"><p className="empty-state">Loading prescriptions…</p></section> : prescriptions.length === 0 ? (
        <section className="panel workspace-panel"><p className="empty-state">No prescriptions are available.</p></section>
      ) : prescriptions.map((record) => (
        <article className="panel workspace-panel prescription-card" key={record.id}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">{new Date(record.created_at).toLocaleDateString()} · {record.status.replaceAll('_', ' ')}</p>
              <h2>{user.role === 'patient' ? `Dr. ${record.doctor_name}` : record.patient_name}</h2>
            </div>
            {record.status === 'released'
              ? <Link className="text-button" to={`/prescriptions/${record.id}/print`}>View / Download PDF</Link>
              : <span className="muted-copy">Prescription payment pending</span>}
          </div>
          <p className="prescription-patient-meta">
            Patient Number: {record.patient_number}
            {record.patient_age !== null && record.patient_age !== undefined ? ` · Age ${record.patient_age}` : ''}
            {record.patient_gender ? ` · ${record.patient_gender}` : ''}
          </p>
          {record.items.map((item) => (
            <div className="compact-list" key={item.id}>
              <div>
                    <strong>{medicineLabel({ name: item.medication_name, strength: item.strength || '' })}</strong>
                <span>{item.dosage}, {item.route}, {item.frequency} for {item.duration}{item.food_timing ? ` · ${item.food_timing.replaceAll('_', ' ')}` : ''}{item.instructions ? ` · ${item.instructions}` : ''}</span>
              </div>
            </div>
          ))}
          {record.instructions && <p className="record-copy">{record.instructions}</p>}
        </article>
      ))}
    </section>
  )
}

export default PrescriptionsPage
