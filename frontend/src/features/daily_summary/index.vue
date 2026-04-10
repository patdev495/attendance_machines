<template>
  <div class="daily-summary-feature">
    <div class="page-header animate-in">
      <div class="header-content">
        <h1>{{ $t('attendance.summary_title') }}</h1>
        <p class="subtitle">Analyze daily attendance, manage shifts, and export reports.</p>
      </div>
      <div class="header-actions">
        <div class="export-group">
          <select v-model="exportMode" class="export-select" :disabled="exporting">
            <option value="both">{{ $t('export.both') }}</option>
            <option value="time">{{ $t('export.time') }}</option>
            <option value="hours">{{ $t('export.hours') }}</option>
          </select>
          <button class="btn btn-primary export-btn" :disabled="exporting" @click="triggerExport">
            <span class="icon" v-if="!exporting">📊</span>
            <div class="spinner-small" v-else></div>
            {{ exporting ? 'Exporting...' : $t('attendance.export.btn') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Export Loading Banner -->
    <div v-if="exporting" class="status-banner animate-in">
      <div class="banner-content">
        <div class="spinner-small"></div>
        <span>Exporting Excel: <strong>{{ exportStatus.current_step }}</strong> ({{ exportStatus.progress }}%)</span>
      </div>
    </div>

    <SummaryFilters :initialFilters="filters" @change="handleFilterChange" />

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
          <span class="count-item">Total records: <strong>{{ pagination.totalCount }}</strong></span>
        </div>
      </template>
    </SummaryTable>

    <!-- Detail Modal -->
    <AppModal 
      :show="!!selectedDetail" 
      :title="selectedDetail ? `Detail: ${selectedDetail.employee_id} - ${selectedDetail.attendance_date}` : ''"
      @close="selectedDetail = null"
      width="450px"
    >
      <div v-if="detailLoading" class="loader-container">
        <div class="loader"></div>
      </div>
      <div v-else class="detail-list">
        <div v-for="log in detailLogs" :key="log.id" class="detail-item">
          <span class="detail-time">{{ formatTime(log.attendance_time) }}</span>
          <span class="detail-machine">{{ log.machine_name || log.machine_ip }}</span>
        </div>
      </div>
    </AppModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notification'
import AppModal from '@/components/shared/AppModal.vue'
import { dailySummaryApi } from './api'
import SummaryFilters from './components/SummaryFilters.vue'
import SummaryTable from './components/SummaryTable.vue'
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

const filters = reactive({
  employee_id: '',
  start_date: '',
  end_date: '',
  status: '',
  shift: '',
  min_hours: null,
  max_hours: null,
  only_missing: false
})

const pagination = reactive({
  page: 1,
  size: 20,
  totalCount: 0,
  totalPages: 0
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

let exportPoller = null
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
        startExportPolling()
    } catch (e) {
        notify.error(t('export.error_failed') + ': ' + e.message)
    }
}

const startExportPolling = () => {
    if (exportPoller) clearInterval(exportPoller)
    exportPoller = setInterval(async () => {
        try {
            const { data } = await dailySummaryApi.getExportStatus()
            exportStatus.value = data
            if (!data.is_running && data.progress === 100) {
                clearInterval(exportPoller)
                exporting.value = false
                dailySummaryApi.downloadExport()
            } else if (data.error) {
                clearInterval(exportPoller)
                exporting.value = false
                alert('Export error: ' + data.error)
            }
        } catch (e) {
            console.error('Export poll error', e)
        }
    }, 1500)
}

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(() => {
  const today = new Date()
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
  
  // Simple YYYY-MM-DD formatting
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
    if (exportPoller) clearInterval(exportPoller)
})
</script>

<style scoped>
.daily-summary-feature {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-content h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 0.95rem;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.export-group {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;
  height: 42px;
}

.export-group:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.export-select {
  background: #1e293b; /* Dark slate background */
  border: none;
  color: #f8fafc;
  padding: 0 12px;
  font-size: 0.9rem;
  font-family: 'Outfit', sans-serif;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  border-right: 1px solid var(--border);
  height: 100%;
}

.export-btn {
  border-radius: 0 !important;
  height: 100%;
  padding: 0 16px !important;
  font-size: 0.9rem !important;
}

.status-banner {
  padding: 12px 20px;
  background: var(--bg-hover);
  border-left: 4px solid var(--primary);
  margin-bottom: 20px;
  border-radius: 8px;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.9rem;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--bg-hover);
  border-top: 2px solid var(--primary);
  border-radius: 50%;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-main);
  border-radius: 8px;
}

.detail-time {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--primary);
}

.detail-machine {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.loader-container {
  padding: 40px;
  display: flex;
  justify-content: center;
}

.animate-in {
  animation: slideUp 0.5s ease-out forwards;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
