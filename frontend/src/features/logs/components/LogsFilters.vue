<template>
  <section class="filters card">
    <div class="filter-row">
      <div class="filter-group">
        <label for="empIdInput">{{ $t('attendance.filters.emp_id') }}</label>
        <input 
          id="empIdInput" 
          v-model="filters.employeeId" 
          :placeholder="$t('attendance.filters.emp_placeholder')" 
          @input="handleSearchInput" 
        />
      </div>
      <div class="filter-group">
        <label for="machineSelect">{{ $t('attendance.filters.machine_ip') }}</label>
        <select id="machineSelect" v-model="filters.machineIp" @change="emitChange">
          <option value="">{{ $t('attendance.filters.all_machines') }}</option>
          <option v-for="m in machines" :key="m.ip || m" :value="m.ip || m">
            {{ getMachineStatusIcon(m.ip || m) }} {{ m.ip || m }}
          </option>
        </select>
      </div>
      <div class="filter-group" v-if="!liveMode">
        <label for="startDateInput">{{ $t('attendance.filters.date_from') }}</label>
        <input id="startDateInput" type="date" v-model="filters.startDate" @change="emitChange" />
      </div>
      <div class="filter-group" v-if="!liveMode">
        <label for="endDateInput">{{ $t('attendance.filters.date_to') }}</label>
        <input id="endDateInput" type="date" v-model="filters.endDate" @change="emitChange" />
      </div>
      <div class="filter-group filter-actions">
        <button class="btn btn-danger" @click="resetFilters">{{ $t('attendance.filters.clear') }}</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, defineProps, defineEmits, ref, onMounted, onUnmounted } from 'vue'
import { getLiveStatus } from '@/features/machines/api'

const props = defineProps({
  machines: {
    type: Array,
    default: () => []
  },
  initialFilters: {
    type: Object,
    default: () => ({})
  },
  liveMode: {
    type: Boolean,
    default: false
  }
})

import { watch } from 'vue'

const emits = defineEmits(['change'])

const filters = reactive({
  employeeId: '',
  machineIp: '',
  startDate: '',
  endDate: '',
  ...props.initialFilters
})

// Custom debounce timer
let debounceTimer = null

function emitChange() {
  emits('change', { ...filters })
}

// Special wrapper for text input to avoid spamming the backend
function handleSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emitChange()
  }, 500) // 500ms delay
}

watch(() => props.initialFilters, (newVal) => {
  if (newVal) {
    Object.assign(filters, {
      employeeId: newVal.employee_id || '',
      machineIp: newVal.machine_ip || '',
      startDate: newVal.start_date || '',
      endDate: newVal.end_date || ''
    })
  }
}, { deep: true, immediate: true })

function resetFilters() {
  filters.employeeId = ''
  filters.machineIp = ''
  filters.startDate = ''
  filters.endDate = ''
  emitChange()
}

const machineStatus = ref({})
let statusInterval = null

async function fetchLiveStatus() {
  try {
    const data = await getLiveStatus()
    machineStatus.value = data || {}
  } catch (e) {
    console.error('Error fetching machine status:', e)
  }
}

function getMachineStatusIcon(ip) {
  const status = machineStatus.value[ip]
  if (!status) return '' // Only show icon for machines that HAVE a live monitor
  if (status === 'connected') return '🟢'
  if (status === 'stuck') return '🟡'
  if (status === 'disconnected') return '🔴'
  return '⚪'
}

onMounted(() => {
  fetchLiveStatus()
  statusInterval = setInterval(fetchLiveStatus, 10000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>

<style scoped>
.filters { padding: 20px 24px; margin-bottom: 24px; background: var(--card-bg); }
.filter-row { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; min-width: 160px; flex: 1; }
.filter-group label { margin-bottom: 8px; font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.filter-actions { flex: 0 0 auto; min-width: auto; }
</style>
