<template>
  <div class="machine-card card glow" :class="{ clickable: machine.status === 'Online', 'is-online': machine.status === 'Online', 'is-offline': machine.status === 'Offline' }" @click="onClick">
    <!-- Card Header -->
    <div class="card-header">
      <div class="ip-group">
        <div class="device-icon-box">
          <Wifi :size="16" v-if="machine.status === 'Online'" class="online-icon" />
          <WifiOff :size="16" v-else class="offline-icon" />
        </div>
        <div class="ip-info">
          <span class="ip-val">{{ machine.ip }}</span>
          <span class="device-type">HANVON TERMINAL</span>
        </div>
      </div>

      <span class="status-badge" :class="machine.status === 'Online' ? 'badge-online' : 'badge-offline'">
        <span class="dot-indicator" :class="machine.status === 'Online' ? 'pulse-green' : 'static-red'"></span>
        <span>{{ machine.status === 'Online' ? $t('common.online') : $t('common.offline') }}</span>
      </span>
    </div>
    
    <!-- Capacity Meters (Online only) -->
    <div v-if="machine.status === 'Online'" class="capacity-info">
      <!-- Users Section -->
      <div class="meter-block">
        <div class="cap-row">
          <span class="cap-label">
            <Users :size="13" class="meter-icon" />
            <span>{{ $t('machines.users') }}</span>
          </span>
          <span class="val">{{ machine.users }} <span class="cap-max">/ {{ machine.users_cap }}</span></span>
        </div>
        <div class="capacity-bar">
          <div class="capacity-fill" :style="{ width: getPct(machine.users, machine.users_cap) + '%', background: getFillGradient(getPct(machine.users, machine.users_cap)) }"></div>
        </div>
      </div>

      <!-- Face Section -->
      <div class="meter-block mt-10">
        <div class="cap-row">
          <span class="cap-label">
            <ScanFace :size="13" class="meter-icon" />
            <span>{{ $t('device.table.face') }}</span>
          </span>
          <span class="val">{{ machine.fingers }} <span class="cap-max">/ {{ machine.fingers_cap }}</span></span>
        </div>
        <div class="capacity-bar">
          <div class="capacity-fill" :style="{ width: getPct(machine.fingers, machine.fingers_cap) + '%', background: getFillGradient(getPct(machine.fingers, machine.fingers_cap)) }"></div>
        </div>
      </div>

      <!-- Admins Section -->
      <div v-if="machine.admins !== undefined" class="meter-block mt-10">
        <div class="cap-row">
          <span class="cap-label">
            <ShieldAlert :size="13" class="meter-icon" />
            <span>{{ $t('device.roles.admin') }}</span>
          </span>
          <span class="val">{{ machine.admins }} <span class="cap-max">/ {{ machine.admins_cap || 10 }}</span></span>
        </div>
        <div class="capacity-bar">
          <div class="capacity-fill" :style="{ width: getPct(machine.admins, machine.admins_cap || 10) + '%', background: getFillGradient(getPct(machine.admins, machine.admins_cap || 10)) }"></div>
        </div>
      </div>

      <!-- Logs Section -->
      <div class="meter-block mt-10">
        <div class="cap-row">
          <span class="cap-label">
            <FileText :size="13" class="meter-icon" />
            <span>{{ $t('machines.records') }}</span>
          </span>
          <span class="val">{{ machine.records?.toLocaleString() }} <span class="cap-max">/ {{ machine.records_cap?.toLocaleString() }}</span></span>
        </div>
        <div class="capacity-bar">
          <div class="capacity-fill" :style="{ width: getPct(machine.records, machine.records_cap) + '%', background: getFillGradient(getPct(machine.records, machine.records_cap)) }"></div>
        </div>
      </div>
    </div>

    <!-- Offline Placeholder -->
    <div v-else class="offline-state-box">
      <WifiOff :size="28" class="offline-hero-icon" />
      <span class="offline-msg">{{ $t('device.unreachable') }}</span>
      <span class="offline-submsg">Kiểm tra kết nối mạng hoặc nguồn điện máy</span>
    </div>

    <!-- Bottom Action Link -->
    <div v-if="machine.status === 'Online'" class="card-footer-action">
      <span>{{ $t('device.help_short') }}</span>
      <ChevronRight :size="14" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Wifi, WifiOff, Users, ScanFace, ShieldAlert, FileText, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  machine: { type: Object, required: true }
})

const router = useRouter()

function onClick() {
  if (props.machine.status === 'Online') {
    router.push(`/machines/${encodeURIComponent(props.machine.ip)}`)
  }
}

function getPct(val, cap) {
  if (!cap || cap === 0) return 0
  return Math.min(100, (val / cap) * 100)
}

function getFillGradient(pct) {
  if (pct >= 90) return 'linear-gradient(90deg, #f43f5e, #ef4444)'
  if (pct >= 70) return 'linear-gradient(90deg, #f59e0b, #fb7185)'
  return 'linear-gradient(90deg, #10b981, #06b6d4)'
}
</script>

<style scoped>
.machine-card {
  padding: 18px 20px;
  min-height: 230px;
  display: flex;
  flex-direction: column;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  border-radius: var(--radius-lg);
  position: relative;
  overflow: hidden;
}

.machine-card.clickable {
  cursor: pointer;
}

.machine-card.clickable:hover {
  transform: translateY(-4px);
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.6), 0 0 25px -4px rgba(6, 182, 212, 0.25);
}

.machine-card.is-offline {
  border-color: rgba(244, 63, 94, 0.2);
  background: rgba(15, 23, 42, 0.5);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.ip-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.device-icon-box {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
}
.online-icon { color: #22d3ee; }
.offline-icon { color: #f43f5e; }

.ip-info {
  display: flex;
  flex-direction: column;
}

.ip-val {
  font-family: var(--font-mono);
  font-size: 1.05rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.02em;
}

.device-type {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--text-dim);
  letter-spacing: 0.08em;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.badge-online {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge-offline {
  background: rgba(244, 63, 94, 0.12);
  color: #fb7185;
  border: 1px solid rgba(244, 63, 94, 0.3);
}

.dot-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.pulse-green {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}
.static-red {
  background: #f43f5e;
}

.capacity-info {
  flex-grow: 1;
}

.meter-block {
  display: flex;
  flex-direction: column;
}

.cap-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  margin-bottom: 4px;
}

.cap-label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-muted);
  font-weight: 600;
}
.meter-icon {
  color: var(--cyan);
}

.cap-row .val {
  font-family: var(--font-mono);
  color: #fff;
  font-weight: 600;
  font-size: 0.84rem;
}
.cap-max {
  color: var(--text-dim);
  font-weight: 400;
}

.mt-10 {
  margin-top: 10px;
}

.offline-state-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 24px;
  text-align: center;
}
.offline-hero-icon {
  color: #f43f5e;
  opacity: 0.8;
  margin-bottom: 4px;
}
.offline-msg {
  font-size: 0.88rem;
  font-weight: 700;
  color: #fb7185;
}
.offline-submsg {
  font-size: 0.74rem;
  color: var(--text-dim);
}

.card-footer-action {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--cyan);
  margin-top: auto;
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  transition: gap 0.2s;
}
.machine-card:hover .card-footer-action {
  gap: 8px;
  color: #38bdf8;
}
</style>
