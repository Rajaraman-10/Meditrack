import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

const roleLandingPaths = {
  admin: '/admin/dashboard',
  doctor: '/doctor/dashboard',
  receptionist: '/receptionist/dashboard',
  billing: '/billing/dashboard',
  patient: '/patient/dashboard',
}

function getRoleLandingPath(role) {
  return roleLandingPaths[role] || '/account'
}

function getErrorMessage(error) {
  const details = error.response?.data
  if (details?.detail) return details.detail
  if (details?.non_field_errors?.[0]) return details.non_field_errors[0]
  return 'Sign-in failed. Check your details and try again.'
}

function LoginPage() {
  const { user, login } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [credentials, setCredentials] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={getRoleLandingPath(user.role)} replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const authenticatedUser = await login(credentials)
      navigate(getRoleLandingPath(authenticatedUser.role), { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="panel auth-panel auth-layout">
      <aside className="auth-aside">
        <div className="auth-brand"><span className="brand-mark" aria-hidden="true">M</span> MediTrack</div>
        <p className="auth-aside-label">CARE, COORDINATED</p>
        <h2>Everything your clinic needs, in one clear place.</h2>
        <p className="auth-aside-copy">Bring appointments, care teams, and patient records together in a workspace designed for better everyday care.</p>
        <ul className="auth-highlights">
          <li>Simple appointment workflows</li>
          <li>One connected care journey</li>
        </ul>
        <p className="auth-aside-foot">A calmer way to manage clinic care.</p>
      </aside>
      <div className="auth-content">
        <p className="eyebrow">WELCOME BACK</p>
        <h1>Sign in to MediTrack</h1>
        <p className="auth-intro">Use your email address and password to continue.</p>
        {location.state?.message && (
          <p className="success-notice" role="status">
            {location.state.message}
            {location.state.patientNumber && (
              <> Your Patient Number is <strong>{location.state.patientNumber}</strong>. Keep it for your clinic visits.</>
            )}
          </p>
        )}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email address
            <input
              autoComplete="email"
              type="email"
              required
              value={credentials.email}
              onChange={(event) => setCredentials({ ...credentials, email: event.target.value })}
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              type="password"
              required
              value={credentials.password}
              onChange={(event) => setCredentials({ ...credentials, password: event.target.value })}
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="auth-switch">New to MediTrack? <Link to="/register">Create a patient account</Link></p>
      </div>
    </section>
  )
}

export default LoginPage
