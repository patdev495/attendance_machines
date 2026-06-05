<template>
  <Transition name="fade-backdrop">
    <div v-if="isOpen" class="modal-backdrop" @click="close">
      <Transition name="scale-modal" appear>
        <div class="modal-card" @click.stop>
          <div class="modal-header">
            <div class="header-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            </div>
            <div>
              <h3>Đồng bộ nhân viên lên các máy khác</h3>
              <p class="subtext">Nhân viên <strong>{{ employeeId }}</strong> — máy nguồn: <code>{{ sourceIp }}</code></p>
            </div>
            <button class="close-btn" @click="close" :disabled="isRunning">✕</button>
          </div>

          <div class="modal-body">
            <!-- Description -->
            <div class="info-banner">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Thao tác này sẽ đẩy mã nhân viên lên các máy được chọn. Tên trên máy sẽ dùng tên trong DB nếu có.
            </div>

            <!-- Loading -->
            <div v-if="loadingMachines" class="loading-state">
              <div class="spinner"></div>
              <span>Đang tải danh sách máy...</span>
            </div>

            <!-- Machine List -->
            <template v-else>
              <div class="list-toolbar">
                <label class="check-all">
                  <input type="checkbox" :checked="isAllSelected" @change="toggleAll" :disabled="isRunning" />
                  <span class="checkmark"></span>
                  Chọn tất cả
                </label>
                <span class="selected-count">{{ selectedIps.length }} / {{ targetMachines.length }} máy</span>
              </div>

              <div class="machines-list">
                <div
                  v-for="m in targetMachines"
                  :key="m.ip"
                  class="machine-row"
                  :class="{
                    'is-processing': isRunning && syncStatus.current_ip === m.ip,
                    'is-done': syncStatus.results?.[m.ip] !== undefined && !isRunning
                  }"
                >
                  <label class="check-row" :class="{ disabled: isRunning }">
                    <input type="checkbox" v-model="selectedIps" :value="m.ip" :disabled="isRunning" />
                    <span class="checkmark"></span>
                    <div class="machine-info">
                      <span class="machine-ip">{{ m.ip }}</span>
                      <span class="machine-status" :class="(m.status || 'unknown').toLowerCase()">
                        {{ m.status || 'Unknown' }}
                      </span>
                    </div>
                  </label>

                  <!-- Result indicator -->
                  <div class="result-cell">
                    <span v-if="syncStatus.results?.[m.ip] === 'Success'" class="result success">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      Thành công
                    </span>
                    <span v-else-if="syncStatus.results?.[m.ip]" class="result error" :title="syncStatus.results[m.ip]">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                      Lỗi
                    </span>
                    <div v-else-if="isRunning && syncStatus.current_ip === m.ip" class="spinner-tiny"></div>
                  </div>
                </div>

                <div v-if="targetMachines.length === 0" class="no-machines">
                  Không có máy nào khác để đồng bộ.
                </div>
              </div>

              <!-- Progress bar -->
              <div v-if="isRunning" class="progress-section">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
                </div>
                <span class="progress-label">
                  Đang xử lý {{ syncStatus.processed_count }} / {{ syncStatus.total_machines }} máy...
                </span>
              </div>

              <!-- Done summary -->
              <div v-if="isDone" class="done-summary">
                <span class="done-ok">✓ {{ successCount }} thành công</span>
                <span v-if="errorCount > 0" class="done-err">✗ {{ errorCount }} lỗi</span>
              </div>
            </template>
          </div>

          <div class="modal-actions">
            <button class="btn btn-ghost" @click="close" :disabled="isRunning">Hủy</button>
            <button
              class="btn btn-primary btn-sync"
              @click="startSync"
              :disabled="selectedIps.length === 0 || isRunning || isDone"
            >
              <template v-if="isRunning">
                <div class="spinner-sm"></div>
                Đang đồng bộ...
              </template>
              <template v-else-if="isDone">
                Hoàn tất
              </template>
              <template v-else>
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                Đồng bộ ({{ selectedIps.length }} máy)
              </template>
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import * as machinesApi from '../api.js'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  employeeId: { type: String, required: true },
  employeeName: { type: String, default: '' },
  sourceIp: { type: String, required: true },
})

