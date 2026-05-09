<template>
  <div v-if="isOpen" class="modal-overlay">
    <div class="modal-content animate-in">
      <div class="modal-header">
        <h3>{{ $t('biometric.clone_title') }}</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <p class="desc">
          {{ $t('biometric.clone_desc', { id: employeeId }) }}
        </p>

        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <span>{{ $t('biometric.loading_machines') }}</span>
        </div>

        <div v-else class="machines-list">
          <div class="list-header">
            <label class="check-container">
              <input type="checkbox" :checked="isAllSelected" @change="toggleAll" />
              <span class="checkmark"></span>
              {{ $t('biometric.select_all') }}
            </label>
            <span class="count">{{ $t('biometric.selected_count', { count: selectedIps.length, total: targetMachines.length }) }}</span>
          </div>

          <div class="scroll-area">
            <div 
              v-for="m in targetMachines" 
              :key="m.ip" 
              class="machine-item"
              :class="{ 'processing': pushStatus.is_running && pushStatus.current_ip === m.ip }"
            >
              <label class="check-container">
                <input 
                  type="checkbox" 
                  v-model="selectedIps" 
                  :value="m.ip" 
                  :disabled="pushStatus.is_running"
                />
                <span class="checkmark"></span>
                <div class="m-info">
                  <span class="m-ip">{{ m.ip }}</span>
                  <span class="m-status" :class="m.status.toLowerCase()">{{ m.status }}</span>
                </div>
              </label>

              <div class="push-result">
                <span v-if="pushStatus.results[m.ip]" :class="pushStatus.results[m.ip].toLowerCase()">
                  {{ pushStatus.results[m.ip] }}
                </span>
                <div v-else-if="pushStatus.is_running && pushStatus.current_ip === m.ip" class="spinner-tiny"></div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="pushStatus.is_running" class="bulk-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <span class="progress-text">{{ $t('biometric.processing_machines', { current: pushStatus.processed_count, total: pushStatus.total_machines }) }}</span>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')" :disabled="pushStatus.is_running">{{ $t('common.cancel') }}</button>
        <button 
          class="btn btn-primary" 
          @click="startPush" 
          :disabled="selectedIps.length === 0 || pushStatus.is_running"
        >
          <span v-if="pushStatus.is_running">{{ $t('biometric.cloning_action') }}</span>
          <span v-else>{{ $t('biometric.push_action', { count: selectedIps.length }) }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useNotificationStore } from '@/stores/notification.js'
import * as machinesApi from '../api'

const notification = useNotificationStore()

const props = defineProps({
  isOpen: Boolean,
  employeeId: String,
  sourceIp: String
})

const emit = defineEmits(['close'])

const loading = ref(true)
const machines = ref([])
const selectedIps = ref([])
const pushStatus = ref({
  is_running: false,
  processed_count: 0,
  total_machines: 0,
  current_ip: '',
  results: {}
})

const targetMachines = computed(() => {
  return machines.value.filter(m => m.ip !== props.sourceIp)
})

const isAllSelected = computed(() => {
  return targetMachines.value.length > 0 && selectedIps.value.length === targetMachines.value.length
})

const progressPercent = computed(() => {
  if (!pushStatus.value.total_machines) return 0
  return (pushStatus.value.processed_count / pushStatus.value.total_machines) * 100
})

function toggleAll() {
  if (isAllSelected.value) {
    selectedIps.value = []
  } else {
    selectedIps.value = targetMachines.value.map(m => m.ip)
  }
}

async function fetchMachines() {
  try {
    loading.value = true
    machines.value = await machinesApi.getMachinesCapacity()
  } catch (err) {
    console.error('Failed to fetch machines', err)
  } finally {
    loading.value = false
  }
}

let pollInterval = null

async function startPush() {
  try {
    await machinesApi.pushFingerprints(props.employeeId, selectedIps.value)
    pushStatus.value.is_running = true
    startPolling()
  } catch (err) {
    notification.error('Failed to start push: ' + err.message)
  }
}

function startPolling() {
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(async () => {
    try {
      const status = await machinesApi.getPushStatus()
      pushStatus.value = status
      if (!status.is_running) {
        clearInterval(pollInterval)
      }
    } catch (err) {
      console.error('Polling error', err)
    }
  }, 1000)
}

onMounted(() => {
  fetchMachines()
})

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    fetchMachines()
    selectedIps.value = []
    pushStatus.value = { is_running: false, results: {}, processed_count: 0, total_machines: 0, current_ip: '' }
  } else {
    if (pollInterval) clearInterval(pollInterval)
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1e1e26;
  width: 100%;
  max-width: 500px;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
  border: 1px solid #334155;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #334155;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 { margin: 0; color: #f8fafc; }
.close-btn { background: none; border: none; font-size: 24px; color: #94a3b8; cursor: pointer; }

.modal-body { padding: 20px; }
.desc { color: #94a3b8; font-size: 0.95rem; margin-bottom: 20px; line-height: 1.5; }

.machines-list {
  border: 1px solid #334155;
  border-radius: 8px;
  background: #0f172a;
}

.list-header {
  padding: 10px 15px;
  border-bottom: 1px solid #475569;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #94a3b8;
}

.scroll-area {
  max-height: 300px;
  overflow-y: auto;
}

.machine-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #1e293b;
  transition: background 0.2s;
}

.machine-item:hover { background: #1e293b; }
.machine-item.processing { background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; }

.m-info { display: flex; flex-direction: column; gap: 2px; }
.m-ip { font-weight: 500; font-family: monospace; color: #f1f5f9; }
.m-status { font-size: 0.75rem; font-weight: bold; text-transform: uppercase; }
.m-status.online { color: #22c55e; }
.m-status.offline { color: #ef4444; }

.push-result { font-size: 0.8rem; font-weight: 600; }
.push-result .success { color: #22c55e; }
.push-result .error { color: #ef4444; }

.bulk-progress { margin-top: 20px; }
.progress-bar { height: 8px; background: #334155; border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.progress-fill { height: 100%; background: #3b82f6; transition: width 0.3s ease; }
.progress-text { font-size: 0.8rem; color: #94a3b8; }

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #334155;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.spinner-tiny {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(59, 130, 246, 0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.animate-in { animation: in 0.3s ease-out; }

/* Custom Checkbox */
.check-container {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  position: relative;
  user-select: none;
}

.check-container input { display: none; }
.checkmark {
  width: 18px;
  height: 18px;
  background: #334155;
  border-radius: 4px;
  position: relative;
  transition: all 0.2s;
}

.check-container:hover input ~ .checkmark { background: #475569; }
.check-container input:checked ~ .checkmark { background: #3b82f6; }
.checkmark:after {
  content: "";
  position: absolute;
  display: none;
  left: 6px; top: 2px; width: 5px; height: 10px;
  border: solid white; border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.check-container input:checked ~ .checkmark:after { display: block; }
</style>
