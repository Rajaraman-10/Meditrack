import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAppointments } from '../api/appointments'
import {
  createInvoice,
  fetchInvoices,
  fetchPrescriptions,
  fetchPrescriptionReleaseQueue,
  fetchUnbilledAppointments,
  releasePrescription,
  updateInvoiceStatus,
} from '../api/clinical'
import { useAuth } from '../auth/useAuth'
import { getApiError } from '../utils/apiError'

const emptyItem = () => ({ description: '', quantity: '1', unit_price: '' })
const initialForm = () => ({
  appointment: '',
  currency: 'INR',
  discount_amount: '0.00',
  items: [emptyItem()],
})

function BillingPage() {
  const { user } = useAuth()
  const [invoices, setInvoices] = useState([])
  const [pendingPrescriptions, setPendingPrescriptions] = useState([])
  const [releasedPrescriptions, setReleasedPrescriptions] = useState([])
  const [appointments, setAppointments] = useState([])
  const [form, setForm] = useState(initialForm)
  const [paymentInvoiceId, setPaymentInvoiceId] = useState(null)
  const [payment, setPayment] = useState({ payment_method: 'upi', transaction_reference: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const canManage = ['admin', 'receptionist', 'billing'].includes(user.role)
  const canReleasePrescriptions = ['admin', 'billing'].includes(user.role)
  const getPageData = useCallback(() => Promise.all([
    fetchInvoices(),
    ['admin', 'receptionist'].includes(user.role)
      ? fetchAppointments()
      : user.role === 'billing' ? fetchUnbilledAppointments() : Promise.resolve([]),
    canReleasePrescriptions ? fetchPrescriptionReleaseQueue() : Promise.resolve([]),
    canReleasePrescriptions ? fetchPrescriptions() : Promise.resolve([]),
  ]), [canReleasePrescriptions, user.role])

  const setPageData = useCallback(([records, bookings, prescriptions, released]) => {
    setInvoices(records)
    setPendingPrescriptions(prescriptions)
    setReleasedPrescriptions(released.filter((prescription) => prescription.status === 'released'))
    setAppointments(bookings.filter((item) => (
      (!item.status || ['in_consultation', 'completed'].includes(item.status))
      && !records.some((invoice) => invoice.appointment_id === item.id)
    )))
  }, [])

  const load = useCallback(async () => {
    try {
      setPageData(await getPageData())
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load invoices.'))
    }
  }, [getPageData, setPageData])

  useEffect(() => {
    let active = true
    getPageData()
      .then((data) => {
        if (active) setPageData(data)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load invoices.'))
      })
    return () => { active = false }
  }, [getPageData, setPageData])

  function updateItem(index, field, value) {
    setForm((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [field]: value } : item
      )),
    }))
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await createInvoice({
        appointment: Number(form.appointment),
        currency: form.currency,
        discount_amount: form.discount_amount,
        items: form.items.map((item) => ({
          ...item,
          quantity: Number(item.quantity),
        })),
      })
      setForm(initialForm())
      setMessage('Draft invoice created.')
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not create the invoice.'))
    } finally {
      setSaving(false)
    }
  }

  async function transition(invoice, nextStatus) {
    setError('')
    setMessage('')
    try {
      await updateInvoiceStatus(invoice.id, nextStatus)
      setMessage(`Invoice ${invoice.invoice_number} marked ${nextStatus}.`)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Invoice status could not be updated.'))
    }
  }

  async function recordPayment(event, invoice) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await updateInvoiceStatus(invoice.id, 'paid', payment)
      setPaymentInvoiceId(null)
      setMessage(`${invoice.invoice_number} marked paid.`)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Payment could not be recorded.'))
    } finally {
      setSaving(false)
    }
  }

  async function unlockPrescription(prescription) {
    setError('')
    setMessage('')
    try {
      await releasePrescription(prescription.id)
      setMessage(`${prescription.prescription_number} released to the patient.`)
      await load()
    } catch (requestError) {
      setError(getApiError(requestError, 'Prescription could not be released.'))
    }
  }

  const isBillingUser = user.role === 'billing'
  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">{isBillingUser ? 'BILLING WORKSPACE' : 'CLINIC FINANCES'}</p><h1>{isBillingUser ? 'Billing dashboard' : 'Billing'}</h1></div>
        <span className="count-pill">{invoices.length} invoices</span>
      </div>
      {error && <p className="form-error notice" role="alert">{error}</p>}
      {message && <p className="success-notice" role="status">{message}</p>}
      {isBillingUser && (
        <p className="muted-copy">
          Counter payments can be recorded here. Online checkout is not connected yet; payment status must only be confirmed after the clinic receives or verifies payment.
        </p>
      )}
      {canReleasePrescriptions && (
        <section className="panel workspace-panel" id="pending-prescriptions">
          <div className="section-heading">
            <div><p className="eyebrow">PAYMENT RELEASE</p><h2>Pending prescriptions</h2></div>
            <span className="count-pill">{pendingPrescriptions.length} awaiting release</span>
          </div>
          {pendingPrescriptions.length === 0
            ? <p className="empty-state">No prescriptions are waiting for payment or release.</p>
            : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Patient</th><th>Patient ID</th><th>Prescription</th><th>Amount</th><th>Payment</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {pendingPrescriptions.map((prescription) => (
                      <tr key={prescription.id}>
                        <td>{prescription.patient_name}</td>
                        <td>{prescription.patient_number}</td>
                        <td>{prescription.prescription_number}</td>
                        <td>{prescription.invoice_total === null ? 'Invoice required' : `${prescription.currency} ${prescription.invoice_total}`}</td>
                        <td>{prescription.invoice_status.replaceAll('_', ' ')}</td>
                        <td>
                          <div className="inline-actions">
                            {prescription.invoice_id && <Link className="text-button" to={`/billing/${prescription.invoice_id}/print`}>View invoice</Link>}
                            {prescription.invoice_status === 'not_generated' && <Link className="text-button" to="/billing#invoices">Generate invoice</Link>}
                            {prescription.can_release
                              ? <button className="text-button" onClick={() => unlockPrescription(prescription)}>Unlock prescription</button>
                              : prescription.invoice_status !== 'not_generated' && <span className="muted-copy">Release after payment</span>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </section>
      )}
      {canReleasePrescriptions && (
        <section className="panel workspace-panel">
          <div className="section-heading">
            <div><p className="eyebrow">AVAILABLE AFTER PAYMENT</p><h2>Released prescriptions</h2></div>
            <span className="count-pill">{releasedPrescriptions.length} released</span>
          </div>
          {releasedPrescriptions.length === 0
            ? <p className="empty-state">Released prescriptions will appear here after payment confirmation.</p>
            : releasedPrescriptions.map((prescription) => (
              <div className="compact-list" key={prescription.id}>
                <div>
                  <strong>{prescription.patient_name} · RX-{String(prescription.id).padStart(5, '0')}</strong>
                  <span>{prescription.patient_number} · Released {new Date(prescription.released_at).toLocaleDateString('en-IN')}</span>
                </div>
                <Link className="text-button" to={`/prescriptions/${prescription.id}/print`}>Print prescription</Link>
              </div>
            ))}
        </section>
      )}
      {canManage && (
        <section className="panel workspace-panel" id="invoices">
          <div className="section-heading">
            <div><p className="eyebrow">NEW CHARGE</p><h2>Create invoice</h2></div>
          </div>
          {appointments.length === 0
            ? <p className="empty-state">No unbilled appointments are ready. Appointments must be in consultation or completed.</p>
            : (
              <form onSubmit={submit}>
                <div className="form-grid">
                  <label>Appointment
                    <select required value={form.appointment} onChange={(event) => setForm({ ...form, appointment: event.target.value })}>
                      <option value="">Choose appointment</option>
                      {appointments.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.patient_name} · {item.patient_number} · {new Date(item.starts_at).toLocaleDateString('en-IN')}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>Currency
                    <input required maxLength="3" pattern="[A-Za-z]{3}" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} />
                  </label>
                  <label>Discount
                    <input required type="number" min="0" step="0.01" value={form.discount_amount} onChange={(event) => setForm({ ...form, discount_amount: event.target.value })} />
                  </label>
                </div>
                <h3 className="invoice-items-heading">Services & charges</h3>
                <div className="invoice-entry-items">
                  {form.items.map((item, index) => (
                    <div className="invoice-entry-row" key={index}>
                      <label>Description
                        <input required maxLength="240" value={item.description} onChange={(event) => updateItem(index, 'description', event.target.value)} placeholder="Doctor consultation, laboratory test, medicines…" />
                      </label>
                      <label>Qty
                        <input required type="number" min="1" max="32767" step="1" value={item.quantity} onChange={(event) => updateItem(index, 'quantity', event.target.value)} />
                      </label>
                      <label>Unit price
                        <input required type="number" min="0" step="0.01" value={item.unit_price} onChange={(event) => updateItem(index, 'unit_price', event.target.value)} />
                      </label>
                      {form.items.length > 1 && <button className="text-button danger-text" type="button" onClick={() => setForm({ ...form, items: form.items.filter((_, itemIndex) => itemIndex !== index) })}>Remove</button>}
                    </div>
                  ))}
                </div>
                <div className="inline-actions">
                  <button className="text-button" type="button" onClick={() => setForm({ ...form, items: [...form.items, emptyItem()] })}>Add charge</button>
                  <button className="primary-button" disabled={saving}>Create draft invoice</button>
                </div>
              </form>
            )}
        </section>
      )}
      {invoices.length === 0
        ? <section className="panel workspace-panel" id="payment-history"><p className="empty-state">No invoices are available.</p></section>
        : invoices.map((invoice, index) => (
          <article
            className="panel workspace-panel"
            id={
              invoice.status === 'paid' && invoices.findIndex((item) => item.status === 'paid') === index
                ? 'payment-history'
                : invoice.status === 'issued' && invoices.findIndex((item) => item.status === 'issued') === index
                  ? 'pending-payments'
                  : undefined
            }
            key={invoice.id}
          >
            <div className="section-heading">
              <div>
                <p className="eyebrow">{invoice.invoice_number} · {invoice.status}</p>
                <h2>{user.role === 'patient' ? `Dr. ${invoice.doctor_name}` : invoice.patient_name}</h2>
              </div>
              <strong className="invoice-total">{invoice.currency} {invoice.total}</strong>
            </div>
            {invoice.items.map((item) => (
              <div className="compact-list" key={item.id}>
                <div><strong>{item.description}</strong><span>{item.quantity} × {invoice.currency} {item.unit_price}</span></div>
              </div>
            ))}
            <div className="inline-actions">
              <Link className="text-button" to={`/billing/${invoice.id}/print`}>View / Print invoice</Link>
              {canManage && invoice.status === 'draft' && <button className="text-button" onClick={() => transition(invoice, 'issued')}>Issue invoice</button>}
              {canManage && invoice.status === 'issued' && (
                <button className="text-button" onClick={() => {
                  setPaymentInvoiceId(paymentInvoiceId === invoice.id ? null : invoice.id)
                  setPayment({ payment_method: 'upi', transaction_reference: '' })
                }}>Mark paid</button>
              )}
              {canManage && ['draft', 'issued'].includes(invoice.status) && <button className="text-button danger-text" onClick={() => transition(invoice, 'void')}>Void</button>}
            </div>
            {invoice.status === 'paid' && (
              <p className="muted-copy">Paid by {invoice.payment_method?.replaceAll('_', ' ') || 'unrecorded'}{invoice.transaction_reference ? ` · Ref ${invoice.transaction_reference}` : ''}</p>
            )}
            {canManage && paymentInvoiceId === invoice.id && (
              <form className="payment-entry-form" onSubmit={(event) => recordPayment(event, invoice)}>
                <label>Payment method
                  <select required value={payment.payment_method} onChange={(event) => setPayment({ ...payment, payment_method: event.target.value })}>
                    <option value="upi">UPI</option>
                    <option value="cash">Cash</option>
                    <option value="card">Card</option>
                    <option value="bank_transfer">Bank transfer</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label>Transaction / reference number
                  <input maxLength="120" value={payment.transaction_reference} onChange={(event) => setPayment({ ...payment, transaction_reference: event.target.value })} placeholder="Optional" />
                </label>
                <button className="primary-button" disabled={saving}>Confirm full payment</button>
              </form>
            )}
          </article>
        ))}
    </section>
  )
}

export default BillingPage
