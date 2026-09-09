<template>
  <div class="machines-list-view anim-up">
    <!-- Header -->
    <div class="page-header">
      <div class="header-info">
        <h2 class="title">{{ $t('device.status') }}</h2>
        <p class="subtitle">{{ $t('device.help') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary" @click="store.fetchMachines()" :disabled="store.machinesLoading">
          <RotateCw :size="16" :class="{ 'spin-anim': store.machinesLoading }" />
          <span>{{ $t('device.refresh') }}</span>
        </button>
      </div>
    </div>

    <!-- Quick Machine Stat Pills -->
    <div class="stat-pills-row" v-if="store.machines.length > 0">
      <div class="stat-pill-item card">
        <span class="pill-dot dot-cyan"></span>
        <span class="pill-label">Tổng thiết bị:</span>
        <span class="pill-val">{{ store.machines.length }}</span>
      </div>
      <div class="stat-pill-item card">
        <span class="pill-dot dot-green"></span>
        <span class="pill-label">Trực tuyến (Online):</span>
        <span class="pill-val text-online">{{ onlineCount }}</span>
      </div>
      <div class="stat-pill-item card" v-if="offlineCount > 0">
        <span class="pill-dot dot-red"></span>
        <span class="pill-label">Mất kết nối:</span>
        <span class="pill-val text-offline">{{ offlineCount }}</span>
      </div>
    </div>

    <!-- Machine List Grid -->
    <LoadingSpinner v-if="store.machinesLoading && store.machines.length === 0" :message="$t('device.checking')" />
    <div v-else-if="store.machines.length === 0" class="empty-state card">
      <Cpu :size="42" class="empty-icon" />
      <p>{{ $t('device.no_machines') }}</p>
    </div>
    <div v-else class="device-grid">
      <MachineCard v-for="d in store.machines" :key="d.ip" :machine="d" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useMachineStore } from '../store.js'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import MachineCard from '../components/MachineCard.vue'
import { RotateCw, Cpu } from 'lucide-vue-next'

const store = useMachineStore()

const onlineCount = computed(() => {
  return store.machines.filter(m => m.status === 'Online').length
})

const offlineCount = computed(() => {
  return store.machines.filter(m => m.status !== 'Online').length
})

onMounted(() => {
  store.fetchMachines()
})
</script>

<style scoped>
.machines-list-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.title {
  font-size: 1.7rem;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--text-muted);
  font-size: 0.88rem;
  margin-top: 2px;
}

.stat-pills-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-pill-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.84rem;
}

.pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot-cyan { background: #22d3ee; box-shadow: 0 0 8px #22d3ee; }
.dot-green { background: #10b981; box-shadow: 0 0 8px #10b981; }
.dot-red { background: #f43f5e; }

.pill-label {
  color: var(--text-muted);
  font-weight: 500;
}

.pill-val {
  font-family: var(--font-mono);
  font-weight: 700;
  color: #fff;
}
.text-online { color: #34d399; }
.text-offline { color: #fb7185; }

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.spin-anim {
  animation: spin 0.8s linear infinite;
}
</style>
