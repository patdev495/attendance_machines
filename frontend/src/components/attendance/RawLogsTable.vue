<template>
  <div class="table-container">
    <div class="table-actions">
      <h3 class="view-title">{{ $t('attendance.raw_logs') }}</h3>
      <button class="btn btn-primary btn-sm" :disabled="syncStore.syncRunning" @click="syncStore.startSync()">
        <span v-if="syncStore.syncRunning" class="spin-icon">⟳</span>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        {{ syncStore.syncRunning ? $t('sync.syncing') + '...' : $t('sync.machines') }}
      </button>
    </div>

    <div class="table-wrap card">
      <LoadingSpinner v-if="store.loading" :message="$t('attendance.table.loading')" />
      <div v-else-if="store.error" class="empty-state" style="color:#f87171;">{{ store.error }}</div>
      <template v-else>
        <table>
          <thead>
            <tr>
              <th>{{ $t('attendance.table.emp_id') }}</th>
              <th>{{ $t('attendance.table.attendance_time') }}</th>
              <th>{{ $t('attendance.table.machine_ip') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.items.length === 0">
              <td colspan="3" class="empty-state">{{ $t('attendance.table.no_records') }}</td>
            </tr>
            <tr v-for="row in store.items" :key="row.id">
              <td style="font-weight:600; color:#fff;">{{ row.employee_id }}</td>
              <td>{{ formatDateTime(row.attendance_time) }}</td>
              <td><span class="badge-ip">{{ row.machine_ip }}</span></td>
            </tr>
          </tbody>
        </table>
        <PaginationBar
          :currentPage="store.currentPage"
          :totalPages="store.totalPages"
          :totalCount="store.totalCount"
          @change="store.loadData"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { useAttendanceStore } from '@/stores/attendance.js'
import { useSyncStore } from '@/stores/sync.js'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'

const store = useAttendanceStore()
const syncStore = useSyncStore()

function formatDateTime(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
.table-container { display: flex; flex-direction: column; gap: 16px; }
.table-actions { display: flex; justify-content: space-between; align-items: center; }
.view-title { margin: 0; font-size: 1.1rem; color: white; font-weight: 600; }
.table-wrap { overflow-x: auto; }
.spin-icon { display: inline-block; animation: spin 1s linear infinite; margin-right: 8px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
