import apiClient from './client'

export async function fetchDashboard() {
  const response = await apiClient.get('/dashboard/')
  return response.data
}

export async function fetchConsultations() {
  const response = await apiClient.get('/consultations/')
  return response.data
}

export async function startConsultation(appointment) {
  const response = await apiClient.post('/consultations/', { appointment })
  return response.data
}

export async function updateConsultation(id, details) {
  const response = await apiClient.patch(`/consultations/${id}/`, details)
  return response.data
}

export async function completeConsultation(id) {
  const response = await apiClient.post(`/consultations/${id}/complete/`)
  return response.data
}

export async function addConsultationNote(id, body) {
  const response = await apiClient.post(`/consultations/${id}/notes/`, { body })
  return response.data
}

export async function fetchPrescriptions() {
  const response = await apiClient.get('/prescriptions/')
  return response.data
}

export async function createPrescription(details) {
  const response = await apiClient.post('/prescriptions/', details)
  return response.data
}

export async function fetchPrescription(id) {
  const response = await apiClient.get(`/prescriptions/${id}/`)
  return response.data
}

export async function fetchPrescriptionReleaseQueue() {
  const response = await apiClient.get('/prescriptions/release-queue/')
  return response.data
}

export async function releasePrescription(id) {
  const response = await apiClient.post(`/prescriptions/${id}/release/`)
  return response.data
}

export async function searchMedicines(search) {
  const response = await apiClient.get('/medicines/', { params: { search } })
  return response.data
}

export async function fetchLabTests() {
  const response = await apiClient.get('/lab-tests/')
  return response.data
}

export async function requestLabTest(details) {
  const response = await apiClient.post('/lab-tests/', details)
  return response.data
}

export async function recordLabReport(testId, details) {
  const response = await apiClient.post(`/lab-tests/${testId}/reports/`, details)
  return response.data
}

export async function reviewLabReport(testId, reportId) {
  const response = await apiClient.post(`/lab-tests/${testId}/review-report/`, { report: reportId })
  return response.data
}

export async function fetchDocuments() {
  const response = await apiClient.get('/documents/')
  return response.data
}

export async function downloadDocument(id, fileName) {
  const response = await apiClient.get(`/documents/${id}/download/`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName || 'medical-document'
  link.click()
  URL.revokeObjectURL(url)
}

export async function uploadDocument(file, details) {
  const formData = new FormData()
  Object.entries(details).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) formData.append(key, value)
  })
  formData.append('file', file)
  const response = await apiClient.post('/documents/', formData)
  return response.data
}

export async function fetchInvoices() {
  const response = await apiClient.get('/invoices/')
  return response.data
}

export async function fetchUnbilledAppointments() {
  const response = await apiClient.get('/invoices/unbilled-appointments/')
  return response.data
}

export async function createInvoice(details) {
  const response = await apiClient.post('/invoices/', details)
  return response.data
}

export async function updateInvoiceStatus(id, value, details = {}) {
  const response = await apiClient.post(`/invoices/${id}/status/`, { status: value, ...details })
  return response.data
}

export async function fetchNotifications() {
  const response = await apiClient.get('/notifications/')
  return response.data
}

export async function markNotificationRead(id) {
  const response = await apiClient.post(`/notifications/${id}/read/`)
  return response.data
}

export async function markAllNotificationsRead() {
  const response = await apiClient.post('/notifications/read-all/')
  return response.data
}

export async function fetchAuditLogs() {
  const response = await apiClient.get('/audit-logs/')
  return response.data
}
