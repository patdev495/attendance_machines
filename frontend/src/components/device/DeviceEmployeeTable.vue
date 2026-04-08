<template>
  <div class="table-wrap card">
    <table>
      <thead>
        <tr>
          <th style="width:40px; text-align:center;">
            <input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="custom-chk" />
          </th>
          <th>{{ $t('device.table.emp_id') }}</th>
          <th>{{ $t('device.table.name_device') }}</th>
          <th>{{ $t('device.table.name_db') }}</th>
          <th>{{ $t('device.table.status') }}</th>
          <th>{{ $t('device.table.department') }}</th>
          <th style="text-align:right">{{ $t('device.table.action') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="employees.length === 0">
          <td colspan="7" class="empty-state">{{ $t('device.table.no_records') }}</td>
        </tr>
        <tr v-for="u in employees" :key="u.user_id" :class="{'selected-row': selectedIds.includes(u.user_id)}">
          <td style="text-align:center;">
            <input type="checkbox" :value="u.user_id" v-model="selectedIds" class="custom-chk" />
          </td>
          <td style="font-weight:600;color:#fff;">{{ u.user_id }}</td>
          <td>{{ u.name || '-' }}</td>
          <td style="color:#fff;">
            <span v-if="u.db_name">{{ u.db_name }}</span>
            <small v-else style="color:var(--text-muted)">{{ $t('device.table.not_synced') }}</small>
          </td>
          <td>
            <span v-if="u.status === 'TV'" class="badge-status-tv">{{ $t('device.table.resigned') }}</span>
            <span v-else-if="u.status === 'Unknown'" style="color:var(--text-muted);font-size:0.83rem;">{{ $t('device.table.unknown') }}</span>
            <span v-else class="badge-status-active">{{ $t('device.table.active') }}</span>
          </td>
          <td>{{ u.department || '-' }}</td>
          <td style="text-align:right;">
            <div class="action-group">
              <button class="btn-icon" :title="$t('device.action.sync_finger')" @click="$emit('syncFinger', u.user_id)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12c0-2.8 2.2-5 5-5s5 2.2 5 5-2.2 5-5 5-5-2.2-5-5Z"/><path d="M7 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M12 9s2-2 5-2 5 2 5 2"/><path d="M12 12s2-2 5-2 5 2 5 2"/><path d="M12 15s2-2 5-2 5 2 5 2"/></svg>
              </button>
              <button class="btn-icon" :title="$t('device.action.rename')" @click="$emit('rename', u)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
              </button>
              <button class="btn-delete" :title="$t('device.action.delete')" @click="$emit('delete', u.user_id)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({ employees: { type: Array, default: () => [] } })
const emit = defineEmits(['delete', 'rename', 'syncFinger', 'selection-change'])

const selectedIds = ref([])

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
  // Clear selection when page changes
  selectedIds.value = []
})
</script>

<style scoped>
.table-wrap { overflow-x: auto; }
.action-group {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
.btn-icon {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-muted);
  border-radius: 6px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-icon:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-color: var(--primary-color);
}
.custom-chk {
  width: 16px; 
  height: 16px; 
  cursor: pointer;
  accent-color: var(--primary-color);
}
.selected-row {
  background: rgba(99, 102, 241, 0.1) !important;
}
</style>
