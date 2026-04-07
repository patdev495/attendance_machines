<template>
  <div class="spinner-wrap" :style="{ padding }">
    <div class="spinner-ring"></div>
    <p v-if="message" class="msg">{{ message }}</p>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: '' },
  padding: { type: String, default: '60px 0' }
})
</script>

<style scoped>
.spinner-wrap { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.spinner-ring {
  width: 40px; height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.msg { color: var(--text-muted); font-size: 0.9rem; }
</style>
