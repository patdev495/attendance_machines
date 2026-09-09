<template>
  <div class="daily-summary-feature anim-up">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="title">{{ $t('attendance.summary_title') }}</h1>
        <p class="subtitle">{{ $t('attendance.summary_subtitle') }}</p>
      </div>

      <div class="header-actions">
        <!-- Sync Machines Button -->
        <button class="btn btn-purple sync-btn" @click="handleMachineSyncOnly" :disabled="syncStatus.is_running">
          <RotateCw :size="16" :class="{ 'spin-anim': syncStatus.is_running }" />
          <span>{{ syncStatus.is_running ? $t('employees.syncing') : $t('employees.sync_machines_only') }}</span>
        </button>

        <!-- Export Group -->
        <div class="export-group">
          <select v-model="exportMode" class="export-select" :disabled="exporting">
            <option value="both">{{ $t('export.both') }}</option>
            <option value="time">{{ $t('export.time') }}</option>
            <option value="hours">{{ $t('export.hours') }}</option>
          </select>
          <button class="btn btn-primary export-btn" :disabled="exporting" @click="triggerExport">
            <FileSpreadsheet :size="16" v-if="!exporting" />
            <div class="spinner-sm" v-else></div>
            <span>{{ exporting ? $t('attendance.export.exporting') : $t('attendance.export.btn') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- KPI Metric Summary Row -->
    <div class="kpi-grid">
      <div class="kpi-card card glow">
        <div class="kpi-icon-box emerald-box">
          <Users :size="20" />
        </div>
        <div class="kpi-details">
          <span class="kpi-label">Tổng lượt tổng hợp</span>
          <div class="kpi-val">{{ pagination.totalCount }}</div>
        </div>
      </div>

      <div class="kpi-card card glow">
        <div class="kpi-icon-box cyan-box">
          <Clock :size="20" />
        </div>
        <div class="kpi-details">
          <span class="kpi-label">Tổng giờ làm việc</span>
          <div class="kpi-val">{{ totalWorkHours.toFixed(1) }}h</div>
        </div>
      </div>

      <div class="kpi-card card glow">
        <div class="kpi-icon-box purple-box">
          <TrendingUp :size="20" />
        </div>
        <div class="kpi-details">
          <span class="kpi-label">Tổng giờ tăng ca (OT)</span>
          <div class="kpi-val text-ot">{{ totalOtHours.toFixed(1) }}h</div>
        </div>
      </div>

      <div class="kpi-card card glow">
        <div class="kpi-icon-box amber-box">
          <AlertTriangle :size="20" />
        </div>
        <div class="kpi-details">
          <span class="kpi-label">Cảnh báo ăn trưa / muộn</span>
          <div class="kpi-val text-alert">{{ totalAlerts }}</div>
        </div>
      </div>
    </div>

    <!-- Export Loading Banner -->
    <div v-if="exporting" class="status-banner sync-banner anim-up">
      <div class="banner-content">
        <div class="spinner-sm"></div>
        <span>{{ $t('attendance.export.status_banner', { step: exportStatus.current_step, progress: exportStatus.progress }) }}</span>
      </div>
    </div>

    <!-- Filters Component -->
    <SummaryFilters :initialFilters="filters" @change="handleFilterChange" />

    <!-- Summary Data Table -->
    <SummaryTable 
      :items="items" 
      :loading="loading" 
      :page="pagination.page"
      :size="pagination.size"
      :totalCount="pagination.totalCount"
      :totalPages="pagination.totalPages"
      @page-change="handlePageChange"
      @view-detail="handleViewDetail"
    >
      <template #actions>
        <div class="table-counts" v-if="pagination.totalCount > 0">
          <span class="badge badge-hours">{{ $t('attendance.table.total_records', { count: pagination.totalCount }) }}</span>
        </div>
      </template>
    </SummaryTable>

    <!-- Detail Modal -->
    <AppModal 
      :show="!!selectedDetail" 
      :title="selectedDetail ? $t('attendance.detail_modal_title', { id: selectedDetail.employee_id, date: selectedDetail.attendance_date }) : ''"
      @close="selectedDetail = null"
      width="480px"
    >
      <div v-if="detailLoading" class="loader-container">
        <div class="spinner-sm"></div>
      </div>
      <div v-else-if="detailLogs && detailLogs.length > 0" class="detail-list">
        <div v-for="log in detailLogs" :key="log.id" class="detail-item">
          <div class="detail-time-box">
            <Clock :size="14" class="time-icon" />
            <span class="detail-time">{{ formatDateTime(log.attendance_time) }}</span>
          </div>
          <span class="detail-machine badge-ip">{{ log.machine_name || log.machine_ip }}</span>
        </div>
      </div>
      <div v-else class="empty-state">
        {{ $t('common.no_data') }}
      </div>
    </AppModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notification'
import { createBackgroundOperation } from '@/composables/useBackgroundOperation.js'
import AppModal from '@/components/shared/AppModal.vue'
import { dailySummaryApi } from './api'
import SummaryFilters from './components/SummaryFilters.vue'
import SummaryTable from './components/SummaryTable.vue'
import { 
  RotateCw, 
  FileSpreadsheet, 
  Users, 
  Clock, 
  TrendingUp, 
  AlertTriangle 
} from 'lucide-vue-next'

const { t } = useI18n()
const notify = useNotificationStore()

const items = ref([])
const loading = ref(false)
const exporting = ref(false)
const exportMode = ref('both')
const exportStatus = ref({})
const selectedDetail = ref(null)
const detailLogs = ref([])
const detailLoading = ref(false)

const syncStatus = ref({
  is_running: false,
  progress: 0,
  current_step: '',
  error: null
})

const filters = reactive({
  employee_id: '',
  start_date: '',
  end_date: '',
  status: '',
  shift: '',
  min_hours: null,
  max_hours: null,
  only_missing: false,
  late_arrival: false,
  early_departure: false
})

const pagination = reactive({
  page: 1,
  size: 20,
  totalCount: 0,
  totalPages: 0
})

// KPI Metrics Computations
const totalWorkHours = computed(() => {
  return items.value.reduce((sum, item) => sum + (Number(item.work_hours) || 0), 0)
})

const totalOtHours = computed(() => {
  return items.value.reduce((sum, item) => sum + (Number(item.hours_ot) || 0), 0)
})

const totalAlerts = computed(() => {
  return items.value.filter(item => 
    item.lunch_status === 'overdue' || 
    item.minutes_late > 0 || 
    item.minutes_early_leave > 0 ||
    item.note
  ).length
})

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await dailySummaryApi.getSummary({
      ...filters,
      page: pagination.page,
      size: pagination.size
    })
    items.value = data.items
    pagination.totalCount = data.total_count
    pagination.totalPages = data.total_pages
  } catch (e) {
    console.error('Failed to fetch summary', e)
  } finally {
    loading.value = false
  }
}

