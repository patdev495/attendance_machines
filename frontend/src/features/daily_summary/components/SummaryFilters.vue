<template>
  <section class="filters card glow">
    <!-- Quick Date Preset Chips -->
    <div class="preset-chips">
      <span class="preset-label">Lọc nhanh:</span>
      <button 
        type="button"
        class="chip-btn" 
        :class="{ active: activePreset === 'today' }"
        @click="applyPreset('today')"
      >
        Hôm nay
      </button>
      <button 
        type="button"
        class="chip-btn" 
        :class="{ active: activePreset === 'yesterday' }"
        @click="applyPreset('yesterday')"
      >
        Hôm qua
      </button>
      <button 
        type="button"
        class="chip-btn" 
        :class="{ active: activePreset === 'this_week' }"
        @click="applyPreset('this_week')"
      >
        Tuần này
      </button>
      <button 
        type="button"
        class="chip-btn" 
        :class="{ active: activePreset === 'this_month' }"
        @click="applyPreset('this_month')"
      >
        Tháng này
      </button>
    </div>

    <!-- Main Filter Row -->
    <div class="filter-row">
      <div class="filter-group">
        <label for="empIdInput">
          <Search :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.emp_id') }}</span>
        </label>
        <input 
          id="empIdInput" 
          v-model="filters.employee_id" 
          :placeholder="$t('attendance.filters.emp_placeholder')" 
          @input="handleSearchInput" 
        />
      </div>

      <div class="filter-group">
        <label for="startDateInput">
          <Calendar :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.date_from') }}</span>
        </label>
        <input 
          id="startDateInput" 
          type="date" 
          v-model="filters.start_date" 
          @change="onDateChange" 
        />
      </div>

      <div class="filter-group">
        <label for="endDateInput">
          <Calendar :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.date_to') }}</span>
        </label>
        <input 
          id="endDateInput" 
          type="date" 
          v-model="filters.end_date" 
          @change="onDateChange" 
        />
      </div>

      <div class="filter-group">
        <label for="statusSelect">
          <Filter :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.status') }}</span>
        </label>
        <select id="statusSelect" v-model="filters.status" @change="emitChange">
          <option value="">{{ $t('attendance.filters.all_status') }}</option>
          <option value="excel_synced">{{ $t('attendance.filters.status_excel') }}</option>
          <option value="machine_only">{{ $t('attendance.filters.status_machine') }}</option>
          <option value="log_only">{{ $t('attendance.filters.status_log') }}</option>
        </select>
      </div>

      <div class="filter-group reset-group">
        <button class="btn btn-ghost reset-btn" @click="resetFilters" :title="$t('attendance.filters.clear')">
          <RotateCcw :size="15" />
          <span>{{ $t('attendance.filters.clear') }}</span>
        </button>
      </div>
    </div>

    <!-- Secondary Filter Row: Shifts, Hours & Flags -->
    <div class="filter-row summary-row">
      <div class="filter-group">
        <label for="shiftSelect">
          <Clock :size="13" class="label-icon" />
          <span>{{ $t('attendance.filters.shift') }}</span>
        </label>
        <select id="shiftSelect" v-model="filters.shift" @change="emitChange">
          <option value="">{{ $t('attendance.filters.all_shifts') }}</option>
          <option v-for="s in shifts" :key="s.value" :value="s.value">
            {{ s.label }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label for="minHoursInput">{{ $t('attendance.filters.min_hours') }}</label>
        <input 
          id="minHoursInput" 
          type="number" 
          v-model="filters.min_hours" 
          :placeholder="$t('attendance.filters.hours_placeholder', { h: 8 })" 
          @input="handleSearchInput" 
        />
      </div>

      <div class="filter-group">
        <label for="maxHoursInput">{{ $t('attendance.filters.max_hours') }}</label>
        <input 
          id="maxHoursInput" 
          type="number" 
          v-model="filters.max_hours" 
          :placeholder="$t('attendance.filters.hours_placeholder', { h: 12 })" 
          @input="handleSearchInput" 
        />
      </div>

      <div class="filter-group checkbox-group">
        <label class="checkbox-container">
          <input type="checkbox" v-model="filters.only_missing" @change="emitChange" class="custom-chk" />
          <span>{{ $t('attendance.filters.only_missing') }}</span>
        </label>
        <label class="checkbox-container">
          <input type="checkbox" v-model="filters.late_arrival" @change="emitChange" class="custom-chk" />
          <span>{{ $t('attendance.filters.late_arrival') }}</span>
        </label>
        <label class="checkbox-container">
          <input type="checkbox" v-model="filters.early_departure" @change="emitChange" class="custom-chk" />
          <span>{{ $t('attendance.filters.early_departure') }}</span>
        </label>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { dailySummaryApi } from '../api'
import { Search, Calendar, Filter, Clock, RotateCcw } from 'lucide-vue-next'

const props = defineProps({
  initialFilters: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['change'])

const shifts = ref([])
const activePreset = ref('')

const filters = reactive({
  employee_id: '',
  start_date: '',
  end_date: '',
  status: '',
  shift: '',
  min_hours: null,
  max_hours: null,
  only_missing: false,
  late_arrival: false,
  early_departure: false,
  ...props.initialFilters
})

let debounceTimer = null

const emitChange = () => {
  emit('change', { ...filters })
}

const onDateChange = () => {
  activePreset.value = ''
  emitChange()
}

const fetchShifts = async () => {
  try {
    const { data } = await dailySummaryApi.getUniqueShifts()
    shifts.value = data.map(s => ({
      value: s,
      label: s
    }))
  } catch (err) {
    console.error('Failed to fetch unique shifts:', err)
  }
}

const formatISODate = (d) => {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function applyPreset(preset) {
  activePreset.value = preset
  const now = new Date()
  
  if (preset === 'today') {
    const todayStr = formatISODate(now)
    filters.start_date = todayStr
    filters.end_date = todayStr
  } else if (preset === 'yesterday') {
    const yest = new Date(now)
    yest.setDate(yest.getDate() - 1)
    const yestStr = formatISODate(yest)
    filters.start_date = yestStr
    filters.end_date = yestStr
  } else if (preset === 'this_week') {
    const day = now.getDay() || 7 // Monday = 1
    const monday = new Date(now)
    monday.setDate(monday.getDate() - (day - 1))
    filters.start_date = formatISODate(monday)
    filters.end_date = formatISODate(now)
  } else if (preset === 'this_month') {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    filters.start_date = formatISODate(firstDay)
    filters.end_date = formatISODate(now)
  }
  emitChange()
}

onMounted(() => {
  fetchShifts()
})

const handleSearchInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emitChange()
  }, 400)
}

