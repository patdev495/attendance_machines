<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="show" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <div class="header-left">
                <div class="icon-pulse" style="background: rgba(99, 102, 241, 0.2); border-color: rgba(99, 102, 241, 0.3);">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                </div>
                <div class="title-stack">
                  <h2 class="title-main">Đẩy Vân Tay Hàng Loạt</h2>
                  <p class="subtitle">Tải file danh sách và chọn máy đích để đẩy vân tay</p>
                </div>
              </div>
              <button class="btn-close-circle" @click="close">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <div class="modal-body custom-scrollbar">
              <!-- Step 1: File Upload -->
              <div class="section-card">
                <label class="section-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  1. Tải lên file TXT
                </label>
                <div class="file-drop-zone" :class="{ 'has-file': employeeIds.length > 0 }">
                  <input type="file" ref="fileInput" accept=".txt" @change="handleFileUpload" hidden :disabled="isProcessing" />
                  <div class="drop-zone-content" @click="!isProcessing && $refs.fileInput.click()">
                    <div v-if="employeeIds.length > 0" class="file-info">
                      <span class="file-name" style="color: #10b981;">Đã nạp {{ employeeIds.length }} mã nhân viên</span>
                    </div>
                    <div v-else class="placeholder">
                      <span>Kéo thả file .txt vào đây hoặc click để chọn<br><small>(Mỗi dòng 1 mã nhân viên)</small></span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 2: Target Machines -->
              <div class="section-card mt-6">
                <label class="section-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
                  2. Chọn Máy Đích
                </label>
                <div class="machine-grid">
                  <div v-if="machines.length === 0" class="text-sm text-gray-500 italic">No machines available.</div>
                  <div v-for="ip in machines" :key="ip" class="machine-checkbox" :class="{ 'active': selectedMachines.includes(ip), 'disabled': isProcessing }" @click="!isProcessing && toggleMachine(ip)">
                    <div class="checkbox-box">
                      <svg v-if="selectedMachines.includes(ip)" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </div>
                    <span class="ip-text">{{ ip }}</span>
                  </div>
                </div>
              </div>

              <!-- Step 2.5: Preview Section -->
              <div class="section-card mt-6" v-if="employeeIds.length > 0 && selectedMachines.length > 0 && !isProcessing && machineProgress.total === 0">
                <button 
                  class="btn-start" 
                  style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; border-radius: 12px; padding: 0.75rem;"
                  @click="previewData" 
                  :disabled="isPreviewing"
                >
                  <div v-if="isPreviewing" class="spinner-sm" style="border-top-color: #818cf8;"></div>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                  {{ isPreviewing ? 'Đang kiểm tra...' : 'Kiểm Tra Dữ Liệu Trước Khi Đẩy' }}
                </button>
                
                <div v-if="previewResult" class="results-table mt-2" style="background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                  <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem; color: #e2e8f0;">
                    <div style="display: flex; justify-content: space-between;">
                      <span style="color: #94a3b8;">Tổng mã NV tải lên:</span>
                      <strong style="color: #fff;">{{ previewResult.total_input_ids }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                      <span style="color: #94a3b8;">Nhân viên hợp lệ trong hệ thống:</span>
                      <strong style="color: #10b981;">{{ previewResult.employees_found_in_db }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                      <span style="color: #94a3b8;">Số nhân viên CÓ vân tay:</span>
                      <strong style="color: #818cf8;">{{ previewResult.employees_with_fingerprints }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.5rem; margin-top: 0.25rem;">
                      <span style="color: #94a3b8; font-weight: bold;">Tổng số vân tay sẽ đẩy xuống máy:</span>
                      <strong style="color: #fbbf24; font-size: 1rem;">{{ previewResult.total_fingerprints }}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 3: Progress & Results -->
              <div v-if="isProcessing || machineProgress.total > 0" class="progress-section mt-6">
                <div class="progress-header">
                  <span class="progress-label">Tổng tiến độ: {{ empProgress.processed }}/{{ empProgress.total }} vân tay</span>
                  <span class="progress-percent">{{ empProgressPercent }}%</span>
                </div>
                <div class="progress-bar-container">
                  <div class="progress-bar-fill" :style="{ width: empProgressPercent + '%' }"></div>
                </div>
                <div class="progress-footer" style="margin-top: 0.75rem; display: flex; flex-direction: column; gap: 0.3rem;">
                  <span style="color: #94a3b8; font-size: 0.8rem;">Máy hoàn tất: {{ machineProgress.processed }}/{{ machineProgress.total }}</span>
                  <span v-if="activeIps.length > 0" style="color: #818cf8; font-size: 0.8rem;">⚡ Đang xử lý: {{ activeIps.join(', ') }}</span>
                </div>
              </div>
              
              <div v-if="Object.keys(results).length > 0" class="results-section mt-6">
                <div class="divider"></div>
                <table class="results-table">
                  <thead>
                    <tr>
                      <th>IP Máy</th>
                      <th class="text-right">Trạng Thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(msg, ip) in results" :key="ip">
                      <td>{{ ip }}</td>
                      <td class="text-right">
                        <span class="status-badge" :class="msg.includes('Lỗi') ? 'error' : 'success'">
                          {{ msg }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            
            <div class="modal-footer">
              <button 
                class="btn-start" 
                style="background: linear-gradient(135deg, #6366f1, #4f46e5); box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4);"
                @click="isComplete ? close() : startPush()" 
                :disabled="isProcessing || (!isComplete && (!previewResult || previewResult.total_fingerprints === 0 || selectedMachines.length === 0))"
              >
                <div v-if="isProcessing" class="spinner-sm"></div>
                <svg v-else-if="isComplete" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                {{ isProcessing ? 'Đang xử lý...' : (isComplete ? 'Đóng' : 'Xác Nhận Đẩy Vân Tay') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { bulkPushFingerprints, getBulkPushStatus, getMachines, previewBulkPush } from '../../machines/api'
import { useNotificationStore } from '@/stores/notification.js'

const props = defineProps({
  show: Boolean
})
const emit = defineEmits(['close', 'success'])

const machines = ref([])
const employeeIds = ref([])
const selectedMachines = ref([])
const isProcessing = ref(false)
const isComplete = ref(false)
const machineProgress = ref({ processed: 0, total: 0 })
const empProgress = ref({ processed: 0, total: 0 })
const activeIps = ref([])
const results = ref({})
const isPreviewing = ref(false)
const previewResult = ref(null)
let pollInterval = null

const notify = useNotificationStore()

const machineProgressPercent = computed(() => {
  if (machineProgress.value.total === 0) return 0
  return Math.round((machineProgress.value.processed / machineProgress.value.total) * 100)
})
const empProgressPercent = computed(() => {
  if (empProgress.value.total === 0) return 0
  return Math.round((empProgress.value.processed / empProgress.value.total) * 100)
})

watch(() => props.show, async (newVal) => {
  if (newVal) {
    resetState()
    try {
      const data = await getMachines()
      machines.value = data || []
    } catch (e) {
      notify?.error('Failed to load machines list')
    }
  }
})

const resetState = () => {
  employeeIds.value = []
  selectedMachines.value = []
  isProcessing.value = false
  isComplete.value = false
  machineProgress.value = { processed: 0, total: 0 }
  empProgress.value = { processed: 0, total: 0 }
  activeIps.value = []
  results.value = {}
  previewResult.value = null
  if (pollInterval) clearInterval(pollInterval)
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target.result
    const ids = text.split(/\r?\n/).map(id => id.trim()).filter(id => id.length > 0)
    employeeIds.value = [...new Set(ids)]
    previewResult.value = null // reset preview when file changes
  }
  reader.readAsText(file)
}

function toggleMachine(ip) {
  const index = selectedMachines.value.indexOf(ip)
  if (index > -1) {
    selectedMachines.value.splice(index, 1)
  } else {
    selectedMachines.value.push(ip)
  }
}

const previewData = async () => {
  if (employeeIds.value.length === 0) return
  
  try {
    isPreviewing.value = true
    const res = await previewBulkPush(employeeIds.value)
    previewResult.value = res
  } catch (err) {
    notify?.error('Lỗi khi kiểm tra dữ liệu: ' + (err.message || ''))
  } finally {
    isPreviewing.value = false
  }
}

const startPush = async () => {
  if (employeeIds.value.length === 0 || selectedMachines.value.length === 0 || !previewResult.value) return
  
  try {
    isProcessing.value = true
    isComplete.value = false
    results.value = {}
    
    await bulkPushFingerprints(employeeIds.value, selectedMachines.value)
    
    pollInterval = setInterval(pollStatus, 1500)
  } catch (err) {
    isProcessing.value = false
    notify?.error(err.response?.data?.detail || err.message || 'Error starting bulk push')
  }
}

const pollStatus = async () => {
  try {
    const status = await getBulkPushStatus()
    machineProgress.value = { processed: status.processed_machines || 0, total: status.total_machines || 0 }
    empProgress.value = { processed: status.processed_employees_total || 0, total: status.total_employees || 0 }
    activeIps.value = status.active_ips || []
    results.value = status.results || {}
    
    // Stop polling when done OR when backend has reset (not running + no machines = stale state)
    if (!status.is_running) {
      if (status.total_machines > 0) {
        clearInterval(pollInterval)
        pollInterval = null
        isProcessing.value = false
        isComplete.value = true
        emit('success')
        notify?.success('Hoàn tất đẩy vân tay!')
      } else {
        // Backend restarted or stale state, stop polling
        clearInterval(pollInterval)
        pollInterval = null
        isProcessing.value = false
      }
    }
  } catch (err) {
    console.error('Error polling status', err)
  }
}

const close = () => {
  if (isProcessing.value) return // Disable close while running if needed, or ask confirm
  resetState()
  emit('close')
}

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 11, 14, 0.8);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 1.5rem;
}

.modal-content {
  background: rgba(23, 25, 30, 0.95);
  width: 100%;
  max-width: 580px;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.modal-header {
  padding: 2rem 2.25rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-left { display: flex; gap: 1.25rem; }

.icon-pulse {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
}

.title-stack { display: flex; flex-direction: column; gap: 0.25rem; }
.title-main { font-size: 1.25rem; color: #fff; font-weight: 800; margin: 0; }
.subtitle { font-size: 0.85rem; color: #94a3b8; margin: 0; }

.btn-close-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-close-circle:hover { background: rgba(244, 63, 94, 0.15); color: #fb7185; transform: rotate(90deg); }

.modal-body { padding: 0 2.25rem 2rem; max-height: 500px; overflow-y: auto; }
.section-card { display: flex; flex-direction: column; gap: 1rem; }
.section-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #818cf8; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; }

.file-drop-zone {
  border: 2px dashed rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.02);
}
.file-drop-zone:hover { border-color: #6366f1; background: rgba(99, 102, 241, 0.05); }
.file-drop-zone.has-file { border-style: solid; border-color: #10b981; background: rgba(16, 185, 129, 0.05); }
.file-name { font-weight: 700; color: #fff; display: block; }

.machine-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.75rem; }
.machine-checkbox {
  background: rgba(255, 255, 255, 0.05);
  border: 1.5px solid rgba(255, 255, 255, 0.15);
  padding: 0.85rem;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.machine-checkbox:hover:not(.disabled) { background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.25); }
.machine-checkbox.active { border-color: #818cf8; background: rgba(129, 140, 248, 0.15); box-shadow: 0 0 20px rgba(129, 140, 248, 0.1); }
.machine-checkbox.disabled { opacity: 0.5; cursor: not-allowed; }

.checkbox-box { width: 20px; height: 20px; border-radius: 6px; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); display: flex; align-items: center; justify-content: center; color: #6366f1; }
.active .checkbox-box { background: #6366f1; color: #fff; border-color: #6366f1; }
.ip-text { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; font-weight: 600; color: #e2e8f0; }

.results-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.results-table th { text-align: left; font-size: 0.7rem; color: #64748b; text-transform: uppercase; padding-bottom: 0.5rem; }
.results-table td { padding: 0.75rem 0; border-top: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.9rem; color: #e2e8f0; }

.status-badge { font-size: 0.7rem; font-weight: 800; padding: 0.25rem 0.6rem; border-radius: 8px; text-transform: uppercase; }
.status-badge.success { color: #10b981; background: rgba(16, 185, 129, 0.1); }
.status-badge.error { color: #f43f5e; background: rgba(244, 63, 94, 0.1); }

.modal-footer { padding: 1.5rem 2.25rem 2.25rem; }
.btn-start { width: 100%; border: none; padding: 1rem; border-radius: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 0.75rem; cursor: pointer; transition: all 0.2s; color: white; }
.btn-start:hover:not(:disabled) { transform: translateY(-2px); }
.btn-start:disabled { opacity: 0.5; cursor: not-allowed; }

.mt-6 { margin-top: 1.5rem; }
.text-right { text-align: right; }
.spinner-sm { width: 18px; height: 18px; border: 3px solid rgba(255, 255, 255, 0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scale-enter-active, .scale-leave-active { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-enter-from, .scale-leave-to { opacity: 0; transform: scale(0.9) translateY(20px); }

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

.progress-section { background: rgba(255, 255, 255, 0.03); padding: 1.25rem; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05); }
.progress-header { display: flex; justify-content: space-between; margin-bottom: 0.75rem; }
.progress-label { font-size: 0.85rem; color: #94a3b8; font-weight: 600; }
.progress-percent { font-size: 0.85rem; color: #818cf8; font-weight: 800; }
.progress-bar-container { height: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 10px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, #6366f1, #818cf8); transition: width 0.4s ease-out; box-shadow: 0 0 15px rgba(99, 102, 241, 0.4); }
.progress-footer { margin-top: 0.75rem; }
.current-ip { font-size: 0.75rem; color: #64748b; font-family: 'JetBrains Mono', monospace; }
</style>
