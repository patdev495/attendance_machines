<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <h3>{{ $t('employees.details_title') }}</h3>
              <button class="btn-close" @click="close">×</button>
            </div>

            <div class="modal-body">
              <div class="details-grid">
                <div class="detail-item">
                  <label>{{ $t('employees.id_label') }}</label>
                  <div class="value">{{ formatValue(employee.employee_id) }}</div>
                </div>

                <div class="detail-item">
                  <label>{{ $t('employees.full_id_label') }}</label>
                  <div class="value">{{ formatValue(employee.full_emp_id) }}</div>
                </div>
                
                <div class="detail-item">
                  <label>{{ $t('employees.name_label') }}</label>
                  <div class="value">{{ formatValue(employee.emp_name) }}</div>
                </div>
                
                <div class="detail-item">
                  <label>{{ $t('employees.dept_label') }}</label>
                  <div class="value">{{ formatValue(employee.department) }}</div>
                </div>
                
                <div class="detail-item">
                  <label>{{ $t('employees.group_label') }}</label>
                  <div class="value">{{ formatValue(employee.group_name) }}</div>
                </div>
                
                <div class="detail-item">
                  <label>{{ $t('employees.shift_label') }}</label>
                  <div class="value">
                    <span v-if="employee.shift === 'D'" class="shift-badge night">{{ $t('attendance.filters.night_shift') }}</span>
                    <span v-else-if="employee.shift === 'N'" class="shift-badge day">{{ $t('attendance.filters.day_shift') }}</span>
                    <span v-else-if="employee.shift === 'TV'" class="shift-badge resigned">{{ $t('attendance.filters.resigned') }}</span>
                    <span v-else>{{ formatValue(employee.shift) }}</span>
                  </div>
                </div>
                
                <div class="detail-item">
                  <label>{{ $t('device.table.status') }}</label>
                  <div class="value">
                    <span :class="['badge', getStatusClass(employee.source_status)]">
                      {{ formatStatus(employee.source_status) }}
                    </span>
                  </div>
                </div>

                <div class="detail-item">
                  <label>{{ $t('employees.start_date') }}</label>
                  <div class="value">{{ formatValue(employee.start_date) }}</div>
                </div>

                <div class="detail-item full-width">
                  <label>{{ $t('employees.last_updated') }}</label>
                  <div class="value">{{ formatDate(employee.updated_at) }}</div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-close-modal" @click="close">{{ $t('common.close') }}</button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps({
  isOpen: Boolean,
  employee: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

const close = () => {
  emit('close')
}

const formatValue = (val) => {
  if (val === null || val === undefined || val === '') return '-'
  // Handle epoch date strings commonly sent by backends or placeholder values
  if (val === '1970-01-01' || val === '01/01/1970') return '-'
  return val
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('vi-VN')
  } catch (e) {
    return dateStr
  }
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
  return status || '-'
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 11, 14, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1.5rem;
}

.modal-content {
  background: rgba(23, 25, 30, 0.95);
  width: 100%;
  max-width: 550px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: white;
  overflow: hidden;
}

.modal-header {
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  background: linear-gradient(to right, #60a5fa, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
  transition: color 0.2s;
}

.btn-close:hover {
  color: #f43f5e;
}

.modal-body {
  padding: 1.5rem;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item.full-width {
  grid-column: span 2;
}

.detail-item label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
  font-weight: 600;
}

.detail-item .value {
  font-size: 1rem;
  color: #e2e8f0;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
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

.shift-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.85rem;
}

.shift-badge.day {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.shift-badge.night {
  background: rgba(168, 85, 247, 0.2);
  color: #a855f7;
}

.shift-badge.resigned {
  background: rgba(244, 63, 94, 0.2);
  color: #fb7185;
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
}

.btn-close-modal {
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close-modal:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-color: rgba(255, 255, 255, 0.2);
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scale-enter-active, .scale-leave-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.scale-enter-from, .scale-leave-to { opacity: 0; transform: scale(0.95); }
</style>
