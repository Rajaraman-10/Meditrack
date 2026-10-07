import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createStaffUser,
  fetchStaffUsers,
  resetStaffPassword,
  updateStaffUser,
} from '../api/staff'
import { getApiError } from '../utils/apiError'

const emptyStaffForm = () => ({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  role: 'receptionist',
})

function StaffManagementPage() {
  const [staff, setStaff] = useState([])
  const [form, setForm] = useState(emptyStaffForm)
  const [editId, setEditId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [resetId, setResetId] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [query, setQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    try {
      setStaff(await fetchStaffUsers())
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load staff accounts.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    fetchStaffUsers()
      .then((records) => {
        if (active) setStaff(records)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load staff accounts.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  const filteredStaff = useMemo(() => staff.filter((person) => {
    const text = `${person.first_name} ${person.last_name} ${person.email}`.toLowerCase()
    return text.includes(query.toLowerCase())
      && (roleFilter === 'all' || person.role === roleFilter)
  }), [query, roleFilter, staff])

  async function createStaff(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await createStaffUser(form)
      setForm(emptyStaffForm())
      setMessage('Staff account created.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not create this staff account.'))
    } finally {
      setSaving(false)
    }
  }

  function startEdit(person) {
    setEditId(person.id)
    setEditForm({
      email: person.email,
      first_name: person.first_name,
      last_name: person.last_name,
      role: person.role,
    })
    setResetId(null)
    setError('')
  }

  async function saveEdit(event, person) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    const details = {
      email: editForm.email,
      first_name: editForm.first_name,
      last_name: editForm.last_name,
    }
    if (person.role !== 'doctor') details.role = editForm.role
    try {
      await updateStaffUser(person.id, details)
      setEditId(null)
      setMessage('Staff details updated.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not update this staff account.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(person) {
    const action = person.is_active ? 'deactivate' : 'activate'
    if (!window.confirm(`${action[0].toUpperCase()}${action.slice(1)} ${person.first_name} ${person.last_name || person.email}?`)) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await updateStaffUser(person.id, { is_active: !person.is_active })
      setMessage(`Staff account ${action}d.`)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not change this staff account status.'))
    } finally {
      setSaving(false)
    }
  }

  async function submitPasswordReset(event, person) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await resetStaffPassword(person.id, newPassword)
      setNewPassword('')
      setResetId(null)
      setMessage(`Password reset for ${person.email}. Share the new password securely.`)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not reset this staff password.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">ADMINISTRATION</p><h1>Staff management</h1></div>
        <span className="count-pill">{staff.length} staff</span>
      </div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">NEW STAFF ACCOUNT</p><h2>Add receptionist or billing staff</h2></div></div>
        <p className="muted-copy">Doctor accounts are created and assigned to a department from Clinic management. Admin accounts cannot be created here.</p>
        <form onSubmit={createStaff}>
          <div className="form-grid">
            <label>First name<input required maxLength="150" value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></label>
            <label>Last name<input maxLength="150" value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></label>
            <label>Email<input required type="email" autoComplete="off" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
            <label>Temporary password<input required type="password" autoComplete="new-password" minLength="12" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
            <label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}><option value="receptionist">Receptionist</option><option value="billing">Billing</option></select></label>
          </div>
          <button className="primary-button form-submit" disabled={saving}>{saving ? 'Creating…' : 'Create staff account'}</button>
        </form>
      </section>

      <section className="panel workspace-panel">
        <div className="section-heading"><div><p className="eyebrow">STAFF DIRECTORY</p><h2>Clinic staff</h2></div></div>
        <div className="staff-table-filters">
          <label>Search staff<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or email" /></label>
          <label>Filter role<select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}><option value="all">All roles</option><option value="doctor">Doctor</option><option value="receptionist">Receptionist</option><option value="billing">Billing</option></select></label>
        </div>
        {loading
          ? <p className="empty-state">Loading staff accounts…</p>
          : filteredStaff.length === 0
            ? <p className="empty-state">No staff accounts match this search.</p>
            : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
                  <tbody>
                    {filteredStaff.map((person) => (
                      <tr key={person.id}>
                        <td>{person.first_name} {person.last_name}</td>
                        <td>{person.email}</td>
                        <td>{person.role}</td>
                        <td>{person.department_name || '—'}</td>
                        <td><span className={`staff-status ${person.is_active ? 'is-active' : 'is-inactive'}`}>{person.is_active ? 'Active' : 'Inactive'}</span></td>
                        <td>{new Date(person.date_joined).toLocaleDateString('en-IN')}</td>
                        <td>
                          <div className="inline-actions">
                            <button className="text-button" type="button" onClick={() => startEdit(person)}>Edit</button>
                            <button className="text-button" type="button" disabled={saving} onClick={() => toggleActive(person)}>{person.is_active ? 'Deactivate' : 'Activate'}</button>
                            <button className="text-button" type="button" onClick={() => { setResetId(resetId === person.id ? null : person.id); setNewPassword(''); setEditId(null) }}>Reset password</button>
                          </div>
                          {editId === person.id && (
                            <form className="staff-inline-form" onSubmit={(event) => saveEdit(event, person)}>
                              <label>Email<input required type="email" value={editForm.email} onChange={(event) => setEditForm({ ...editForm, email: event.target.value })} /></label>
                              <label>First name<input required value={editForm.first_name} onChange={(event) => setEditForm({ ...editForm, first_name: event.target.value })} /></label>
                              <label>Last name<input value={editForm.last_name} onChange={(event) => setEditForm({ ...editForm, last_name: event.target.value })} /></label>
                              {person.role !== 'doctor' && <label>Role<select value={editForm.role} onChange={(event) => setEditForm({ ...editForm, role: event.target.value })}><option value="receptionist">Receptionist</option><option value="billing">Billing</option></select></label>}
                              <button className="primary-button" disabled={saving}>Save</button>
                            </form>
                          )}
                          {resetId === person.id && (
                            <form className="staff-inline-form" onSubmit={(event) => submitPasswordReset(event, person)}>
                              <label>New temporary password<input required type="password" minLength="12" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
                              <button className="primary-button" disabled={saving}>Set password</button>
                            </form>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
      </section>
    </section>
  )
}

export default StaffManagementPage