const handleFilterChange = (newFilters) => {
  Object.assign(filters, newFilters)
  pagination.page = 1
  fetchData()
}

const handlePageChange = (newPage) => {
  pagination.page = newPage
  fetchData()
}

const handleViewDetail = async (item) => {
  selectedDetail.value = item
  detailLoading.value = true
  try {
    const { data } = await dailySummaryApi.getDetail(item.employee_id, item.attendance_date)
    detailLogs.value = data
  } catch (e) {
    console.error('Failed to fetch detail', e)
  } finally {
    detailLoading.value = false
  }
}

const exportOperation = createBackgroundOperation({
  getStatus: dailySummaryApi.getExportStatus,
  intervalMs: 1500,
  requireRunningBeforeComplete: true,
  maxInitialStalePolls: 2,
  onStatus(status) {
    exportStatus.value = status
  },
  onError(status) {
    exporting.value = false
    notify.error(t('attendance.export.error_prefix') + ': ' + status.error)
  },
  onComplete(status) {
    exporting.value = false
    if (status.progress === 100) {
      dailySummaryApi.downloadExport()
    }
  },
  onPollError(e) {
    console.error('Export poll error', e)
  },
})

const triggerExport = async () => {
  if (!filters.start_date || !filters.end_date) {
    notify.warn(t('export.error_missing_dates'))
    return
  }
  try {
    await dailySummaryApi.startExport({
      start_date: filters.start_date,
      end_date: filters.end_date,
      view_mode: exportMode.value
    })
    exporting.value = true
    exportOperation.startPolling({ immediate: true })
  } catch (e) {
    notify.error(t('export.error_failed') + ': ' + e.message)
    exporting.value = false
  }
}

const syncOperation = createBackgroundOperation({
  getStatus: dailySummaryApi.getSyncStatus,
  intervalMs: 2000,
  requireRunningBeforeComplete: true,
  maxInitialStalePolls: 2,
  initialStatus: syncStatus.value,
  onStatus(status) {
    syncStatus.value = status
  },
  onComplete(status) {
    syncStatus.value = status
    if (!status.error) {
      fetchData()
    }
  },
  onPollError(err) {
    console.error('Sync poll error', err)
  },
})

const handleMachineSyncOnly = async () => {
  try {
    syncStatus.value.is_running = true
    syncStatus.value.progress = 0
    syncStatus.value.current_step = t('sync.initiating')
    syncStatus.value.error = null
    
    await dailySummaryApi.syncExcel(null)
    syncOperation.startPolling({ immediate: true })
  } catch (err) {
    syncStatus.value.is_running = false
    syncStatus.value.error = err.response?.data?.detail || t('common.error')
  }
}

const formatDateTime = (timeStr) => {
  if (!timeStr) return '—'
  const d = new Date(timeStr)
  return d.toLocaleString('vi-VN', { 
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit' 
  })
}

onMounted(() => {
  const today = new Date()
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
  
  const formatDate = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  filters.start_date = formatDate(firstDay)
  filters.end_date = formatDate(today)
  
  fetchData()
})

onUnmounted(() => {
  exportOperation.dispose()
  syncOperation.dispose()
})
</script>

<style scoped>
.daily-summary-feature {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
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

.export-group {
  display: flex;
  align-items: center;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  height: 38px;
}

.export-select {
  background: transparent;
  border: none;
  color: #f8fafc;
  padding: 0 12px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  border-right: 1px solid var(--border);
  height: 100%;
}

.export-btn {
  border-radius: 0 !important;
  height: 100%;
  padding: 0 16px !important;
  font-size: 0.85rem !important;
}

.sync-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: var(--radius-md);
}

.spin-anim {
  animation: spin 0.8s linear infinite;
}

/* KPI Summary Cards Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 4px;
}

.kpi-card {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-radius: var(--radius-lg);
}

.kpi-icon-box {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.emerald-box { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.cyan-box { background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3); }
.purple-box { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
.amber-box { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

.kpi-details {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.kpi-val {
  font-family: var(--font-mono);
  font-size: 1.4rem;
  font-weight: 800;
  color: #fff;
  margin-top: 2px;
}
.text-ot { color: #c084fc; }
.text-alert { color: #fbbf24; }

/* Detail modal list */
.detail-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.detail-time-box {
  display: flex;
  align-items: center;
  gap: 8px;
}
.time-icon { color: var(--cyan); }
.detail-time {
  font-family: var(--font-mono);
  font-weight: 600;
  color: #e2e8f0;
}

.loader-container {
  padding: 40px;
  display: flex;
  justify-content: center;
}
</style>
