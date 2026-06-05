<template>
  <Transition name="fade-backdrop">
    <div v-if="isOpen" class="modal-backdrop" @click="close">
      <Transition name="scale-modal" appear>
        <form class="modal-card" @submit.prevent="submit" @click.stop>
          <div class="modal-header">
            <h3>{{ $t('device.machine_employee.edit_title') }}</h3>
            <p>{{ ip }} · {{ employee?.user_id }}</p>
          </div>

          <div class="modal-body">
            <label>
              <span>{{ $t('device.machine_employee.employee_id') }}</span>
              <input :value="employee?.user_id || ''" type="text" disabled />
            </label>

            <div class="role-tabs">
              <button type="button" :class="['role-tab', form.role === 'employee' ? 'active' : '']" @click="form.role = 'employee'">
                {{ $t('device.roles.employee') }}
              </button>
              <button type="button" :class="['role-tab', form.role === 'admin' ? 'active admin' : '']" @click="form.role = 'admin'">
                {{ $t('device.roles.admin') }}
              </button>
              <button type="button" :class="['role-tab', form.role === 'super_admin' ? 'active super' : '']" @click="form.role = 'super_admin'">
                {{ $t('device.roles.super_admin') }}
              </button>
            </div>

            <label v-if="form.role === 'employee'">
              <span>{{ $t('device.machine_employee.device_name') }}</span>
              <input ref="nameInput" v-model.trim="form.name" type="text" autocomplete="off" :placeholder="$t('device.machine_employee.device_name_placeholder')" />
            </label>

            <label v-if="isManagerRole">
              <span>{{ $t('device.machine_employee.manager_password') }}</span>
              <input v-model.trim="form.password" type="text" autocomplete="off" :placeholder="$t('device.machine_employee.manager_password_placeholder')" />
              <small>{{ $t('device.machine_employee.manager_password_hint') }}</small>
            </label>

            <div class="photo-section">
              <span>{{ $t('device.machine_employee.face_photo') }}</span>
              <button type="button" class="photo-button" @click="fileInput?.click()">
                {{ photoPreview ? $t('device.machine_employee.change_selected_photo') : $t('device.machine_employee.choose_new_photo') }}
              </button>
              <input ref="fileInput" type="file" accept="image/jpeg,image/jpg" hidden @change="handleFileSelect" />
              <img v-if="photoPreview" :src="photoPreview" class="photo-preview" alt="preview" />
              <button v-if="photoPreview" type="button" class="clear-photo" @click="clearPhoto">
                {{ $t('device.machine_employee.clear_new_photo') }}
              </button>
              <small>{{ $t('device.machine_employee.preserve_existing_photo') }}</small>
            </div>

            <div v-if="errorMessage" class="error-msg">{{ errorMessage }}</div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" @click="close">{{ $t('common.cancel') }}</button>
            <button type="submit" class="btn btn-primary" :disabled="isSubmitting || !employee?.user_id">
              {{ isSubmitting ? $t('device.machine_employee.saving') : $t('device.machine_employee.save_changes') }}
            </button>
          </div>
        </form>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  ip: { type: String, required: true },
  employee: { type: Object, default: null },
  isSubmitting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'submit'])
const { t } = useI18n()

const nameInput = ref(null)
const fileInput = ref(null)
const photoPreview = ref('')
const photoBase64 = ref('')
const errorMessage = ref('')

const form = reactive({
  name: '',
  role: 'employee',
  password: '',
})

const isManagerRole = computed(() => form.role === 'admin' || form.role === 'super_admin')

watch(() => props.isOpen, async (open) => {
  if (!open) return
  form.name = props.employee?.name || props.employee?.db_name || ''
  form.role = normalizeRole(props.employee?.role)
  form.password = ''
  clearPhoto()
  errorMessage.value = ''
  await nextTick()
  nameInput.value?.focus()
})

function normalizeRole(role) {
  if (role === 'Super Admin') return 'super_admin'
  if (role === 'Admin' || role === 'Machine Manager') return 'admin'
  return 'employee'
}

function close() {
  if (!props.isSubmitting) emit('close')
}

function clearPhoto() {
  photoPreview.value = ''
  photoBase64.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  errorMessage.value = ''

  if (!file.type.startsWith('image/jpeg') && !file.name.toLowerCase().endsWith('.jpg')) {
    errorMessage.value = t('device.machine_employee.jpeg_only')
    return
  }

  const reader = new FileReader()
  reader.onload = (event) => {
    const result = event.target.result
    photoPreview.value = result
    photoBase64.value = result.split(',')[1] || ''
  }
  reader.readAsDataURL(file)
}

function submit() {
  emit('submit', {
    employeeId: props.employee?.user_id,
    name: form.name,
    role: form.role,
    password: form.password,
    photoBase64: photoBase64.value,
  })
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(8px);
  z-index: 10002;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  width: 100%;
  max-width: 460px;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 22px 24px 12px;
}

h3 {
  margin: 0;
  color: #fff;
  font-size: 1.15rem;
}

.modal-header p {
  margin: 6px 0 0;
  color: #94a3b8;
  font-family: monospace;
}

.modal-body {
  padding: 0 24px 20px;
  display: grid;
  gap: 14px;
}

label, .photo-section {
  display: grid;
  gap: 7px;
}

label > span, .photo-section > span {
  color: #cbd5e1;
  font-size: 0.9rem;
  font-weight: 600;
}

input {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #fff;
  padding: 11px 12px;
  font-size: 0.95rem;
  outline: none;
  box-sizing: border-box;
}

input:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

small {
  color: #64748b;
  font-size: 0.78rem;
}

.role-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 6px;
}

.role-tab {
  padding: 9px 6px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.role-tab.active { background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.3); color: #60a5fa; }
.role-tab.active.admin { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.3); color: #fbbf24; }
.role-tab.active.super { background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.3); color: #a78bfa; }

.photo-button, .clear-photo {
  width: fit-content;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(99, 102, 241, 0.12);
  color: #a5b4fc;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 700;
}

.clear-photo {
  border-color: rgba(239, 68, 68, 0.25);
  background: rgba(239, 68, 68, 0.12);
  color: #f87171;
}

.photo-preview {
  max-width: 140px;
  max-height: 140px;
  border-radius: 8px;
  object-fit: cover;
}

.error-msg {
  color: #f87171;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.85rem;
}

.modal-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 18px 24px 22px;
  background: rgba(255, 255, 255, 0.02);
}

.btn {
  padding: 11px 12px;
  border: none;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
}

.btn:disabled { cursor: not-allowed; opacity: 0.45; }
.btn-ghost { background: rgba(255, 255, 255, 0.06); color: #cbd5e1; }
.btn-primary { background: #3b82f6; color: white; }

.fade-backdrop-enter-active,
.fade-backdrop-leave-active { transition: opacity 0.2s ease; }
.fade-backdrop-enter-from,
.fade-backdrop-leave-to { opacity: 0; }
.scale-modal-enter-active { transition: all 0.2s ease; }
.scale-modal-leave-active { transition: all 0.15s ease; }
.scale-modal-enter-from,
.scale-modal-leave-to { opacity: 0; transform: scale(0.96) translateY(10px); }
</style>