watch(() => props.initialFilters, (newVal) => {
  if (newVal) {
    Object.assign(filters, newVal)
  }
}, { deep: true })

const resetFilters = () => {
  activePreset.value = ''
  Object.assign(filters, {
    employee_id: '',
    start_date: '',
    end_date: '',
    status: '',
    shift: '',
    min_hours: null,
    max_hours: null,
    only_missing: false,
    late_arrival: false,
    early_departure: false
  })
  emitChange()
}
</script>

<style scoped>
.filters {
  padding: 18px 22px;
  margin-bottom: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preset-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.preset-label {
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 4px;
}

.chip-btn {
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.chip-btn:hover {
  background: var(--primary-light);
  color: #fff;
  border-color: var(--primary);
}
.chip-btn.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
  box-shadow: 0 0 12px var(--primary-glow);
}

.filter-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.summary-row {
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}

.filter-group {
  flex: 1;
  min-width: 160px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.label-icon {
  color: var(--cyan);
}

.reset-group {
  flex: 0;
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

.checkbox-group {
  justify-content: flex-start;
  padding-bottom: 5px;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 18px;
  align-items: center;
}

.checkbox-container {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 0.86rem;
  font-weight: 500;
  color: #e2e8f0;
}

@media (max-width: 768px) {
  .filter-group {
    min-width: 100%;
  }
}
</style>
