<template>
  <div class="table-container">
    <div class="table-actions">
      <h3 class="view-title">{{ $t('attendance.daily_summary') }}</h3>
      
      <div class="action-buttons">
        <!-- Export mode -->
        <label for="exportModeSelect" style="display:none">Export Mode</label>
        <select id="exportModeSelect" name="view_mode" v-model="exportMode" class="select-sm">
          <option value="time">{{ $t('export.time') }}</option>
          <option value="hours">{{ $t('export.hours') }}</option>
          <option value="both">{{ $t('export.both') }}</option>
        </select>

        <!-- Export Excel -->
        <button v-if="!exportStore.isRunning" class="btn btn-ghost btn-sm" @click="handleExport">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ $t('export.btn') }}
        </button>
        <button v-else class="btn btn-ghost btn-sm" @click="exportStore.cancel" style="border-color:#f87171; color:#f87171;">
          <span class="spin-icon">⟳</span>
          {{ $t('export.cancel') }}({{ exportStore.progress }}%)
        </button>

        <!-- Sync Excel -->
        <button class="btn btn-ghost btn-sm" :disabled="syncStore.excelSyncRunning" @click="triggerExcelPicker" style="border-color:#2dd4bf; color:#2dd4bf;">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          {{ syncStore.excelSyncRunning ? `${$t('sync.syncing')} (${syncStore.excelSyncProgress}%)` : $t('sync.excel') }}
        </button>
        <input ref="excelInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onExcelSelected" />
      </div>
    </div>

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
                <button class="btn-fingerprint" :title="$t('biometric.view_coverage')" @click="openCoverage(row.employee_id)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12c0-2.8 2.2-5 5-5s5 2.2 5 5-2.2 5-5 5-5-2.2-5-5Z"/><circle cx="7" cy="12" r=".5"/><path d="M12 12c0-2.8 2.2-5 5-5s5 2.2 5 5-2.2 5-5 5-5-2.2-5-5Z"/><circle cx="17" cy="12" r=".5"/><path d="M22 12c0-2.8-2.2-5-5-5s-5 2.2-5 5 2.2 5 5 5 5-2.2 5-5Z"/></svg>
                </button>
                <button class="btn-delete" :title="$t('actions.delete_all_confirm')" @click="confirmDelete(row.employee_id)">
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
    
    <BiometricCoverageModal 
      :isOpen="showCoverageModal" 
      :employeeId="selectedEmployeeId"
      @close="closeCoverage"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAttendanceStore } from '@/stores/attendance.js'
import { useSyncStore } from '@/stores/sync.js'
import { useExportStore } from '@/stores/export.js'
import { useNotificationStore } from '@/stores/notification.js'
import { useI18n } from 'vue-i18n'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PaginationBar from '@/components/shared/PaginationBar.vue'
import BiometricCoverageModal from '@/components/employees/BiometricCoverageModal.vue'

const store = useAttendanceStore()
const syncStore = useSyncStore()
const exportStore = useExportStore()
const notification = useNotificationStore()
const { t } = useI18n()

const showCoverageModal = ref(false)
const selectedEmployeeId = ref('')
const exportMode = ref('time')
const excelInput = ref(null)

function formatTime(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(11, 16)
}

function openCoverage(id) {
  selectedEmployeeId.value = id
  showCoverageModal.value = true
}

function closeCoverage() {
  showCoverageModal.value = false
  selectedEmployeeId.value = ''
}

async function confirmDelete(employeeId) {
  const confirmed = await notification.confirm(
    t('actions.delete_global_warn', { id: employeeId }),
    t('actions.confirm')
  )
  if (!confirmed) return
  syncStore.startDeleteEmployee(employeeId)
}

function handleExport() {
  const { startDate, endDate } = store.filters
  if (!startDate || !endDate) { 
    notification.warn('Please select a date range first.')
    return 
  }
  exportStore.start(startDate, endDate, exportMode.value)
}

function triggerExcelPicker() {
  excelInput.value.value = ''
  excelInput.value.click()
}

async function onExcelSelected(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    await syncStore.syncExcelFile(file)
    store.loadData(1)
  } catch (err) {
    console.error('Excel sync failed', err)
  }
}
</script>

<style scoped>
.table-container { display: flex; flex-direction: column; gap: 16px; }
.table-actions { display: flex; justify-content: space-between; align-items: center; }
.view-title { margin: 0; font-size: 1.1rem; color: white; font-weight: 600; }
.action-buttons { display: flex; gap: 10px; align-items: center; }
.select-sm { padding: 4px 8px; font-size: 0.85rem; border-radius: 6px; }
.table-wrap { overflow-x: auto; }
.spin-icon { display: inline-block; animation: spin 1s linear infinite; margin-right: 8px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
