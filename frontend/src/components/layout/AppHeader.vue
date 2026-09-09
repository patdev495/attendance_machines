<template>
  <header class="site-header" v-if="route.name !== 'meal'">
    <div class="header-left">
      <div class="breadcrumb-trail">
        <span class="system-chip">NIENYI CLOUD</span>
        <span class="trail-sep">/</span>
        <h2 class="current-view-title">{{ pageTitle }}</h2>
      </div>
      <p class="tagline">{{ $t('layout.tagline') }}</p>
    </div>

    <nav class="header-actions">
      <!-- Live Time Display -->
      <div class="header-clock" :title="'Thời gian hệ thống'">
        <Clock :size="14" class="clock-icon" />
        <span>{{ headerClock }}</span>
      </div>

      <!-- Language Switcher -->
      <div class="lang-selector-box">
        <Globe :size="14" class="globe-icon" />
        <select v-model="currentLang" @change="changeLanguage" id="langSwitcher" name="lang" class="header-select">
          <option value="vi">Tiếng Việt</option>
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
      </div>

      <!-- Machine Settings Trigger -->
      <button class="settings-trigger" @click="openMachineSettings" :title="$t('meal.machine_settings') || 'Cấu hình máy chấm công'">
        <SlidersHorizontal :size="16" />
        <span class="settings-label">{{ $t('nav.machines') }}</span>
        <span class="device-count-badge" v-if="onlineDeviceCount > 0">{{ onlineDeviceCount }}</span>
      </button>
    </nav>
  </header>

  <!-- Machine Settings Modal (Global) -->
  <teleport to="body">
    <div v-if="showMachineSettings" class="modal-overlay-global" @click.self="showMachineSettings = false">
      <div class="modal-content-global machine-settings-modal card">
        <div class="modal-header-global">
          <div class="modal-title-with-icon">
            <div class="modal-icon-badge">
              <SlidersHorizontal :size="18" />
            </div>
            <h3>{{ $t('meal.machine_settings') || 'Cấu hình máy chấm công' }}</h3>
          </div>
          <button class="close-btn-global" @click="showMachineSettings = false">
            <X :size="18" />
          </button>
        </div>

        <div class="modal-body-global">
          <div class="machine-config-list">
            <div v-for="m in allMachineConfigs" :key="m.ip" class="machine-config-item">
              <div class="m-info-col">
                <div class="m-ip">
                  <span :class="['m-status-dot', getMachineStatusClass(m.ip)]"></span>
                  <span class="ip-text">{{ m.ip }}</span>
                </div>
                <div v-if="machineStatus[m.ip] && machineStatus[m.ip].last_real_event" class="m-last-activity">
                  {{ $t('meal.last_event') }} {{ formatLastEventTime(machineStatus[m.ip].last_real_event) }}
                </div>
                <div v-else-if="machineStatus[m.ip] && m.is_live" class="m-last-activity no-activity">
                  {{ $t('meal.no_event') }}
                </div>
              </div>

              <div class="m-toggles">
                <label class="toggle-switch" :title="$t('meal.toggle_live') || 'Live Monitor'">
                  <input type="checkbox" v-model="m.is_live" @change="toggleMachineConfig(m)">
                  <span class="slider"></span>
                  <span class="label">Live</span>
                </label>
                <label class="toggle-switch" :title="$t('meal.toggle_canteen') || 'Canteen'">
                  <input type="checkbox" v-model="m.is_canteen" @change="toggleMachineConfig(m)">
                  <span class="slider"></span>
                  <span class="label">{{ $t('meal.toggle_canteen') || 'Canteen' }}</span>
                </label>
                <button 
                  v-if="m.is_live"
                  class="btn btn-reconnect-small" 
                  @click="handleReconnect(m.ip)"
                  :disabled="reconnectingIps.includes(m.ip)"
                  :title="$t('meal.reconnect_title') + ' ' + m.ip"
                >
                  <RotateCw :size="13" :class="{ 'spin-anim': reconnectingIps.includes(m.ip) }" />
                  <span>{{ reconnectingIps.includes(m.ip) ? '...' : $t('meal.reconnect_btn') }}</span>
                </button>
                <button
                  class="btn-icon-danger"
                  @click="handleDeleteMachine(m.ip)"
                  :disabled="deletingIps.includes(m.ip)"
                  :title="$t('meal.delete_machine') || 'Xóa máy'"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
          </div>

          <div class="add-machine-section">
            <div class="add-machine-title">
              <Plus :size="15" />
              <span>{{ $t('meal.add_machine') || 'Thêm Máy Mới' }}</span>
            </div>
            <div class="add-machine-row">
              <input
                v-model="newMachineIp"
                class="add-machine-input"
                type="text"
                :placeholder="$t('meal.ip_placeholder') || 'VD: 192.168.1.100'"
                @keyup.enter="handleAddMachine"
              />
              <button
                class="btn btn-primary btn-add-machine"
                @click="handleAddMachine"
                :disabled="addingMachine"
              >
                <Plus :size="14" v-if="!addingMachine" />
                <span class="spinner-sm" v-else></span>
                <span>{{ addingMachine ? '...' : ($t('meal.add_btn') || 'Thêm') }}</span>
              </button>
            </div>
          </div>

          <div class="modal-note">
            {{ $t('meal.config_note') || '* Thay đổi sẽ được hệ thống cập nhật sau tối đa 10 giây.' }}
          </div>
        </div>
      </div>
    </div>
  </teleport>

  <!-- Status banners -->
  <div v-if="syncStore.syncRunning" class="status-banner sync-banner anim-up">
    <span class="spinner-sm"></span>
    <span>{{ syncStore.syncMessage }}</span>
  </div>
  <div v-if="syncStore.deleteRunning" class="status-banner delete-banner anim-up">
    <span class="spinner-sm"></span>
    <span>{{ syncStore.deleteMessage }}</span>
  </div>
  
  <!-- Export Progress Banner -->
  <div v-if="exportStore.isRunning || exportStore.error" class="status-banner anim-up" :class="exportStore.error ? 'delete-banner' : 'sync-banner'">
    <div v-if="exportStore.error">{{ exportStore.error }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: exportStore.progress + '%' }"></div>
      </div>
      <span>{{ $t('export.progress_label') || 'Export' }}: {{ exportStore.currentStep }} ({{ exportStore.progress }}%)</span>
    </div>
  </div>

  <!-- Excel Sync Progress Banner -->
  <div v-if="syncStore.excelSyncRunning || syncStore.excelSyncError" class="status-banner anim-up" :class="syncStore.excelSyncError ? 'delete-banner' : 'sync-banner'" style="background: rgba(6, 182, 212, 0.12); border-color: rgba(6, 182, 212, 0.35);">
    <div v-if="syncStore.excelSyncError" style="color: #fb7185;">{{ syncStore.excelSyncError }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: syncStore.excelSyncProgress + '%', backgroundColor: '#06b6d4' }"></div>
      </div>
      <span style="color: #22d3ee;">{{ $t('sync.progress_label') || 'Sync' }}: {{ syncStore.excelSyncStep }} ({{ syncStore.excelSyncProgress }}%)</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { getLiveStatus, reconnectMachine } from '@/features/machines/api.js'
