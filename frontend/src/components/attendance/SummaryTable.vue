<template>
  <div class="table-wrap card">
    <LoadingSpinner v-if="store.loading" message="Loading summary..." />
    <div v-else-if="store.error" class="empty-state" style="color:#f87171;">{{ store.error }}</div>
    <template v-else>
      <table>
        <thead>
          <tr>
            <th>Employee ID</th>
            <th>Date</th>
            <th>Check In</th>
            <th>Check Out</th>
            <th>Work Hours</th>
            <th>Shift</th>
            <th>Status</th>
            <th>Note</th>
            <th style="text-align:right">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.items.length === 0">
            <td colspan="9" class="empty-state">No records found.</td>
          </tr>
          <tr v-for="row in store.items" :key="`${row.employee_id}-${row.attendance_date}`">
            <td style="font-weight:600; color:#fff;">{{ row.employee_id }}</td>
            <td>{{ row.attendance_date }}</td>
            <td>{{ formatTime(row.first_tap) }}</td>
            <td>{{ formatTime(row.last_tap) }}</td>
            <td>
              <span v-if="row.work_hours > 0" class="badge-hours">{{ row.work_hours }}h</span>
              <span v-else class="note-missing">-</span>
            </td>
            <td>
              <span class="badge-shift" :class="{ night: row.shift === 'D' }">{{ row.shift }}</span>
            </td>
            <td>
              <span v-if="row.status === 'TV'" class="badge-status-tv">TV</span>
              <span v-else class="badge-status-active">{{ row.status }}</span>
            </td>
            <td>
              <span v-if="row.note" class="note-missing">{{ row.note }}</span>
              <span v-else style="color: var(--text-muted); font-size:0.83rem;">
                <span v-if="row.minutes_late > 0" style="color:#fbbf24;">⚠ +{{ row.minutes_late }}m late</span>
                <span v-if="row.minutes_early_leave > 0" style="color:#fb923c;"> ⚠ -{{ row.minutes_early_leave }}m early out</span>
              </span>
            </td>
            <td style="text-align:right;">
              <button class="btn-delete" title="Delete from all machines" @click="confirmDelete(row.employee_id)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
              </button>
            </td>
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
</template>

<script setup>
import { useAttendanceStore } from '@/stores/attendance.js'
import { useSyncStore } from '@/stores/sync.js'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'

const store = useAttendanceStore()
const syncStore = useSyncStore()

function formatTime(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(11, 16)
}

function confirmDelete(employeeId) {
  if (!confirm(`Delete employee ${employeeId} from all machines?\nThis cannot be undone.`)) return
  syncStore.startDeleteEmployee(employeeId)
}
</script>

<style scoped>
.table-wrap { overflow-x: auto; }
</style>
