<template>
  <header class="site-header" v-if="route.name !== 'meal'">
    <div class="header-left">
      <a href="#" class="site-title" @click.prevent="goHome">{{ $t('nav.title') }}</a>
      <p class="tagline">{{ $t('layout.tagline') }}</p>
    </div>
    <nav class="header-actions">
      <!-- Language Switcher -->
      <select v-model="currentLang" @change="changeLanguage" id="langSwitcher" name="lang">
        <option value="vi">🇻🇳 Tiếng Việt</option>
        <option value="en">🇬🇧 English</option>
        <option value="zh">🇨🇳 中文</option>
      </select>
      <button class="settings-trigger" @click="openMachineSettings" title="Cấu hình máy">
        ⚙️
      </button>
    </nav>
  </header>

  <!-- Machine Settings Modal (Global) -->
  <teleport to="body">
    <div v-if="showMachineSettings" class="modal-overlay-global" @click.self="showMachineSettings = false">
      <div class="modal-content-global machine-settings-modal">
        <div class="modal-header-global">
          <h3>⚙️ {{ $t('meal.machine_settings') || 'Cấu hình máy chấm công' }}</h3>
          <button class="close-btn-global" @click="showMachineSettings = false">&times;</button>
        </div>
        <div class="modal-body-global">
          <div class="machine-config-list">
            <div v-for="m in allMachineConfigs" :key="m.ip" class="machine-config-item">
              <div class="m-info-col">
                <div class="m-ip">
                  {{ getMachineStatusIcon(m.ip) }} {{ m.ip }}
                </div>
                <div v-if="machineStatus[m.ip] && machineStatus[m.ip].last_real_event" class="m-last-activity">
                  {{ $t('meal.last_event') }} {{ formatLastEventTime(machineStatus[m.ip].last_real_event) }}
                </div>
                <div v-else-if="machineStatus[m.ip] && m.is_live" class="m-last-activity no-activity">
                  {{ $t('meal.no_event') }}
                </div>
              </div>
                <div class="m-toggles">
                  <label class="toggle-switch">
                    <input type="checkbox" v-model="m.is_live" @change="toggleMachineConfig(m)">
                    <span class="slider"></span>
                    <span class="label">Live</span>
                  </label>
                  <label class="toggle-switch">
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
                    🔄 {{ reconnectingIps.includes(m.ip) ? '...' : $t('meal.reconnect_btn') }}
                  </button>
                  <button
                    class="btn btn-delete-machine"
                    @click="handleDeleteMachine(m.ip)"
                    :disabled="deletingIps.includes(m.ip)"
                    :title="$t('meal.delete_machine') || 'Xóa máy'"
                  >
                    🗑️
                  </button>
                </div>
            </div>
          </div>
          <div class="add-machine-section">
            <div class="add-machine-title">➕ {{ $t('meal.add_machine') || 'Thêm Máy Mới' }}</div>
            <div class="add-machine-row">
              <input
                v-model="newMachineIp"
                class="add-machine-input"
                type="text"
                :placeholder="$t('meal.ip_placeholder') || 'VD: 192.168.1.100'"
                @keyup.enter="handleAddMachine"
              />
              <button
                class="btn btn-add-machine"
                @click="handleAddMachine"
                :disabled="addingMachine"
              >
                {{ addingMachine ? '...' : ($t('meal.add_btn') || 'Thêm') }}
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

  <!-- Status banners (Intelligent slimmest version) -->
  <div v-if="syncStore.syncRunning" class="status-banner sync-banner">{{ syncStore.syncMessage }}</div>
  <div v-if="syncStore.deleteRunning" class="status-banner delete-banner">{{ syncStore.deleteMessage }}</div>
  
  <!-- Export Progress Banner -->
  <div v-if="exportStore.isRunning || exportStore.error" class="status-banner" :class="exportStore.error ? 'delete-banner' : 'sync-banner'">
    <div v-if="exportStore.error">{{ exportStore.error }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: exportStore.progress + '%' }"></div>
      </div>
      <span>{{ $t('export.progress_label') || 'Export' }}: {{ exportStore.currentStep }} ({{ exportStore.progress }}%)</span>
    </div>
  </div>

  <!-- Excel Sync Progress Banner -->
  <div v-if="syncStore.excelSyncRunning || syncStore.excelSyncError" class="status-banner" :class="syncStore.excelSyncError ? 'delete-banner' : 'sync-banner'" style="background: rgba(45, 212, 191, 0.1); border-bottom-color: #2dd4bf;">
    <div v-if="syncStore.excelSyncError" style="color: #f87171;">{{ syncStore.excelSyncError }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: syncStore.excelSyncProgress + '%', backgroundColor: '#2dd4bf' }"></div>
      </div>
      <span style="color: #2dd4bf;">{{ $t('sync.progress_label') || 'Sync' }}: {{ syncStore.excelSyncStep }} ({{ syncStore.excelSyncProgress }}%)</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted, watch } from 'vue'
import { getLiveStatus, reconnectMachine } from '@/features/machines/api.js'
import { useSyncStore } from '@/stores/sync.js'
import { useExportStore } from '@/stores/export.js'
import { useAttendanceStore } from '@/stores/attendance.js'
import { useI18n } from 'vue-i18n'
import { setLanguage } from '@/i18n/index.js'
import { useRouter, useRoute } from 'vue-router'
import { mealApi } from '@/features/meal_tracking/api.js'

const syncStore = useSyncStore()
const exportStore = useExportStore()
const attendanceStore = useAttendanceStore()
const router = useRouter()
const route = useRoute()

const { locale, t } = useI18n()
const currentLang = ref(locale.value)