const emit = defineEmits(['close'])

const loadingMachines = ref(false)
const machines = ref([])
const selectedIps = ref([])
const isRunning = ref(false)
const isDone = ref(false)

const syncStatus = ref({
  is_running: false,
  processed_count: 0,
  total_machines: 0,
  current_ip: '',
  results: {},
})

let pollTimer = null

const targetMachines = computed(() =>
  machines.value.filter(m => m.ip !== props.sourceIp)
)

const isAllSelected = computed(() =>
  targetMachines.value.length > 0 && selectedIps.value.length === targetMachines.value.length
)

const progressPercent = computed(() => {
  if (!syncStatus.value.total_machines) return 0
  return (syncStatus.value.processed_count / syncStatus.value.total_machines) * 100
})

const successCount = computed(() =>
  Object.values(syncStatus.value.results || {}).filter(v => v === 'Success').length
)

const errorCount = computed(() =>
  Object.values(syncStatus.value.results || {}).filter(v => v !== 'Success').length
)

function toggleAll() {
  if (isAllSelected.value) {
    selectedIps.value = []
  } else {
    selectedIps.value = targetMachines.value.map(m => m.ip)
  }
}

function close() {
  if (!isRunning.value) {
    stopPolling()
    emit('close')
  }
}

async function fetchMachines() {
  loadingMachines.value = true
  try {
    machines.value = await machinesApi.getMachinesCapacity()
  } catch (err) {
    console.error('Failed to fetch machines', err)
  } finally {
    loadingMachines.value = false
  }
}

async function startSync() {
  if (selectedIps.value.length === 0 || isRunning.value) return

  isRunning.value = true
  isDone.value = false
  syncStatus.value = {
    is_running: true,
    processed_count: 0,
    total_machines: selectedIps.value.length,
    current_ip: '',
    results: {},
  }

  try {
    await machinesApi.syncEmployeeToMachines(
      props.sourceIp,
      props.employeeId,
      props.employeeName,
      selectedIps.value
    )
    startPolling()
  } catch (err) {
    isRunning.value = false
    syncStatus.value.results['General'] = 'Lỗi: ' + err.message
    isDone.value = true
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const status = await machinesApi.getSyncEmployeeStatus()
      syncStatus.value = status
      if (!status.is_running) {
        stopPolling()
        isRunning.value = false
        isDone.value = true
      }
    } catch (err) {
      console.error('Poll error', err)
    }
  }, 800)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(() => props.isOpen, (open) => {
  if (open) {
    selectedIps.value = []
    isRunning.value = false
    isDone.value = false
    syncStatus.value = { is_running: false, processed_count: 0, total_machines: 0, current_ip: '', results: {} }
    fetchMachines()
  } else {
    stopPolling()
  }
})
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(8px);
  z-index: 10010;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: linear-gradient(145deg, #1a1f2e, #141820);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 20px 22px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}

.header-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #818cf8;
  flex-shrink: 0;
}

