import axios from 'axios'

const API_BASE = '/api/daily-summary'

export const dailySummaryApi = {
  getSummary(params) {
    // Strip empty strings to prevent FastAPI 422 errors
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
    )
    return axios.get(API_BASE, { params: cleanParams })
  },
  
  getDetail(employeeId, workDate) {
    return axios.get(`${API_BASE}/detail`, {
      params: { employee_id: employeeId, work_date: workDate }
    })
  },
  
  startExport(params) {
    return axios.post(`${API_BASE}/export`, null, { params })
  },
  
  getExportStatus() {
    return axios.get(`${API_BASE}/export/status`)
  },
  
  downloadExport() {
    window.location.href = `${API_BASE}/export/download`
  },
  
  cancelExport() {
    return axios.post(`${API_BASE}/export/cancel`)
  },
  
  syncExcel(file) {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post(`${API_BASE}/sync-excel`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  getSyncStatus() {
    return axios.get(`${API_BASE}/sync-excel/status`)
  }
}
