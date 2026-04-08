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
        <button class="btn btn-ghost" @click="handleBulkSyncFinger" style="border-color:#fbbf24; color:#fbbf24;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Sync All Fingerprints
        </button>
        <a :href="device.filteredExportUrl" class="btn btn-ghost" style="border-color:#2dd4bf; color:#2dd4bf; text-decoration:none;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export Excel
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
        <input v-model="device.searchTerm" placeholder="Type to search..." @input="device.applyFilter()" />
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
import { onMounted } from 'vue'
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

onMounted(() => {
  device.loadDeviceEmployees(props.ip)
})

async function handleDelete(employeeId) {
  const confirmed = await notification.confirm(
    `Bạn có chắc chắn muốn xóa nhân viên ${employeeId} khỏi máy ${props.ip} KHÔNG?\n(Lưu ý: Hành động này CHỈ xóa dữ liệu trên máy này, không ảnh hưởng đến các máy khác).`,
    t('actions.confirm')
  )
  if (!confirmed) return
  try {
    await device.deleteEmployee(employeeId)
    notification.success(`Successfully deleted employee ${employeeId}`)
  } catch (e) {
    notification.error('Error: ' + e.message)
  }
}

async function handleRename(user) {
  const newName = prompt(`Enter new name for employee ${user.user_id}:`, user.name || '')
  if (newName === null || newName === user.name) return
  
  const notifyId = notification.info(`Updating name to "${newName}" on all machines...`, 0)
  try {
    await device.renameEmployee(user.user_id, newName)
    notification.success(`Name updated successfully for ${user.user_id}`)
  } catch (e) {
    notification.error('Rename failed: ' + e.message)
  } finally {
    notification.remove(notifyId)
    // Extra safety: make sure all info types are clear after success/error
    setTimeout(() => notification.clearByType('info'), 500)
  }
}

async function handleSyncFinger(employeeId) {
  const notifyId = notification.info(`Retrieving fingerprints from machine ${props.ip}...`, 0)
  try {
    const res = await device.syncEmployeeFingerprints(employeeId)
    if (res.count > 0) {
      notification.success(`Successfully downloaded ${res.count} fingerprint(s) for ${employeeId}`)
    } else {
      notification.warn(`No fingerprint found on machine ${props.ip} for ${employeeId}`)
    }
  } catch (e) {
    notification.error('Sync failed: ' + e.message)
  } finally {
    notification.remove(notifyId)
    setTimeout(() => notification.clearByType('info'), 500)
  }
}

async function handleBulkSyncFinger() {
  const confirmed = await notification.confirm(
    `Are you sure you want to download ALL fingerprints from machine ${props.ip}? This may take a while.`,
    t('actions.confirm')
  )
  if (!confirmed) return

  const notifyId = notification.info(`Bulk retrieving ALL fingerprints from machine ${props.ip}...`, 0)
  try {
    const res = await device.bulkSyncFingerprints()
    notification.success(`Successfully downloaded ${res.count} fingerprint(s) from machine ${props.ip}`)
  } catch (e) {
    notification.error('Bulk sync failed: ' + e.message)
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
