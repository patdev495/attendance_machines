<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <div class="header-left">
                <div class="icon-pulse bg-indigo-500/20">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12c0-2.8 2.2-5 5-5s5 2.2 5 5-2.2 5-5 5-5-2.2-5-5Z"/><circle cx="7" cy="12" r=".5"/><path d="M12 12c0-2.8 2.2-5 5-5s5 2.2 5 5-2.2 5-5 5-5-2.2-5-5Z"/><circle cx="17" cy="12" r=".5"/><path d="M22 12c0-2.8-2.2-5-5-5s-5 2.2-5 5 2.2 5 5 5 5-2.2 5-5Z"/></svg>
                </div>
                <div class="title-stack">
                  <span class="eyebrow">{{ $t('biometric.realtime_scan') }}</span>
                  <h3>{{ $t('biometric.coverage_title', { id: employeeId }) }}</h3>
                </div>
              </div>
              <button class="btn-close-circle" :title="$t('export.cancel')" @click="close">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <div class="modal-body custom-scrollbar">
              <div v-if="loading" class="loading-container">
                <div class="dna-spinner"></div>
                <p class="loading-text">{{ $t('biometric.scanning') }}</p>
              </div>
              
              <div v-else class="status-list">
                <div v-for="m in sortedResults" :key="m.ip" class="status-card" :class="m.status.toLowerCase()">
                  <div class="card-glow"></div>
                  <div class="machine-meta">
                    <span class="machine-label">Machine Terminal</span>
                    <a :href="router.resolve({ name: 'device-detail', params: { ip: m.ip } }).href" target="_blank" class="machine-ip machine-link" title="Quản lý thiết bị này">
                      {{ m.ip }}
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 4px; opacity: 0.6;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    </a>
                  </div>
                  
                  <div class="badges-area">
                    <template v-if="m.status === 'Offline'">
                      <div class="badge-pill error">
                        <div class="dot red-pulse"></div>
                        {{ $t('biometric.terminal_offline') }}
                      </div>
                    </template>
                    <template v-else>
                      <div class="badge-pill" :class="m.has_finger ? 'success' : (m.has_user ? 'warning' : 'info')">
                        <div class="dot" :class="{ 'green-glow': m.has_finger }"></div>
                        {{ m.has_finger ? $t('biometric.template_ok') : (m.has_user ? $t('biometric.no_template') : $t('biometric.not_registered')) }}
                      </div>
                    </template>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-refresh" :disabled="loading" @click="fetchCoverage">
                <svg :class="{ 'spin': loading }" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                {{ loading ? $t('device.checking') : $t('biometric.refresh') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { employeesApi } from '../api.js'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  isOpen: Boolean,
  employeeId: String
})

const emit = defineEmits(['close'])

const loading = ref(false)
const results = ref([])

const sortedResults = computed(() => {
  return [...results.value].sort((a, b) => a.ip.localeCompare(b.ip))
})

async function fetchCoverage() {
  if (!props.employeeId) return
  loading.value = true
  try {
    results.value = await employeesApi.getBiometricCoverage(props.employeeId)
  } catch (e) {
    console.error('Failed to fetch biometric coverage', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.isOpen, (newVal) => {
  if (newVal) fetchCoverage()
})

function close() {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 11, 14, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1.5rem;
}

.modal-content {
  background: rgba(23, 25, 30, 0.95);
  width: 100%;
  max-width: 500px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
  overflow: hidden;
}

.glass {
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 1.5rem 1.75rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-left {
  display: flex;
  gap: 1.25rem;
}

.icon-pulse {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(129, 140, 248, 0.2);
}

.title-stack {
  display: flex;
  flex-direction: column;
}

.eyebrow {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #818cf8;
  font-weight: 700;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.15rem;
  color: #fff;
  font-weight: 700;
}

.btn-close-circle {
  width: 32px;
  height: 32px;
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
  border-color: rgba(244, 63, 94, 0.3);
  color: #fb7185;
  transform: rotate(90deg);
}

.modal-body {
  padding: 0.5rem 1.75rem 1.75rem;
  max-height: 450px;
  overflow-y: auto;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-card {
  position: relative;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  padding: 1rem 1.25rem;
  border-radius: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.status-card:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.machine-meta {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.machine-label {
  font-size: 0.65rem;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
}

.machine-ip {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #e2e8f0;
  font-size: 0.95rem;
}

.machine-link {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s;
}

.machine-link:hover {
  color: #818cf8;
}

.badge-pill {
  padding: 0.4rem 0.8rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
}

.badge-pill.success { color: #4ade80; background: rgba(34, 197, 94, 0.1); border-color: rgba(34, 197, 94, 0.2); }
.badge-pill.error { color: #f87171; background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.2); }
.badge-pill.warning { color: #fbbf24; background: rgba(245, 158, 11, 0.1); border-color: rgba(245, 158, 11, 0.2); }
.badge-pill.info { color: #94a3b8; }

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.red-pulse { animation: pulse-red 1.5s infinite; }
.green-glow { box-shadow: 0 0 8px #4ade80; }

@keyframes pulse-red {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.modal-footer {
  padding: 1.5rem 1.75rem;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: center;
}

.btn-refresh {
  width: 100%;
  background: #6366f1;
  color: #fff;
  border: none;
  padding: 0.85rem;
  border-radius: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  background: #4f46e5;
  transform: translateY(-1px);
}

.btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.scale-enter-active, .scale-leave-active { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-enter-from, .scale-leave-to { opacity: 0; transform: scale(0.9) translateY(20px); }

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 4rem 0;
}

.dna-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
</style>
