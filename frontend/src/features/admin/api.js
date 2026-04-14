import axios from 'axios'

const API_BASE_URL = '/api/shifts'

export const shiftsApi = {
  getShifts: async () => {
    const res = await axios.get(`${API_BASE_URL}/`)
    return res.data
  },
  
  createShift: async (shiftData) => {
    const res = await axios.post(`${API_BASE_URL}/`, shiftData)
    return res.data
  },
  
  updateShift: async (code, shiftData) => {
    const res = await axios.put(`${API_BASE_URL}/${code}`, shiftData)
    return res.data
  },
  
  deleteShift: async (code) => {
    const res = await axios.delete(`${API_BASE_URL}/${code}`)
    return res.data
  }
}
