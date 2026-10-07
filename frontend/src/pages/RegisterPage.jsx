import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

function getErrorMessage(error) {
  const details = error.response?.data
  if (details?.email?.[0]) return details.email[0]
  if (details?.password?.[0]) return details.password[0]
  if (details?.detail) return details.detail
  return 'Registration failed. Check the information and try again.'
}

function RegisterPage() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [details, setDetails] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/account" replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const registration = await register(details)
      navigate('/login', {
        replace: true,
        state: {
          message: 'Your account is ready. Sign in to continue.',
          patientNumber: registration.patient_number,
        },
      })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  function updateField(event) {
    setDetails({ ...details, [event.target.name]: event.target.value })
  }

  return (
    <section className="panel auth-panel auth-layout">
      <aside className="auth-aside">
        <div className="auth-brand"><span className="brand-mark" aria-hidden="true">M</span> MediTrack</div>
        <p className="auth-aside-label">YOUR CARE, IN ONE PLACE</p>
        <h2>Stay connected to every step of your care.</h2>
        <p className="auth-aside-copy">Keep your appointments, prescriptions, and care updates together in one secure patient account.</p>
        <ul className="auth-highlights">
          <li>Manage upcoming appointments</li>
          <li>Keep your care history close</li>
        </ul>
        <p className="auth-aside-foot">Clinic staff accounts are created by an administrator.</p>
      </aside>
      <div className="auth-content">
        <p className="eyebrow">PATIENT ACCESS</p>
        <h1>Create your account</h1>
        <p className="auth-intro">A few details are all you need to get started.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-row">
          <label>
            First name
            <input autoComplete="given-name" name="first_name" value={details.first_name} onChange={updateField} />
          </label>
          <label>
            Last name
            <input autoComplete="family-name" name="last_name" value={details.last_name} onChange={updateField} />
          </label>
          </div>
          <label>
            Email address
            <input autoComplete="email" type="email" name="email" required value={details.email} onChange={updateField} />
          </label>
          <label>
            Password
            <input
              autoComplete="new-password"
              type="password"
              name="password"
              minLength={8}
              required
              value={details.password}
              onChange={updateField}
            />
            <span className="field-hint">Use a strong password; the server checks it against Django’s password rules.</span>
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create patient account'}
          </button>
        </form>
        <p className="auth-switch">Already registered? <Link to="/login">Sign in</Link></p>
      </div>
    </section>
  )
}

export default RegisterPage
