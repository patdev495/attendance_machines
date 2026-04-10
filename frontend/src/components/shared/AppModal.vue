<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
        <Transition name="scale">
          <div v-if="show" class="modal-container scrollable shadow-glow animate-in" :style="{ maxWidth: width }">
            <div class="modal-header">
              <h3 class="modal-title">{{ title || $t('common.info') }}</h3>
              <button class="btn-close" @click="$emit('close')">×</button>
            </div>
            <div class="modal-body">
              <slot></slot>
            </div>
            <div v-if="$slots.footer" class="modal-footer">
              <slot name="footer"></slot>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, default: 'Notification' },
  width: { type: String, default: '500px' }
})

defineEmits(['close'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-container {
  background: var(--bg-card, #1e293b);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
  border-radius: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  position: relative;
  overflow: hidden;
}

.shadow-glow {
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 20px rgba(99, 102, 241, 0.2);
}

.modal-header {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.modal-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  letter-spacing: -0.5px;
}

.btn-close {
  background: rgba(255, 255, 255, 0.05);
  border: none;
  color: #94a3b8;
  font-size: 24px;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  transform: rotate(90deg);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 16px 24px;
  background: rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.scale-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.scale-leave-active {
  transition: all 0.2s ease-in;
}
.scale-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(20px);
}
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}
</style>
