<template>
  <div class="table-container card">
    <table class="employees-table">
      <thead>
        <tr>
          <th style="width:40px; text-align:center;">
            <input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="custom-chk" />
          </th>
          <th class="sortable" @click="toggleSort">
            {{ $t('attendance.table.emp_id') }}
            <span class="sort-icon" :class="store.idSortOrder">
              <svg v-if="store.idSortOrder === 'asc'" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
            </span>
          </th>
          <th>{{ $t('device.table.name_device') }}</th>
          <th>{{ $t('device.table.name_db') }}</th>
          <th>{{ $t('device.table.department') }}</th>
          <th>{{ $t('device.table.group') }}</th>
          <th>{{ $t('attendance.table.shift') }}</th>
          <th>{{ $t('device.table.status') }}</th>
          <th>{{ $t('device.table.action') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="employees.length === 0">
          <td colspan="9" class="empty-state">{{ $t('device.table.no_records') }}</td>
        </tr>
        <tr v-for="u in employees" :key="u.user_id" :class="{'selected-row': selectedIds.includes(u.user_id)}">
          <td style="text-align:center;">
            <input type="checkbox" :value="u.user_id" v-model="selectedIds" class="custom-chk" />
          </td>
          <td style="font-weight:600; color:#fff;">{{ u.user_id }}</td>
          <td style="color:var(--accent); font-size:0.85rem;">{{ u.name || '—' }}</td>
          <td>{{ u.db_name || '—' }}</td>
          <td>{{ u.department || '—' }}</td>
          <td>{{ u.group_name || '—' }}</td>
          <td>
            <span v-if="u.status === 'N'" class="badge-shift">{{ $t('attendance.filters.day_shift') }}</span>
            <span v-else-if="u.status === 'D'" class="badge-shift night">{{ $t('attendance.filters.night_shift') }}</span>
            <span v-else-if="u.status === 'TV'" class="badge-status-tv">{{ $t('attendance.filters.resigned') }}</span>
            <span v-else style="color:var(--text-muted);font-size:0.83rem;">—</span>
          </td>
          <td>
            <span :class="['badge', getStatusClass(u.source_status)]">
              {{ formatStatus(u.source_status) }}
            </span>
          </td>
          <td class="actions">
            <div class="action-group">
              <button class="btn-view" :title="$t('common.info')" @click="$emit('view', u)">{{ $t('common.info') }}</button>
              <button class="btn-sync" :title="$t('device.action.sync_finger')" @click="$emit('syncFinger', u.user_id)">{{ $t('device.action.sync_finger') }}</button>
              <button class="btn-edit" :title="$t('device.action.rename')" @click="$emit('rename', u)">{{ $t('device.action.rename') }}</button>
              <button class="btn-delete" :title="$t('device.action.delete')" @click="$emit('delete', u.user_id)">{{ $t('device.action.delete') }}</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { useMachineStore } from '../store.js'

const props = defineProps({ employees: { type: Array, default: () => [] } })
const emit = defineEmits(['delete', 'rename', 'syncFinger', 'selection-change', 'view'])

const store = useMachineStore()
const selectedIds = ref([])

function toggleSort() {
  store.idSortOrder = store.idSortOrder === 'asc' ? 'desc' : 'asc'
  store.applyFilter()
}

const getStatusClass = (status) => {
  if (status === 'excel_synced') return 'badge-excel'
  if (status === 'machine_only') return 'badge-machine'
  return 'badge-log'
}

const formatStatus = (status) => {
  if (status === 'excel_synced') return t('attendance.filters.status_excel')
  if (status === 'machine_only') return t('attendance.filters.status_machine')
  if (status === 'log_only') return t('attendance.filters.status_log')
  return status || t('attendance.filters.status_machine')
}

const isAllSelected = computed(() => {
  return props.employees.length > 0 && selectedIds.value.length === props.employees.length
})

function toggleAll(e) {
  if (e.target.checked) {
    selectedIds.value = props.employees.map(u => u.user_id)
  } else {
    selectedIds.value = []
  }
}

watch(selectedIds, (newVal) => {
  emit('selection-change', newVal)
}, { deep: true })

watch(() => props.employees, () => {
  selectedIds.value = []
})
</script>

<style scoped>
.table-container {
  overflow-x: auto;
  background: var(--card-bg);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid var(--border);
}

.employees-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.employees-table th, .employees-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.employees-table th {
  background: rgba(45, 55, 72, 0.4);
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.85rem;
  text-transform: none;
}

.employees-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
  position: relative;
}

.employees-table th.sortable:hover {
  color: #fff;
}

.sort-icon {
  display: inline-flex;
  margin-left: 4px;
  vertical-align: middle;
  color: var(--primary);
  opacity: 0.7;
}

.employees-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: var(--text-muted);
}

/* Badge System copied from Registry */
.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.82rem;
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
  min-width: 280px;
}

.action-group {
  display: flex;
  gap: 6px;
}

button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

.btn-view { background: #10b981; color: white; }
.btn-sync { background: #8b5cf6; color: white; }
.btn-edit { background: #3b82f6; color: white; }
.btn-delete { background: #ef4444; color: white; }

button:hover { opacity: 0.8; }

.custom-chk { width: 16px; height: 16px; cursor: pointer; accent-color: var(--primary); }
.selected-row { background: rgba(99, 102, 241, 0.1) !important; }
</style>
