<template>
  <div class="employees-view">
    <div class="header">
      <h1>{{ $t('employees.title') }}</h1>
      
      <div class="header-actions">
        <!-- Hidden file input for Excel -->
        <input type="file" accept=".xlsx,.xls" hidden ref="fileInput" @change="handleFileSelect" />
        
        <button class="btn-primary" @click="$refs.fileInput.click()" :disabled="syncStatus.is_running">
          <span class="icon">📥</span> {{ syncStatus.is_running ? $t('employees.syncing') : $t('employees.upload_sync') }}
        </button>

        <transition name="fade">
          <button v-if="selectedIds.length > 0" class="btn-danger" @click="handleBulkDeleteGlobal" :disabled="bulkActionStatus.is_running">
            <span class="icon">🗑️</span> {{ $t('employees.bulk_delete_all', { count: selectedIds.length }) }}
          </button>
        </transition>

        <a :href="exportUrl" class="btn-secondary" style="text-decoration: none;">
          <span class="icon">📊</span> {{ $t('biometric.export_fingerprints') || 'Xuất Excel' }}
        </a>

        <button class="btn-secondary" @click="isBulkDeleteModalOpen = true">
          <span class="icon">📁</span> {{ $t('employees.bulk_hardware_delete.title') }}
        </button>
      </div>
    </div>
    
    <!-- Bulk Global Action Progress -->
    <div v-if="bulkActionStatus.is_running" class="status-banner animate-in bulk-banner">
      <div class="banner-content">
        <div class="spinner-small"></div>
        <span>
          {{ $t('employees.bulk_delete_progress', { current: bulkActionStatus.processed_count + 1, total: bulkActionStatus.total_machines, ip: bulkActionStatus.current_ip }) }}
        </span>
      </div>
    </div>
    
    <!-- Inline Progress Banner -->
    <div v-if="syncStatus.is_running || syncStatus.progress > 0" class="status-banner animate-in" :class="{ 'status-success': syncStatus.progress === 100 && !syncStatus.is_running }">
      <div class="banner-content">
        <div class="spinner-small" v-if="syncStatus.is_running"></div>
        <span v-if="syncStatus.is_running">
          {{ $t('sync.syncing') }}: <strong>{{ syncStatus.current_step }}</strong> ({{ syncStatus.progress }}%)
        </span>
        <span v-else-if="syncStatus.error" class="text-danger">
          {{ $t('common.error') }}: {{ syncStatus.error }}
        </span>
        <span v-else>
          {{ $t('employees.sync_complete', { excel: syncStatus.excel_count, machine: syncStatus.machine_only_count }) }}
        </span>
      </div>
    </div>
    <div class="filter-bar">
      <input type="text" v-model="searchQuery" :placeholder="$t('employees.search_placeholder')" @input="resetAndFetch" />
      <select v-model="statusFilter" @change="resetAndFetch">
        <option value="">{{ $t('attendance.filters.all_status') }}</option>
        <option value="excel_synced">{{ $t('attendance.filters.status_excel') }}</option>
        <option value="machine_only">{{ $t('attendance.filters.status_machine') }}</option>
        <option value="log_only">{{ $t('attendance.filters.status_log') }}</option>
      </select>
    </div>



    <EmployeesTable 
      :employees="employees" 
      :idSortOrder="idSortOrder"
      @sort="handleSort"
      @selection-change="handleSelectionChange"
      @view="onView"
      @edit="onEdit" 
      @delete="onDelete" 
      @coverage="onCoverage" 
    />

    <PaginationBar
      :currentPage="currentPage"
      :totalPages="totalPages"
      :totalCount="totalCount"
      @change="onPageChange"
    />

    <EditEmployeeModal 
      :isOpen="isEditModalOpen"
      :employee="selectedEmployee"
      @close="isEditModalOpen = false"
      @saved="fetchEmployees"
    />

    <BiometricCoverageModal 
      :isOpen="isCoverageModalOpen"
      :employeeId="selectedEmployee?.employee_id"
      @close="isCoverageModalOpen = false"
    />

    <EmployeeDetailsModal
      :isOpen="isDetailsModalOpen"
      :employee="selectedEmployee"
      @close="isDetailsModalOpen = false"
    />

    <BulkDeleteHardwareModal
      :isOpen="isBulkDeleteModalOpen"
      @close="isBulkDeleteModalOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { employeesApi } from './api'
