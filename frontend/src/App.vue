<template>
  <div class="app-layout">
    <AppSidebar v-if="route.name !== 'meal'" />
    <div class="main-content" :style="route.name === 'meal' ? { padding: 0 } : {}">
      <AppHeader />
      <ToastNotification />
      <ConfirmModal />
      <PromptModal />
      <main :class="route.name === 'meal' ? 'kiosk-main-wrapper' : 'container'">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import ToastNotification from '@/components/shared/ToastNotification.vue'
import ConfirmModal from '@/components/shared/ConfirmModal.vue'
import PromptModal from '@/components/shared/PromptModal.vue'

const route = useRoute()
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background-color: transparent;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.container {
  max-width: 1600px;
  margin: 16px auto 32px;
  padding: 0 32px;
  width: 100%;
  flex: 1;
}

.kiosk-main-wrapper {
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 1024px) {
  .container { padding: 0 20px; margin-top: 12px; }
}

@media (max-width: 768px) {
  .container { padding: 0 14px; margin-top: 8px; }
}
</style>
