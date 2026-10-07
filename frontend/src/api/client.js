import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const apiClient = axios.create({
  baseURL,
  headers: {
    Accept: 'application/json',
  },
  timeout: 5000,
})

let refreshRequest

function clearTokens() {
  sessionStorage.removeItem('accessToken')
  sessionStorage.removeItem('refreshToken')
  window.dispatchEvent(new Event('mediatrack:session-expired'))
}

apiClient.interceptors.request.use((config) => {
  const accessToken = sessionStorage.getItem('accessToken')
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthEndpoint = /\/auth\/(login|register|refresh|logout)\/?$/.test(
      originalRequest?.url || '',
    )

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      isAuthEndpoint
    ) {
      return Promise.reject(error)
    }

    const refreshToken = sessionStorage.getItem('refreshToken')
    if (!refreshToken) {
      clearTokens()
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      if (!refreshRequest) {
        refreshRequest = axios
          .post(`${baseURL}/auth/refresh/`, { refresh: refreshToken }, { timeout: 5000 })
          .then(({ data }) => {
            sessionStorage.setItem('accessToken', data.access)
            if (data.refresh) {
              sessionStorage.setItem('refreshToken', data.refresh)
            }
            return data.access
          })
          .finally(() => {
            refreshRequest = null
          })
      }

      const accessToken = await refreshRequest
      originalRequest.headers.Authorization = `Bearer ${accessToken}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      clearTokens()
      return Promise.reject(refreshError)
    }
  },
)

export default apiClient
