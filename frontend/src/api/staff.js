import apiClient from './client'

export async function fetchStaffUsers() {
  const response = await apiClient.get('/auth/users/')
  return response.data
}

export async function createStaffUser(details) {
  const response = await apiClient.post('/auth/users/', details)
  return response.data
}

export async function updateStaffUser(id, details) {
  const response = await apiClient.patch(`/auth/users/${id}/`, details)
  return response.data
}

export async function resetStaffPassword(id, password) {
  const response = await apiClient.post(`/auth/users/${id}/reset-password/`, { password })
  return response.data
}
