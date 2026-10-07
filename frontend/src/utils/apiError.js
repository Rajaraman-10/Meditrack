export function getApiError(error, fallback = 'The request could not be completed.') {
  const data = error.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (typeof data === 'string') return data

  if (data && typeof data === 'object') {
    const firstError = Object.values(data).flat().find((value) => typeof value === 'string')
    if (firstError) return firstError
  }

  return error.message || fallback
}
