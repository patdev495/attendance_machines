<template>
  <div class="table-container card glow">
    <div class="table-header">
      <div class="header-left-title">
        <h3 class="table-title">{{ $t('attendance.summary_table') }}</h3>
      </div>
      <div class="table-actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <div class="scrollable">
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 120px;">{{ $t('attendance.table.emp_id') }}</th>
            <th>{{ $t('attendance.table.emp_name') }}</th>
            <th style="width: 110px;">{{ $t('attendance.table.date') }}</th>
            <th style="width: 90px;">{{ $t('attendance.table.first_tap') }}</th>
            <th style="width: 90px;">{{ $t('attendance.table.last_tap') }}</th>
            <th style="width: 90px;">{{ $t('attendance.table.lunch_out') }}</th>
            <th style="width: 90px;">{{ $t('attendance.table.lunch_in') }}</th>
            <th style="width: 90px;" class="text-center">{{ $t('attendance.table.lunch_duration') }}</th>
            <th style="width: 120px;">{{ $t('attendance.table.lunch_status') }}</th>
            <th style="width: 100px;">{{ $t('attendance.table.work_hours') }}</th>
            <th style="width: 90px;">{{ $t('attendance.table.hours_ot') }}</th>
            <th class="text-center" style="width: 50px;" :title="'Phép năm (P)'">P</th>
            <th class="text-center" style="width: 50px;" :title="'Nghỉ bù/chế độ (R)'">R</th>
            <th class="text-center" style="width: 50px;" :title="'Nghỉ không lương (O)'">O</th>
            <th>{{ $t('attendance.table.note') }}</th>
            <th class="actions-col" style="width: 70px;">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <!-- Loading State -->
          <tr v-if="loading">
            <td colspan="16" class="empty-state">
              <div class="spinner-sm"></div>
              <span>{{ $t('common.loading') }}</span>
            </td>
          </tr>

          <!-- Empty State -->
          <tr v-else-if="!items || items.length === 0">
            <td colspan="16" class="empty-state">
              <Inbox :size="36" class="empty-icon" />
              <span>{{ $t('common.no_data') }}</span>
            </td>
          </tr>

          <!-- Data Rows -->
          <tr v-for="item in items" :key="item.employee_id + item.attendance_date" class="summary-row-item">
            <td class="emp-id-cell">
              <span class="id-badge">{{ item.employee_id }}</span>
            </td>
            <td class="emp-name-cell">
              <span class="name-text">{{ item.emp_name || '—' }}</span>
            </td>
            <td class="date-cell">
              <span class="mono-text">{{ formatDate(item.attendance_date) }}</span>
            </td>
            <td class="time-cell">
              <span class="mono-text in-time" v-if="item.first_tap">{{ formatTime(item.first_tap) }}</span>
              <span class="dimmed" v-else>—</span>
            </td>
            <td class="time-cell">
              <span class="mono-text out-time" v-if="item.last_tap">{{ formatTime(item.last_tap) }}</span>
              <span class="dimmed" v-else>—</span>
            </td>
            <td class="time-cell">
              <span class="mono-text" v-if="item.lunch_out">{{ formatTime(item.lunch_out) }}</span>
              <span class="dimmed" v-else>—</span>
            </td>
            <td class="time-cell">
              <span class="mono-text" v-if="item.lunch_in">{{ formatTime(item.lunch_in) }}</span>
              <span class="dimmed" v-else>—</span>
            </td>
            <td class="text-center">
              <span v-if="item.lunch_duration_minutes !== null && item.lunch_duration_minutes !== undefined" class="lunch-pill">
                {{ item.lunch_duration_minutes }}p
              </span>
              <span class="dimmed" v-else>—</span>
            </td>
            <td>
              <span class="badge" :class="getLunchStatusClass(item.lunch_status)">
                {{ getLunchStatusLabel(item.lunch_status) }}
              </span>
            </td>
            <td>
              <span class="hours-badge" :class="{ 'warning-hours': typeof item.work_hours === 'number' && item.work_hours < 8 && item.work_hours > 0 }">
                {{ formatHours(item.work_hours) }}h
              </span>
            </td>
            <td>
              <span v-if="item.hours_ot && item.hours_ot > 0" class="ot-badge-glow">
                +{{ formatHours(item.hours_ot) }}h
              </span>
              <span v-else class="dimmed">—</span>
            </td>
            <td class="text-center font-bold text-success" :class="{ 'dimmed': !item.hours_p }">
              {{ item.hours_p ? item.hours_p.toFixed(1) : '—' }}
            </td>
            <td class="text-center font-bold text-warning" :class="{ 'dimmed': !item.hours_r }">
              {{ item.hours_r ? item.hours_r.toFixed(1) : '—' }}
            </td>
            <td class="text-center font-bold text-info" :class="{ 'dimmed': !item.hours_o }">
              {{ item.hours_o ? item.hours_o.toFixed(1) : '—' }}
            </td>
            <td class="note-cell">
              <span :class="{ 'error-text': item.note }">{{ translateNote(item.note) }}</span>
              <div v-if="item.minutes_late" class="sub-note late">
                {{ $t('attendance.table.late', { m: item.minutes_late }) }}
              </div>
              <div v-if="item.minutes_early_leave" class="sub-note early">
                {{ $t('attendance.table.early', { m: item.minutes_early_leave }) }}
              </div>
            </td>
            <td class="actions-col">
              <button class="btn-icon" :title="$t('common.info') || 'Xem chi tiết'" @click="$emit('view-detail', item)">
                <Eye :size="15" />
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
import { Eye, Inbox } from 'lucide-vue-next'
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
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('vi-VN', { month: '2-digit', day: '2-digit' })
}

