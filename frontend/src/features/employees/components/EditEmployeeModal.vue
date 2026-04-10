<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <h3>Edit Employee</h3>
              <button class="btn-close" @click="close">×</button>
            </div>

            <div class="modal-body">
              <form @submit.prevent="handleSave">
                <div class="form-group">
                  <label>ID</label>
                  <input type="text" :value="employee.employee_id" disabled class="input-disabled" />
                </div>
                
                <div class="form-group">
                  <label>Name</label>
                  <input type="text" v-model="formData.emp_name" placeholder="Leave empty if N/A" />
                </div>
                
                <div class="form-group">
                  <label>Department</label>
                  <input type="text" v-model="formData.department" placeholder="Department" />
                </div>
                
                <div class="form-group">
                  <label>Group</label>
                  <input type="text" v-model="formData.group_name" placeholder="Group" />
                </div>
                
                <div class="form-group">
                  <label>Shift</label>
                  <select v-model="formData.shift">
                    <option value="">N/A</option>
                    <option value="D">Day</option>
                    <option value="N">Night</option>
                  </select>
                </div>
              </form>
            </div>

            <div class="modal-footer">
              <button class="btn-cancel" @click="close" :disabled="loading">Cancel</button>
              <button class="btn-save" @click="handleSave" :disabled="loading">
                <span v-if="loading">Saving & Syncing...</span>
                <span v-else>Save Changes</span>
              </button>
            </div>
            
            <div v-if="saveResult" class="save-result">
              <h4>Sync Results</h4>
              <ul>
                <li v-for="(res, ip) in saveResult" :key="ip">
                  {{ ip }}: {{ res }}
                </li>
              </ul>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { employeesApi } from '../api.js'

const props = defineProps({
  isOpen: Boolean,
  employee: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close', 'saved'])

const loading = ref(false)
const saveResult = ref(null)

const formData = ref({
  emp_name: '',
  department: '',
  group_name: '',
  shift: ''
})

watch(() => props.isOpen, (newVal) => {
  if (newVal && props.employee) {
    formData.value = {
      emp_name: props.employee.emp_name || '',
      department: props.employee.department || '',
      group_name: props.employee.group_name || '',
      shift: props.employee.shift || ''
    }
    saveResult.value = null
  }
})

const handleSave = async () => {
  if (!props.employee.employee_id) return
  loading.value = true
  try {
    const res = await employeesApi.updateEmployeeName(
      props.employee.employee_id,
      formData.value.emp_name,
      formData.value.department,
      formData.value.group_name,
      formData.value.shift
    )
    saveResult.value = res.results
    // Delay closing to show results briefly
    setTimeout(() => {
      emit('saved')
      close()
    }, 2000)
  } catch (err) {
    console.error(err)
    alert('Failed to save changes')
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
  padding: 1.5rem;
}

.modal-content {
  background: rgba(23, 25, 30, 0.95);
  width: 100%;
  max-width: 450px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: white;
}

.modal-header {
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
}

.btn-close:hover {
  color: #f43f5e;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #cbd5e1;
  font-size: 0.9rem;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 0.75rem;
  border-radius: 6px;
  border: 1px solid #475569;
  background-color: transparent;
  color: white;
  outline: none;
}

.form-group input:focus, .form-group select:focus {
  border-color: #3b82f6;
}

.input-disabled {
  background-color: #1e293b !important;
  color: #94a3b8 !important;
  cursor: not-allowed;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

button {
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  border: none;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  background-color: transparent;
  color: #cbd5e1;
}

.btn-cancel:hover {
  color: white;
}

.btn-save {
  background-color: #3b82f6;
  color: white;
}

.btn-save:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-save:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.save-result {
  padding: 0 1.5rem 1.5rem;
  font-size: 0.85rem;
  color: #a7f3d0;
}

.save-result h4 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
}

.save-result ul {
  margin: 0;
  padding-left: 1.5rem;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scale-enter-active, .scale-leave-active { transition: all 0.3s; }
.scale-enter-from, .scale-leave-to { opacity: 0; transform: scale(0.95); }
</style>
