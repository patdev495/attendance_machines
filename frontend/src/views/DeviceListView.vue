<template>
  <div class="anim-up">
    <div class="page-header">
      <div>
        <h2>{{ $t('device.status') }}</h2>
        <p style="color:var(--text-muted); margin-top: 4px; font-size:0.9rem;">{{ $t('device.help') }}</p>
      </div>
      <button class="btn btn-primary" @click="store.fetchDevices()">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.08-7.49"/></svg>
        {{ $t('device.refresh') }}
      </button>
    </div>

    <LoadingSpinner v-if="store.devicesLoading" :message="$t('device.checking')" />
    <div v-else-if="store.devices.length === 0" class="empty-state card">{{ $t('device.no_machines') }}</div>
    <div v-else class="device-grid">
      <DeviceCard v-for="d in store.devices" :key="d.ip" :device="d" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useDeviceStore } from '@/stores/device.js'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import DeviceCard from '@/components/device/DeviceCard.vue'

const store = useDeviceStore()

onMounted(() => {
  store.fetchDevices()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
h2 { font-size: 1.6rem; font-weight: 600; }
.device-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
</style>
