import { useEffect, useState } from 'react'
import { fetchHealth } from '../api/health'

function HomePage() {
  const [health, setHealth] = useState({ state: 'loading', message: '' })
  const [checkNumber, setCheckNumber] = useState(0)

  useEffect(() => {
    let isCurrent = true

    fetchHealth()
      .then((data) => {
        if (isCurrent) {
          setHealth({ state: 'connected', message: data.service })
        }
      })
      .catch((error) => {
        if (isCurrent) {
          setHealth({ state: 'error', message: error.message })
        }
      })

    return () => {
      isCurrent = false
    }
  }, [checkNumber])

  return (
    <>
      <section className="hero">
        <p className="eyebrow">CLINIC MANAGEMENT SYSTEM</p>
        <h1>A thoughtful foundation for better clinic care.</h1>
        <p className="hero-copy">
          Secure patient sign-in is now connected to the backend. MediTrack
          continues to grow one understandable, testable feature at a time.
        </p>
      </section>

      <section className="panel connection-panel" aria-live="polite">
        <div>
          <p className="eyebrow">BACKEND CONNECTION</p>
          <h2>
            {health.state === 'loading' && 'Checking the API…'}
            {health.state === 'connected' && 'API is reachable'}
            {health.state === 'error' && 'Could not reach the API'}
          </h2>
          <p className="connection-message">
            {health.state === 'loading' && 'Waiting for the health check response.'}
            {health.state === 'connected' && `${health.message} responded successfully.`}
            {health.state === 'error' && `${health.message}. Start Django and try again.`}
          </p>
        </div>
        <span className={`status-badge status-${health.state}`}>
          <span className="status-dot" />
          {health.state === 'loading' ? 'Checking' : health.state === 'connected' ? 'Connected' : 'Offline'}
        </span>
        {health.state === 'error' && (
          <button className="secondary-button" onClick={() => setCheckNumber((n) => n + 1)}>
            Try again
          </button>
        )}
      </section>

      <section className="next-step">
        <div>
          <p className="eyebrow">CURRENT PHASE</p>
          <h2>Clinic operations foundation</h2>
          <p>Role-scoped patient records, doctor schedules, appointment booking, check-in, and the waiting queue are ready.</p>
        </div>
        <span className="phase-number">10</span>
      </section>
    </>
  )
}

export default HomePage
