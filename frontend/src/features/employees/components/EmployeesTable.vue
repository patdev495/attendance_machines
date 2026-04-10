<template>
  <div class="table-container">
    <table class="employees-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Machine Name</th>
          <th>Department</th>
          <th>Group</th>
          <th>Shift</th>
          <th>Source Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="emp in employees" :key="emp.employee_id">
          <td>{{ emp.employee_id }}</td>
          <td>{{ emp.emp_name || '—' }}</td>
          <td>{{ emp.machine_name || '—' }}</td>
          <td>{{ emp.department || '—' }}</td>
          <td>{{ emp.group_name || '—' }}</td>
          <td>{{ emp.shift || '—' }}</td>
          <td>
            <span :class="['badge', getStatusClass(emp.source_status)]">
              {{ formatStatus(emp.source_status) }}
            </span>
          </td>
          <td class="actions">
            <button @click="$emit('edit', emp)" class="btn-edit" title="Rename and Update">Edit</button>
            <button @click="$emit('delete', emp)" class="btn-delete" title="Hard Delete from Machine">Delete</button>
            <button @click="$emit('coverage', emp)" class="btn-info" title="Check Biometric Coverage">Coverage</button>
          </td>
        </tr>
        <tr v-if="employees.length === 0">
          <td colspan="8" class="empty-state">No employees found.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  employees: {
    type: Array,
    required: true,
    default: () => []
  }
})

const emit = defineEmits(['edit', 'delete', 'coverage'])

const getStatusClass = (status) => {
  if (status === 'excel_synced') return 'badge-excel'
  if (status === 'machine_only') return 'badge-machine'
  return 'badge-log'
}

const formatStatus = (status) => {
  if (status === 'excel_synced') return 'Excel'
  if (status === 'machine_only') return 'Machine Only'
  if (status === 'log_only') return 'Log Only'
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

.btn-delete {
  background-color: #ef4444;
  color: white;
}

.btn-info {
  background-color: #8b5cf6;
  color: white;
}
</style>