.modal-header h3 { margin: 0; font-size: 1.05rem; color: #f1f5f9; }
.subtext { margin: 4px 0 0; font-size: 0.82rem; color: #64748b; }
.subtext strong { color: #94a3b8; }
.subtext code { background: rgba(99,102,241,0.1); padding: 1px 5px; border-radius: 3px; color: #818cf8; font-size: 0.8rem; }

.close-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: #475569;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  transition: color 0.2s;
}
.close-btn:hover:not(:disabled) { color: #94a3b8; }
.close-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.modal-body { padding: 20px 22px; }

.info-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.83rem;
  color: #93c5fd;
  margin-bottom: 18px;
  line-height: 1.5;
}

.info-banner svg { flex-shrink: 0; margin-top: 2px; }

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: #64748b;
  font-size: 0.9rem;
}

.list-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.selected-count { font-size: 0.82rem; color: #64748b; }

.machines-list {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
  max-height: 280px;
  overflow-y: auto;
}

.machine-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  transition: background 0.15s;
}

.machine-row:last-child { border-bottom: none; }
.machine-row:hover { background: rgba(255,255,255,0.03); }
.machine-row.is-processing { background: rgba(59, 130, 246, 0.08); border-left: 2px solid #3b82f6; }
.machine-row.is-done .machine-ip { opacity: 0.7; }

.check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex: 1;
}

.check-row.disabled { cursor: not-allowed; opacity: 0.6; }

.check-all {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.88rem;
  color: #94a3b8;
}

/* Custom checkbox */
.check-row input[type="checkbox"],
.check-all input[type="checkbox"] { display: none; }

.checkmark {
  width: 17px;
  height: 17px;
  border-radius: 4px;
  border: 1.5px solid #334155;
  background: #0f172a;
  position: relative;
  flex-shrink: 0;
  transition: all 0.15s;
}

.check-row:hover .checkmark,
.check-all:hover .checkmark { border-color: #6366f1; }

.check-row input:checked ~ .checkmark,
.check-all input:checked ~ .checkmark {
  background: #6366f1;
  border-color: #6366f1;
}

.checkmark::after {
  content: '';
  position: absolute;
  display: none;
  left: 5px; top: 2px;
  width: 5px; height: 9px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.check-row input:checked ~ .checkmark::after,
.check-all input:checked ~ .checkmark::after { display: block; }

.machine-info { display: flex; flex-direction: column; gap: 2px; }
.machine-ip { font-size: 0.88rem; font-weight: 500; font-family: monospace; color: #e2e8f0; }
.machine-status { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.machine-status.online { color: #4ade80; }
.machine-status.offline { color: #f87171; }
.machine-status.unknown { color: #94a3b8; }

.result-cell { font-size: 0.8rem; font-weight: 600; min-width: 90px; text-align: right; }
.result { display: flex; align-items: center; gap: 5px; justify-content: flex-end; }
.result.success { color: #4ade80; }
.result.error { color: #f87171; cursor: help; }

.no-machines {
  padding: 24px;
  text-align: center;
  color: #475569;
  font-size: 0.88rem;
}

.progress-section { margin-top: 18px; }
.progress-bar {
  height: 6px;
  background: rgba(255,255,255,0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #818cf8);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.progress-label { font-size: 0.8rem; color: #64748b; }

.done-summary {
  display: flex;
  gap: 14px;
  margin-top: 14px;
  padding: 10px 14px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
}
.done-ok { color: #4ade80; }
.done-err { color: #f87171; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px;
  border-top: 1px solid rgba(255,255,255,0.07);
}

.btn-sync {
  display: flex;
  align-items: center;
  gap: 7px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border: none;
  color: white;
  padding: 9px 20px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
}
.btn-sync:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
.btn-sync:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

/* Spinners */
.spinner {
  width: 20px; height: 20px;
  border: 2px solid rgba(99,102,241,0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.spinner-sm {
  width: 15px; height: 15px;
  border: 2px solid rgba(255,255,255,0.2);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.spinner-tiny {
  width: 14px; height: 14px;
  border: 2px solid rgba(99,102,241,0.15);
  border-top-color: #818cf8;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-left: auto;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Transitions */
.fade-backdrop-enter-active, .fade-backdrop-leave-active { transition: opacity 0.25s ease; }
.fade-backdrop-enter-from, .fade-backdrop-leave-to { opacity: 0; }

.scale-modal-enter-active, .scale-modal-leave-active { transition: all 0.25s ease; }
.scale-modal-enter-from { opacity: 0; transform: scale(0.94) translateY(12px); }
.scale-modal-leave-to { opacity: 0; transform: scale(0.96) translateY(8px); }
</style>
