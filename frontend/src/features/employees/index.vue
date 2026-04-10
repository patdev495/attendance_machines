<template>
  <div class="employees-view">
    <div class="header">
      <h1>Employee Management</h1>
      <button class="btn-primary" @click="showSyncModal = true">
        Update Registry
      </button>
    </div>
    


    <div class="filter-bar">
      <input type="text" v-model="searchQuery" placeholder="Search by ID or Name..." @input="fetchEmployees" />
      <select v-model="statusFilter" @change="fetchEmployees">
        <option value="">All Statuses</option>
        <option value="excel_synced">Excel Synced</option>
        <option value="machine_only">Machine Only</option>
        <option value="log_only">Log Only</option>
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

    <SyncRegistryModal 
      v-if="showSyncModal"
      @close="showSyncModal = false"
      @synced="onRegistrySynced"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { employeesApi } from './api'
import EmployeesTable from './components/EmployeesTable.vue'
import EditEmployeeModal from './components/EditEmployeeModal.vue'
import BiometricCoverageModal from './components/BiometricCoverageModal.vue'
import SyncRegistryModal from './components/SyncRegistryModal.vue'

const employees = ref([])
const searchQuery = ref('')
const statusFilter = ref('')

const showSyncModal = ref(false)

const onRegistrySynced = () => {
  showSyncModal.value = false
  fetchEmployees()
}

const fetchEmployees = async () => {
  try {
    const filters = {}
    if (searchQuery.value) filters.search = searchQuery.value
    if (statusFilter.value) filters.source_status = statusFilter.value
    
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
})

onUnmounted(() => {
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
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 24px;
  border-left: 4px solid #3b82f6;
}

.status-success {
  border-left-color: #22c55e;
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
