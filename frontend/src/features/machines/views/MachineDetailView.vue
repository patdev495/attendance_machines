<template>
  <div class="anim-up">
    <!-- Page Header -->
    <div class="page-header">
      <div style="display:flex; align-items:center; gap:16px;">
        <router-link to="/machines" class="btn btn-ghost">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          {{ $t('device.all_devices') }}
        </router-link>
        <h2>{{ $t('device.machine') }} <span class="ip-label">{{ ip }}</span></h2>
      </div>
      <div style="display:flex; gap:10px;">
        <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="handleBulkDelete" style="background:#ef4444; color:#fff; border:none; display:flex; align-items:center; gap:6px;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          {{ $t('device.action.delete') }} ({{ selectedIds.length }})
        </button>
        <button class="btn btn-primary" @click="store.loadMachineEmployees(ip)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.08-7.49"/></svg>
          {{ $t('device.refresh') }}
        </button>
        <button class="btn btn-primary btn-add-employee" @click="isAddModalOpen = true">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M16 11h6"/></svg>
          <span class="btn-label">{{ $t('device.machine_employee.add_employee_button') }}</span>
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="filter-bar card">
      <div class="filter-group" style="flex:1;">
        <label>{{ $t('attendance.filters.search') }}</label>
        <input v-model="store.searchTerm" :placeholder="$t('employees.search_placeholder')" @input="store.applyFilter()" />
      </div>
      <div class="filter-group" style="min-width:160px;">
        <label>{{ $t('attendance.filters.status') }}</label>
        <select v-model="store.sourceStatusFilter" @change="store.applyFilter()">
          <option value="">{{ $t('attendance.filters.all_status') }}</option>
          <option value="excel_synced">{{ $t('attendance.filters.status_excel') }}</option>
          <option value="machine_only">{{ $t('attendance.filters.status_machine') }}</option>
          <option value="log_only">{{ $t('attendance.filters.status_log') }}</option>
        </select>
      </div>
    </div>

    <!-- Count summary -->
    <div class="summary-row" v-if="!store.employeesLoading">
      <span class="count-badge">{{ $t('device.employee_count', { filtered: store.filteredEmployees.length, total: store.allEmployees.length }) }}</span>
    </div>

    <LoadingSpinner v-if="store.employeesLoading" :message="$t('device.connecting')" />
    <div v-else-if="store.employeeError" class="empty-state card" style="color:#f87171;">{{ store.employeeError }}</div>
    <template v-else>
      <MachineEmployeeTable 
        :employees="store.pagedEmployees" 
        @view="handleView"
        @edit="handleEdit"
        @delete="handleDelete" 
        @sync="handleSync"
        @selection-change="ids => selectedIds = ids"
      />
      <PaginationBar
        :currentPage="store.empPage"
        :totalPages="store.empTotalPages"
        :totalCount="store.filteredEmployees.length"
        @change="p => store.empPage = p"
      />
    </template>

    <!-- Details Modal -->
    <EmployeeDetailsModal
      :isOpen="isDetailsModalOpen"
      :employee="selectedEmployee"
      @close="isDetailsModalOpen = false"
    />

    <AddMachineEmployeeModal
      :isOpen="isAddModalOpen"
      :ip="ip"
      :isSubmitting="isAddingEmployee"
      @close="isAddModalOpen = false"
      @submit="handleAddEmployeeModal"
    />

    <EditMachineEmployeeModal
      :isOpen="isEditMachineEmployeeOpen"
      :ip="ip"
      :employee="editingMachineEmployee"
      :isSubmitting="isUpdatingMachineEmployee"
      @close="isEditMachineEmployeeOpen = false"
      @submit="handleUpdateMachineEmployee"
    />

    <SyncToMachinesModal
      :isOpen="isSyncModalOpen"
      :employeeId="syncEmployeeId"
      :employeeName="syncEmployeeName"
      :sourceIp="ip"
      @close="isSyncModalOpen = false"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useMachineStore } from '../store.js'
import { useNotificationStore } from '@/stores/notification.js'
import { useI18n } from 'vue-i18n'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import MachineEmployeeTable from '../components/MachineEmployeeTable.vue'
import AddMachineEmployeeModal from '../components/AddMachineEmployeeModal.vue'
import EditMachineEmployeeModal from '../components/EditMachineEmployeeModal.vue'
import EmployeeDetailsModal from '@/features/employees/components/EmployeeDetailsModal.vue'
import SyncToMachinesModal from '../components/SyncToMachinesModal.vue'

const props = defineProps({ ip: { type: String, required: true } })
const store = useMachineStore()
const notification = useNotificationStore()
const { t } = useI18n()