function changeLanguage() {
  setLanguage(currentLang.value)
}

function goHome() {
  router.push('/logs')
}

const showMachineSettings = ref(false)
const allMachineConfigs = ref([])
const machineStatus = ref({})
const reconnectingIps = ref([])
const deletingIps = ref([])
const newMachineIp = ref('')
const addingMachine = ref(false)
let statusInterval = null

async function fetchLiveStatus() {
  try {
    const data = await getLiveStatus()
    machineStatus.value = data || {}
  } catch (e) {
    console.error('Error fetching machine status:', e)
  }
}

function getMachineStatusIcon(ip) {
  const m = machineStatus.value[ip]
  if (!m) return '⚪'
  const status = typeof m === 'object' ? m.status : m
  if (status === 'connected') return '🟢'
  if (status === 'stuck') return '🟡'
  if (status === 'disconnected') return '🔴'
  return '⚪'
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

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})

async function openMachineSettings() {
  console.log('Opening machine settings...');
  try {
    const { data } = await mealApi.getAllMachineConfigs()
    if (!data || data.length === 0) {
       alert('Không tìm thấy danh sách máy hoặc tệp cấu hình trống.');
    }
    allMachineConfigs.value = data
    showMachineSettings.value = true
    
    // Fetch live status immediately
    fetchLiveStatus()
    // Start interval
    if (statusInterval) clearInterval(statusInterval)
    statusInterval = setInterval(fetchLiveStatus, 10000)
  } catch (e) {
    console.error('Error fetching machine configs:', e)
    alert('Không thể kết nối đến máy chủ: ' + (e.response?.data?.detail || e.message));
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
  // Basic IP validation
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
  padding: 16px clamp(16px, 3vw, 40px);
  border-bottom: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(10px);
}
.site-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: white;
  text-decoration: none;
  letter-spacing: -0.3px;
  cursor: pointer;
  transition: color 0.2s;
}
.site-title:hover { color: var(--primary); }

.tagline { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; }
.header-actions { display: flex; gap: 10px; align-items: center; }

select { 
  padding: 6px 10px; 
  font-size: 0.85rem; 
  background: #1e293b; 
  color: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  outline: none;
}
option {
  background: #1e293b;
  color: white;
}

.status-banner {
  padding: 8px 24px;
  font-size: 0.85rem;
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

.export-banner-content { display: flex; align-items: center; justify-content: center; gap: 12px; max-width: 600px; margin: 0 auto; }
.progress-container { flex: 1; height: 6px; background: rgba(0,0,0,0.2); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--primary); transition: width 0.3s ease; }

/* Global Machine Settings Styles */
.settings-trigger {
  background: none;
  border: 1px solid var(--border);
  color: white;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.settings-trigger:hover {
  background: rgba(255,255,255,0.05);
  border-color: var(--primary);
}

.modal-overlay-global {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content-global {
  width: 680px;
  max-width: 95vw;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header-global {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header-global h3 { margin: 0; font-size: 1.1rem; color: white; }

.close-btn-global {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
}

.machine-config-list {
  padding: 20px;
  max-height: 50vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.machine-config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}

.m-ip { font-family: monospace; color: #60a5fa; font-weight: 600; }
.m-toggles { display: flex; gap: 15px; align-items: center; }

.m-info-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.m-last-activity {
  font-size: 0.75rem;
  color: #94a3b8;
  text-align: left;
}

.m-last-activity.no-activity {
  color: #f59e0b;
  opacity: 0.8;
}

.btn-reconnect-small {
  padding: 4px 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #ef4444;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
}

.btn-reconnect-small:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.25);
  color: white;
  border-color: rgba(239, 68, 68, 0.4);
}

.btn-reconnect-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Toggle Switch Styling */
.toggle-switch { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.toggle-switch input { display: none; }
.toggle-switch .slider { position: relative; width: 34px; height: 18px; background: #334155; border-radius: 18px; transition: 0.3s; }
.toggle-switch .slider:before { content: ""; position: absolute; width: 12px; height: 12px; left: 3px; bottom: 3px; background: #94a3b8; border-radius: 50%; transition: 0.3s; }
.toggle-switch input:checked + .slider { background: #10b981; }
.toggle-switch input:checked + .slider:before { transform: translateX(16px); background: white; }
.toggle-switch .label { font-size: 0.8rem; color: #94a3b8; }
.toggle-switch input:checked ~ .label { color: #10b981; }

.modal-note { padding: 12px 20px; font-size: 0.75rem; color: #64748b; font-style: italic; border-top: 1px solid rgba(255, 255, 255, 0.05); }

/* Add Machine Section */
.add-machine-section {
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(99, 102, 241, 0.04);
}
.add-machine-title {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-bottom: 8px;
  font-weight: 600;
}
.add-machine-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.add-machine-input {
  flex: 1;
  padding: 7px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: white;
  font-size: 0.85rem;
  font-family: monospace;
  outline: none;
  transition: border-color 0.2s;
}
.add-machine-input:focus {
  border-color: var(--primary);
  background: rgba(99, 102, 241, 0.08);
}
.add-machine-input::placeholder { color: #475569; }
.btn-add-machine {
  padding: 7px 16px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #818cf8;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.btn-add-machine:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.3);
  color: white;
  border-color: rgba(99, 102, 241, 0.5);
}
.btn-add-machine:disabled { opacity: 0.5; cursor: not-allowed; }

/* Delete Machine Button */
.btn-delete-machine {
  padding: 4px 8px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
  color: #ef4444;
  font-size: 0.85rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  line-height: 1;
}
.btn-delete-machine:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
}
.btn-delete-machine:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
