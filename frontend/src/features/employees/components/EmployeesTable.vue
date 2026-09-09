<template>
  <div class="table-container card glow">
    <table class="employees-table">
      <thead>
        <tr>
          <th style="width: 44px; text-align: center;">
            <input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="custom-chk" />
          </th>
          <th class="sortable" @click="$emit('sort', 'id')" style="width: 140px;">
            <div class="th-content">
              <span>{{ $t('attendance.table.emp_id') }}</span>
              <span class="sort-icon-box">
                <ArrowUp v-if="idSortOrder === 'asc'" :size="13" />
                <ArrowDown v-else :size="13" />
              </span>
            </div>
          </th>
          <th>{{ $t('device.table.name_db') }}</th>
          <th>{{ $t('device.table.department') }}</th>
          <th>{{ $t('device.table.group') }}</th>
          <th>{{ $t('attendance.table.shift') }}</th>
          <th style="width: 150px;">{{ $t('device.table.status') }}</th>
          <th style="width: 170px; text-align: center;">{{ $t('attendance.table.action') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="emp in employees" :key="emp.employee_id" class="employee-row">
          <td style="text-align: center;">
            <input type="checkbox" v-model="selectedIds" :value="emp.employee_id" class="custom-chk" />
          </td>
          <td class="emp-id-cell">
            <span class="id-badge">{{ emp.employee_id }}</span>
          </td>
          <td class="emp-name-cell">
            <span class="emp-name-val">{{ emp.emp_name || '—' }}</span>
          </td>
          <td class="dept-cell">{{ emp.department || '—' }}</td>
          <td class="group-cell">{{ emp.group_name || '—' }}</td>
          <td>
            <span class="badge-shift" v-if="emp.shift">{{ emp.shift }}</span>
            <span class="dimmed" v-else>—</span>
          </td>
          <td>
            <span :class="['badge', getStatusClass(emp.source_status)]">
              {{ formatStatus(emp.source_status) }}
            </span>
          </td>
          <td class="actions-cell">
            <div class="row-actions">
              <button 
                @click="$emit('view', emp)" 
                class="btn-icon" 
                :title="$t('common.info') || 'Chi tiết'"
              >
                <Eye :size="14" />
              </button>
              <button 
                @click="$emit('edit', emp)" 
                class="btn-icon" 
                :title="$t('device.action.rename') || 'Đổi tên'"
              >
                <Edit2 :size="14" />
              </button>
              <button 
                @click="$emit('coverage', emp)" 
                class="btn-icon btn-icon-coverage" 
                :title="$t('biometric.view_coverage') || 'Sinh trắc học'"
              >
                <Fingerprint :size="14" />
              </button>
              <button 
                @click="$emit('delete', emp)" 
                class="btn-icon delete" 
                :title="$t('device.action.delete') || 'Xóa'"
              >
                <Trash2 :size="14" />
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="employees.length === 0">
          <td colspan="8" class="empty-state">
            <Inbox :size="38" class="empty-icon" />
            <span>{{ $t('attendance.table.no_records') }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, Edit2, Fingerprint, Trash2, ArrowUp, ArrowDown, Inbox } from 'lucide-vue-next'

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
.sortable {
  cursor: pointer;
  user-select: none;
}
.th-content {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sort-icon-box {
  color: var(--cyan);
}

.id-badge {
  font-family: var(--font-mono);
  font-weight: 700;
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 7px;
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 0.84rem;
}

.emp-name-val {
  font-weight: 600;
  color: #f1f5f9;
}

.dept-cell, .group-cell {
  color: #cbd5e1;
  font-size: 0.86rem;
}

.dimmed {
  opacity: 0.35;
}

.actions-cell {
  text-align: center;
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-icon-coverage:hover {
  background: rgba(6, 182, 212, 0.15);
  border-color: var(--cyan);
  color: #22d3ee;
}
</style>