import EmployeesTable from './components/EmployeesTable.vue'
import EditEmployeeModal from './components/EditEmployeeModal.vue'
import EmployeeDetailsModal from './components/EmployeeDetailsModal.vue'
import BiometricCoverageModal from './components/BiometricCoverageModal.vue'
import BulkDeleteHardwareModal from './components/BulkDeleteHardwareModal.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import { dailySummaryApi } from '@/features/daily_summary/api'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notification.js'

const { t } = useI18n()
const notification = useNotificationStore()

const employees = ref([])
const searchQuery = ref('')
const statusFilter = ref('')


const currentPage = ref(1)
const totalCount = ref(0)
const totalPages = ref(0)
const idSortOrder = ref('asc')
const PAGE_SIZE = 50

const selectedIds = ref([])
const bulkActionStatus = ref({
  is_running: false,
  total_machines: 0,
  processed_count: 0,
  current_ip: '',
  error: null
})


const fileInput = ref(null)

const exportUrl = computed(() => {
  const params = new URLSearchParams()
  if (searchQuery.value) params.append('search', searchQuery.value)
  if (statusFilter.value) params.append('source_status', statusFilter.value)
  return `/api/employees/export?${params.toString()}`
})

import { bulkDeleteGlobal, getBulkDeleteStatus } from '@/features/machines/api'

const handleSelectionChange = (ids) => {
  selectedIds.value = ids
}

let bulkPollInterval = null

const handleBulkDeleteGlobal = async () => {
  if (selectedIds.value.length === 0) return
  
  const confirmed = await notification.confirm(
    t('employees.delete_bulk_global_confirm', { count: selectedIds.value.length }),
    t('actions.confirm')
  )
  if (!confirmed) return

  try {
    const res = await bulkDeleteGlobal(selectedIds.value)
    bulkActionStatus.value.is_running = true
    bulkActionStatus.value.error = null
    startBulkPolling()
  } catch (err) {
    notification.error(t('common.error') + ': ' + err.message)
  }
}

const startBulkPolling = () => {
  if (bulkPollInterval) clearInterval(bulkPollInterval)
  bulkPollInterval = setInterval(async () => {
    try {
      const data = await getBulkDeleteStatus()
      bulkActionStatus.value = {
        is_running: data.is_running,
        total_machines: data.total_machines,
        processed_count: data.processed_count,
        current_ip: data.current_ip,
        error: data.results?.[data.current_ip]?.status === 'Error' ? data.results[data.current_ip].message : null
      }
      
      if (!data.is_running) {
        clearInterval(bulkPollInterval)
        selectedIds.value = []
        fetchEmployees()
      }
    } catch (e) {
      console.error('Bulk polling error', e)
    }
  }, 1000)
}

const syncStatus = ref({
  is_running: false,
  progress: 0,
  current_step: '',
  excel_count: 0,
  machine_only_count: 0,
  error: null
})

let syncPollInterval = null

const handleFileSelect = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  try {
    syncStatus.value.is_running = true
    syncStatus.value.progress = 0
    syncStatus.value.current_step = t('sync.uploading')
    syncStatus.value.error = null
    
    await dailySummaryApi.syncExcel(file)
    startSyncPolling()
  } catch (err) {
    syncStatus.value.is_running = false
    syncStatus.value.error = err.response?.data?.detail || t('common.error')
  } finally {
    e.target.value = '' // reset
  }
}

