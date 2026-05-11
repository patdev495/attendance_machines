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
  background-color: #020617; /* Darker slate/black */
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0; /* Prevent flex blowout */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.container {
  max-width: 1400px;
  margin: 20px auto;
  padding: 0 40px;
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
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .container { padding: 0 15px; }
}
</style>
