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
          <span class="icon">📊</span> {{ $t('employees.export_excel') }}
        </a>

        <button class="btn-secondary" @click="handleGlobalSync" :disabled="globalSyncStatus.is_running" style="border-color: #10b981; color: #10b981;">
          <span class="icon" :class="{'spin': globalSyncStatus.is_running}">🔄</span> 
          {{ globalSyncStatus.is_running ? $t('employees.syncing_fingerprints') : $t('employees.collect_all_fingerprints') }}
        </button>

        <button class="btn-secondary" @click="isBulkPushModalOpen = true">
          <span class="icon">📤</span> {{ $t('employees.bulk_push_fingerprints') }}
        </button>

        <div class="dropdown-wrapper" style="position: relative;">
          <button class="btn-secondary" @click="showClearDropdown = !showClearDropdown" style="border-color: #ef4444; color: #ef4444;">
            <span class="icon">🗑️</span> {{ $t('employees.clear_fingerprints_machine') }}
          </button>
          <div v-if="showClearDropdown" class="clear-dropdown">
            <div class="clear-dropdown-header">{{ $t('employees.select_machine_to_clear') }}</div>
            <button v-for="ip in clearMachineList" :key="ip" class="clear-dropdown-item" @click="handleClearMachine(ip)" :disabled="isClearingMachine">
              {{ ip }}
            </button>
          </div>
        </div>

        <button class="btn-secondary" @click="isBulkDeleteModalOpen = true">
          <span class="icon">📁</span> {{ $t('employees.bulk_hardware_delete.title') }}
        </button>
      </div>
    </div>
    
    <div v-if="bulkActionStatus.is_running" class="status-banner animate-in bulk-banner">
      <div class="banner-content">
        <div class="spinner-small"></div>
        <span>
          {{ $t('employees.bulk_delete_progress', { current: bulkActionStatus.processed_count + 1, total: bulkActionStatus.total_machines, ip: bulkActionStatus.current_ip }) }}
        </span>
      </div>
    </div>

    <!-- Global Sync Progress -->
    <div v-if="globalSyncStatus.is_running" class="status-banner animate-in bulk-banner" style="background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3);">
      <div class="banner-content">
        <div class="spinner-small" style="border-top-color: #10b981;"></div>
        <span style="color: #10b981;">
          {{ $t('employees.collect_progress', { current: globalSyncStatus.processed_count + 1, total: globalSyncStatus.total_machines, ip: globalSyncStatus.current_ip }) }}
        </span>
      </div>
    </div>

    <!-- Clear Fingerprints Progress -->
    <div v-if="clearFpStatus.is_running" class="status-banner animate-in bulk-banner" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3);">
      <div class="banner-content">
        <div class="spinner-small" style="border-top-color: #ef4444;"></div>
        <span style="color: #ef4444;">
          {{ $t('employees.clear_progress', { ip: clearFpStatus.ip, processed: clearFpStatus.processed_users, total: clearFpStatus.total_users }) }}
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

      <select v-model="privilegeFilter" @change="resetAndFetch">
        <option value="">{{ $t('attendance.filters.all_privilege') }}</option>
        <option value="0">{{ $t('attendance.filters.privilege_user') }}</option>
        <option value="14">{{ $t('attendance.filters.privilege_admin') }}</option>
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

    <BulkPushHardwareModal
      :show="isBulkPushModalOpen"
      @close="isBulkPushModalOpen = false"
      @success="handleBulkPushSuccess"
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
import BulkPushHardwareModal from './components/BulkPushHardwareModal.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import { dailySummaryApi } from '@/features/daily_summary/api'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notification.js'

const { t } = useI18n()
const notification = useNotificationStore()

const employees = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const privilegeFilter = ref('')

const isBulkPushModalOpen = ref(false)

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
  if (privilegeFilter.value !== '') params.append('privilege', privilegeFilter.value)
  return `/api/employees/export?${params.toString()}`
})

