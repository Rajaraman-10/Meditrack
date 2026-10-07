import { useAuth } from '../auth/useAuth'
import { useState } from 'react'

function AccountPage() {
  const { user, logout } = useAuth()
  const [logoutError, setLogoutError] = useState('')

  async function handleLogout() {
    try {
      await logout()
    } catch {
      setLogoutError('You are signed out on this device, but the server could not revoke the refresh token.')
    }
  }

  return (
    <section className="panel account-panel">
      <p className="eyebrow">AUTHENTICATED ACCOUNT</p>
      <h1>Hello{user.first_name ? `, ${user.first_name}` : ''}</h1>
      <p className="auth-intro">This profile was loaded from the protected Django API using your access token.</p>
      <dl className="profile-list">
        <div><dt>Email</dt><dd>{user.email}</dd></div>
        <div><dt>Role</dt><dd>{user.role}</dd></div>
      </dl>
      {logoutError && <p className="form-error" role="alert">{logoutError}</p>}
      <button className="secondary-button" onClick={handleLogout}>Sign out</button>
    </section>
  )
}

export default AccountPage
