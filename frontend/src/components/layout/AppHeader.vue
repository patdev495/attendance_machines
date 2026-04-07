<template>
  <header class="site-header">
    <div class="header-left">
      <router-link to="/" class="site-title">Nienyi Attendance</router-link>
      <p class="tagline">Time Attendance Management System</p>
    </div>
    <nav class="header-actions">
      <!-- Export mode -->
      <select id="exportMode" v-model="exportMode">
        <option value="time">Export: Time (In/Out)</option>
        <option value="hours">Export: Hours (Work/OT)</option>
        <option value="both">Export: Time + Hours</option>
      </select>

      <!-- Export Excel -->
      <button v-if="!exportStore.isRunning" class="btn btn-ghost" id="exportExcelBtn" @click="handleExport">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Export Excel
      </button>
      <button v-else class="btn btn-ghost" @click="exportStore.cancel" style="border-color:#f87171; color:#f87171;">
        <span class="spin-icon">⟳</span>
        Cancel ({{ exportStore.progress }}%)
      </button>

      <!-- Sync Excel -->
      <button class="btn btn-ghost" id="excelSyncBtn" :disabled="syncStore.syncRunning" @click="triggerExcelPicker" style="border-color:#2dd4bf; color:#2dd4bf;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        {{ syncingExcel ? 'Syncing...' : 'Sync Excel' }}
      </button>
      <input ref="excelInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onExcelSelected" />

      <!-- Device Status → navigate to /devices -->
      <router-link to="/devices" class="btn btn-ghost" style="border-color:#8b5cf6; color:#a78bfa;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        Device Status
      </router-link>

      <!-- Sync Machines -->
      <button class="btn btn-primary" id="syncBtn" :disabled="syncStore.syncRunning" @click="syncStore.startSync()">
        <span v-if="syncStore.syncRunning" class="spin-icon">⟳</span>
        {{ syncStore.syncRunning ? 'Syncing...' : 'Sync Machines' }}
      </button>
    </nav>
  </header>

  <!-- Status banners -->
  <div v-if="syncStore.syncRunning" class="status-banner sync-banner">{{ syncStore.syncMessage }}</div>
  <div v-if="syncStore.deleteRunning" class="status-banner delete-banner">{{ syncStore.deleteMessage }}</div>
  
  <!-- Export Progress Banner -->
  <div v-if="exportStore.isRunning || exportStore.error" class="status-banner" :class="exportStore.error ? 'delete-banner' : 'sync-banner'">
    <div v-if="exportStore.error">{{ exportStore.error }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: exportStore.progress + '%' }"></div>
      </div>
      <span>{{ exportStore.currentStep }} ({{ exportStore.progress }}%)</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSyncStore } from '@/stores/sync.js'
import { useAttendanceStore } from '@/stores/attendance.js'
import { useExportStore } from '@/stores/export.js'

const syncStore = useSyncStore()
const attendanceStore = useAttendanceStore()
const exportStore = useExportStore()
const exportMode = ref('time')
const excelInput = ref(null)
const syncingExcel = ref(false)

function handleExport() {
  const { startDate, endDate } = attendanceStore.filters
  if (!startDate || !endDate) { alert('Please select a date range first.'); return }
  exportStore.start(startDate, endDate, exportMode.value)
}

function triggerExcelPicker() {
  excelInput.value.value = ''
  excelInput.value.click()
}

async function onExcelSelected(e) {
  const file = e.target.files[0]
  if (!file) return
  syncingExcel.value = true
  try {
    const result = await syncStore.syncExcelFile(file)
    alert(result.message)
    attendanceStore.loadData(1)
  } catch (err) {
    alert('Sync failed: ' + err.message)
  } finally {
    syncingExcel.value = false
  }
}
</script>

<style scoped>
.site-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 28px clamp(16px, 3vw, 40px) 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 100;
}
.site-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: white;
  text-decoration: none;
  transition: color 0.2s;
  letter-spacing: -0.3px;
}
.site-title:hover { color: var(--accent); }
.tagline { font-size: 0.83rem; color: var(--text-muted); margin-top: 2px; }
.header-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
select { width: auto; padding: 10px 14px; }

.status-banner {
  padding: 10px 24px;
  font-size: 0.9rem;
  text-align: center;
}
.sync-banner {
  background: rgba(99,102,241,0.1);
  border-bottom: 1px solid var(--primary);
  color: var(--accent);
}
.delete-banner {
  background: rgba(239,68,68,0.08);
  border-bottom: 1px solid var(--danger);
  color: #f87171;
}
.spin-icon { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.export-banner-content { display: flex; align-items: center; justify-content: center; gap: 12px; max-width: 600px; margin: 0 auto; }
.progress-container { flex: 1; height: 8px; background: rgba(0,0,0,0.2); border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--primary); transition: width 0.3s ease; }
</style>