const selectedIds = ref([])
const selectedEmployee = ref(null)
const isDetailsModalOpen = ref(false)
const isAddModalOpen = ref(false)
const isAddingEmployee = ref(false)
const isEditMachineEmployeeOpen = ref(false)
const isUpdatingMachineEmployee = ref(false)
const editingMachineEmployee = ref(null)

const isSyncModalOpen = ref(false)
const syncEmployeeId = ref('')
const syncEmployeeName = ref('')

onMounted(() => {
  store.loadMachineEmployees(props.ip)
})

function handleSync(u) {
  syncEmployeeId.value = u.user_id
  syncEmployeeName.value = u.db_name || u.name || ''
  isSyncModalOpen.value = true
}

function handleView(u) {
  // Map machine-specific fields to registry-style fields for the modal
  selectedEmployee.value = {
    employee_id: u.user_id,
    emp_name: u.db_name,
    department: u.department,
    group_name: u.group_name,
    shift: u.shift,
    source_status: u.source_status
  }
  isDetailsModalOpen.value = true
}

function handleEdit(u) {
  editingMachineEmployee.value = u
  isEditMachineEmployeeOpen.value = true
}

async function handleDelete(employeeId) {
  const confirmed = await notification.confirm(
    t('actions.delete_single_warn', { id: employeeId, ip: props.ip }),
    t('actions.confirm')
  )
  if (!confirmed) return
  try {
    await store.deleteEmployee(employeeId)
    notification.success(t('device.delete_success', { id: employeeId }))
  } catch (e) {
    notification.error(t('device.sync_failed', { err: e.message }))
  }
}

async function handleBulkDelete() {
  const confirmed = await notification.confirm(
    t('device.bulk_delete_confirm', { count: selectedIds.value.length }),
    t('actions.confirm')
  )
  if (!confirmed) return
  
  const notifyId = notification.info(t('device.bulk_deleting', { count: selectedIds.value.length }), 0)
  try {
    const res = await store.bulkDeleteEmployees(selectedIds.value)
    const actualDeleted = res?.count !== undefined ? res.count : selectedIds.value.length
    notification.success(t('device.bulk_delete_success', { count: actualDeleted }))
    selectedIds.value = []
  } catch (e) {
    notification.error(t('common.error') + ': ' + e.message)
  } finally {
    notification.remove(notifyId)
  }
}

async function handleAddEmployeeModal(payload) {
  const normalizedId = payload.employeeId.trim()
  if (!normalizedId) {
    notification.error(t('device.machine_employee.employee_id_required'))
    return
  }

  const roleLabel = machineRoleLabel(payload.role)
  isAddingEmployee.value = true
  const notifyId = notification.info(t('device.machine_employee.adding_notice', { role: roleLabel, id: normalizedId, ip: props.ip }), 0)
  try {
    await store.addEmployee(normalizedId, payload.name?.trim() || '', payload.role, payload.photoBase64 || '', payload.password || '123456')
    isAddModalOpen.value = false
    notification.success(t('device.machine_employee.add_success', { role: roleLabel, id: normalizedId, ip: props.ip }))
  } catch (e) {
    notification.error(t('common.error') + ': ' + e.message)
  } finally {
    isAddingEmployee.value = false
    notification.remove(notifyId)
  }
}

async function handleUpdateMachineEmployee(payload) {
  if (!payload?.employeeId) return

  isUpdatingMachineEmployee.value = true
  const notifyId = notification.info(t('device.machine_employee.updating_notice', { id: payload.employeeId, ip: props.ip }), 0)
  try {
    await store.updateEmployee(payload.employeeId, {
      name: payload.name?.trim() || '',
      role: payload.role,
      photoBase64: payload.photoBase64 || '',
      password: payload.password || '',
    })
    isEditMachineEmployeeOpen.value = false
    editingMachineEmployee.value = null
    notification.success(t('device.machine_employee.update_success', { id: payload.employeeId, ip: props.ip }))
  } catch (e) {
    notification.error(t('common.error') + ': ' + e.message)
  } finally {
    isUpdatingMachineEmployee.value = false
    notification.remove(notifyId)
  }
}

function machineRoleLabel(role) {
  if (role === 'super_admin') return t('device.roles.super_admin')
  if (role === 'admin') return t('device.roles.admin')
  return t('device.roles.employee')
}

</script>

<style scoped>
.filter-bar { display: flex; gap: 16px; flex-wrap: wrap; padding: 16px 20px; margin-bottom: 16px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.summary-row { margin-bottom: 12px; }
.count-badge { background: rgba(99,102,241,0.1); border: 1px solid var(--primary); color: #a5b4fc; padding: 4px 14px; border-radius: 20px; font-size: 0.85rem; }
.btn-add-employee {
  font-size: 0;
}
.btn-add-employee svg {
  flex: 0 0 auto;
}
.btn-add-employee .btn-label {
  font-size: 0.95rem;
}
</style>
