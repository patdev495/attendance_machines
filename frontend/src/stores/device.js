import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getDevicesCapacity, getDeviceEmployees, deleteDeviceEmployee } from '@/api/devices.js'

export const useDeviceStore = defineStore('device', () => {
  // Device list
  const devices = ref([])
  const devicesLoading = ref(false)

  // Device employee view
  const currentIp = ref('')
  const allEmployees = ref([])
  const filteredEmployees = ref([])
  const employeesLoading = ref(false)
  const employeeError = ref(null)

  // Filters for employee page
  const searchTerm = ref('')
  const statusFilter = ref('')

  // Pagination (client-side)
  const empPage = ref(1)
  const empPageSize = 15

  const empTotalPages = computed(() => Math.ceil(filteredEmployees.value.length / empPageSize))
  const pagedEmployees = computed(() => {
    const start = (empPage.value - 1) * empPageSize
    return filteredEmployees.value.slice(start, start + empPageSize)
  })

  async function fetchDevices() {
    devicesLoading.value = true
    try {
      devices.value = await getDevicesCapacity()
    } catch (e) {
      console.error(e)
    } finally {
      devicesLoading.value = false
    }
  }

  async function loadDeviceEmployees(ip) {
    currentIp.value = ip
    allEmployees.value = []
    filteredEmployees.value = []
    searchTerm.value = ''
    statusFilter.value = ''
    employeesLoading.value = true
    employeeError.value = null

    try {
      const data = await getDeviceEmployees(ip)
      allEmployees.value = data.items
      applyFilter()
    } catch (e) {
      employeeError.value = e.message
    } finally {
      employeesLoading.value = false
    }
  }

  function applyFilter() {
    const s = searchTerm.value.toLowerCase()
    const st = statusFilter.value
    filteredEmployees.value = allEmployees.value.filter(u => {
      const matchSearch = !s ||
        u.user_id.toLowerCase().includes(s) ||
        (u.name && u.name.toLowerCase().includes(s)) ||
        (u.db_name && u.db_name.toLowerCase().includes(s))
      const matchStatus = !st || u.status === st
      return matchSearch && matchStatus
    })
    empPage.value = 1
  }

  async function deleteEmployee(employeeId) {
    await deleteDeviceEmployee(currentIp.value, employeeId)
    await loadDeviceEmployees(currentIp.value)
  }

  return {
    devices, devicesLoading,
    currentIp, allEmployees, filteredEmployees, employeesLoading, employeeError,
    searchTerm, statusFilter,
    empPage, empPageSize, empTotalPages, pagedEmployees,
    fetchDevices, loadDeviceEmployees, applyFilter, deleteEmployee
  }
})
