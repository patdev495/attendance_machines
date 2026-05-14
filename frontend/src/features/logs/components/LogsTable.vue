<template>
  <div class="table-wrap card">
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>{{ $t('attendance.table.loading') }}</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="error-icon"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      {{ error }}
    </div>

    <template v-else>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{{ $t('attendance.table.emp_id') }}</th>
              <th>{{ $t('attendance.table.emp_name') }}</th>
              <th>{{ $t('attendance.table.attendance_time') }}</th>
              <th>Ca làm việc</th>
              <th>{{ $t('attendance.table.machine_ip') }}</th>
            </tr>
          </thead>
          <transition-group name="list" tag="tbody">
            <tr v-if="items.length === 0" key="empty">
              <td colspan="4" class="empty-state">
                <div class="empty-content">
                  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="empty-icon"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/></svg>
                  <p>{{ $t('attendance.table.no_records') }}</p>
                </div>
              </td>
            </tr>
            <tr v-for="row in items" :key="row.id || row.attendance_time" :class="{ 'live-row': row.is_live }">
              <td class="emp-id">
                {{ row.employee_id }}
              </td>
              <td class="emp-name">
                <span v-if="row.emp_name">{{ row.emp_name }}</span>
                <span v-else class="text-muted italic">-</span>
                <span v-if="row.is_live" class="badge-live">LIVE</span>
              </td>
              <td class="time-col">{{ formatDateTime(row.attendance_time) }}</td>
              <td><span class="badge-shift" v-if="row.shift">{{ row.shift }}</span><span v-else class="text-muted italic">-</span></td>
              <td><span class="badge-ip">{{ row.machine_ip }}</span></td>
            </tr>
          </transition-group>
        </table>
      </div>
      
      <div class="pagination-container" v-if="!liveMode">
        <PaginationBar
          :currentPage="currentPage"
          :totalPages="totalPages"
          :totalCount="totalCount"
          @change="emitPageChange"
        />
      </div>
      <div v-else class="live-status-bar">
        <div class="live-indicator">
          <span class="pulse-dot"></span>
          Đang theo dõi trực tiếp...
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'

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
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
.table-wrap { position: relative; min-height: 200px; display: flex; flex-direction: column; }
.table-scroll { overflow-x: auto; flex: 1; }

.emp-name { color: white; display: flex; align-items: center; gap: 8px; }
.italic { font-style: italic; opacity: 0.5; font-size: 0.85rem; }

.badge-live { background: #ef4444; color: white; font-size: 0.65rem; font-weight: 800; padding: 2px 6px; border-radius: 4px; letter-spacing: 0.5px; }
.badge-ip { background: rgba(59, 130, 246, 0.1); color: #60a5fa; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 500; border: 1px solid rgba(59, 130, 246, 0.2); }
.badge-shift { background: rgba(16, 185, 129, 0.1); color: #34d399; padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(16, 185, 129, 0.2); }

/* Live Row and Animations */
.live-row { background: rgba(239, 68, 68, 0.05); animation: highlight 2s ease-out; }

@keyframes highlight {
  from { background: rgba(239, 68, 68, 0.2); }
  to { background: rgba(239, 68, 68, 0.05); }
}

.list-enter-active, .list-leave-active { transition: all 0.5s ease; }
.list-enter-from { opacity: 0; transform: translateX(-30px); }
.list-leave-to { opacity: 0; transform: translateX(30px); }

.live-status-bar { padding: 16px 24px; border-top: 1px solid var(--border); background: rgba(0, 0, 0, 0.2); }
.live-indicator { display: flex; align-items: center; gap: 10px; color: #94a3b8; font-size: 0.9rem; font-weight: 500; }
.pulse-dot { width: 8px; height: 8px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 0 rgba(239, 68, 68, 0.4); animation: dotPulse 1.5s infinite; }

@keyframes dotPulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.loading-overlay { position: absolute; inset: 0; background: rgba(15, 23, 42, 0.7); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 10; border-radius: var(--radius); }
.spinner { width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.1); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 12px; }
@keyframes spin { to { transform: rotate(360deg); } }

.error-state { padding: 40px; text-align: center; color: #f87171; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.error-icon { color: #ef4444; }

.empty-state { padding: 80px 0; }
.empty-content { display: flex; flex-direction: column; align-items: center; color: var(--text-muted); gap: 16px; }
.empty-icon { opacity: 0.3; }

.pagination-container { padding: 20px 24px; border-top: 1px solid var(--border); }
</style>
