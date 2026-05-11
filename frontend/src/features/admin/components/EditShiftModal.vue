<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <h3>{{ isEdit ? $t('employees.shifts.modal.edit_title') : $t('employees.shifts.modal.add_title') }}</h3>
              <button class="btn-close" @click="close">×</button>
            </div>

            <div class="modal-body">
              <form @submit.prevent="handleSave">
                <!-- Shift Code -->
                <div class="form-group">
                  <label>{{ $t('employees.shifts.modal.code_label') }}</label>
                  <input 
                    type="text" 
                    v-model="formData.shift_code" 
                    :disabled="isEdit"
                    :class="{ 'input-disabled': isEdit }"
                    :placeholder="$t('employees.shifts.modal.code_placeholder')"
                    required
                  />
                </div>

                <!-- Shift Category -->
                <div class="form-group">
                  <label>{{ $t('employees.shifts.modal.cat_label') }}</label>
                  <select v-model="formData.shift_category" class="form-select">
                    <option value="NORMAL">{{ $t('employees.shifts.modal.cat_normal_hint') }}</option>
                    <option value="HOLIDAY">{{ $t('employees.shifts.modal.cat_holiday_hint') }}</option>
                    <option value="ROTATION">{{ $t('employees.shifts.modal.cat_rotation_hint') }}</option>
                  </select>
                </div>

                <div class="form-row">
                  <!-- Start Time -->
                  <div class="form-group flex-1">
                    <label>{{ $t('employees.shifts.modal.start_time') }}</label>
                    <input type="time" v-model="formData.start_time" step="1" />
                  </div>
                  <!-- End Time -->
                  <div class="form-group flex-1">
                    <label>{{ $t('employees.shifts.modal.end_time') }}</label>
                    <input type="time" v-model="formData.end_time" step="1" />
                  </div>
                </div>

                <!-- Night Shift Toggle -->
                <div class="form-group checkbox-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="formData.is_night_shift" />
                    <span>{{ $t('employees.shifts.modal.night_toggle') }}</span>
                  </label>
                </div>

                <!-- OT Start Time (Custom Anchor) -->
                <div class="form-group">
                  <label>{{ $t('employees.shifts.modal.ot_start_label') }} <span class="text-xs text-muted">{{ $t('employees.shifts.modal.ot_start_hint') }}</span></label>
                  <input type="time" v-model="formData.ot_start_time" step="1" />
                </div>


                <div class="form-row">
                  <!-- Work Hours -->
                  <div class="form-group flex-1">
                    <label>{{ $t('employees.shifts.modal.work_hours') }}</label>
                    <input type="number" v-model.number="formData.work_hours" step="0.1" min="0" />
                  </div>
                  <!-- Break Hours -->
                  <div class="form-group flex-1">
                    <label>{{ $t('employees.shifts.modal.break_hours') }}</label>
                    <input type="number" v-model.number="formData.break_hours" step="0.1" min="0" />
                  </div>
                </div>
                <div class="form-row">
                  <!-- P -->
                  <div class="form-group flex-1">
                    <label>P</label>
                    <input type="number" v-model.number="formData.leave_hours_p" step="0.1" min="0" />
                  </div>
                  <!-- R -->
                  <div class="form-group flex-1">
                    <label>R</label>
                    <input type="number" v-model.number="formData.leave_hours_r" step="0.1" min="0" />
                  </div>
                  <!-- O -->
                  <div class="form-group flex-1">
                    <label>O</label>
                    <input type="number" v-model.number="formData.leave_hours_o" step="0.1" min="0" />
                  </div>
                </div>

                <div class="form-row">
                  <!-- T -->
                  <div class="form-group flex-1">
                    <label>T</label>
                    <input type="number" v-model.number="formData.leave_hours_t" step="0.1" min="0" />
                  </div>
                  <!-- C -->
                  <div class="form-group flex-1">
                    <label>C</label>
                    <input type="number" v-model.number="formData.leave_hours_c" step="0.1" min="0" />
                  </div>
                  <!-- K -->
                  <div class="form-group flex-1">
                    <label>K</label>
                    <input type="number" v-model.number="formData.leave_hours_k" step="0.1" min="0" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group flex-1">
                    <label>{{ $t('employees.shifts.table.round') }}</label>
                    <input type="number" v-model.number="formData.standard_hours" step="0.1" min="0" />
                  </div>
                  <div class="form-group flex-1">
                    <label>{{ $t('employees.shifts.table.base') }}</label>
                    <input type="number" v-model.number="formData.workday_base" step="0.1" min="0" />
                  </div>
                </div>

                <div class="form-group">
                  <label>{{ $t('employees.shifts.modal.desc_label') }}</label>
                  <input type="text" v-model="formData.description" :placeholder="$t('employees.shifts.modal.desc_placeholder')" />
                </div>
              </form>
            </div>

            <div class="modal-footer">
              <button class="btn-cancel" @click="close" :disabled="loading">{{ $t('common.cancel') }}</button>
              <button class="btn-save" @click="handleSave" :disabled="loading">
                <span v-if="loading">{{ $t('employees.shifts.modal.saving') }}</span>
                <span v-else>{{ $t('employees.shifts.modal.save_btn') }}</span>
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { shiftsApi } from '../api.js'
import { useNotificationStore } from '@/stores/notification'

