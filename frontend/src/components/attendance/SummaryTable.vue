<template>
  <div class="table-wrap card">
    <LoadingSpinner v-if="store.loading" :message="$t('attendance.table.loading')" />
    <div v-else-if="store.error" class="empty-state" style="color:#f87171;">{{ store.error }}</div>
    <template v-else>
      <table>
        <thead>
          <tr>
            <th>{{ $t('attendance.table.emp_id') }}</th>
            <th>{{ $t('attendance.table.date') }}</th>
            <th>{{ $t('attendance.table.check_in') }}</th>
            <th>{{ $t('attendance.table.check_out') }}</th>
            <th>{{ $t('attendance.table.work_hours') }}</th>
            <th>{{ $t('attendance.table.shift') }}</th>
            <th>{{ $t('attendance.table.status') }}</th>
            <th>{{ $t('attendance.table.note') }}</th>
            <th style="text-align:right">{{ $t('attendance.table.action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.items.length === 0">
            <td colspan="9" class="empty-state">{{ $t('attendance.table.no_records') }}</td>
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
                <span v-if="row.minutes_late > 0" style="color:#fbbf24;">{{ $t('attendance.table.late', { m: row.minutes_late }) }}</span>
                <span v-if="row.minutes_early_leave > 0" style="color:#fb923c;">{{ $t('attendance.table.early', { m: row.minutes_early_leave }) }}</span>
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
import { useI18n } from 'vue-i18n'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'

const store = useAttendanceStore()
const syncStore = useSyncStore()
const notification = useNotificationStore()
const { t } = useI18n()

function formatTime(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(11, 16)
}

async function confirmDelete(employeeId) {
  const confirmed = await notification.confirm(
    t('actions.delete_confirm', { id: employeeId }),
    t('actions.confirm')
  )
  if (!confirmed) return
  syncStore.startDeleteEmployee(employeeId)
}
</script>

<style scoped>
.table-wrap { overflow-x: auto; }
</style>
