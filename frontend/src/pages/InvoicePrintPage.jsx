import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchInvoices } from '../api/clinical'
import { getApiError } from '../utils/apiError'

function formatDate(value) {
  if (!value) return 'Not recorded'
  return new Date(value).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function formatAmount(currency, value) {
  const amount = Number(value || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return currency === 'INR' ? `₹${amount}` : `${currency} ${amount}`
}

function InvoicePrintPage() {
  const { invoiceId } = useParams()
  const [invoice, setInvoice] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchInvoices()
      .then((records) => {
        const record = records.find((item) => String(item.id) === invoiceId)
        if (!record) {
          if (active) setError('This invoice is not available to your account.')
          return
        }
        if (active) setInvoice(record)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load this invoice.'))
      })
    return () => { active = false }
  }, [invoiceId])

  if (error) {
    return (
      <section className="workspace-page">
        <p className="form-error notice" role="alert">{error}</p>
        <Link className="text-button" to="/billing">Back to billing</Link>
      </section>
    )
  }
  if (!invoice) return <p className="route-message" role="status">Loading invoice…</p>

  const paid = invoice.status === 'paid'
  const voided = invoice.status === 'void'
  const total = Number(invoice.total)
  const amountPaid = paid ? total : 0
  const balance = paid || voided ? 0 : total

  return (
    <section className="workspace-page invoice-print-page">
      <div className="invoice-print-actions">
        <Link className="text-button" to="/billing">← Back to billing</Link>
        <button className="primary-button" type="button" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>
      <article className="panel invoice-paper">
        <header className="invoice-paper-header">
          <p className="eyebrow">MEDiTRACK</p>
          <p className="invoice-clinic-contact">Clinic contact details are not configured.</p>
          <h1>INVOICE</h1>
          <dl className="invoice-top-details">
            <div><dt>Invoice No.</dt><dd>{invoice.invoice_number}</dd></div>
            <div><dt>Invoice Date</dt><dd>{formatDate(invoice.created_at)}</dd></div>
            <div><dt>Payment Status</dt><dd className={`invoice-status invoice-status-${invoice.status}`}>{invoice.status.toUpperCase()}</dd></div>
          </dl>
        </header>

        <section className="invoice-paper-section">
          <h2>Patient details</h2>
          <dl className="invoice-details-grid">
            <div><dt>Patient ID</dt><dd>{invoice.patient_number}</dd></div>
            <div><dt>Patient Name</dt><dd>{invoice.patient_name}</dd></div>
            <div><dt>Age / Gender</dt><dd>{invoice.patient_age ?? 'Not recorded'} / {invoice.patient_gender || 'Not recorded'}</dd></div>
            <div><dt>Doctor</dt><dd>Dr. {invoice.doctor_name}</dd></div>
            <div><dt>Department</dt><dd>{invoice.department_name || 'Not recorded'}</dd></div>
            <div><dt>Consultation Date</dt><dd>{formatDate(invoice.consultation_date)}</dd></div>
          </dl>
        </section>

        <section className="invoice-paper-section">
          <h2>Services &amp; charges</h2>
          <div className="table-wrap">
            <table className="invoice-paper-table">
              <thead><tr><th>#</th><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr></thead>
              <tbody>
                {invoice.items.map((item, index) => (
                  <tr key={item.id}>
                    <td>{index + 1}</td>
                    <td>{item.description}</td>
                    <td>{item.quantity}</td>
                    <td>{formatAmount(invoice.currency, item.unit_price)}</td>
                    <td>{formatAmount(invoice.currency, Number(item.quantity) * Number(item.unit_price))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <dl className="invoice-totals">
            <div><dt>Subtotal</dt><dd>{formatAmount(invoice.currency, invoice.subtotal)}</dd></div>
            <div><dt>Discount</dt><dd>− {formatAmount(invoice.currency, invoice.discount_amount)}</dd></div>
            <div className="invoice-grand-total"><dt>TOTAL</dt><dd>{formatAmount(invoice.currency, invoice.total)}</dd></div>
          </dl>
        </section>

        <section className="invoice-paper-section">
          <h2>Payment information</h2>
          <dl className="invoice-details-grid">
            <div><dt>Payment Method</dt><dd>{invoice.payment_method ? invoice.payment_method.replaceAll('_', ' ').toUpperCase() : '—'}</dd></div>
            <div><dt>Payment Status</dt><dd>{invoice.status.toUpperCase()}</dd></div>
            <div><dt>Amount Paid</dt><dd>{formatAmount(invoice.currency, amountPaid)}</dd></div>
            <div><dt>Balance Due</dt><dd>{formatAmount(invoice.currency, balance)}</dd></div>
            <div className="invoice-reference"><dt>Transaction / Reference No.</dt><dd>{invoice.transaction_reference || '—'}</dd></div>
          </dl>
        </section>

        <section className="invoice-paper-section invoice-notes">
          <h2>Notes</h2>
          <p>Thank you for choosing MediTrack.</p>
          <p>Please retain this invoice for your records.</p>
        </section>

        <footer className="invoice-paper-footer">
          <div className="invoice-signature"><span>Authorized By</span><strong>{invoice.created_by_name}</strong><small>Doctor / Receptionist</small></div>
          <p>MediTrack · Secure Digital Healthcare Management</p>
        </footer>
      </article>
    </section>
  )
}

export default InvoicePrintPage