import { useSyncStore } from '@/stores/sync.js'
import { useExportStore } from '@/stores/export.js'
import { useAttendanceStore } from '@/stores/attendance.js'
import { useI18n } from 'vue-i18n'
import { setLanguage } from '@/i18n/index.js'
import { useRouter, useRoute } from 'vue-router'
import { mealApi } from '@/features/meal_tracking/api.js'
import { 
  SlidersHorizontal, 
  Globe, 
  Clock, 
  X, 
  RotateCw, 
  Trash2, 
  Plus 
} from 'lucide-vue-next'

const syncStore = useSyncStore()
const exportStore = useExportStore()
const attendanceStore = useAttendanceStore()
const router = useRouter()
const route = useRoute()

const { locale, t } = useI18n()
const currentLang = ref(locale.value)

const headerClock = ref('')
let clockTimer = null

function updateClock() {
  const now = new Date()
  headerClock.value = now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (statusInterval) clearInterval(statusInterval)
})

const pageTitle = computed(() => {
  if (route.name === 'logs') return t('attendance.raw_logs')
  if (route.name === 'summary') return t('attendance.daily_summary')
  if (route.path.startsWith('/machines')) return t('nav.machines')
  if (route.path.startsWith('/employees')) return t('nav.employees')
  if (route.path.startsWith('/shifts')) return t('nav.shifts')
  if (route.name === 'meal') return t('meal.kiosk_title')
  return t('nav.title')
})

