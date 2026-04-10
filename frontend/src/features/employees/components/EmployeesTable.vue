<template>
  <div class="table-container">
    <table class="employees-table">
      <thead>
        <tr>
          <th style="width:40px; text-align:center;">
            <input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="custom-chk" />
          </th>
          <th class="sortable" @click="$emit('sort', 'id')">
            {{ $t('attendance.table.emp_id') }}
            <span class="sort-icon">
              <svg v-if="idSortOrder === 'asc'" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
            </span>
          </th>
          <th>{{ $t('device.table.name_db') }}</th>
          <th>{{ $t('device.table.department') }}</th>
          <th>{{ $t('device.table.group') }}</th>
          <th>{{ $t('attendance.table.shift') }}</th>
          <th>{{ $t('device.table.status') }}</th>
          <th>{{ $t('attendance.table.action') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="emp in employees" :key="emp.employee_id">
          <td style="text-align:center;">
            <input type="checkbox" v-model="selectedIds" :value="emp.employee_id" class="custom-chk" />
          </td>
          <td>{{ emp.employee_id }}</td>
          <td>{{ emp.emp_name || '—' }}</td>
          <td>{{ emp.department || '—' }}</td>
          <td>{{ emp.group_name || '—' }}</td>
          <td>{{ emp.shift || '—' }}</td>
          <td>
            <span :class="['badge', getStatusClass(emp.source_status)]">
              {{ formatStatus(emp.source_status) }}
            </span>
          </td>
          <td class="actions">
            <button @click="$emit('view', emp)" class="btn-view" :title="$t('common.info')">{{ $t('common.info') }}</button>
            <button @click="$emit('edit', emp)" class="btn-edit" :title="$t('device.action.rename')">{{ $t('device.action.rename') }}</button>
            <button @click="$emit('delete', emp)" class="btn-delete" :title="$t('device.action.delete')">{{ $t('device.action.delete') }}</button>
            <button @click="$emit('coverage', emp)" class="btn-info" :title="$t('biometric.view_coverage')">{{ $t('biometric.view_coverage') }}</button>
          </td>
        </tr>
        <tr v-if="employees.length === 0">
          <td colspan="7" class="empty-state">{{ $t('attendance.table.no_records') }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps({
  employees: {
    type: Array,
    required: true,
    default: () => []
  },
  idSortOrder: {
    type: String,
    default: 'asc'
  }
})

const emit = defineEmits(['edit', 'delete', 'coverage', 'view', 'sort', 'selection-change'])

const selectedIds = ref([])

const isAllSelected = computed(() => {
  return props.employees.length > 0 && selectedIds.value.length === props.employees.length
})

function toggleAll() {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = props.employees.map(e => e.employee_id)
  }
}

watch(selectedIds, (newVal) => {
  emit('selection-change', newVal)
})

const getStatusClass = (status) => {
  if (status === 'excel_synced') return 'badge-excel'
  if (status === 'machine_only') return 'badge-machine'
  return 'badge-log'
}

const formatStatus = (status) => {
  if (status === 'excel_synced') return t('attendance.filters.status_excel')
  if (status === 'machine_only') return t('attendance.filters.status_machine')
  if (status === 'log_only') return t('attendance.filters.status_log')
  return status
}
</script>

<style scoped>
.table-container {
  overflow-x: auto;
  background-color: #1a1a24;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}

.employees-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  color: #e2e8f0;
}

.employees-table th, .employees-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #2d3748;
}

.employees-table th {
  background-color: #2d3748;
  font-weight: 600;
  color: #cbd5e1;
}

.employees-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}

.employees-table th.sortable:hover {
  background-color: #4a5568;
  color: #fff;
}

.sort-icon {
  display: inline-flex;
  margin-left: 6px;
  vertical-align: middle;
  color: #6366f1;
}

/* Custom Checkbox Styles */
.custom-chk {
  width: 17px;
  height: 17px;
  cursor: pointer;
  accent-color: #3b82f6;
  border-radius: 4px;
}

.employees-table tbody tr:hover {
  background-color: #2a2a35;
}

.empty-state {
  text-align: center;
  padding: 24px;
  color: #94a3b8;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.badge-excel {
  background-color: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.badge-machine {
  background-color: rgba(249, 115, 22, 0.2);
  color: #fb923c;
}

.badge-log {
  background-color: rgba(148, 163, 184, 0.2);
  color: #cbd5e1;
}

.actions {
  display: flex;
  gap: 8px;
}

button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

button:hover {
  opacity: 0.8;
}

.btn-edit {
  background-color: #3b82f6;
  color: white;
}

.btn-view {
  background-color: #10b981;
  color: white;
}

.btn-delete {
  background-color: #ef4444;
  color: white;
}

.btn-info {
  background-color: #8b5cf6;
  color: white;
}
</style>
