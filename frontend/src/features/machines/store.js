import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { 
  getMachinesCapacity, getMachineEmployees, deleteMachineEmployee, bulkDeleteMachineEmployees,
  updateEmployeeName, syncFingerprints, syncAllMachineFingerprints,
  updateUserPrivilege, EXPORT_FINGERPRINTS_URL
} from './api.js'

export const useMachineStore = defineStore('machines', () => {
  const machines = ref([])
  const machinesLoading = ref(false)

  // Machine employee view
  const currentIp = ref('')
  const allEmployees = ref([])
  const filteredEmployees = ref([])
  const employeesLoading = ref(false)
  const employeeError = ref(null)

  // Filters
  const searchTerm = ref('')
  const sourceStatusFilter = ref('')
  const shiftFilter = ref('')
  const idSortOrder = ref('asc') // 'asc' or 'desc'

  // Pagination
  const empPage = ref(1)
  const empPageSize = 15

  const exportUrl = EXPORT_FINGERPRINTS_URL
  const filteredExportUrl = computed(() => {
    return currentIp.value ? `${exportUrl}?ip=${encodeURIComponent(currentIp.value)}` : exportUrl
  })

  const empTotalPages = computed(() => Math.ceil(filteredEmployees.value.length / empPageSize))
  const pagedEmployees = computed(() => {
    const start = (empPage.value - 1) * empPageSize
    return filteredEmployees.value.slice(start, start + empPageSize)
  })

  async function fetchMachines() {
    machinesLoading.value = true
    try {
      machines.value = await getMachinesCapacity()
    } catch (e) {
      console.error(e)
    } finally {
      machinesLoading.value = false
    }
  }

  async function loadMachineEmployees(ip) {
    currentIp.value = ip
    allEmployees.value = []
    filteredEmployees.value = []
    searchTerm.value = ''
    sourceStatusFilter.value = ''
    shiftFilter.value = ''
    idSortOrder.value = 'asc'
    employeesLoading.value = true
    employeeError.value = null

    try {
      const data = await getMachineEmployees(ip)
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
    const st = sourceStatusFilter.value
    const sh = shiftFilter.value
    
    let result = allEmployees.value.filter(u => {
      const matchSearch = !s ||
        u.user_id.toLowerCase().includes(s) ||
        (u.name && u.name.toLowerCase().includes(s)) ||
        (u.db_name && u.db_name.toLowerCase().includes(s))
      
      const matchSource = !st || u.source_status === st
      
      let matchShift = true
      if (sh) {
        if (sh === '__none__') {
          matchShift = !u.shift || u.shift === '-'
        } else {
          matchShift = u.shift === sh
        }
      }
      
      return matchSearch && matchSource && matchShift
    })

    // Apply Numeric Sorting
    result.sort((a, b) => {
      const idA = parseInt(a.user_id) || 0
      const idB = parseInt(b.user_id) || 0
      return idSortOrder.value === 'asc' ? idA - idB : idB - idA
    })

    filteredEmployees.value = result
    empPage.value = 1
  }

  async function deleteEmployee(employeeId) {
    await deleteMachineEmployee(currentIp.value, employeeId)
    await loadMachineEmployees(currentIp.value)
  }

  async function bulkDeleteEmployees(employeeIds) {
    const res = await bulkDeleteMachineEmployees(currentIp.value, employeeIds)
    await loadMachineEmployees(currentIp.value)
    return res
  }

  async function renameEmployee(employeeId, newName) {
    await updateEmployeeName(employeeId, newName)
    await loadMachineEmployees(currentIp.value)
  }

  async function syncEmployeeFingerprints(employeeId) {
    return await syncFingerprints(currentIp.value, employeeId)
  }

  async function bulkSyncFingerprints() {
    return await syncAllMachineFingerprints(currentIp.value)
  }

  async function updatePrivilege(employeeId, privilege) {
    await updateUserPrivilege(currentIp.value, employeeId, privilege)
    const emp = allEmployees.value.find(u => u.user_id === employeeId)
    if (emp) {
      emp.privilege = privilege
    }
  }

  return {
    machines, machinesLoading,
    currentIp, allEmployees, filteredEmployees, employeesLoading, employeeError,
    searchTerm, sourceStatusFilter, shiftFilter, idSortOrder, exportUrl, filteredExportUrl,
    empPage, empPageSize, empTotalPages, pagedEmployees,
    fetchMachines, loadMachineEmployees, applyFilter, deleteEmployee, bulkDeleteEmployees,
    renameEmployee, syncEmployeeFingerprints, bulkSyncFingerprints, updatePrivilege
  }
})
