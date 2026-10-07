import apiClient from './client'

export async function fetchHealth() {
  const response = await apiClient.get('/health/')
  return response.data
}
