import { useCallback, useEffect, useState } from 'react'
import { createDepartment, fetchDepartments, fetchDoctors, updateDepartment } from '../api/clinics'
import { getApiError } from '../utils/apiError'

const emptyForm = () => ({ name: '', code: '', description: '' })

function DepartmentManagementPage() {
  const [departments, setDepartments] = useState([])
  const [doctors, setDoctors] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    try {
      const [departmentData, doctorData] = await Promise.all([fetchDepartments(), fetchDoctors()])
      setDepartments(departmentData)
      setDoctors(doctorData)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load departments.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    Promise.all([fetchDepartments(), fetchDoctors()])
      .then(([departmentData, doctorData]) => {
        if (!active) return
        setDepartments(departmentData)
        setDoctors(doctorData)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load departments.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  function startEdit(department) {
    setEditing(department.id)
    setForm({
      name: department.name,
      code: department.code,
      description: department.description,
    })
    setError('')
    setMessage('')
  }

  function cancelEdit() {
    setEditing(null)
    setForm(emptyForm())
  }

  async function saveDepartment(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      if (editing) {
        await updateDepartment(editing, form)
        setMessage('Department updated.')
      } else {
        await createDepartment(form)
        setMessage('Department created.')
      }
      cancelEdit()
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Department could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleStatus(department) {
    const nextActive = !department.is_active
    if (!window.confirm(`${nextActive ? 'Activate' : 'Deactivate'} ${department.name}?`)) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await updateDepartment(department.id, { is_active: nextActive })
      setMessage(`Department ${nextActive ? 'activated' : 'deactivated'}.`)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Department status could not be updated.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">ADMINISTRATION</p><h1>Departments</h1></div>
        <span className="count-pill">{departments.length} departments</span>
      </div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}
      <section className="panel workspace-panel">
        <div className="section-heading">
          <div><p className="eyebrow">{editing ? 'EDIT DEPARTMENT' : 'DEPARTMENT DIRECTORY'}</p><h2>{editing ? 'Update department' : 'Create department'}</h2></div>
        </div>
        <form onSubmit={saveDepartment}>
          <div className="form-grid">
            <label>Department name<input required maxLength="120" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
            <label>Department code<input required maxLength="24" pattern="[A-Za-z0-9][A-Za-z0-9_-]{1,23}" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} placeholder="e.g. CARDIO" /></label>
            <label className="span-all">Description<input maxLength="500" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          </div>
          <div className="inline-actions form-submit">
            <button className="primary-button" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save department' : 'Create department'}</button>
            {editing && <button className="text-button" type="button" onClick={cancelEdit}>Cancel edit</button>}
          </div>
        </form>
      </section>

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">DATABASE DIRECTORY</p><h2>Departments and assigned doctors</h2></div></div>
        {loading
          ? <p className="empty-state">Loading departments…</p>
          : departments.length === 0
            ? <p className="empty-state">No departments have been created.</p>
            : (
              <div className="department-management-list">
                {departments.map((department) => {
                  const assignedDoctors = doctors.filter((doctor) => doctor.department === department.id)
                  return (
                    <article className="department-management-card" key={department.id}>
                      <div className="section-heading">
                        <div>
                          <p className="eyebrow">{department.code} · {department.is_active ? 'Active' : 'Inactive'}</p>
                          <h3>{department.name}</h3>
                          <p>{department.description || 'No description provided.'}</p>
                        </div>
                        <span className="count-pill">{assignedDoctors.length} doctors</span>
                      </div>
                      <p className="muted-copy">{assignedDoctors.length ? assignedDoctors.map((doctor) => `Dr. ${doctor.first_name} ${doctor.last_name}`.trim()).join(', ') : 'No active doctors assigned.'}</p>
                      <div className="inline-actions">
                        <button className="text-button" type="button" onClick={() => startEdit(department)}>Edit</button>
                        <button className="text-button" type="button" disabled={saving} onClick={() => toggleStatus(department)}>{department.is_active ? 'Deactivate' : 'Activate'}</button>
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
      </section>
    </section>
  )
}

export default DepartmentManagementPage
