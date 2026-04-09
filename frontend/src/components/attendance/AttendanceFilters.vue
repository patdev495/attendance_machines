<template>
  <section class="filters card">
    <!-- Row 1: shared filters -->
    <div class="filter-row">
      <div class="filter-group">
        <label for="empIdInput">{{ $t('attendance.filters.emp_id') }}</label>
        <input id="empIdInput" name="employee_id" v-model="store.filters.employeeId" :placeholder="$t('attendance.filters.emp_placeholder')" @input="store.loadData(1)" />
      </div>
      <div class="filter-group">
        <label for="machineSelect">{{ $t('attendance.filters.machine_ip') }}</label>
        <select id="machineSelect" name="machine_ip" v-model="store.filters.machineIp" @change="store.loadData(1)">
          <option value="">{{ $t('attendance.filters.all_machines') }}</option>
          <option v-for="m in store.machines" :key="m.ip || m" :value="m.ip || m">
            {{ m.ip || m }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label for="startDateInput">{{ $t('attendance.filters.date_from') }}</label>
        <input id="startDateInput" name="start_date" type="date" v-model="store.filters.startDate" @change="store.loadData(1)" />
      </div>
      <div class="filter-group">
        <label for="endDateInput">{{ $t('attendance.filters.date_to') }}</label>
        <input id="endDateInput" name="end_date" type="date" v-model="store.filters.endDate" @change="store.loadData(1)" />
      </div>
      <div class="filter-group" v-if="store.currentView !== 'raw'">
        <label for="statusSelect">{{ $t('attendance.filters.status') }}</label>
        <select id="statusSelect" name="status" v-model="store.filters.status" @change="store.loadData(1)">
          <option value="">{{ $t('attendance.filters.all_status') }}</option>
          <option value="Active">{{ $t('attendance.filters.active') }}</option>
          <option value="TV">{{ $t('attendance.filters.resigned') }}</option>
        </select>
      </div>
      <div class="filter-group" style="justify-content: flex-end; align-items: flex-end;">
        <button class="btn btn-danger" @click="store.resetFilters()">{{ $t('attendance.filters.clear') }}</button>
      </div>
    </div>

    <!-- Row 2: summary-only filters -->
    <div class="filter-row summary-row" v-if="store.currentView === 'summary'">
      <div class="filter-group">
        <label for="minHoursInput">{{ $t('attendance.filters.min_hours') }}</label>
        <input id="minHoursInput" name="min_hours" type="number" v-model="store.summaryFilters.minHours" :placeholder="$t('attendance.filters.hours_placeholder', { h: 8 })" @input="store.loadData(1)" />
      </div>
      <div class="filter-group">
        <label for="maxHoursInput">{{ $t('attendance.filters.max_hours') }}</label>
        <input id="maxHoursInput" name="max_hours" type="number" v-model="store.summaryFilters.maxHours" :placeholder="$t('attendance.filters.hours_placeholder', { h: 12 })" @input="store.loadData(1)" />
      </div>
      <div class="filter-group">
        <label for="shiftSelect">{{ $t('attendance.filters.shift') }}</label>
        <select id="shiftSelect" name="shift" v-model="store.summaryFilters.shift" @change="store.loadData(1)">
          <option value="">{{ $t('attendance.filters.all_shifts') }}</option>
          <option value="N">{{ $t('attendance.filters.day_shift') }}</option>
          <option value="D">{{ $t('attendance.filters.night_shift') }}</option>
          <option value="NA">{{ $t('attendance.filters.na_shift') }}</option>
        </select>
      </div>
      <div class="filter-group" style="flex-direction: row; align-items: center; gap: 10px; padding-top: 22px;">
        <input type="checkbox" id="onlyMissing" name="only_missing" v-model="store.summaryFilters.onlyMissing" @change="store.loadData(1)" style="width:18px;height:18px;cursor:pointer;" />
        <label for="onlyMissing" style="margin-bottom:0; cursor:pointer; text-transform:none; font-size:0.9rem;">{{ $t('attendance.filters.only_missing') }}</label>
      </div>
    </div>
  </section>
</template>

<script setup>
import { useAttendanceStore } from '@/stores/attendance.js'
const store = useAttendanceStore()
</script>

<style scoped>
.filters { padding: 20px 24px; margin-bottom: 16px; }
.filter-row { display: flex; gap: 16px; flex-wrap: wrap; }
.filter-row + .filter-row { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border); }
.filter-group { display: flex; flex-direction: column; min-width: 140px; flex: 1; }
</style>
