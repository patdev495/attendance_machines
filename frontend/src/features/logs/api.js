// Feature: Log Management API
import axios from 'axios'

const BASE = '/api/logs'

export const logsApi = {
  getLogs(params) {
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
    )
    return axios.get(BASE, { params: cleanParams })
  },
  getDateRange() {
    return axios.get(`${BASE}/date-range`)
  },
  startSync(params = {}) {
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
    )
    return axios.post(`${BASE}/sync`, null, { params: cleanParams })
  },
  getSyncStatus() {
    return axios.get(`${BASE}/sync/status`)
  }
}
