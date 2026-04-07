<template>
  <div class="device-card card" :class="{ clickable: device.status === 'Online' }" @click="onClick">
    <div class="card-header">
      <div class="ip">{{ device.ip }}</div>
      <span class="status-dot" :class="device.status === 'Online' ? 'online' : 'offline'">
        {{ device.status }}
      </span>
    </div>
    
    <div v-if="device.status === 'Online'" class="capacity-info">
      <!-- Users Section -->
      <div class="cap-row">
        <span class="label">{{ $t('machines.users') }}</span>
        <span class="val">{{ device.users }} / {{ device.users_cap }}</span>
      </div>
      <div class="capacity-bar">
        <div class="capacity-fill" :style="{ width: getPct(device.users, device.users_cap) + '%', background: fillColor(getPct(device.users, device.users_cap)) }"></div>
      </div>

      <!-- Fingers Section -->
      <div class="cap-row mt-12">
        <span class="label">{{ $t('machines.fingerprints') }}</span>
        <span class="val">{{ device.fingers }} / {{ device.fingers_cap }}</span>
      </div>
      <div class="capacity-bar">
        <div class="capacity-fill" :style="{ width: getPct(device.fingers, device.fingers_cap) + '%', background: fillColor(getPct(device.fingers, device.fingers_cap)) }"></div>
      </div>

      <!-- Logs Section -->
      <div class="cap-row mt-12">
        <span class="label">{{ $t('machines.records') }}</span>
        <span class="val">{{ device.records?.toLocaleString() }} / {{ device.records_cap?.toLocaleString() }}</span>
      </div>
      <div class="capacity-bar">
        <div class="capacity-fill" :style="{ width: getPct(device.records, device.records_cap) + '%', background: fillColor(getPct(device.records, device.records_cap)) }"></div>
      </div>
    </div>

    <div v-else-if="device.status === 'Offline'" class="offline-label">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;"><path d="m2 2 20 20"/><path d="m19.2 13.5c.3-.5.4-1.1.4-1.7 0-1.9-1.5-3.4-3.4-3.4-.6 0-1.2.2-1.7.5"/><path d="M12 12c-1.9 0-3.4-1.5-3.4-3.4 0-.6.2-1.2.5-1.7"/><path d="M10.5 19.2c-.5.3-1.1.4-1.7.4-1.9 0-3.4-1.5-3.4-3.4 0-.6.2-1.2.5-1.7"/><path d="M13.5 19.2c.5.3 1.1.4 1.7.4 1.9 0 3.4-1.5 3.4-3.4 0-.6-.2-1.2-.5-1.7"/></svg>
      {{ $t('device.unreachable') }}
    </div>

    <div v-if="device.status === 'Online'" class="hint">{{ $t('device.help_short') }}</div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  device: { type: Object, required: true }
})

const router = useRouter()

function onClick() {
  if (props.device.status === 'Online') {
    router.push(`/devices/${props.device.ip}`)
  }
}

function getPct(val, cap) {
  if (!cap || cap === 0) return 0
  return Math.min(100, (val / cap) * 100)
}

function fillColor(pct) {
  if (pct >= 90) return '#ef4444'
  if (pct >= 70) return '#f59e0b'
  return '#4ade80'
}
</script>

<style scoped>
.device-card { padding: 20px 24px; transition: transform 0.2s, box-shadow 0.2s; min-height: 220px; display: flex; flex-direction: column; }
.device-card.clickable { cursor: pointer; }
.device-card.clickable:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0,0,0,0.3); border-color: var(--primary); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.ip { font-family: monospace; font-size: 1.1rem; font-weight: 600; color: var(--accent); }
.status-dot { padding: 3px 12px; border-radius: 20px; font-size: 0.83rem; font-weight: 600; }
.online { background: rgba(74,222,128,0.15); color: #4ade80; }
.offline { background: rgba(239,68,68,0.15); color: #f87171; }

.capacity-info { flex-grow: 1; }
.cap-row { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; }
.cap-row .val { color: #fff; font-weight: 500; }
.mt-12 { margin-top: 12px; }

.offline-label { color: #f87171; font-size: 0.85rem; margin-top: 10px; display: flex; align-items: center; justify-content: center; background: rgba(239,68,68,0.05); padding: 12px; border-radius: 8px; border: 1px dashed rgba(239,68,68,0.2); }
.hint { font-size: 0.78rem; color: var(--primary); margin-top: auto; padding-top: 16px; text-align: right; border-top: 1px hide; }
</style>
