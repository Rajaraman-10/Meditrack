import apiClient from './client'

export async function fetchPatients() {
  const response = await apiClient.get('/patients/')
  return response.data
}

export async function createPatient(details) {
  const response = await apiClient.post('/patients/', details)
  return response.data
}

export async function updatePatient(patientId, details) {
  const response = await apiClient.patch(`/patients/${patientId}/`, details)
  return response.data
}

export async function searchDoctorPatient(patientNumber) {
  const response = await apiClient.get('/patients/doctor-search/', {
    params: { patient_number: patientNumber },
  })
  return response.data
}

export async function fetchDoctorPatientRecord(patientId) {
  const response = await apiClient.get(`/patients/doctor-records/${patientId}/`)
  return response.data
}