const { t } = useI18n()
const notify = useNotificationStore()

const props = defineProps({
  isOpen: Boolean,
  shift: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.shift)
const loading = ref(false)

const formData = ref({
  shift_code: '',
  shift_category: 'NORMAL',
  start_time: '08:00:00',
  end_time: '17:00:00',
  ot_start_time: null,
  is_night_shift: false,
  break_hours: 1.0,

  work_hours: 8.0,
  leave_hours_p: 0.0,
  leave_hours_r: 0.0,
  leave_hours_o: 0.0,
  leave_hours_t: 0.0,
  leave_hours_c: 0.0,
  leave_hours_k: 0.0,
  standard_hours: 8.0,
  workday_base: 8.0,
  description: ''
})

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (props.shift) {
      formData.value = { ...props.shift }
    } else {
      formData.value = {
        shift_code: '',
        shift_category: 'NORMAL',
        start_time: '08:00:00',
        end_time: '17:00:00',
        ot_start_time: null,
        is_night_shift: false,
        break_hours: 1.0,

        work_hours: 8.0,
        leave_hours_p: 0.0,
        leave_hours_r: 0.0,
        leave_hours_o: 0.0,
        leave_hours_t: 0.0,
        leave_hours_c: 0.0,
        leave_hours_k: 0.0,
        standard_hours: 8.0,
        workday_base: 8.0,
        description: ''
      }
    }
  }
})

const handleSave = async () => {
  if (!formData.value.shift_code) return
  
  loading.value = true
  try {
    if (isEdit.value) {
      await shiftsApi.updateShift(formData.value.shift_code, formData.value)
    } else {
      await shiftsApi.createShift(formData.value)
    }
    notify.success(t('common.updated_success'))
    emit('saved')
    close()
  } catch (err) {
    console.error(err)
    notify.error(t('common.error') + ': ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

const close = () => {
  if (!loading.value) {
    emit('close')
  }
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
  padding: 1rem;
}

.modal-content {
  background: rgba(23, 25, 30, 0.95);
  width: 100%;
  max-width: 480px;
  max-height: 95vh;
  overflow-y: auto;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: white;
}

.modal-header {
  padding: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  position: sticky;
  top: 0;
  background: rgba(23, 25, 30, 0.98);
  z-index: 10;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.4rem;
  cursor: pointer;
}

.modal-body {
  padding: 1.25rem;
}

.form-row {
  display: flex;
  gap: 0.75rem;
}

.flex-1 { flex: 1; }

.form-group {
  margin-bottom: 0.75rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.35rem;
  color: #94a3b8;
  font-size: 0.8rem;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.65rem;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: white;
  outline: none;
  font-size: 0.9rem;
}

.form-group select option {
  background: #1e293b;
  color: white;
}

.form-group input:focus,
.form-group select:focus {
  border-color: #3b82f6;
}

.checkbox-group {
  padding: 0.25rem 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.85rem;
}

.input-disabled {
  background-color: rgba(255, 255, 255, 0.05) !important;
  color: #64748b !important;
  cursor: not-allowed;
}

.modal-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  position: sticky;
  bottom: 0;
  background: rgba(23, 25, 30, 0.98);
  z-index: 10;
}

button {
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-cancel {
  background-color: transparent;
  color: #94a3b8;
}

.btn-save {
  background-color: #3b82f6;
  color: white;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scale-enter-active, .scale-leave-active { transition: all 0.2s; }
.scale-enter-from, .scale-leave-to { opacity: 0; transform: scale(0.95); }
</style>
