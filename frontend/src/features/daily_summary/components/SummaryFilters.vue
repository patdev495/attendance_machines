<template>
  <section class="filters card glow">
    <div class="filter-row">
      <div class="filter-group">
        <label for="empIdInput">{{ $t('attendance.filters.emp_id') }}</label>
        <div class="input-wrapper">
          <input 
            id="empIdInput" 
            v-model="filters.employee_id" 
            :placeholder="$t('attendance.filters.emp_placeholder')" 
            @input="handleSearchInput" 
          />
        </div>
      </div>
      <div class="filter-group">
        <label for="startDateInput">{{ $t('attendance.filters.date_from') }}</label>
        <input 
          id="startDateInput" 
          type="date" 
          v-model="filters.start_date" 
          @change="emitChange" 
        />
      </div>
      <div class="filter-group">
        <label for="endDateInput">{{ $t('attendance.filters.date_to') }}</label>
        <input 
          id="endDateInput" 
          type="date" 
          v-model="filters.end_date" 
          @change="emitChange" 
        />
      </div>
      <div class="filter-group">
        <label for="statusSelect">{{ $t('attendance.filters.status') }}</label>
        <select id="statusSelect" v-model="filters.status" @change="emitChange">
          <option value="">{{ $t('attendance.filters.all_status') }}</option>
          <option value="excel_synced">{{ $t('attendance.filters.status_excel') }}</option>
          <option value="machine_only">{{ $t('attendance.filters.status_machine') }}</option>
          <option value="log_only">{{ $t('attendance.filters.status_log') }}</option>
        </select>
      </div>
      <div class="filter-group reset-group">
        <button class="btn btn-secondary" @click="resetFilters">
          <span class="icon">↺</span> {{ $t('attendance.filters.clear') }}
        </button>
      </div>
    </div>

    <div class="filter-row summary-row">
      <div class="filter-group">
        <label for="shiftSelect">{{ $t('attendance.filters.shift') }}</label>
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
          <input type="checkbox" v-model="filters.only_missing" @change="emitChange" />
          <span class="checkmark"></span>
          {{ $t('attendance.filters.only_missing') }}
        </label>
        <label class="checkbox-container">
          <input type="checkbox" v-model="filters.late_arrival" @change="emitChange" />
          <span class="checkmark"></span>
          {{ $t('attendance.filters.late_arrival') }}
        </label>
        <label class="checkbox-container">
          <input type="checkbox" v-model="filters.early_departure" @change="emitChange" />
          <span class="checkmark"></span>
          {{ $t('attendance.filters.early_departure') }}
        </label>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { dailySummaryApi } from '../api'

const props = defineProps({
  initialFilters: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['change'])

const shifts = ref([])
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

// Custom debounce timer
let debounceTimer = null

const emitChange = () => {
  emit('change', { ...filters })
}

const fetchShifts = async () => {
  try {
    const { data } = await dailySummaryApi.getUniqueShifts()
    shifts.ref = data
    // Simplified: use the raw code as both value and label
    shifts.value = data.map(s => ({
      value: s,
      label: s
    }))

  } catch (err) {
    console.error('Failed to fetch unique shifts:', err)
  }
}

onMounted(() => {
  fetchShifts()
})

// Special wrapper for text/number input to avoid spamming the backend
const handleSearchInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emitChange()
  }, 500) // 500ms delay
}

watch(() => props.initialFilters, (newVal) => {
  if (newVal) {
    Object.assign(filters, newVal)
  }
}, { deep: true })

const resetFilters = () => {
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
  padding: 24px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.summary-row {
  padding-top: 20px;
  border-top: 1px solid var(--border-light);
}

.filter-group {
  flex: 1;
  min-width: 160px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.reset-group {
  flex: 0;
  min-width: auto;
}

.checkbox-group {
  justify-content: flex-start;
  padding-bottom: 5px;
  flex-direction: row;
  gap: 24px;
}

.checkbox-container {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  font-size: 0.95rem;
  color: var(--text-main);
  text-transform: none !important;
}

.checkbox-container input {
  width: 18px;
  height: 18px;
}

.btn-secondary {
  background: var(--bg-hover);
  color: var(--text-main);
}

.icon {
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .filter-group {
    min-width: 100%;
  }
}
</style>