const formatTime = (timeStr) => {
  if (!timeStr) return '—'
  return timeStr.slice(11, 16)
}

const formatHours = (hours) => {
  if (hours === undefined || hours === null) return '—'
  return typeof hours === 'number' ? hours.toFixed(1) : hours
}

const getLunchStatusClass = (status) => {
  if (status === 'normal') return 'badge-excel'
  if (status === 'overdue') return 'badge-status-tv'
  if (status === 'missing_in' || status === 'missing_out') return 'badge-warning'
  return 'badge-log'
}

const getLunchStatusLabel = (status) => {
  if (!status) return '—'
  return t(`attendance.lunch_status.${status}`) || status
}

const translateNote = (note) => {
  if (!note) return ''
  return note
}
</script>

<style scoped>
.table-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border);
}

.table-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: white;
  margin: 0;
}

.id-badge {
  font-family: var(--font-mono);
  font-weight: 700;
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 7px;
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 0.84rem;
}

.name-text {
  font-weight: 600;
  color: #f1f5f9;
}

.mono-text {
  font-family: var(--font-mono);
  font-size: 0.85rem;
}
.in-time { color: #34d399; }
.out-time { color: #38bdf8; }

.lunch-pill {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  background: rgba(245, 158, 11, 0.12);
  color: #fcd34d;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid rgba(245, 158, 11, 0.25);
}

.hours-badge {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 0.86rem;
  color: #cbd5e1;
}

.warning-hours {
  color: #fb923c;
  font-weight: 700;
}

.ot-badge-glow {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.84rem;
  color: #34d399;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
}

.dimmed {
  opacity: 0.35;
}

.text-success { color: #34d399; }
.text-warning { color: #fbbf24; }
.text-info { color: #38bdf8; }

.sub-note {
  font-size: 0.74rem;
  font-weight: 600;
  margin-top: 2px;
}
.sub-note.late { color: #f87171; }
.sub-note.early { color: #fb923c; }

.error-text {
  color: #f87171;
  font-weight: 600;
}

.table-footer {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
}
</style>
