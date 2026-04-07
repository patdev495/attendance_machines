<template>
  <Transition name="fade-backdrop">
    <div v-if="store.confirmState.isOpen" class="modal-backdrop" @click="store.resolveConfirm(false)">
      <Transition name="scale-modal" appear>
        <div class="modal-card" @click.stop>
          <div class="modal-header">
            <div class="warning-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            </div>
            <h3>{{ store.confirmState.title }}</h3>
          </div>
          <div class="modal-body">
            <p>{{ store.confirmState.message }}</p>
          </div>
          <div class="modal-actions">
            <button class="btn btn-ghost" @click="store.resolveConfirm(false)">Cancel</button>
            <button class="btn btn-danger" @click="store.resolveConfirm(true)">Confirm</button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { useNotificationStore } from '@/stores/notification.js'
const store = useNotificationStore()
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.7);
  backdrop-filter: blur(8px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  width: 100%;
  max-width: 400px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 24px 24px 16px;
  text-align: center;
}

.warning-icon {
  width: 60px;
  height: 60px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f43f5e;
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
  text-align: center;
}

.modal-body p {
  color: #94a3b8;
  font-size: 0.95rem;
  line-height: 1.6;
  margin: 0;
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
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

/* Transitions */
.fade-backdrop-enter-active, .fade-backdrop-leave-active { transition: opacity 0.3s ease; }
.fade-backdrop-enter-from, .fade-backdrop-leave-to { opacity: 0; }

.scale-modal-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-modal-leave-active { transition: all 0.2s ease-in; }
.scale-modal-enter-from { opacity: 0; transform: scale(0.9) translateY(20px); }
.scale-modal-leave-to { opacity: 0; transform: scale(0.95); }
</style>