function changeLanguage() {
  setLanguage(currentLang.value)
}

const showMachineSettings = ref(false)
const allMachineConfigs = ref([])
const machineStatus = ref({})
const reconnectingIps = ref([])
const deletingIps = ref([])
const newMachineIp = ref('')
const addingMachine = ref(false)
let statusInterval = null

const onlineDeviceCount = computed(() => {
  return Object.values(machineStatus.value).filter(m => {
    const status = typeof m === 'object' ? m.status : m
    return status === 'connected'
  }).length
})

async function fetchLiveStatus() {
  try {
    const data = await getLiveStatus()
    machineStatus.value = data || {}
  } catch (e) {
    console.error('Error fetching machine status:', e)
  }
}

function getMachineStatusClass(ip) {
  const m = machineStatus.value[ip]
  if (!m) return 'dot-offline'
  const status = typeof m === 'object' ? m.status : m
  if (status === 'connected') return 'dot-online'
  if (status === 'stuck') return 'dot-warning'
  if (status === 'disconnected') return 'dot-offline'
  return 'dot-offline'
}

async function handleReconnect(ip) {
  reconnectingIps.value.push(ip)
  try {
    const res = await reconnectMachine(ip)
    console.log(`Reconnected machine ${ip}:`, res.message)
    await fetchLiveStatus()
  } catch (e) {
    console.error(`Failed to reconnect machine ${ip}:`, e)
    alert(`Không thể kết nối lại máy ${ip}: ${e.message}`)
  } finally {
    reconnectingIps.value = reconnectingIps.value.filter(item => item !== ip)
  }
}

function formatLastEventTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp * 1000)
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

watch(showMachineSettings, (newVal) => {
  if (!newVal && statusInterval) {
    clearInterval(statusInterval)
    statusInterval = null
  }
})

async function openMachineSettings() {
  try {
    const { data } = await mealApi.getAllMachineConfigs()
    allMachineConfigs.value = data || []
    showMachineSettings.value = true
    fetchLiveStatus()
    if (statusInterval) clearInterval(statusInterval)
    statusInterval = setInterval(fetchLiveStatus, 10000)
  } catch (e) {
    console.error('Error fetching machine configs:', e)
    alert('Không thể kết nối đến máy chủ: ' + (e.response?.data?.detail || e.message))
  }
}

async function toggleMachineConfig(machine) {
  try {
    await mealApi.updateMachineConfig(machine.ip, {
      is_live: machine.is_live,
      is_canteen: machine.is_canteen
    })
  } catch (e) {
    console.error('Error updating machine config:', e)
    alert('Lỗi khi cập nhật cấu hình máy')
    openMachineSettings()
  }
}

async function handleAddMachine() {
  const ip = newMachineIp.value.trim()
  if (!ip) return
  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipRegex.test(ip)) {
    alert(t('meal.ip_invalid') || 'Định dạng IP không hợp lệ')
    return
  }
  addingMachine.value = true
  try {
    await mealApi.updateMachineConfig(ip, { is_live: false, is_canteen: false })
    newMachineIp.value = ''
    await openMachineSettings()
  } catch (e) {
    console.error('Error adding machine:', e)
    alert('Lỗi khi thêm máy: ' + (e.response?.data?.detail || e.message))
  } finally {
    addingMachine.value = false
  }
}

async function handleDeleteMachine(ip) {
  const msg = t('meal.delete_machine_confirm') || `Bạn có chắc chắn muốn xóa máy ${ip} không?`
  if (!confirm(msg)) return
  deletingIps.value.push(ip)
  try {
    await mealApi.deleteMachineConfig(ip)
    await openMachineSettings()
  } catch (e) {
    console.error('Error deleting machine:', e)
    alert('Lỗi khi xóa máy: ' + (e.response?.data?.detail || e.message))
  } finally {
    deletingIps.value = deletingIps.value.filter(i => i !== ip)
  }
}
</script>

<style scoped>
.site-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px clamp(16px, 2.5vw, 36px);
  border-bottom: 1px solid var(--border);
  background: rgba(10, 16, 30, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  flex-direction: column;
}

.breadcrumb-trail {
  display: flex;
  align-items: center;
  gap: 8px;
}

