import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchPrescription } from '../api/clinical'
import { getApiError } from '../utils/apiError'

function PrescriptionPrintPage() {
  const { prescriptionId } = useParams()
  const [prescription, setPrescription] = useState(null)
  const [error, setError] = useState('')
  const medicineLabel = (item) => item.medication_name.toLocaleLowerCase().includes(
    (item.strength || '').toLocaleLowerCase(),
  ) ? item.medication_name : `${item.medication_name} ${item.strength}`.trim()

  useEffect(() => {
    let active = true
    fetchPrescription(prescriptionId)
      .then((data) => {
        if (active) setPrescription(data)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load this prescription.'))
      })
    return () => {
      active = false
    }
  }, [prescriptionId])

  if (error) {
    return (
      <section className="workspace-page">
        <p className="form-error notice" role="alert">{error}</p>
        <Link className="text-button" to="/prescriptions">Back to prescriptions</Link>
      </section>
    )
  }
  if (!prescription) return <p className="route-message" role="status">Loading prescription…</p>

  return (
    <section className="workspace-page prescription-print-page">
      <div className="prescription-print-actions">
        <Link className="text-button" to="/prescriptions">← Back to prescriptions</Link>
        <button className="primary-button" type="button" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>
      <article className="panel prescription-paper">
        <header className="prescription-paper-header">
          <p className="eyebrow">MEDiTRACK</p>
          <h1>PRESCRIPTION</h1>
          <p>{new Date(prescription.created_at).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}</p>
        </header>
        <dl className="prescription-paper-details">
          <div><dt>Doctor</dt><dd>Dr. {prescription.doctor_name}</dd></div>
          <div><dt>Department</dt><dd>{prescription.department_name || '—'}</dd></div>
          <div><dt>Patient Number</dt><dd>{prescription.patient_number}</dd></div>
          <div><dt>Patient name</dt><dd>{prescription.patient_name}</dd></div>
          <div><dt>Age</dt><dd>{prescription.patient_age ?? 'Not recorded'}</dd></div>
          <div><dt>Gender</dt><dd>{prescription.patient_gender || 'Not recorded'}</dd></div>
        </dl>
        <div className="table-wrap prescription-paper-table">
          <table>
            <thead>
              <tr><th>Medicine</th><th>Dosage</th><th>Frequency</th><th>Duration</th><th>Food timing</th></tr>
            </thead>
            <tbody>
              {prescription.items.map((item) => (
                <tr key={item.id}>
                  <td><strong>{medicineLabel(item)}</strong>{item.route ? <><br />{item.route}</> : null}</td>
                  <td>{item.dosage}</td>
                  <td>{item.frequency}</td>
                  <td>{item.duration}</td>
                  <td>{item.food_timing ? item.food_timing.replaceAll('_', ' ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {prescription.items.some((item) => item.instructions) && (
          <section className="prescription-paper-notes">
            <h2>Medicine instructions</h2>
            {prescription.items.filter((item) => item.instructions).map((item) => (
              <p key={item.id}><strong>{item.medication_name}:</strong> {item.instructions}</p>
            ))}
          </section>
        )}
        <section className="prescription-paper-notes">
          <h2>Additional instructions / Doctor’s notes</h2>
          <p>{prescription.instructions || '—'}</p>
        </section>
        <footer className="prescription-paper-signature">
          <span>Doctor signature</span>
        </footer>
      </article>
    </section>
  )
}

export default PrescriptionPrintPage
