<template>
  <div class="table-wrap card">
    <LoadingSpinner v-if="store.loading" message="Loading data..." />
    <div v-else-if="store.error" class="empty-state" style="color:#f87171;">{{ store.error }}</div>
    <template v-else>
      <table>
        <thead>
          <tr>
            <th>Employee ID</th>
            <th>Attendance Time</th>
            <th>Machine IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.items.length === 0">
            <td colspan="3" class="empty-state">No records found.</td>
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
</template>

<script setup>
import { useAttendanceStore } from '@/stores/attendance.js'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'

const store = useAttendanceStore()

function formatDateTime(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
.table-wrap { overflow-x: auto; }
</style>
