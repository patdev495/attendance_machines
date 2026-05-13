import axios from 'axios'

export const mealApi = {
  checkMeal(empId, checkDate) {
    let url = `/api/meal/check/${empId}`
    if (checkDate) {
      url += `?check_date=${checkDate}`
    }
    return axios.get(url)
  },
  
  getMealList(params) {
    return axios.get('/api/meal/list', { params })
  },
  
  manualSwipe(empId, machineIp) {
    return axios.post('/api/meal/manual_swipe', { emp_id: empId, machine_ip: machineIp })
  },
  
  getCanteenMachines() {
    return axios.get('/api/meal/canteen-machines')
  },
  
  getTodayStats() {
    return axios.get(`/api/meal/today_stats?t=${Date.now()}`)
  },
  
  getTodayPickups() {
    return axios.get(`/api/meal/today_pickups?t=${Date.now()}`)
  },

  getAllMachineConfigs() {
    return axios.get('/api/machines/configs')
  },

  updateMachineConfig(ip, config) {
    return axios.post(`/api/machines/${ip}/config`, config)
  }
}
