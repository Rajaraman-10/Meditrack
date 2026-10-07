import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchNotifications, markAllNotificationsRead, markNotificationRead } from '../api/clinical'
import { getApiError } from '../utils/apiError'

function NotificationsPage() {
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  async function load() {
    try {
      setNotifications(await fetchNotifications())
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load notifications.'))
    }
  }

  useEffect(() => {
    let active = true
    fetchNotifications()
      .then((records) => { if (active) setNotifications(records) })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load notifications.'))
      })
    return () => { active = false }
  }, [])

  async function markRead(id) {
    setSaving(true)
    setError('')
    try {
      await markNotificationRead(id)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not update this notification.'))
    } finally {
      setSaving(false)
    }
  }

  async function markAllRead() {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const result = await markAllNotificationsRead()
      setMessage(`${result.updated} notification${result.updated === 1 ? '' : 's'} marked as read.`)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not update notifications.'))
    } finally {
      setSaving(false)
    }
  }

  const unread = notifications.filter((notification) => !notification.read_at).length
  return (
    <section className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">YOUR UPDATES</p><h1>Notifications</h1></div><span className="count-pill">{unread} unread</span></div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}
      {unread > 0 && <button className="secondary-button mark-all-button" disabled={saving} onClick={markAllRead}>Mark all as read</button>}
      {notifications.length === 0 ? <section className="panel workspace-panel"><p className="empty-state">You are all caught up. New updates will appear here.</p></section> : notifications.map((item) => (
        <article className={`panel notification-card${item.read_at ? '' : ' notification-unread'}`} key={item.id}>
          <div className="notification-copy"><p className="eyebrow">{item.category} · {new Date(item.created_at).toLocaleString()}</p><h2>{item.title}</h2><p>{item.message}</p></div>
          <div className="inline-actions">
            {item.target_url && <Link className="text-button" to={item.target_url}>View</Link>}
            {!item.read_at && <button className="text-button" disabled={saving} onClick={() => markRead(item.id)}>Mark read</button>}
          </div>
        </article>
      ))}
    </section>
  )
}

export default NotificationsPage
