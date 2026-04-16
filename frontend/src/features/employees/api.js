import axios from 'axios'

const BASE = '/api/employees'

export const employeesApi = {
  getEmployees: async (filters = {}, page = 1, pageSize = 50) => {
    const response = await axios.get(BASE, { params: { ...filters, page, page_size: pageSize } })
    return response.data
  },
  
  rebuildRegistry: async () => {
    const response = await axios.post(`${BASE}/update-registry`)
    return response.data
  },
  
  getRebuildStatus: async () => {
    const response = await axios.get(`${BASE}/update-status`)
    return response.data
  },
  
  deleteEmployee: async (id) => {
    const response = await axios.delete(`${BASE}/${id}`)
    return response.data
  },
  
  // Notice: the delete status might simply be returned from the deleteEmployee call as it runs synchronously,
  // or it could be polled if it takes too long. The plan specifies returning results.
  // We'll keep getDeleteStatus in case we need it, but hardware deletion seems to be synchronous in the backend block.
  getDeleteStatus: async (id) => {
    // Currently delete is synchronous, so this might not be needed
    return null
  },
  
  updateEmployeeName: async (id, name, department, group_name, shift) => {
    const payload = { emp_name: name, department, group_name, shift }
    const response = await axios.put(`${BASE}/${id}`, payload)
    return response.data
  },
  
  getBiometricCoverage: async (id) => {
    const response = await axios.get(`${BASE}/${id}/biometric-coverage`)
    return response.data
  },

  bulkDeleteHardware: async (file, machineIps) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('machine_ips', machineIps.join(','))
    const response = await axios.post(`${BASE}/bulk-delete-hardware`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }
}
