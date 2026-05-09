<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <div class="header-left">
                <div class="icon-pulse bg-rose-500/20">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                </div>
                <div class="title-stack">
                  <h2 class="title-main">{{ $t('employees.bulk_hardware_delete.title') }}</h2>
                  <p class="subtitle">{{ $t('employees.bulk_hardware_delete.subtitle') }}</p>
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
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  {{ $t('employees.bulk_hardware_delete.upload_label') }}
                </label>
                <div class="file-drop-zone" :class="{ 'has-file': selectedFile }">
                  <input type="file" ref="fileInput" accept=".txt" @change="handleFileChange" hidden />
                  <div class="drop-zone-content" @click="$refs.fileInput.click()">
                    <div v-if="selectedFile" class="file-info">
                      <span class="file-name">{{ selectedFile.name }}</span>
                      <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
                    </div>
                    <div v-else class="placeholder">
                      <span>{{ $t('employees.bulk_hardware_delete.file_help') }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 2: Machine Selection -->
              <div class="section-card mt-6">
                <label class="section-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
                  {{ $t('employees.bulk_hardware_delete.select_machines') }}
                </label>
                <div class="machine-grid">
                  <div v-for="ip in machineList" :key="ip" class="machine-checkbox" :class="{ 'active': selectedMachineIps.includes(ip) }" @click="toggleMachine(ip)">
                    <div class="checkbox-box">
                      <svg v-if="selectedMachineIps.includes(ip)" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </div>
                    <span class="ip-text">{{ ip }}</span>
                  </div>
                </div>
              </div>

              <!-- Progress Section -->
              <div v-if="isLoading" class="progress-section mt-6">
                <div class="progress-header">
                  <span class="progress-label">{{ $t('employees.bulk_hardware_delete.status_running', { current: progressInfo?.processed_count || 0, total: progressInfo?.total_machines || 0 }) }}</span>
                  <span class="progress-percent">{{ Math.round((progressInfo?.processed_count / progressInfo?.total_machines) * 100) || 0 }}%</span>
                </div>
                <div class="progress-bar-container">
                  <div class="progress-bar-fill" :style="{ width: `${(progressInfo?.processed_count / progressInfo?.total_machines) * 100 || 0}%` }"></div>
                </div>
                <div class="progress-footer">
                  <span class="current-ip" v-if="progressInfo?.current_ip">{{ $t('employees.bulk_delete_progress', { current: progressInfo.processed_count, total: progressInfo.total_machines, ip: progressInfo.current_ip }) }}</span>
                </div>
              </div>

              <!-- Results Section -->
              <div v-if="results" class="results-section mt-6">
                <div class="divider"></div>
                <table class="results-table">
                  <thead>
                    <tr>
                      <th>{{ $t('employees.bulk_hardware_delete.results_table.ip') }}</th>
                      <th class="text-center">{{ $t('employees.bulk_hardware_delete.results_table.deleted') }}</th>
                      <th class="text-right">{{ $t('employees.bulk_hardware_delete.results_table.status') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(res, ip) in results" :key="ip">
                      <td>{{ ip }}</td>
                      <td class="text-center">{{ res.deleted }}</td>
                      <td class="text-right">
                        <span class="status-badge" :class="res.status.toLowerCase() === 'success' ? 'success' : 'error'">
                          {{ res.status }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-start" :disabled="isLoading || !selectedFile || selectedMachineIps.length === 0" @click="handleStart">
                <div v-if="isLoading" class="spinner-sm"></div>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                {{ isLoading ? $t('employees.bulk_hardware_delete.status_running', { current: '...' }) : $t('employees.bulk_hardware_delete.start') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { employeesApi } from '../api'
import { getMachines, getBulkDeleteStatus } from '../../machines/api'
import { useNotificationStore } from '@/stores/notification'

const notification = useNotificationStore()

// Add getBulkDeleteStatus to employeesApi if not there, or use it directly
employeesApi.getBulkDeleteStatus = getBulkDeleteStatus

const props = defineProps({
  isOpen: Boolean
})

const emit = defineEmits(['close'])

const isLoading = ref(false)
const machineList = ref([])
const selectedMachineIps = ref([])
const selectedFile = ref(null)
const results = ref(null)
const progressInfo = ref(null)
let pollTimer = null

onMounted(async () => {
  try {
    machineList.value = await getMachines()
    // Select all by default
    selectedMachineIps.value = [...machineList.value]
  } catch (e) {
    console.error('Failed to load machines', e)
  }
})

function handleFileChange(event) {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
  }
}

function toggleMachine(ip) {
  const index = selectedMachineIps.value.indexOf(ip)
  if (index > -1) {
    selectedMachineIps.value.splice(index, 1)
  } else {
    selectedMachineIps.value.push(ip)
  }
}

async function handleStart() {
  if (!selectedFile.value || selectedMachineIps.value.length === 0) return
  
  isLoading.value = true
  results.value = null
  progressInfo.value = { processed_count: 0, total_machines: selectedMachineIps.value.length, current_ip: 'Initializing...' }
  
  try {
    await employeesApi.bulkDeleteHardware(selectedFile.value, selectedMachineIps.value)
    
    // Start polling
    startPolling()
  } catch (e) {
    console.error('Bulk hardware delete failed', e)
    notification.error(e.message)
    isLoading.value = false
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  
  pollTimer = setInterval(async () => {
    try {
      const status = await employeesApi.getBulkDeleteStatus()
      progressInfo.value = status
      
      if (!status.is_running) {
        clearInterval(pollTimer)
        pollTimer = null
        results.value = status.results
        isLoading.value = false
      }
    } catch (e) {
      console.error('Polling failed', e)
    }
  }, 1000)
}

function close() {
  if (isLoading.value) return
  emit('close')
  // Reset after close delay
  setTimeout(() => {
    selectedFile.value = null
    results.value = null
  }, 400)
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  return (bytes / 1024).toFixed(1) + ' KB'
}
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

.header-left {
  display: flex;
  gap: 1.25rem;
}

.icon-pulse {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(244, 63, 94, 0.2);
}

.title-stack {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.title-main {
  font-size: 1.25rem;
  color: #fff;
  font-weight: 800;
  margin: 0;
}

.subtitle {
  font-size: 0.85rem;
  color: #94a3b8;
  margin: 0;
}

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

.btn-close-circle:hover {
  background: rgba(244, 63, 94, 0.15);
  color: #fb7185;
  transform: rotate(90deg);
}

.modal-body {
  padding: 0 2.25rem 2rem;
  max-height: 500px;
  overflow-y: auto;
}

.section-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-title {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6366f1;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-drop-zone {
  border: 2px dashed rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.02);
}

.file-drop-zone:hover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.file-drop-zone.has-file {
  border-style: solid;
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.05);
}

.file-name {
  font-weight: 700;
  color: #fff;
  display: block;
}

.file-size {
  font-size: 0.75rem;
  color: #94a3b8;
}

.machine-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 0.75rem;
}

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

.machine-checkbox:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.25);
}

.machine-checkbox.active {
  border-color: #818cf8;
  background: rgba(129, 140, 248, 0.15);
  box-shadow: 0 0 20px rgba(129, 140, 248, 0.1);
}

.checkbox-box {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
}

.active .checkbox-box {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}

.ip-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 600;
  color: #e2e8f0;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.results-table th {
  text-align: left;
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
  padding-bottom: 0.5rem;
}

.results-table td {
  padding: 0.75rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.9rem;
  color: #e2e8f0;
}

.status-badge {
  font-size: 0.7rem;
  font-weight: 800;
  padding: 0.25rem 0.6rem;
  border-radius: 8px;
  text-transform: uppercase;
}

.status-badge.success { color: #10b981; background: rgba(16, 185, 129, 0.1); }
.status-badge.error { color: #f43f5e; background: rgba(244, 63, 94, 0.1); }

.modal-footer {
  padding: 1.5rem 2.25rem 2.25rem;
}

.btn-start {
  width: 100%;
  background: linear-gradient(135deg, #f43f5e, #e11d48);
  color: #fff;
  border: none;
  padding: 1rem;
  border-radius: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-start:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px -5px rgba(244, 63, 94, 0.4);
}

.btn-start:disabled { opacity: 0.5; cursor: not-allowed; }

.mt-6 { margin-top: 1.5rem; }
.text-center { text-align: center; }
.text-right { text-align: right; }

.spinner-sm {
  width: 18px;
  height: 18px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

/* Transitions same as sample */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scale-enter-active, .scale-leave-active { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-enter-from, .scale-leave-to { opacity: 0; transform: scale(0.9) translateY(20px); }

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

/* Progress Styles */
.progress-section {
  background: rgba(255, 255, 255, 0.03);
  padding: 1.25rem;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.progress-label {
  font-size: 0.85rem;
  color: #94a3b8;
  font-weight: 600;
}

.progress-percent {
  font-size: 0.85rem;
  color: #818cf8;
  font-weight: 800;
}

.progress-bar-container {
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #818cf8);
  transition: width 0.4s ease-out;
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
}

.progress-footer {
  margin-top: 0.75rem;
}

.current-ip {
  font-size: 0.75rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}
</style>
