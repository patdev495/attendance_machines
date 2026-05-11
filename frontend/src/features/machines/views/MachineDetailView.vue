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
        <button class="btn btn-ghost" @click="handleSyncTime" style="border-color:#10b981; color:#10b981;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {{ $t('device.sync_time') }}
        </button>
        <button class="btn btn-ghost" @click="handleBulkSyncFinger" style="border-color:#fbbf24; color:#fbbf24;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ $t('biometric.sync_all') }}
        </button>
        <a :href="store.filteredExportUrl" class="btn btn-ghost" style="border-color:#2dd4bf; color:#2dd4bf; text-decoration:none;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ $t('biometric.export_fingerprints') }}
        </a>
        <button class="btn btn-primary" @click="store.loadMachineEmployees(ip)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.08-7.49"/></svg>
          {{ $t('device.refresh') }}
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
      <div class="filter-group" style="min-width:180px;">
        <label>{{ $t('attendance.filters.shift') }}</label>
        <select v-model="store.shiftFilter" @change="store.applyFilter()">
          <option value="">{{ $t('employees.all_shifts') }}</option>
          <option value="N">{{ $t('attendance.filters.day_shift') }}</option>
          <option value="D">{{ $t('attendance.filters.night_shift') }}</option>
          <option value="TV">{{ $t('attendance.filters.resigned') }}</option>
          <option value="__none__">{{ $t('employees.none_shift') }}</option>
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
        @change-privilege="handleChangePrivilege"
        @delete="handleDelete" 
        @rename="handleRename"
        @sync-finger="handleSyncFinger"
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

    <FingerprintCloneModal
      :isOpen="isCloneModalOpen"
      :employeeId="selectedIdForClone"
      :sourceIp="ip"
      @close="isCloneModalOpen = false"
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
import EmployeeDetailsModal from '@/features/employees/components/EmployeeDetailsModal.vue'
import FingerprintCloneModal from '../components/FingerprintCloneModal.vue'
import { syncMachineTime } from '../api.js'

const props = defineProps({ ip: { type: String, required: true } })
const store = useMachineStore()
const notification = useNotificationStore()
const { t } = useI18n()

const selectedIds = ref([])
const selectedEmployee = ref(null)
const isDetailsModalOpen = ref(false)

const isCloneModalOpen = ref(false)
const selectedIdForClone = ref('')

onMounted(() => {
  store.loadMachineEmployees(props.ip)
})

async function handleSyncTime() {
  const notifyId = notification.info(t('device.syncing_time'), 0)
  try {
    await syncMachineTime(props.ip)
    notification.success(t('device.sync_time_success'))
  } catch (e) {
    notification.error(t('device.sync_time_failed', { err: e.message }))
  } finally {
    notification.remove(notifyId)
  }
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

async function handleRename(user) {
  const newName = await notification.prompt(t('device.rename_prompt', { id: user.user_id }), t('device.action.rename'), user.name || '')
  if (newName === null || newName === user.name) return
  
  const notifyId = notification.info(t('device.renaming', { name: newName }), 0)
  try {
    await store.renameEmployee(user.user_id, newName)
    notification.success(t('device.rename_success', { id: user.user_id }))
  } catch (e) {
    notification.error(t('device.rename_failed', { err: e.message }))
  } finally {
    notification.remove(notifyId)
    setTimeout(() => notification.clearByType('info'), 500)
  }
}

async function handleSyncFinger(employeeId) {
  const notifyId = notification.info(t('device.syncing_user', { ip: props.ip, id: employeeId }), 0)
  try {
    const res = await store.syncEmployeeFingerprints(employeeId)
    if (res.count > 0) {
      notification.success(t('device.sync_success', { count: res.count, id: employeeId }))
      // Launch Clone Modal
      selectedIdForClone.value = employeeId
      isCloneModalOpen.value = true
    } else {
      notification.warn(t('device.sync_no_data', { ip: props.ip, id: employeeId }))
    }
  } catch (e) {
    notification.error(t('device.sync_failed', { err: e.message }))
  } finally {
    notification.remove(notifyId)
    setTimeout(() => notification.clearByType('info'), 500)
  }
}

async function handleChangePrivilege(user) {
  const isCurrentlyAdmin = user.privilege === 14
  const targetPrivilege = isCurrentlyAdmin ? 0 : 14
  const actionKey = isCurrentlyAdmin ? 'device.action.demote_to_user' : 'device.action.promote_to_admin'
  
  const confirmed = await notification.confirm(
    t('device.privilege_confirm', { id: user.user_id, action: t(actionKey) }),
    t('actions.confirm')
  )
  if (!confirmed) return

  const notifyId = notification.info(t('common.processing'), 0)
  try {
    await store.updatePrivilege(user.user_id, targetPrivilege)
    notification.success(t('common.success'))
  } catch (e) {
    notification.error(t('common.error') + ': ' + e.message)
  } finally {
    notification.remove(notifyId)
  }
}

async function handleBulkSyncFinger() {
  const confirmed = await notification.confirm(
    t('device.bulk_sync_confirm', { ip: props.ip }),
    t('actions.confirm')
  )
  if (!confirmed) return

  const notifyId = notification.info(t('device.bulk_syncing', { ip: props.ip }), 0)
  try {
    const res = await store.bulkSyncFingerprints()
    notification.success(t('device.bulk_sync_success', { count: res.count, ip: props.ip }))
  } catch (e) {
    notification.error(t('device.bulk_sync_failed', { err: e.message }))
  } finally {
    notification.remove(notifyId)
    setTimeout(() => notification.clearByType('info'), 500)
  }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
h2 { font-size: 1.4rem; font-weight: 600; }
.ip-label { color: var(--accent); font-family: monospace; }
.filter-bar { display: flex; gap: 16px; flex-wrap: wrap; padding: 16px 20px; margin-bottom: 16px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.summary-row { margin-bottom: 12px; }
.count-badge { background: rgba(99,102,241,0.1); border: 1px solid var(--primary); color: #a5b4fc; padding: 4px 14px; border-radius: 20px; font-size: 0.85rem; }
</style>
