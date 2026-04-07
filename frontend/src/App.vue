<template>
  <div class="app-wrapper">
    <AppHeader />
    <ToastNotification />
    <ConfirmModal />
    <main class="container">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import AppHeader from '@/components/layout/AppHeader.vue'
import ToastNotification from '@/components/shared/ToastNotification.vue'
import ConfirmModal from '@/components/shared/ConfirmModal.vue'
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.container {
  max-width: 1200px;
  margin: 30px auto;
  padding: 0 20px;
  width: 100%;
  flex: 1;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
