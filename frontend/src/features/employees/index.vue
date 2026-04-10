<template>
  <div class="employees-view">
    <div class="header">
      <h1>Employee Management</h1>
      
      <div class="header-actions">
        <!-- Hidden file input for Excel -->
        <input type="file" accept=".xlsx,.xls" hidden ref="fileInput" @change="handleFileSelect" />
        
        <button class="btn-primary" @click="$refs.fileInput.click()" :disabled="syncStatus.is_running">
          <span class="icon">📥</span> {{ syncStatus.is_running ? 'Syncing...' : 'Upload & Sync Registry' }}
        </button>
      </div>
    </div>
    
    <!-- Inline Progress Banner -->
    <div v-if="syncStatus.is_running || syncStatus.progress > 0" class="status-banner animate-in" :class="{ 'status-success': syncStatus.progress === 100 && !syncStatus.is_running }">
      <div class="banner-content">
        <div class="spinner-small" v-if="syncStatus.is_running"></div>
        <span v-if="syncStatus.is_running">
          Syncing: <strong>{{ syncStatus.current_step }}</strong> ({{ syncStatus.progress }}%)
        </span>
        <span v-else-if="syncStatus.error" class="text-danger">
          Error: {{ syncStatus.error }}
        </span>
        <span v-else>
          Sync Complete. Excel Synced: <strong>{{ syncStatus.excel_count }}</strong>, Machine Only: <strong>{{ syncStatus.machine_only_count }}</strong>.
        </span>
      </div>
    </div>
    <div class="filter-bar">
      <input type="text" v-model="searchQuery" placeholder="Search by ID or Name..." @input="fetchEmployees" />
      <select v-model="statusFilter" @change="fetchEmployees">
        <option value="">All Statuses</option>
        <option value="excel_synced">Excel Synced</option>
        <option value="machine_only">Machine Only</option>
        <option value="log_only">Log Only</option>
      </select>
      <select v-model="shiftFilter" @change="fetchEmployees">
        <option value="">All Shifts</option>
        <option value="N">Ngày (N)</option>
        <option value="D">Đêm (D)</option>
        <option value="TV">Nghỉ việc (TV)</option>
        <option value="__none__">Không có thông tin</option>
      </select>
    </div>

    <EmployeesTable 
      :employees="employees" 
      @edit="onEdit" 
      @delete="onDelete" 
      @coverage="onCoverage" 
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { employeesApi } from './api'
import EmployeesTable from './components/EmployeesTable.vue'
import EditEmployeeModal from './components/EditEmployeeModal.vue'
import BiometricCoverageModal from './components/BiometricCoverageModal.vue'
import { dailySummaryApi } from '@/features/daily_summary/api'

const employees = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const shiftFilter = ref('')

const fileInput = ref(null)

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
    syncStatus.value.current_step = 'Starting upload...'
    syncStatus.value.error = null
    
    await dailySummaryApi.syncExcel(file)
    startSyncPolling()
  } catch (err) {
    syncStatus.value.is_running = false
    syncStatus.value.error = err.response?.data?.detail || 'Upload failed'
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
    if (shiftFilter.value) filters.shift = shiftFilter.value
    
    employees.value = await employeesApi.getEmployees(filters)
  } catch (err) {
    console.error('Failed to fetch employees:', err)
  }
}



const isEditModalOpen = ref(false)
const isCoverageModalOpen = ref(false)
const selectedEmployee = ref(null)

const onEdit = (emp) => {
  selectedEmployee.value = emp
  isEditModalOpen.value = true
}

const onDelete = async (emp) => {
  if (confirm(`Are you sure you want to delete ${emp.emp_name || emp.employee_id} from hardware?`)) {
    try {
      const res = await employeesApi.deleteEmployee(emp.employee_id)
      alert("Delete response:\n" + JSON.stringify(res.results, null, 2))
      // It does not delete from DB according to spec, but we might want to refresh anyway
      fetchEmployees()
    } catch (err) {
      alert("Failed to delete from hardware")
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

.status-banner {
  background-color: #334155;
  padding: 12px 20px;
  border-radius: 6px;
  margin-bottom: 24px;
  border-left: 4px solid #3b82f6;
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