.system-chip {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.trail-sep {
  color: var(--text-dim);
  font-size: 0.85rem;
}

.current-view-title {
  font-size: 1.18rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.tagline {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.header-clock {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 0.82rem;
  color: var(--cyan);
  letter-spacing: 0.05em;
}

.clock-icon {
  color: var(--cyan);
  opacity: 0.8;
}

.lang-selector-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 0 10px;
  transition: border-color 0.2s;
}
.lang-selector-box:hover {
  border-color: rgba(255, 255, 255, 0.2);
}

.globe-icon {
  color: var(--text-muted);
}

.header-select {
  padding: 7px 4px;
  font-size: 0.84rem;
  font-weight: 600;
  background: transparent;
  color: #f1f5f9;
  border: none;
  outline: none;
  cursor: pointer;
  width: auto;
}
.header-select option {
  background: #0f172a;
  color: white;
}

.settings-trigger {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(6, 182, 212, 0.12) 100%);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: #c7d2fe;
  padding: 7px 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  align-items: center;
  gap: 8px;
}
.settings-trigger:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.28) 0%, rgba(6, 182, 212, 0.22) 100%);
  border-color: var(--primary);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
}

.device-count-badge {
  background: #10b981;
  color: #070b14;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 10px;
  font-family: var(--font-mono);
}

/* Modal Global Styles */
.modal-overlay-global {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-content-global {
  width: 100%;
  max-width: 620px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: #0f172a;
  border: 1px solid var(--border-highlight);
  border-radius: var(--radius-xl);
  box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 30px rgba(99, 102, 241, 0.15);
  overflow: hidden;
  animation: fadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.modal-header-global {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}

.modal-title-with-icon {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-icon-badge {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--primary-light);
  color: #a5b4fc;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.modal-header-global h3 {
  font-size: 1.15rem;
  font-weight: 700;
  color: white;
  margin: 0;
}

.close-btn-global {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.close-btn-global:hover {
  background: var(--rose-light);
  color: var(--rose);
  border-color: var(--rose);
}

.modal-body-global {
  padding: 20px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.machine-config-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.machine-config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  transition: all 0.2s;
}
.machine-config-item:hover {
  border-color: var(--border-highlight);
  background: rgba(255, 255, 255, 0.05);
}

.m-info-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.m-ip {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ip-text {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  font-weight: 600;
  color: #fff;
}

.m-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot-online { background: #10b981; box-shadow: 0 0 8px #10b981; }
.dot-warning { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
.dot-offline { background: #f43f5e; }

.m-last-activity {
  font-size: 0.74rem;
  color: var(--text-dim);
}

.m-toggles {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Modern Toggle Switch */
.toggle-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}
.toggle-switch input { display: none; }
.toggle-switch .slider {
  width: 36px;
  height: 20px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  position: relative;
  transition: background 0.3s;
  border: 1px solid var(--border);
}
.toggle-switch .slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: white;
  border-radius: 50%;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.toggle-switch input:checked + .slider {
  background: var(--primary);
  border-color: var(--primary);
}
.toggle-switch input:checked + .slider::after {
  transform: translateX(16px);
}
.toggle-switch .label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: none;
  margin-bottom: 0;
}

.btn-reconnect-small {
  padding: 4px 10px;
  font-size: 0.78rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: #e2e8f0;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-reconnect-small:hover {
  background: var(--cyan-light);
  border-color: var(--cyan);
  color: #fff;
}

.btn-icon-danger {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: rgba(244, 63, 94, 0.1);
  border: 1px solid rgba(244, 63, 94, 0.25);
  color: #fb7185;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-icon-danger:hover {
  background: var(--rose);
  color: #fff;
}

.spin-anim {
  animation: spin 0.8s linear infinite;
}

.add-machine-section {
  padding: 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.add-machine-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--cyan);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.add-machine-row {
  display: flex;
  gap: 10px;
}

.add-machine-input {
  flex: 1;
}

.btn-add-machine {
  padding: 8px 18px;
}

.modal-note {
  font-size: 0.74rem;
  color: var(--text-dim);
  font-style: italic;
}

.export-banner-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  max-width: 600px;
  margin: 0 auto;
}

.progress-container {
  flex: 1;
  height: 6px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #22d3ee);
  border-radius: 4px;
  transition: width 0.3s ease;
}

@media (max-width: 768px) {
  .site-header { padding: 10px 14px; }
  .header-clock { display: none; }
  .settings-label { display: none; }
}
</style>
