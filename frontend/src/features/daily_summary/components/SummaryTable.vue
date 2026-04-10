<template>
  <div class="table-container card glow">
    <div class="table-header">
      <h3 class="table-title">{{ $t('attendance.summary_table') }}</h3>
      <div class="table-actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <div class="scrollable">
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ $t('attendance.table.emp_id') }}</th>
            <th>{{ $t('attendance.table.date') }}</th>
            <th>{{ $t('attendance.table.shift') }}</th>
            <th>{{ $t('attendance.table.first_tap') }}</th>
            <th>{{ $t('attendance.table.last_tap') }}</th>
            <th>{{ $t('attendance.table.work_hours') }}</th>
            <th>{{ $t('attendance.table.status') }}</th>
            <th>{{ $t('attendance.table.note') }}</th>
            <th class="actions-col">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" class="empty-state">
              <div class="loader"></div>
              {{ $t('common.loading') }}
            </td>
          </tr>
          <tr v-else-if="!items || items.length === 0">
            <td colspan="9" class="empty-state">
              {{ $t('common.no_data') }}
            </td>
          </tr>
          <tr v-for="item in items" :key="item.employee_id + item.attendance_date">
            <td class="bold">{{ item.employee_id }}</td>
            <td>{{ formatDate(item.attendance_date) }}</td>
            <td>
              <span class="badge" :class="getShiftClass(item.shift)">
                {{ item.shift }}
              </span>
            </td>
            <td class="time">{{ item.first_tap ? formatTime(item.first_tap) : '-' }}</td>
            <td class="time">{{ item.last_tap ? formatTime(item.last_tap) : '-' }}</td>
            <td class="hours" :class="{ 'warning': item.work_hours < 8 && item.work_hours > 0 }">
              {{ item.work_hours ? item.work_hours.toFixed(2) : '0.00' }}
            </td>
            <td>
              <span class="status-indicator" :class="getStatusClass(item.status)"></span>
              {{ getStatusLabel(item.status) }}
            </td>
            <td class="note">
              <span :class="{ 'error-text': item.note }">{{ (item.note && item.note.toLowerCase().includes('missing') && item.note.toLowerCase().includes('check-in/out')) ? $t('attendance.notes.missing_tap') : (item.note || '-') }}</span>
              <div v-if="item.minutes_late" class="sub-note late">{{ $t('attendance.table.late', { m: item.minutes_late }) }}</div>
              <div v-if="item.minutes_early_leave" class="sub-note early">{{ $t('attendance.table.early', { m: item.minutes_early_leave }) }}</div>
            </td>
            <td class="actions-col">
              <button class="btn-icon" @click="$emit('view-detail', item)">
                <span class="icon">🔍</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="table-footer" v-if="totalCount > 0">
      <PaginationBar 
        :currentPage="page" 
        :totalPages="totalPages" 
        :totalCount="totalCount" 
        @change="$emit('page-change', $event)" 
      />
    </div>
  </div>
</template>

<script setup>
import PaginationBar from '@/components/shared/PaginationBar.vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps({
  items: Array,
  loading: Boolean,
  page: Number,
  size: Number,
  totalCount: Number,
  totalPages: Number
})

defineEmits(['page-change', 'view-detail'])

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('vi-VN')
}

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

const getShiftClass = (shift) => {
  if (shift === 'N') return 'badge-success'
  if (shift === 'D') return 'badge-info'
  if (shift === 'TV') return 'badge-danger'
  return 'badge-secondary'
}

const getStatusLabel = (status) => {
  if (status === 'excel_synced') return t('attendance.filters.status_excel')
  if (status === 'machine_only') return t('attendance.filters.status_machine')
  if (status === 'log_only') return t('attendance.filters.status_log')
  return status || t('attendance.filters.active')
}

const getStatusClass = (status) => {
  if (status === 'excel_synced') return 'status-excel'
  if (status === 'machine_only') return 'status-machine'
  if (status === 'log_only') return 'status-log'
  return 'status-default'
}
</script>

<style scoped>
.table-container {
  display: flex;
  flex-direction: column;
}

.table-header {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-light);
}

.table-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-main);
}

.scrollable {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background: var(--bg-main);
  text-align: left;
  padding: 14px 16px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--border-light);
}

td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
  font-size: 0.95rem;
  color: var(--text-main);
}

tr:hover td {
  background: var(--bg-hover);
}

.bold { font-weight: 600; }
.time { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; }
.hours { font-weight: 700; color: var(--primary); }
.hours.warning { color: var(--warning); }
.error-text { color: var(--danger); font-size: 0.85rem; font-weight: 500; }

.sub-note {
  font-size: 0.75rem;
  margin-top: 4px;
}
.sub-note.late { color: var(--warning); }
.sub-note.early { color: var(--secondary); }

.badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
}

.status-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-indicator.status-excel { background: var(--success); }
.status-indicator.status-machine { background: var(--primary); }
.status-indicator.status-log { background: var(--secondary); }
.status-indicator.status-default { background: var(--text-muted); }

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--text-muted);
}

.table-footer {
  padding: 0px 24px;
  border-top: 1px solid var(--border-light);
}

.loader {
  border: 3px solid var(--bg-hover);
  border-top: 3px solid var(--primary);
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
