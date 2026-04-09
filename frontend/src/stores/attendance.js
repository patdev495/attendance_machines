import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { getAttendance, getAttendanceSummary, getMachines } from '@/api/attendance.js'

async function fetchDateRange() {
  try {
    const res = await fetch('/api/attendance/date-range')
    return await res.json()
  } catch { return null }
}

export const useAttendanceStore = defineStore('attendance', () => {
  // View: 'raw' | 'summary'
  const currentView = ref('raw')
  const machines = ref([])

  // Shared filters
  const filters = reactive({
    employeeId: '',
    machineIp: '',
    startDate: '',
    endDate: '',
    status: ''
  })

  // Summary-specific filters
  const summaryFilters = reactive({
    minHours: '',
    maxHours: '',
    shift: '',
    onlyMissing: false
  })

  // Pagination
  const currentPage = ref(1)
  const pageSize = 50

  // Data
  const items = ref([])
  const totalCount = ref(0)
  const totalPages = ref(0)
  const loading = ref(false)
  const error = ref(null)
  const dateRangeLoaded = ref(false)
  let lastRequestId = 0

  async function initDateRange() {
    if (dateRangeLoaded.value) return
    const range = await fetchDateRange()
    if (range) {
      if (range.min_date && !filters.startDate) filters.startDate = range.min_date
      if (range.max_date && !filters.endDate) filters.endDate = range.max_date
    }
    dateRangeLoaded.value = true
  }

  async function fetchMachines() {
    try {
      machines.value = await getMachines()
    } catch (e) {
      console.error('Failed to load machines', e)
    }
  }

  async function loadData(page = 1) {
    const requestId = ++lastRequestId
    currentPage.value = page
    loading.value = true
    error.value = null

    const params = {
      page,
      size: pageSize,
      ...(filters.employeeId && { employee_id: filters.employeeId }),
      ...(filters.machineIp && { machine_ip: filters.machineIp }),
      ...(filters.startDate && { start_date: filters.startDate }),
      ...(filters.endDate && { end_date: filters.endDate }),
      ...(filters.status && { status: filters.status })
    }

    try {
      let data
      if (currentView.value === 'raw') {
        data = await getAttendance(params)
      } else {
        if (summaryFilters.minHours) params.min_hours = summaryFilters.minHours
        if (summaryFilters.maxHours) params.max_hours = summaryFilters.maxHours
        if (summaryFilters.shift) params.shift = summaryFilters.shift
        if (summaryFilters.onlyMissing) params.only_missing = 'true'
        data = await getAttendanceSummary(params)
      }
      
      // Only apply if this is still the most recent request
      if (requestId === lastRequestId) {
        items.value = data.items
        totalCount.value = data.total_count
        totalPages.value = data.total_pages
      }
    } catch (e) {
      if (requestId === lastRequestId) {
        error.value = e.message
        items.value = []
      }
    } finally {
      if (requestId === lastRequestId) {
        loading.value = false
      }
    }
  }

  function resetFilters() {
    Object.assign(filters, { employeeId: '', machineIp: '', startDate: '', endDate: '', status: '' })
    Object.assign(summaryFilters, { minHours: '', maxHours: '', shift: '', onlyMissing: false })
    loadData(1)
  }

  function setView(view, load = true) {
    if (currentView.value !== view) {
      items.value = [] // Clear incompatible data immediately
      totalCount.value = 0
    }
    currentView.value = view
    if (load) loadData(1)
  }

  return {
    currentView, machines, filters, summaryFilters,
    currentPage, pageSize, items, totalCount, totalPages,
    loading, error,
    fetchMachines, loadData, resetFilters, setView, initDateRange
  }
})
