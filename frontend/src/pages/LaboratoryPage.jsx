import { useCallback, useEffect, useState } from 'react'
import { downloadDocument, fetchConsultations, fetchLabTests, recordLabReport, requestLabTest, reviewLabReport, uploadDocument } from '../api/clinical'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

function LaboratoryPage() {
  const { user } = useAuth()
  const [tests, setTests] = useState([])
  const [consultations, setConsultations] = useState([])
  const [consultation, setConsultation] = useState('')
  const [name, setName] = useState('')
  const [clinicalQuestion, setClinicalQuestion] = useState('')
  const [results, setResults] = useState({})
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const getPageData = useCallback(() => {
    return Promise.all([
      fetchLabTests(),
      user.role === 'doctor' ? fetchConsultations() : Promise.resolve([]),
    ])
  }, [user.role])

  const load = useCallback(async () => {
    try {
      const [testRecords, clinicalRecords] = await getPageData()
      setTests(testRecords)
      setConsultations(clinicalRecords.filter((item) => item.status === 'in_progress'))
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load laboratory records.'))
    }
  }, [getPageData])

  useEffect(() => {
    let active = true
    getPageData()
      .then(([testRecords, clinicalRecords]) => {
        if (!active) return
        setTests(testRecords)
        setConsultations(clinicalRecords.filter((item) => item.status === 'in_progress'))
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load laboratory records.'))
      })
    return () => { active = false }
  }, [getPageData])

  async function createTest(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await requestLabTest({ consultation: Number(consultation), name, clinical_question: clinicalQuestion })
      setName('')
      setClinicalQuestion('')
      setConsultation('')
      setMessage('Laboratory test requested.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not request the laboratory test.'))
    } finally {
      setSaving(false)
    }
  }

  async function submitResult(event, test) {
    event.preventDefault()
    const result = results[test.id] || {}
    setSaving(true)
    setError('')
    setMessage('')
    try {
      let documentId = result.document || ''
      if (result.file) {
        const document = await uploadDocument(result.file, {
          title: `${test.name} result`,
          category: 'lab_result',
          appointment: test.appointment_id,
          ...(user.role === 'admin' ? { patient: test.patient_id } : {}),
        })
        documentId = document.id
      }
      await recordLabReport(test.id, { result_text: result.result_text || '', ...(documentId ? { document: Number(documentId) } : {}) })
      setResults({ ...results, [test.id]: { result_text: '', document: '', file: null } })
      setMessage('Laboratory result recorded and shared with the patient.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not record the laboratory result.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">DIAGNOSTICS</p><h1>Laboratory</h1></div><span className="count-pill">{tests.length} tests</span></div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}
      {user.role === 'doctor' && consultations.length > 0 && (
        <section className="panel workspace-panel"><div className="section-heading"><div><p className="eyebrow">ACTIVE CONSULTATION</p><h2>Request a test</h2></div></div>
          <form onSubmit={createTest}><div className="form-grid">
            <label>Consultation<select required value={consultation} onChange={(event) => setConsultation(event.target.value)}><option value="">Choose consultation</option>{consultations.map((item) => <option value={item.id} key={item.id}>{item.patient_name}</option>)}</select></label>
            <label>Test name<input required maxLength="180" value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label className="span-all">Clinical question<input maxLength="500" value={clinicalQuestion} onChange={(event) => setClinicalQuestion(event.target.value)} /></label>
          </div><button className="primary-button form-submit" disabled={saving}>Request test</button></form>
        </section>
      )}
      {tests.length === 0 ? <section className="panel workspace-panel"><p className="empty-state">No laboratory tests are available.</p></section> : tests.map((test) => {
        return <article className="panel workspace-panel" key={test.id}>
          <div className="section-heading"><div><p className="eyebrow">{test.status.replaceAll('_', ' ')}</p><h2>{test.name}</h2><p className="record-copy">{test.patient_name} · Requested {new Date(test.requested_at).toLocaleDateString()}</p></div></div>
          {test.clinical_question && <p><strong>Clinical question:</strong> {test.clinical_question}</p>}
          {test.reports.map((report) => <div className="report-card" key={report.id}><strong>Result</strong><p>{report.result_text || 'Result document uploaded.'}</p>{report.document && <DocumentDownload document={report.document} />}</div>)}
          {test.reports.map((report) => (
            <div className="report-review" key={`review-${report.id}`}>
              {report.reviewed_at
                ? <span className="muted-copy">Reviewed {new Date(report.reviewed_at).toLocaleString()}</span>
                : (user.role === 'doctor' || user.role === 'admin') && <button className="text-button" disabled={saving} onClick={async () => {
                  setSaving(true)
                  setError('')
                  try {
                    await reviewLabReport(test.id, report.id)
                    setMessage('Laboratory result marked as reviewed.')
                    await load()
                  } catch (requestError) {
                    setError(getApiError(requestError, 'Could not mark this result as reviewed.'))
                  } finally {
                    setSaving(false)
                  }
                }}>Mark result reviewed</button>}
            </div>
          ))}
          {(user.role === 'doctor' || user.role === 'admin') && test.status !== 'cancelled' && test.reports.length === 0 && (
            <form className="result-form" onSubmit={(event) => submitResult(event, test)}>
              <label className="wide-label">Result<textarea rows="3" value={results[test.id]?.result_text || ''} onChange={(event) => setResults({ ...results, [test.id]: { ...results[test.id], result_text: event.target.value } })} /></label>
              <label className="wide-label">Optional result file (PDF, JPG, PNG)<input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setResults({ ...results, [test.id]: { ...results[test.id], file: event.target.files?.[0] || null } })} /></label>
              <button className="primary-button form-submit" disabled={saving}>{saving ? 'Saving…' : 'Record result'}</button>
            </form>
          )}
        </article>
      })}
    </section>
  )
}

function DocumentDownload({ document }) {
  return <a className="download-link" href="#" onClick={async (event) => {
    event.preventDefault()
    try {
      await downloadDocument(document.id, document.file_name)
    } catch {
      window.alert('The document could not be downloaded.')
    }
  }}>Download {document.title}</a>
}

export default LaboratoryPage