const startSyncPolling = () => {
  if (syncPollInterval) clearInterval(syncPollInterval)
  syncPollInterval = setInterval(async () => {
    try {
      const { data } = await dailySummaryApi.getSyncStatus()
      syncStatus.value = data
      
      if (!data.is_running && data.progress === 100) {
        clearInterval(syncPollInterval)
        fetchEmployees()
      } else if (data.error) {
        clearInterval(syncPollInterval)
      }
    } catch (e) {
      console.error('Polling error', e)
    }
  }, 1000)
}

const fetchEmployees = async () => {
  try {
    const filters = {}
    if (searchQuery.value) filters.search = searchQuery.value
    if (statusFilter.value) filters.source_status = statusFilter.value

    filters.order = idSortOrder.value
    
    const result = await employeesApi.getEmployees(filters, currentPage.value, PAGE_SIZE)
    employees.value = result.items
    totalCount.value = result.total_count
    totalPages.value = result.total_pages
  } catch (err) {
    console.error('Failed to fetch employees:', err)
  }
}

const onPageChange = (page) => {
  currentPage.value = page
  fetchEmployees()
}

const resetAndFetch = () => {
  currentPage.value = 1
  fetchEmployees()
}

const handleSort = (key) => {
  if (key === 'id') {
    idSortOrder.value = idSortOrder.value === 'asc' ? 'desc' : 'asc'
    resetAndFetch()
  }
}



const isEditModalOpen = ref(false)
const isDetailsModalOpen = ref(false)
const isCoverageModalOpen = ref(false)
const isBulkDeleteModalOpen = ref(false)
const selectedEmployee = ref(null)

const onView = (emp) => {
  selectedEmployee.value = emp
  isDetailsModalOpen.value = true
}

const onEdit = (emp) => {
  selectedEmployee.value = emp
  isEditModalOpen.value = true
}

const onDelete = async (emp) => {
  const name = emp.emp_name || emp.employee_id
  const confirmed = await notification.confirm(
    t('employees.delete_hardware_confirm', { name }),
    t('actions.confirm')
  )
  if (confirmed) {
    try {
      await employeesApi.deleteEmployee(emp.employee_id)
      notification.success(t('device.delete_success', { id: emp.employee_id }))
      fetchEmployees()
    } catch (err) {
      notification.error(t('common.error'))
    }
  }
}

const onCoverage = async (emp) => {
  selectedEmployee.value = emp
  isCoverageModalOpen.value = true
}

onMounted(() => {
  fetchEmployees()
  
  // Resume polling if it was running
  dailySummaryApi.getSyncStatus().then(({ data }) => {
    if (data.is_running) {
      syncStatus.value = data
      startSyncPolling()
    }
  }).catch(e => console.error(e))
})

onUnmounted(() => {
  if (syncPollInterval) clearInterval(syncPollInterval)
})
</script>

<style scoped>
.employees-view {
  padding: 24px;
  color: #e2e8f0;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 1.8rem;
  margin: 0;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-primary:disabled {
  background-color: #475569;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #475569;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #64748b;
}

.btn-danger {
  background-color: #dc2626;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-danger:hover {
  background-color: #b91c1c;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.btn-danger:disabled {
  background-color: #7f1d1d;
  opacity: 0.6;
  cursor: not-allowed;
}

.status-banner {
  background-color: #334155;
  padding: 12px 20px;
  border-radius: 6px;
  margin-bottom: 24px;
  border-left: 4px solid #3b82f6;
}

.bulk-banner {
  border-left-color: #f87171;
  background-color: rgba(239, 68, 68, 0.05);
}

.status-success {
  border-left-color: #22c55e;
  background-color: #0f172a;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.95rem;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top: 2px solid #fff;
  border-radius: 50%;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.text-danger {
  color: #ef4444;
}

.animate-in {
  animation: slideDown 0.4s ease-out forwards;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.filter-bar input, .filter-bar select {
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid #475569;
  background-color: #1e293b;
  color: white;
  outline: none;
}

.filter-bar input:focus, .filter-bar select:focus {
  border-color: #3b82f6;
}
</style>
