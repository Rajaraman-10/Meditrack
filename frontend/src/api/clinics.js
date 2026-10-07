import apiClient from './client'

export async function fetchDoctors() {
  const response = await apiClient.get('/doctors/')
  return response.data
}

export async function createDoctor(details) {
  const response = await apiClient.post('/doctors/', details)
  return response.data
}

export async function updateDoctor(id, details) {
  const response = await apiClient.patch(`/doctors/${id}/`, details)
  return response.data
}

export async function fetchDepartments() {
  const response = await apiClient.get('/departments/')
  return response.data
}

export async function createDepartment(details) {
  const response = await apiClient.post('/departments/', details)
  return response.data
}

export async function updateDepartment(id, details) {
  const response = await apiClient.patch(`/departments/${id}/`, details)
  return response.data
}

export async function createReceptionist(details) {
  const response = await apiClient.post('/auth/users/', { ...details, role: 'receptionist' })
  return response.data
}

export async function fetchAvailability(doctorId) {
  const response = await apiClient.get('/availabilities/', { params: { doctor: doctorId } })
  return response.data
}

export async function createAvailability(details) {
  const response = await apiClient.post('/availabilities/', details)
  return response.data
}

export async function updateAvailability(id, details) {
  const response = await apiClient.patch(`/availabilities/${id}/`, details)
  return response.data
}

export async function deleteAvailability(id) {
  await apiClient.delete(`/availabilities/${id}/`)
}

export async function fetchScheduleExceptions(doctorId) {
  const response = await apiClient.get('/schedule-exceptions/', { params: { doctor: doctorId } })
  return response.data
}

export async function createScheduleException(details) {
  const response = await apiClient.post('/schedule-exceptions/', details)
  return response.data
}

export async function updateScheduleException(id, details) {
  const response = await apiClient.patch(`/schedule-exceptions/${id}/`, details)
  return response.data
}

export async function deleteScheduleException(id) {
  await apiClient.delete(`/schedule-exceptions/${id}/`)
}

export async function fetchDoctorSlots(doctorId, date) {
  const response = await apiClient.get(`/doctors/${doctorId}/slots/`, { params: { date } })
  return response.data
}
