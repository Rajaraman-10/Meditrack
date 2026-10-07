import apiClient from './client'

export async function registerUser(details) {
  const response = await apiClient.post('/auth/register/', details)
  return response.data
}

export async function loginUser(credentials) {
  const response = await apiClient.post('/auth/login/', credentials)
  return response.data
}

export async function fetchCurrentUser() {
  const response = await apiClient.get('/auth/me/')
  return response.data
}

export async function revokeRefreshToken(refreshToken) {
  await apiClient.post('/auth/logout/', { refresh: refreshToken })
}
