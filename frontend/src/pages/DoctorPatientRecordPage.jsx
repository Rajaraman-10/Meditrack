import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchDoctorPatientRecord } from '../api/patients'
import { getApiError } from '../utils/apiError'

function DoctorPatientRecordPage() {
  const { patientId } = useParams()
  const [record, setRecord] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchDoctorPatientRecord(patientId)
      .then((data) => {
        if (active) setRecord(data)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load this patient record.'))
      })
    return () => {
      active = false
    }
  }, [patientId])

  if (error) {
    return (
      <section className="workspace-page">
        <p className="form-error notice" role="alert">{error}</p>
        <Link className="text-button" to="/doctor">Back to doctor dashboard</Link>
      </section>
    )
  }
  if (!record) return <p className="route-message" role="status">Loading patient record…</p>

  const { patient } = record
  const patientName = `${patient.first_name} ${patient.last_name}`.trim()

  return (
    <section className="workspace-page doctor-record-page">
      <Link className="text-button" to="/doctor">← Doctor dashboard</Link>
      <header className="panel doctor-record-header">
        <div>
          <p className="eyebrow">AUTHORIZED PATIENT RECORD</p>
          <h1>{patientName || patient.email}</h1>
          <p className="doctor-record-number">{patient.patient_number}</p>
        </div>
        <dl className="doctor-record-details">
          <div><dt>Date of birth</dt><dd>{patient.date_of_birth || 'Not recorded'}</dd></div>
          <div><dt>Gender</dt><dd>{patient.gender || 'Not recorded'}</dd></div>
          <div><dt>Blood group</dt><dd>{patient.blood_group || 'Not recorded'}</dd></div>
          <div><dt>Phone</dt><dd>{patient.phone || 'Not recorded'}</dd></div>
        </dl>
      </header>

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">CARE HISTORY</p><h2>Appointments</h2></div></div>
        {!record.appointments.length ? <p className="empty-state">No appointments with you are recorded.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Department</th><th>Reason</th><th>Status</th></tr></thead>
              <tbody>{record.appointments.map((appointment) => (
                <tr key={appointment.id}>
                  <td>{new Date(appointment.starts_at).toLocaleString()}</td>
                  <td>{appointment.department_name || '—'}</td>
                  <td>{appointment.reason || 'General consultation'}</td>
                  <td>{appointment.status.replaceAll('_', ' ')}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">CLINICAL NOTES</p><h2>Consultations</h2></div></div>
        {!record.consultations.length ? <p className="empty-state">No consultation notes are recorded.</p> : (
          <div className="doctor-record-list">
            {record.consultations.map((consultation) => (
              <article className="doctor-record-item" key={consultation.id}>
                <div className="section-heading">
                  <strong>{new Date(consultation.appointment_starts_at).toLocaleDateString()}</strong>
                  <span className="status-chip">{consultation.status.replaceAll('_', ' ')}</span>
                </div>
                <p><strong>Diagnosis:</strong> {consultation.diagnosis || 'Not recorded'}</p>
                <p><strong>Clinical notes:</strong> {consultation.clinical_notes || 'Not recorded'}</p>
                {consultation.follow_up_date && <p><strong>Follow-up:</strong> {consultation.follow_up_date}</p>}
                {consultation.notes?.map((note) => <p key={note.id}>{note.body}</p>)}
              </article>
            ))}
          </div>
        )}
      </section>

      <div className="doctor-record-grid">
        <section className="panel workspace-panel">
          <div className="section-heading"><div><p className="eyebrow">MEDICATION</p><h2>Prescriptions</h2></div></div>
          {!record.prescriptions.length ? <p className="empty-state">No prescriptions are recorded.</p> : (
            <div className="doctor-record-list">
              {record.prescriptions.map((prescription) => (
                <article className="doctor-record-item" key={prescription.id}>
                  <p>{prescription.instructions || 'No additional instructions.'}</p>
                  {prescription.items.map((item) => (
                    <p key={item.id}><strong>{item.medication_name}</strong> — {item.dosage}, {item.frequency}, {item.duration}</p>
                  ))}
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel workspace-panel">
          <div className="section-heading"><div><p className="eyebrow">DIAGNOSTICS</p><h2>Laboratory tests</h2></div></div>
          {!record.lab_tests.length ? <p className="empty-state">No laboratory tests are recorded.</p> : (
            <div className="doctor-record-list">
              {record.lab_tests.map((test) => (
                <article className="doctor-record-item" key={test.id}>
                  <strong>{test.name}</strong><p>{test.status.replaceAll('_', ' ')}</p>
                  {test.reports.map((report) => <p key={report.id}>{report.result_text || 'Report uploaded'} · {new Date(report.reported_at).toLocaleDateString()}</p>)}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">DOCUMENTS</p><h2>Medical documents</h2></div></div>
        {!record.documents.length ? <p className="empty-state">No documents are linked to your appointments with this patient.</p> : (
          <div className="doctor-record-list">
            {record.documents.map((document) => (
              <article className="doctor-record-item" key={document.id}>
                <strong>{document.title}</strong>
                <p>{document.file_name} · {document.category} · {new Date(document.uploaded_at).toLocaleDateString()}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

export default DoctorPatientRecordPage
