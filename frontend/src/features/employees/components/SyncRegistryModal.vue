<template>
  <AppModal 
    :show="true" 
    :title="$t('attendance.excel_sync.title')" 
    @close="$emit('close')"
  >

      <div class="modal-body">
        <div v-if="!status.is_running && !status.current_step" class="upload-area" 
             :class="{ 'dragging': dragging }"
             @dragover.prevent="dragging = true"
             @dragleave.prevent="dragging = false"
             @drop.prevent="handleDrop">
          <div class="upload-icon">📁</div>
          <p>{{ $t('attendance.excel_sync.drag_drop') }}</p>
          <span class="or">{{ $t('common.or') }}</span>
          <label class="btn btn-primary">
            {{ $t('attendance.excel_sync.select_file') }}
            <input type="file" accept=".xlsx,.xls" hidden @change="handleFileSelect" />
          </label>
        </div>

        <div v-else class="status-area">
          <div class="status-step">{{ status.current_step }}</div>
          
          <div class="progress-container">
            <div class="progress-bar" :style="{ width: status.progress + '%' }"></div>
          </div>
          <div class="progress-text">{{ status.progress }}%</div>

          <div v-if="status.progress === 100" class="results-summary animate-in">
            <div class="result-item">
              <span class="label">Excel Synced:</span>
              <span class="value">{{ status.excel_count }}</span>
            </div>
            <div class="result-item">
              <span class="label">Machine Only:</span>
              <span class="value alert">{{ status.machine_only_count }}</span>
            </div>
            <p class="result-note">Users from machines were automatically merged into the local registry.</p>
          </div>

          <div v-if="status.error" class="error-box animate-in">
            <strong>Error:</strong> {{ status.error }}
          </div>
        </div>
      </div>

    <template #footer>
      <button v-if="!status.is_running" class="btn btn-secondary" @click="$emit('close')">
        {{ status.progress === 100 ? 'Close' : 'Cancel' }}
      </button>
    </template>
  </AppModal>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AppModal from '@/components/shared/AppModal.vue'
import { dailySummaryApi } from '@/features/daily_summary/api'

const emit = defineEmits(['close', 'synced'])
const dragging = ref(false)
const status = ref({
  is_running: false,
  progress: 0,
  current_step: '',
  excel_count: 0,
  machine_only_count: 0,
  error: null
})

let pollInterval = null

const startPolling = () => {
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(async () => {
    try {
      const { data } = await dailySummaryApi.getSyncStatus()
      status.value = data
      if (!data.is_running && data.progress === 100) {
        clearInterval(pollInterval)
        emit('synced')
      } else if (data.error) {
        clearInterval(pollInterval)
      }
    } catch (e) {
      console.error('Polling error', e)
    }
  }, 1000)
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) uploadFile(file)
}

const handleDrop = (e) => {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) uploadFile(file)
}

const uploadFile = async (file) => {
  try {
    status.value.is_running = true
    status.value.current_step = 'Starting upload...'
    await dailySummaryApi.syncExcel(file)
    startPolling()
  } catch (e) {
    status.value.is_running = false
    status.value.error = e.response?.data?.detail || 'Upload failed'
  }
}

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.upload-area {
  border: 2px dashed var(--border);
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-area.dragging {
  border-color: var(--primary);
  background: var(--bg-hover);
  transform: scale(1.02);
}

.upload-icon { font-size: 3rem; }
.or { color: var(--text-muted); font-size: 0.9rem; }

.status-area {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-step { font-weight: 600; color: var(--text-main); }

.progress-container {
  height: 8px;
  background: var(--bg-hover);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s;
}

.progress-text { font-size: 0.85rem; color: var(--text-muted); }

.results-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
  padding: 20px;
  background: var(--bg-main);
  border-radius: 12px;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-item .label { font-size: 0.8rem; color: var(--text-muted); }
.result-item .value { font-size: 1.5rem; font-weight: 700; color: var(--primary); }
.result-item .value.alert { color: var(--warning); }

.result-note {
  grid-column: span 2;
  font-size: 0.8rem;
  color: var(--text-muted);
  font-style: italic;
  margin: 0;
}

.error-box {
  padding: 16px;
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
  border-radius: 8px;
  font-size: 0.9rem;
}

.animate-in {
  animation: fadeIn 0.4s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
