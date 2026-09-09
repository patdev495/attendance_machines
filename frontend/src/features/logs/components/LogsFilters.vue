<template>
  <section class="filters card glow">
    <div class="filter-row">
      <!-- Search Emp ID / Name -->
      <div class="filter-group">
        <label for="empIdInput">
          <Search :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.emp_id') }}</span>
        </label>
        <div class="input-with-icon">
          <input 
            id="empIdInput" 
            v-model="filters.employeeId" 
            :placeholder="$t('attendance.filters.emp_placeholder')" 
            @input="handleSearchInput" 
          />
        </div>
      </div>

      <!-- Select Machine IP -->
      <div class="filter-group">
        <label for="machineSelect">
          <Cpu :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.machine_ip') }}</span>
        </label>
        <select id="machineSelect" v-model="filters.machineIp" @change="emitChange">
          <option value="">{{ $t('attendance.filters.all_machines') }}</option>
          <option v-for="m in machines" :key="m.ip || m" :value="m.ip || m">
            {{ formatMachineLabel(m.ip || m) }}
          </option>
        </select>
      </div>

      <!-- Date Range (hidden in live mode) -->
      <div class="filter-group" v-if="!liveMode">
        <label for="startDateInput">
          <Calendar :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.date_from') }}</span>
        </label>
        <input id="startDateInput" type="date" v-model="filters.startDate" @change="emitChange" />
      </div>

      <div class="filter-group" v-if="!liveMode">
        <label for="endDateInput">
          <Calendar :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.date_to') }}</span>
        </label>
        <input id="endDateInput" type="date" v-model="filters.endDate" @change="emitChange" />
      </div>

      <!-- Reset Action -->
      <div class="filter-group filter-actions">
        <button class="btn btn-ghost reset-btn" @click="resetFilters" :title="$t('attendance.filters.clear')">
          <RotateCcw :size="15" />
          <span>{{ $t('attendance.filters.clear') }}</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, defineProps, defineEmits, ref, onMounted, onUnmounted, watch } from 'vue'
import { getLiveStatus } from '@/features/machines/api'
import { Search, Cpu, Calendar, RotateCcw } from 'lucide-vue-next'

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

const emits = defineEmits(['change'])

const filters = reactive({
  employeeId: '',
  machineIp: '',
  startDate: '',
  endDate: '',
  ...props.initialFilters
})

let debounceTimer = null

function emitChange() {
  emits('change', { ...filters })
}

function handleSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emitChange()
  }, 400)
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

function formatMachineLabel(ip) {
  const m = machineStatus.value[ip]
  const status = m ? (typeof m === 'object' ? m.status : m) : 'offline'
  const prefix = status === 'connected' ? '[Online]' : status === 'stuck' ? '[Busy]' : '[Offline]'
  return `${prefix} ${ip}`
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
.filters {
  padding: 16px 20px;
  margin-bottom: 20px;
  border-radius: var(--radius-lg);
}

.filter-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  min-width: 170px;
  flex: 1;
}

.filter-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.label-icon {
  color: var(--cyan);
}

.filter-actions {
  flex: 0 0 auto;
  min-width: auto;
}

.reset-btn {
  height: 40px;
  padding: 0 16px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.03);
}
.reset-btn:hover {
  background: var(--rose-light);
  border-color: var(--rose);
  color: #fb7185;
}

@media (max-width: 768px) {
  .filter-row {
    gap: 12px;
  }
  .filter-group {
    min-width: 100%;
  }
}
</style>
