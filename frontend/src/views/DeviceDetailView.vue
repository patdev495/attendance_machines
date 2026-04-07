<template>
  <div class="anim-up">
    <!-- Page Header -->
    <div class="page-header">
      <div style="display:flex; align-items:center; gap:16px;">
        <router-link to="/devices" class="btn btn-ghost">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          All Devices
        </router-link>
        <h2>Machine: <span class="ip-label">{{ ip }}</span></h2>
      </div>
      <button class="btn btn-primary" @click="device.loadDeviceEmployees(ip)">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.08-7.49"/></svg>
        Refresh
      </button>
    </div>

    <!-- Filters -->
    <div class="filter-bar card">
      <div class="filter-group" style="flex:1;">
        <label>Search (ID / Name)</label>
        <input v-model="device.searchTerm" placeholder="Type to search..." @input="device.applyFilter()" />
      </div>
      <div class="filter-group" style="min-width:180px;">
        <label>Status</label>
        <select v-model="device.statusFilter" @change="device.applyFilter()">
          <option value="">All Status</option>
          <option value="Active">Active</option>
          <option value="TV">Resigned (TV)</option>
          <option value="Unknown">Unknown (Not in DB)</option>
        </select>
      </div>
    </div>

    <!-- Count summary -->
    <div class="summary-row" v-if="!device.employeesLoading">
      <span class="count-badge">{{ device.filteredEmployees.length }} / {{ device.allEmployees.length }} employees</span>
    </div>

    <LoadingSpinner v-if="device.employeesLoading" message="Connecting to machine..." />
    <div v-else-if="device.employeeError" class="empty-state card" style="color:#f87171;">{{ device.employeeError }}</div>
    <template v-else>
      <DeviceEmployeeTable :employees="device.pagedEmployees" @delete="handleDelete" />
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
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import DeviceEmployeeTable from '@/components/device/DeviceEmployeeTable.vue'

const props = defineProps({ ip: { type: String, required: true } })
const device = useDeviceStore()
const notification = useNotificationStore()

onMounted(() => {
  device.loadDeviceEmployees(props.ip)
})

async function handleDelete(employeeId) {
  const confirmed = await notification.confirm(
    `Delete employee ${employeeId} from machine ${props.ip}?\nThis cannot be undone.`,
    'Confirm Deletion'
  )
  if (!confirmed) return
  try {
    await device.deleteEmployee(employeeId)
    notification.success(`Successfully deleted employee ${employeeId}`)
  } catch (e) {
    notification.error('Error: ' + e.message)
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