import { bulkDeleteGlobal, getBulkDeleteStatus, triggerGlobalSync, getGlobalSyncStatus, getMachines, clearMachineFingerprints, getClearFpStatus } from '@/features/machines/api'

const showClearDropdown = ref(false)
const clearMachineList = ref([])
const isClearingMachine = ref(false)
const clearFpStatus = ref({ is_running: false, ip: '', total_users: 0, processed_users: 0, result: '' })
let clearFpPollInterval = null

// Load machine list for clear dropdown
const loadClearMachines = async () => {
  try {
    clearMachineList.value = await getMachines() || []
  } catch (e) { console.error(e) }
}
loadClearMachines()

// Close dropdown on click outside
const handleClickOutside = (e) => {
  if (showClearDropdown.value && !e.target.closest('.dropdown-wrapper')) {
    showClearDropdown.value = false
  }
}


onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))

const handleClearMachine = async (ip) => {
  const confirmed = await notification.confirm(t('employees.clear_confirm', { ip }))
  if (!confirmed) return
  
  try {
    showClearDropdown.value = false
    await clearMachineFingerprints(ip)
    clearFpStatus.value.is_running = true
    clearFpStatus.value.ip = ip
    
    clearFpPollInterval = setInterval(async () => {
      try {
        const status = await getClearFpStatus()
        clearFpStatus.value = status
        if (!status.is_running) {
          clearInterval(clearFpPollInterval)
          clearFpPollInterval = null
          if (status.result) {
            notification.success(status.result)
          }
        }
      } catch (e) { console.error(e) }
    }, 1000)
  } catch (err) {
    notification.error(`Lỗi xóa vân tay trên ${ip}: ${err.message || err}`)
  }
}

const globalSyncStatus = ref({
  is_running: false,
  total_machines: 0,
  processed_count: 0,
  current_ip: ''
})

let globalSyncPollInterval = null

const handleGlobalSync = async () => {
  const confirmed = await notification.confirm(t('employees.collect_confirm'))
  if (!confirmed) return
  
  try {
    await triggerGlobalSync()
    notification.success(t('employees.collect_start_success'))
    globalSyncStatus.value.is_running = true
    startGlobalSyncPoll()
  } catch (err) {
    notification.error('Lỗi khi bắt đầu gom vân tay: ' + err.message)
  }
}

const startGlobalSyncPoll = () => {
  if (globalSyncPollInterval) clearInterval(globalSyncPollInterval)
  globalSyncPollInterval = setInterval(async () => {
    try {
      const status = await getGlobalSyncStatus()
      globalSyncStatus.value = status
      
      if (!status.is_running && status.total_machines > 0) {
        clearInterval(globalSyncPollInterval)
        globalSyncPollInterval = null
        
        // Calculate total
        let totalFp = 0
        Object.values(status.results || {}).forEach(msg => {
          const match = msg.match(/(\d+) vân tay/)
          if (match) totalFp += parseInt(match[1])
        })
        
        notification.success(t('employees.collect_complete_success', { count: totalFp, machines: status.total_machines }))
      }
    } catch (e) {
      console.error(e)
    }
  }, 1500)
}

const handleSelectionChange = (ids) => {
  selectedIds.value = ids
}

const handleBulkPushSuccess = () => {
  isBulkPushModalOpen.value = false
  fetchEmployees()
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
    if (privilegeFilter.value !== '') filters.privilege = parseInt(privilegeFilter.value)
    
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
<style scoped>
.spin {
  animation: spin 1.5s linear infinite;
  display: inline-block;
}
.clear-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 0.5rem;
  z-index: 100;
  min-width: 200px;
  backdrop-filter: blur(12px);
  box-shadow: 0 10px 25px rgba(0,0,0,0.5);
}
.clear-dropdown-header {
  font-size: 0.75rem;
  color: #94a3b8;
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.25rem;
}
.clear-dropdown-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  color: #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.15s;
}
.clear-dropdown-item:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}
.clear-dropdown-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
