<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <div class="header-left">
                <div class="icon-bg bg-purple-500/20">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
                </div>
                <div class="title-stack">
                  <span class="eyebrow">{{ $t('device.machine') }}: {{ ip }}</span>
                  <h3>{{ $t('device.add_and_enroll') }}</h3>
                </div>
              </div>
              <button class="btn-close-circle" @click="close">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <div class="modal-body">
              <!-- Progress Monitoring State -->
              <div v-if="sessionStatus === 'waiting' || sessionStatus === 'initiating'" class="status-monitor anim-fade">
                <div class="monitor-pulse">
                  <div class="pulse-ring"></div>
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
                </div>
                <p class="status-msg">{{ statusMessage }}</p>
                <div class="progress-steps">
                   <div class="step-dot active"></div>
                   <div class="step-dot"></div>
                   <div class="step-dot"></div>
                </div>
              </div>

              <!-- Success State -->
              <div v-else-if="sessionStatus === 'success'" class="status-result success anim-scale">
                <div class="result-icon-bg">
                  <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </div>
                <h3>{{ $t('common.success') }}</h3>
                <p>{{ statusMessage }}</p>
              </div>

              <!-- Failed State -->
              <div v-else-if="sessionStatus === 'failed'" class="status-result error anim-scale">
                <div class="result-icon-bg">
                  <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </div>
                <h3>{{ $t('common.error') }}</h3>
                <p>{{ statusMessage }}</p>
                <button class="btn-retry" @click="sessionStatus = 'idle'">{{ $t('common.retry') || 'Thử lại' }}</button>
              </div>

              <!-- Initial Form State -->
              <template v-else>
                <div class="form-group">
                  <label>{{ $t('employees.id_label') }}</label>
                  <input 
                    type="text" 
                    v-model="employeeId" 
                    class="form-input" 
                    :placeholder="$t('employees.search_placeholder')"
                    ref="idInput"
                    @keyup.enter="handleEnroll"
                  />
                </div>

                <div class="form-group">
                  <label>{{ $t('biometric.finger_slot') || 'Vị trí ngón tay (0-9)' }}</label>
                  <select v-model="fingerIndex" class="form-input">
                    <option v-for="i in 10" :key="i-1" :value="i-1">
                      {{ $t('biometric.slot_name', { n: i-1 }) || `Ngón tay ${i-1}` }}
                    </option>
                  </select>
                  <p class="help-text">
                    {{ $t('biometric.enroll_help') || 'Nếu ID đã tồn tại, vân tay tại vị trí này sẽ bị ghi đè.' }}
                  </p>
                </div>
              </template>
            </div>

            <div class="modal-footer">
              <button v-if="sessionStatus === 'waiting'" class="btn-cancel" @click="handleCancel">
                {{ $t('common.cancel') }}
              </button>
              <button v-else-if="sessionStatus === 'idle'" class="btn-cancel" @click="close">{{ $t('common.cancel') }}</button>
              
              <button 
                v-if="sessionStatus === 'idle'"
                class="btn-submit" 
                :disabled="!employeeId || loading" 
                @click="handleEnroll"
              >
                <div v-if="loading" class="spinner-tiny"></div>
                <span v-else>{{ $t('device.add_and_enroll') }}</span>
              </button>

              <button v-if="sessionStatus === 'success' || sessionStatus === 'failed'" class="btn-submit" @click="close">
                {{ $t('common.close') || 'Đóng' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { enrollUser, getEnrollStatus, cancelEnroll } from '../api'
import { useNotificationStore } from '@/stores/notification'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  isOpen: Boolean,
  ip: String
})

const emit = defineEmits(['close', 'success'])
const { t } = useI18n()
const notification = useNotificationStore()

const employeeId = ref('')
const fingerIndex = ref(0)
const loading = ref(false)
const idInput = ref(null)

const sessionStatus = ref('idle') // idle, initiating, waiting, success, failed, cancelled
const statusMessage = ref('')
let pollTimer = null

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    employeeId.value = ''
    fingerIndex.value = 0
    sessionStatus.value = 'idle'
    statusMessage.value = ''
    nextTick(() => {
      idInput.value?.focus()
    })
  } else {
    stopPolling()
  }
})

async function handleEnroll() {
  if (!employeeId.value || loading.value) return
  
  loading.value = true
  try {
    await enrollUser(props.ip, employeeId.value, fingerIndex.value)
    sessionStatus.value = 'initiating'
    startPolling()
  } catch (err) {
    notification.error(err.message || t('common.error'))
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const data = await getEnrollStatus(props.ip)
      sessionStatus.value = data.status
      statusMessage.value = data.message

      if (data.status === 'success') {
        notification.success(data.message)
        stopPolling()
        emit('success')
        // Auto close after 3 seconds
        setTimeout(() => {
          if (props.isOpen) close()
        }, 3000)
      } else if (data.status === 'failed') {
        stopPolling()
        loading.value = false
      } else if (data.status === 'cancelled') {
        stopPolling()
        loading.value = false
        sessionStatus.value = 'idle'
      }
    } catch (e) {
      console.error('Polling error', e)
    }
  }, 1000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleCancel() {
  try {
    await cancelEnroll(props.ip)
    sessionStatus.value = 'idle'
    loading.value = false
    stopPolling()
  } catch (e) {
    console.error('Cancel error', e)
  }
}

function close() {
  if (sessionStatus.value === 'waiting' || sessionStatus.value === 'initiating') {
    handleCancel()
  }
  emit('close')
}

onBeforeUnmount(() => {
  stopPolling()
})
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
  background: #1e293b;
  width: 100%;
  max-width: 400px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 1.25rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.header-left {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.icon-bg {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.title-stack h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #fff;
}

.eyebrow {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #94a3b8;
}

.btn-close-circle {
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
}

.modal-body {
  padding: 1.5rem;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.status-monitor {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem 0;
}

.status-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.result-icon-bg {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
}

.status-result.success .result-icon-bg {
  background: rgba(34, 197, 94, 0.1);
}

.status-result.error .result-icon-bg {
  background: rgba(239, 68, 68, 0.1);
}

.status-result h3 {
  color: #fff;
  margin-bottom: 0.5rem;
}

.status-result p {
  color: #94a3b8;
  font-size: 0.9rem;
}

.btn-retry {
  margin-top: 1.5rem;
  background: #334155;
  border: none;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
}

.monitor-pulse {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 4px solid #a855f7;
  border-radius: 50%;
  animation: pulse-ring 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.33); opacity: 0; }
  80%, 100% { opacity: 0; }
}

.status-msg {
  text-align: center;
  color: #e2e8f0;
  font-weight: 500;
  margin-bottom: 1.5rem;
}

.progress-steps {
  display: flex;
  gap: 8px;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #334155;
}

.step-dot.active {
  background: #a855f7;
  box-shadow: 0 0 10px #a855f7;
  animation: bounce 1s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.5rem;
}

.form-input {
  width: 100%;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 0.75rem;
  color: #fff;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: #a855f7;
}

.help-text {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.5rem;
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  background: rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-cancel {
  background: transparent;
  border: 1px solid #334155;
  color: #e2e8f0;
  padding: 0.6rem 1.25rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.05);
}

.btn-submit {
  background: #8b5cf6;
  border: none;
  color: #fff;
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled) {
  background: #7c3aed;
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner-tiny {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scale-enter-active, .scale-leave-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-enter-from, .scale-leave-to { transform: scale(0.9); opacity: 0; }
.anim-fade { animation: fadeIn 0.3s ease; }
.anim-scale { animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }

@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes scaleIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
</style>
