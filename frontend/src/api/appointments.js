import apiClient from './client'

export async function fetchAppointments(date) {
  const response = await apiClient.get('/appointments/', {
    params: date ? { date } : {},
  })
  return response.data
}

export async function createAppointment(details) {
  const response = await apiClient.post('/appointments/', details)
  return response.data
}

export async function updateAppointment(appointmentId, details) {
  const response = await apiClient.patch(`/appointments/${appointmentId}/`, details)
  return response.data
}

export async function checkInAppointment(appointmentId) {
  const response = await apiClient.post(`/appointments/${appointmentId}/check-in/`)
  return response.data
}

export async function fetchQueue(date) {
  const response = await apiClient.get('/queue/', { params: { date } })
  return response.data
}

export async function updateQueueEntry(entryId, details) {
  const response = await apiClient.patch(`/queue/${entryId}/`, details)
  return response.data
}
