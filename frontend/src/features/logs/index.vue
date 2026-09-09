<template>
  <div class="logs-feature anim-up">
    <!-- Header Section -->
    <header class="feature-header">
      <div class="header-content">
        <h1 class="title">{{ $t('attendance.raw_logs') }}</h1>
        <p class="subtitle">{{ $t('attendance.logs_subtitle') }}</p>
      </div>
      <div class="header-actions">
        <!-- Live Stream Toggle -->
        <button 
          class="btn live-toggle" 
          :class="{ 'active': liveMode }"
          @click="toggleLiveMode"
        >
          <span class="live-dot" :class="{ 'pulsing': liveMode }"></span>
          <Radio :size="15" />
          <span>{{ liveMode ? 'LIVE: ON' : 'LIVE MODE' }}</span>
        </button>

        <!-- Sync Machines Button -->
        <button 
          class="btn btn-primary sync-btn" 
          :disabled="syncStore.syncRunning || liveMode" 
          @click="syncStore.startSync(activeFilters)"
        >
          <RotateCw :size="16" :class="{ 'spin-anim': syncStore.syncRunning }" />
          <span>{{ syncStore.syncRunning ? $t('sync.syncing') + '...' : $t('sync.machines') }}</span>
        </button>
      </div>
    </header>

    <!-- Syncing Progress Banner -->
    <div v-if="syncStore.syncRunning" class="sync-banner anim-up">
      <div class="banner-content">
        <span class="spinner-sm"></span>
        <span>{{ syncStore.syncMessage }}</span>
      </div>
    </div>

    <!-- Filters Bar -->
    <LogsFilters 
      :machines="attendanceStore.machines" 
      :initial-filters="activeFilters"
      :live-mode="liveMode"
      @change="handleFilterChange" 
    />

    <!-- Logs Data Table -->
    <LogsTable 
      :items="items"
      :loading="loading"
      :error="error"
      :currentPage="currentPage"
      :totalPages="totalPages"
      :totalCount="totalCount"
      :liveMode="liveMode"
      @page-change="loadData"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { logsApi } from './api'
import { useSyncStore } from '@/stores/sync.js'
import { useAttendanceStore } from '@/stores/attendance.js'
import { useLiveLogs } from './composables/useLiveLogs'
import LogsFilters from './components/LogsFilters.vue'
import LogsTable from './components/LogsTable.vue'
import { Radio, RotateCw } from 'lucide-vue-next'

const syncStore = useSyncStore()
const attendanceStore = useAttendanceStore()

const items = ref([])
const loading = ref(false)
const error = ref(null)
const currentPage = ref(1)
const totalPages = ref(1)
const totalCount = ref(0)
const activeFilters = ref({})
const liveMode = ref(false)

const { connect, disconnect } = useLiveLogs((payload) => {
  if ((payload.type === 'new_log' || payload.type === 'meal_event') && liveMode.value) {
    const newLog = payload.data
    
    rawLiveItems.value.unshift({
      ...newLog,
      is_live: true,
      id: Date.now() + Math.random()
    })
    if (rawLiveItems.value.length > 500) rawLiveItems.value.pop()

    const params = activeFilters.value
    items.value = rawLiveItems.value.filter(item => {
      if (params.employee_id && !item.employee_id.includes(params.employee_id)) return false
      if (params.machine_ip && item.machine_ip !== params.machine_ip) return false
      return true
    })
  }
})

const rawLiveItems = ref([])

function toggleLiveMode() {
  liveMode.value = !liveMode.value
  if (liveMode.value) {
    items.value = []
    rawLiveItems.value = []
    totalCount.value = 0
    totalPages.value = 1
    connect()
  } else {
    disconnect()
    loadData(1)
  }
}

async function loadData(page = 1) {
  if (liveMode.value) return
  
  currentPage.value = page
  loading.value = true
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
    error.value = 'Không thể tải nhật ký chấm công'
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
  
  if (liveMode.value) {
    items.value = rawLiveItems.value.filter(item => {
      if (params.employee_id && !item.employee_id.includes(params.employee_id)) return false
      if (params.machine_ip && item.machine_ip !== params.machine_ip) return false
      return true
    })
  } else {
    loadData(1)
  }
}

watch(() => syncStore.syncRunning, (newVal, oldVal) => {
  if (oldVal === true && newVal === false && !liveMode.value) {
    loadData(1)
  }
})

onMounted(() => {
  attendanceStore.fetchMachines()
  
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
.logs-feature {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.title {
  font-size: 1.7rem;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--text-muted);
  font-size: 0.88rem;
  margin-top: 2px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.live-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-weight: 600;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.live-toggle.active {
  background: rgba(244, 63, 94, 0.15);
  border-color: rgba(244, 63, 94, 0.4);
  color: #fb7185;
  box-shadow: 0 0 20px rgba(244, 63, 94, 0.25);
}

.live-dot {
  width: 8px;
  height: 8px;
  background: currentColor;
  border-radius: 50%;
  opacity: 0.5;
}

.live-dot.pulsing {
  opacity: 1;
  background: #f43f5e;
  animation: livePulse 1.5s infinite;
}

.sync-btn {
  padding: 8px 18px;
}

.spin-anim {
  animation: spin 0.8s linear infinite;
}

.sync-banner {
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-left: 4px solid var(--primary);
  padding: 12px 20px;
  border-radius: var(--radius-md);
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #c7d2fe;
  font-weight: 600;
  font-size: 0.9rem;
}
</style>
