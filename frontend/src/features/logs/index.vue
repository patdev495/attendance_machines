<template>
  <div class="logs-feature">
    <header class="feature-header">
      <div class="header-content">
        <h1 class="title">{{ $t('attendance.raw_logs') }}</h1>
        <p class="subtitle">{{ $t('attendance.logs_subtitle') }}</p>
      </div>
      <div class="header-actions">
        <button 
          class="btn btn-primary sync-btn" 
          :disabled="syncStore.syncRunning" 
          @click="syncStore.startSync()"
        >
          <span v-if="syncStore.syncRunning" class="spin-icon">⟳</span>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="btn-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          {{ syncStore.syncRunning ? $t('sync.syncing') + '...' : $t('sync.machines') }}
        </button>
      </div>
    </header>

    <div v-if="syncStore.syncRunning" class="sync-banner">
      <div class="banner-content">
        <div class="spinner-sm"></div>
        <span>{{ syncStore.syncMessage }}</span>
      </div>
    </div>

    <LogsFilters 
      :machines="attendanceStore.machines" 
      :initial-filters="activeFilters"
      @change="handleFilterChange" 
    />

    <LogsTable 
      :items="items"
      :loading="loading"
      :error="error"
      :currentPage="currentPage"
      :totalPages="totalPages"
      :totalCount="totalCount"
      @page-change="loadData"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { logsApi } from './api'
import { useSyncStore } from '@/stores/sync.js'
import { useAttendanceStore } from '@/stores/attendance.js'
import LogsFilters from './components/LogsFilters.vue'
import LogsTable from './components/LogsTable.vue'

const syncStore = useSyncStore()
const attendanceStore = useAttendanceStore()

const items = ref([])
const loading = ref(false)
const error = ref(null)
const currentPage = ref(1)
const totalPages = ref(1)
const totalCount = ref(0)
const activeFilters = ref({})

async function loadData(page = 1) {
  currentPage.value = page
  loading.value = true
  error.value = null
  
  try {
    const params = {
      page,
      size: 50,
      ...activeFilters.value
    }
    const { data } = await logsApi.getLogs(params)
    items.value = data.items
    totalCount.value = data.total_count
    totalPages.value = data.total_pages
  } catch (e) {
    error.value = i18n.global.t('attendance.table.error_load_logs')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleFilterChange(filters) {
  const params = {}
  if (filters.employeeId) params.employee_id = filters.employeeId
  if (filters.machineIp) params.machine_ip = filters.machineIp
  if (filters.startDate) params.start_date = filters.startDate
  if (filters.endDate) params.end_date = filters.endDate
  
  activeFilters.value = params
  loadData(1)
}

// Watch for sync completion to refresh data
watch(() => syncStore.syncRunning, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    loadData(1)
  }
})

onMounted(() => {
  attendanceStore.fetchMachines()
  
  // Set default dates: first day of month to today
  const today = new Date()
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
  
  const formatDate = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  activeFilters.value = {
    start_date: formatDate(firstDay),
    end_date: formatDate(today)
  }
  
  loadData(1)
})
</script>

<style scoped>
.logs-feature { display: flex; flex-direction: column; gap: 24px; padding-bottom: 40px; }

.feature-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.title { font-size: 1.85rem; font-weight: 700; color: white; margin: 0 0 4px 0; letter-spacing: -0.5px; }
.subtitle { color: var(--text-muted); font-size: 0.95rem; margin: 0; }

.header-actions { display: flex; gap: 12px; }
.sync-btn { display: flex; align-items: center; gap: 8px; font-weight: 600; padding: 10px 20px; border-radius: 10px; transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
.sync-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4); }
.btn-icon { opacity: 0.9; }

.sync-banner { background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); border-left: 4px solid var(--primary); padding: 12px 20px; border-radius: 8px; }
.banner-content { display: flex; align-items: center; gap: 12px; color: #93c5fd; font-weight: 500; font-size: 0.95rem; }

.spin-icon { display: inline-block; animation: spin 1s linear infinite; font-size: 1.2rem; }
.spinner-sm { width: 16px; height: 16px; border: 2px solid rgba(255, 255, 255, 0.1); border-top-color: #60a5fa; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

:deep(.card) { border-radius: 16px; border: 1px solid var(--border); background: var(--card-bg); overflow: hidden; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); }
:deep(.btn) { cursor: pointer; border-radius: 8px; }
</style>
