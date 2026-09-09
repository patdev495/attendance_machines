<template>
  <div class="table-wrap card glow">
    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner-sm"></div>
      <p>{{ $t('attendance.table.loading') }}</p>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <AlertCircle :size="24" class="error-icon" />
      <span>{{ error }}</span>
    </div>

    <!-- Table Content -->
    <template v-else>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 140px;">{{ $t('attendance.table.emp_id') }}</th>
              <th>{{ $t('attendance.table.emp_name') }}</th>
              <th style="width: 180px;">{{ $t('attendance.table.attendance_time') }}</th>
              <th style="width: 150px;">{{ $t('attendance.table.shift') || 'Ca làm việc' }}</th>
              <th style="width: 160px;">{{ $t('attendance.table.machine_ip') }}</th>
            </tr>
          </thead>
          <transition-group name="row-slide" tag="tbody">
            <tr v-if="items.length === 0" key="empty">
              <td colspan="5" class="empty-state">
                <Inbox :size="42" class="empty-icon" />
                <p>{{ $t('attendance.table.no_records') }}</p>
              </td>
            </tr>
            <tr 
              v-for="row in items" 
              :key="row.id || row.attendance_time" 
              :class="['log-row', { 'live-row': row.is_live }]"
            >
              <td class="emp-id-cell">
                <span class="id-badge">{{ row.employee_id }}</span>
              </td>
              <td class="emp-name-cell">
                <span v-if="row.emp_name" class="emp-name-text">{{ row.emp_name }}</span>
                <span v-else class="text-muted italic">—</span>
                <span v-if="row.is_live" class="badge-live">
                  <span class="live-dot-ping"></span>
                  LIVE
                </span>
              </td>
              <td class="time-cell">
                <span class="mono-time">{{ formatDateTime(row.attendance_time) }}</span>
              </td>
              <td>
                <span class="badge-shift" v-if="row.shift">{{ row.shift }}</span>
                <span v-else class="text-muted italic">—</span>
              </td>
              <td>
                <span class="badge-ip">{{ row.machine_ip }}</span>
              </td>
            </tr>
          </transition-group>
        </table>
      </div>
      
      <!-- Footer: Pagination or Live Tracker -->
      <div class="table-footer-bar" v-if="!liveMode">
        <PaginationBar
          :currentPage="currentPage"
          :totalPages="totalPages"
          :totalCount="totalCount"
          @change="emitPageChange"
        />
      </div>
      <div v-else class="live-status-bar">
        <div class="live-indicator">
          <span class="pulse-dot-red"></span>
          <span class="live-status-text">Đang nhận dữ liệu trực tiếp từ các máy chấm công...</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import { AlertCircle, Inbox } from 'lucide-vue-next'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  currentPage: { type: Number, default: 1 },
  totalPages: { type: Number, default: 1 },
  totalCount: { type: Number, default: 0 },
  liveMode: { type: Boolean, default: false }
})

const emits = defineEmits(['page-change'])

function emitPageChange(page) {
  emits('page-change', page)
}

function formatDateTime(dt) {
  if (!dt) return '—'
  return dt.replace('T', ' ').substring(0, 19)
}
</script>

<style scoped>
.table-wrap {
  position: relative;
  min-height: 240px;
  display: flex;
  flex-direction: column;
}

.loading-overlay {
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
}

.error-state {
  padding: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--rose);
}

.emp-id-cell .id-badge {
  font-family: var(--font-mono);
  font-weight: 700;
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
}

.emp-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.emp-name-text {
  font-weight: 600;
  color: #ffffff;
}

.time-cell .mono-time {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  color: #cbd5e1;
}

.live-row {
  background: rgba(244, 63, 94, 0.08) !important;
  border-left: 3px solid var(--rose);
}

.live-dot-ping {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f43f5e;
  display: inline-block;
  animation: livePulse 1.5s infinite;
}

.table-footer-bar {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
}

.live-status-bar {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(244, 63, 94, 0.04);
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.live-status-text {
  font-size: 0.84rem;
  font-weight: 600;
  color: #fb7185;
  letter-spacing: 0.02em;
}

/* Row animations */
.row-slide-enter-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.row-slide-enter-from {
  opacity: 0;
  transform: translateY(-12px);
  background: rgba(99, 102, 241, 0.2);
}
</style>
