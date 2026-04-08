<template>
  <div class="anim-up">
    <!-- Page Header -->
    <div class="page-header">
      <div style="display:flex; align-items:center; gap:16px;">
        <router-link to="/devices" class="btn btn-ghost">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          {{ $t('device.all_devices') }}
        </router-link>
        <h2>{{ $t('device.machine') }} <span class="ip-label">{{ ip }}</span></h2>
      </div>
      <div style="display:flex; gap:10px;">
        <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="handleBulkDelete" style="background:#ef4444; color:#fff; border:none; display:flex; align-items:center; gap:6px;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          Delete ({{ selectedIds.length }})
        </button>
        <button class="btn btn-ghost" @click="handleBulkSyncFinger" style="border-color:#fbbf24; color:#fbbf24;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ $t('biometric.sync_all') }}
        </button>
        <a :href="device.filteredExportUrl" class="btn btn-ghost" style="border-color:#2dd4bf; color:#2dd4bf; text-decoration:none;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ $t('biometric.export_fingerprints') }}
        </a>
        <button class="btn btn-primary" @click="device.loadDeviceEmployees(ip)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.08-7.49"/></svg>
          {{ $t('device.refresh') }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="filter-bar card">
      <div class="filter-group" style="flex:1;">
        <label>{{ $t('attendance.filters.search') }}</label>
        <input v-model="device.searchTerm" :placeholder="$t('attendance.filters.search') + '...'" @input="device.applyFilter()" />
      </div>
      <div class="filter-group" style="min-width:180px;">
        <label>{{ $t('attendance.filters.status') }}</label>
        <select v-model="device.statusFilter" @change="device.applyFilter()">
          <option value="">{{ $t('attendance.filters.all_status') }}</option>
          <option value="Active">{{ $t('attendance.filters.active') }}</option>
          <option value="TV">{{ $t('attendance.filters.resigned') }}</option>
          <option value="Unknown">{{ $t('attendance.filters.unknown') }}</option>
        </select>
      </div>
    </div>

    <!-- Count summary -->
    <div class="summary-row" v-if="!device.employeesLoading">
      <span class="count-badge">{{ $t('device.employee_count', { filtered: device.filteredEmployees.length, total: device.allEmployees.length }) }}</span>
    </div>

    <LoadingSpinner v-if="device.employeesLoading" :message="$t('device.connecting')" />
    <div v-else-if="device.employeeError" class="empty-state card" style="color:#f87171;">{{ device.employeeError }}</div>
    <template v-else>
      <DeviceEmployeeTable 
        :employees="device.pagedEmployees" 
        @delete="handleDelete" 
        @rename="handleRename"
        @sync-finger="handleSyncFinger"
        @selection-change="ids => selectedIds = ids"
      />
      <PaginationBar
        :currentPage="device.empPage"
        :totalPages="device.empTotalPages"
        :totalCount="device.filteredEmployees.length"
        @change="p => device.empPage = p"
      />
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useDeviceStore } from '@/stores/device.js'
import { useNotificationStore } from '@/stores/notification.js'
import { useI18n } from 'vue-i18n'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import DeviceEmployeeTable from '@/components/device/DeviceEmployeeTable.vue'

const props = defineProps({ ip: { type: String, required: true } })
const device = useDeviceStore()
const notification = useNotificationStore()
const { t } = useI18n()

const selectedIds = ref([])

onMounted(() => {
  device.loadDeviceEmployees(props.ip)
})

async function handleDelete(employeeId) {
  const confirmed = await notification.confirm(
    t('actions.delete_single_warn', { id: employeeId, ip: props.ip }),
    t('actions.confirm')
  )
  if (!confirmed) return
  try {
    await device.deleteEmployee(employeeId)
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
    const res = await device.bulkDeleteEmployees(selectedIds.value)
    const actualDeleted = res?.count !== undefined ? res.count : selectedIds.value.length
    notification.success(t('device.bulk_delete_success', { count: actualDeleted }))
    selectedIds.value = []
  } catch (e) {
    notification.error(`Xóa thất bại: ${e.message}`)
  } finally {
    notification.remove(notifyId)
  }
}

async function handleRename(user) {
  const newName = prompt(t('device.rename_prompt', { id: user.user_id }), user.name || '')
  if (newName === null || newName === user.name) return
  
  const notifyId = notification.info(t('device.renaming', { name: newName }), 0)
  try {
    await device.renameEmployee(user.user_id, newName)
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
    const res = await device.syncEmployeeFingerprints(employeeId)
    if (res.count > 0) {
      notification.success(t('device.sync_success', { count: res.count, id: employeeId }))
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

async function handleBulkSyncFinger() {
  const confirmed = await notification.confirm(
    t('device.bulk_sync_confirm', { ip: props.ip }),
    t('actions.confirm')
  )
  if (!confirmed) return

  const notifyId = notification.info(t('device.bulk_syncing', { ip: props.ip }), 0)
  try {
    const res = await device.bulkSyncFingerprints()
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
