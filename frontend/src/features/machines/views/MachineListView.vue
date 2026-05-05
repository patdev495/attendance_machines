<template>
  <div class="anim-up">
    <div class="page-header">
      <div>
        <h2>{{ $t('device.status') }}</h2>
        <p style="color:var(--text-muted); margin-top: 4px; font-size:0.9rem;">{{ $t('device.help') }}</p>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn btn-ghost" @click="handleSyncAllTime" style="border-color:#10b981; color:#10b981;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {{ $t('device.sync_time') }}
        </button>
        <button class="btn btn-primary" @click="store.fetchMachines()">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.08-7.49"/></svg>
          {{ $t('device.refresh') }}
        </button>
      </div>
    </div>

    <LoadingSpinner v-if="store.machinesLoading" :message="$t('device.checking')" />
    <div v-else-if="store.machines.length === 0" class="empty-state card">{{ $t('device.no_machines') }}</div>
    <div v-else class="device-grid">
      <MachineCard v-for="d in store.machines" :key="d.ip" :machine="d" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useMachineStore } from '../store.js'
import { syncAllMachinesTime } from '../api.js'
import { useNotificationStore } from '@/stores/notification.js'
import { useI18n } from 'vue-i18n'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import MachineCard from '../components/MachineCard.vue'

const store = useMachineStore()
const notification = useNotificationStore()
const { t } = useI18n()

async function handleSyncAllTime() {
  const notifyId = notification.info(t('device.syncing_time'), 0)
  try {
    await syncAllMachinesTime()
    notification.success(t('device.sync_time_success'))
  } catch (e) {
    notification.error(t('device.sync_time_failed', { err: e.message }))
  } finally {
    notification.remove(notifyId)
  }
}

onMounted(() => {
  store.fetchMachines()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
h2 { font-size: 1.6rem; font-weight: 600; }
.device-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
</style>
