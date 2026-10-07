function SetupPage() {
  return (
    <section className="panel setup-panel">
      <p className="eyebrow">PHASE 1 · ARCHITECTURE</p>
      <h1>How the pieces communicate</h1>
      <ol className="flow-list">
        <li><strong>React</strong><span>Shows the interface and sends requests through Axios.</span></li>
        <li><strong>Django REST Framework</strong><span>Validates requests, applies permissions, and returns JSON.</span></li>
        <li><strong>MySQL</strong><span>Will store clinic data; local setup uses SQLite until database configuration.</span></li>
      </ol>
      <p className="setup-note">
        The browser never connects directly to the database. The API is the
        controlled boundary between the user interface and stored data.
      </p>
    </section>
  )
}

export default SetupPage
