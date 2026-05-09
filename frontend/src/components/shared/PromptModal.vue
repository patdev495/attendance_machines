<template>
  <Transition name="fade-backdrop">
    <div v-if="store.promptState.isOpen" class="modal-backdrop" @click="cancel">
      <Transition name="scale-modal" appear>
        <div class="modal-card" @click.stop>
          <div class="modal-header">
            <div class="info-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
            </div>
            <h3>{{ store.promptState.title }}</h3>
          </div>
          <div class="modal-body">
            <p>{{ store.promptState.message }}</p>
            <div class="input-wrapper">
              <input 
                ref="inputRef"
                v-model="inputValue" 
                type="text" 
                class="prompt-input"
                @keyup.enter="confirm"
                @keyup.esc="cancel"
              />
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn btn-ghost" @click="cancel">{{ $t('common.cancel') }}</button>
            <button class="btn btn-primary" @click="confirm">{{ $t('common.confirm') }}</button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useNotificationStore } from '@/stores/notification.js'

const store = useNotificationStore()
const inputValue = ref('')
const inputRef = ref(null)

watch(() => store.promptState.isOpen, (newVal) => {
  if (newVal) {
    inputValue.value = store.promptState.defaultValue || ''
    nextTick(() => {
      if (inputRef.value) inputRef.value.focus()
    })
  }
})

function confirm() {
  store.resolvePrompt(inputValue.value)
}

function cancel() {
  store.resolvePrompt(null)
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.7);
  backdrop-filter: blur(8px);
  z-index: 10001;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  width: 100%;
  max-width: 420px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 24px 24px 16px;
  text-align: center;
}

.info-icon {
  width: 60px;
  height: 60px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  margin: 0 auto 16px;
}

.modal-header h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  margin: 0;
  font-family: 'Outfit', sans-serif;
}

.modal-body {
  padding: 0 24px 24px;
}

.modal-body p {
  color: #94a3b8;
  font-size: 0.95rem;
  line-height: 1.6;
  margin: 0 0 16px;
  text-align: center;
}

.input-wrapper {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 2px;
}

.prompt-input {
  width: 100%;
  background: transparent;
  border: none;
  color: white;
  padding: 12px 16px;
  font-size: 1rem;
  outline: none;
}

.modal-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 20px 24px 24px;
  background: rgba(255, 255, 255, 0.02);
}

.btn {
  padding: 12px;
  font-weight: 600;
  font-size: 0.95rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

/* Transitions */
.fade-backdrop-enter-active, .fade-backdrop-leave-active { transition: opacity 0.3s ease; }
.fade-backdrop-enter-from, .fade-backdrop-leave-to { opacity: 0; }

.scale-modal-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-modal-leave-active { transition: all 0.2s ease-in; }
.scale-modal-enter-from { opacity: 0; transform: scale(0.9) translateY(20px); }
.scale-modal-leave-to { opacity: 0; transform: scale(0.95); }
</style>
