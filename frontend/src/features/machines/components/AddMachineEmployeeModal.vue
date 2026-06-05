<template>
  <Transition name="fade-backdrop">
    <div v-if="isOpen" class="modal-backdrop" @click="close">
      <Transition name="scale-modal" appear>
        <form class="modal-card" @submit.prevent="submit" @click.stop>
          <div class="modal-header">
            <div class="icon-wrap" :class="iconClass">
              <svg v-if="form.role === 'employee'" xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M16 11h6"/></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <h3>{{ isManagerRole ? $t('device.machine_employee.add_manager_title') : $t('device.machine_employee.add_employee_title') }}</h3>
            <p>{{ ip }}</p>
          </div>

          <div class="modal-body">
            <div class="role-tabs">
              <button type="button" :class="['role-tab', form.role === 'employee' ? 'active' : '']" @click="form.role = 'employee'">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M16 11h6"/></svg>
                {{ $t('device.roles.employee') }}
              </button>
              <button type="button" :class="['role-tab', form.role === 'admin' ? 'active admin' : '']" @click="form.role = 'admin'">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                {{ $t('device.roles.admin') }}
              </button>
              <button type="button" :class="['role-tab', form.role === 'super_admin' ? 'active super' : '']" @click="form.role = 'super_admin'">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                {{ $t('device.roles.super_admin') }}
              </button>
            </div>

            <div class="role-description" :class="roleDescClass">
              <template v-if="form.role === 'employee'">
                <strong>{{ $t('device.machine_employee.role_employee_title') }}</strong> — {{ $t('device.machine_employee.role_employee_desc') }}
              </template>
              <template v-else-if="form.role === 'admin'">
                <strong>{{ $t('device.machine_employee.role_admin_title') }}</strong> — {{ $t('device.machine_employee.role_admin_desc') }}
                <span class="required-badge">{{ $t('device.machine_employee.photo_required_badge') }}</span>
              </template>
              <template v-else>
                <strong>{{ $t('device.machine_employee.role_super_title') }}</strong> — {{ $t('device.machine_employee.role_super_desc') }}
                <span class="required-badge">{{ $t('device.machine_employee.photo_required_badge') }}</span>
              </template>
            </div>

            <label>
              <span>{{ isManagerRole ? $t('device.machine_employee.manager_id') : $t('device.machine_employee.employee_id') }}</span>
              <input ref="employeeInput" v-model.trim="form.employeeId" type="text" autocomplete="off" required :placeholder="isManagerRole ? $t('device.machine_employee.manager_id_placeholder') : $t('device.machine_employee.employee_id_placeholder')" />
            </label>

            <label v-if="form.role === 'employee'">
              <span>{{ $t('device.machine_employee.device_name') }}</span>
              <input v-model.trim="form.name" type="text" autocomplete="off" :placeholder="$t('device.machine_employee.device_name_placeholder')" />
            </label>

            <div class="photo-section">
              <span class="field-label">
                {{ $t('device.machine_employee.face_photo') }}
                <span v-if="isManagerRole" class="required-star">*</span>
              </span>
              <div class="photo-drop" :class="{ 'has-photo': photoPreview, 'required': isManagerRole && !photoPreview }" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
                <img v-if="photoPreview" :src="photoPreview" class="photo-preview" alt="preview" />
                <div v-else class="photo-placeholder">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                  <p>{{ $t('device.machine_employee.photo_drop') }}</p>
                  <p class="drop-hint">{{ isManagerRole ? $t('device.machine_employee.photo_manager_hint') : $t('device.machine_employee.photo_optional_hint') }}</p>
                </div>
              </div>
              <input ref="fileInput" type="file" accept="image/jpeg,image/jpg" style="display:none" @change="handleFileSelect" />
              <button v-if="photoPreview" type="button" class="btn-remove-photo" @click.stop="clearPhoto">
                × {{ $t('device.machine_employee.remove_photo') }}
              </button>
            </div>

            <label v-if="isManagerRole">
              <span>{{ $t('device.machine_employee.manager_password') }} <span class="required-star">*</span></span>
              <input v-model.trim="form.password" type="text" autocomplete="off" :placeholder="$t('device.machine_employee.manager_password_unique_placeholder')" required />
              <span class="field-hint">{{ $t('device.machine_employee.manager_password_hint') }}</span>
            </label>

            <div v-if="errorMessage" class="error-msg">⚠ {{ errorMessage }}</div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" @click="close">{{ $t('common.cancel') }}</button>
            <button type="submit" class="btn btn-primary" :class="{ 'btn-admin': isManagerRole }" :disabled="isSubmitting || !canSubmit">
              {{ isSubmitting ? $t('device.machine_employee.adding') : (isManagerRole ? $t('device.machine_employee.register_manager') : $t('device.machine_employee.add_employee_button')) }}
            </button>
          </div>
        </form>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { nextTick, reactive, ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  ip: { type: String, required: true },
  isSubmitting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'submit'])
const { t } = useI18n()

const employeeInput = ref(null)
const fileInput = ref(null)
const photoPreview = ref(null)
const photoBase64 = ref('')
const errorMessage = ref('')

const form = reactive({
  employeeId: '',
  name: '',
  role: 'employee',
  password: '123456',
})

const isManagerRole = computed(() => form.role === 'admin' || form.role === 'super_admin')

const canSubmit = computed(() => {
  if (!form.employeeId) return false
  if (isManagerRole.value && !photoBase64.value) return false
  if (isManagerRole.value && !form.password.trim()) return false
  return true
})

const iconClass = computed(() => ({
  'icon-blue': form.role === 'employee',
  'icon-amber': form.role === 'admin',
  'icon-purple': form.role === 'super_admin',
}))

const roleDescClass = computed(() => ({
  'desc-employee': form.role === 'employee',
  'desc-admin': form.role === 'admin',
  'desc-super': form.role === 'super_admin',
}))

watch(() => props.isOpen, async (open) => {
  if (!open) return
  form.employeeId = ''
  form.name = ''
  form.role = 'employee'
  form.password = '123456'
  clearPhoto()
  errorMessage.value = ''
  await nextTick()
  employeeInput.value?.focus()
})

function close() {
  if (!props.isSubmitting) emit('close')
}

function triggerFileInput() {
  fileInput.value?.click()
}

function clearPhoto() {
  photoPreview.value = null
  photoBase64.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) processImageFile(file)
}

function handleDrop(e) {
  const file = e.dataTransfer.files?.[0]
  if (file) processImageFile(file)
}

function processImageFile(file) {
  errorMessage.value = ''

  if (!file.type.startsWith('image/jpeg') && !file.name.toLowerCase().endsWith('.jpg')) {
    errorMessage.value = t('device.machine_employee.jpeg_only')
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target.result
    const base64 = result.split(',')[1] || ''
    const sizeKB = Math.round((base64.length * 3/4) / 1024)

    if (isManagerRole.value && sizeKB < 15) {
      errorMessage.value = t('device.machine_employee.photo_too_small', { size: sizeKB })
      return
    }

    photoPreview.value = result
    photoBase64.value = base64
  }
  reader.readAsDataURL(file)
}

function submit() {
  errorMessage.value = ''

  if (!form.employeeId) return

  if (isManagerRole.value && !photoBase64.value) {
    errorMessage.value = t('device.machine_employee.photo_required')
    return
  }

  emit('submit', {
    employeeId: form.employeeId,
    name: form.name,
    role: form.role,
    photoBase64: photoBase64.value,
    password: form.password,
  })
}
</script>

<style scoped>
.modal-backdrop { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.75); backdrop-filter: blur(8px); z-index: 10002; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-card { width: 100%; max-width: 500px; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 18px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); max-height: 90vh; overflow-y: auto; }
.modal-header { padding: 22px 24px 14px; text-align: center; }
.icon-wrap { width: 54px; height: 54px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; transition: background 0.3s; }
.icon-blue { background: rgba(59, 130, 246, 0.12); color: #60a5fa; }
.icon-amber { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.icon-purple { background: rgba(139, 92, 246, 0.12); color: #a78bfa; }
h3 { color: #fff; font-size: 1.2rem; margin: 0; transition: color 0.2s; }
.modal-header p { color: #94a3b8; font-family: monospace; margin: 6px 0 0; }
.role-tabs { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; background: rgba(255,255,255,0.03); border-radius: 12px; padding: 6px; }
.role-tab { display: flex; align-items: center; gap: 6px; justify-content: center; padding: 9px 6px; border: 1px solid transparent; border-radius: 8px; background: transparent; color: #64748b; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.role-tab:hover { color: #94a3b8; background: rgba(255,255,255,0.04); }
.role-tab.active { background: rgba(59,130,246,0.15); border-color: rgba(59,130,246,0.3); color: #60a5fa; }
.role-tab.active.admin { background: rgba(245,158,11,0.15); border-color: rgba(245,158,11,0.3); color: #fbbf24; }
.role-tab.active.super { background: rgba(139,92,246,0.15); border-color: rgba(139,92,246,0.3); color: #a78bfa; }
.role-description { padding: 10px 14px; border-radius: 10px; font-size: 0.83rem; line-height: 1.5; border: 1px solid; }
.desc-employee { color: #94a3b8; background: rgba(20,184,166,0.06); border-color: rgba(20,184,166,0.15); }
.desc-admin { color: #fde68a; background: rgba(245,158,11,0.08); border-color: rgba(245,158,11,0.2); }
.desc-super { color: #e9d5ff; background: rgba(139,92,246,0.08); border-color: rgba(139,92,246,0.2); }
.required-badge { display: inline-block; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #f87171; border-radius: 6px; padding: 1px 6px; font-size: 0.77rem; font-weight: 700; }
.modal-body { padding: 0 24px 20px; display: grid; gap: 14px; }
label { display: grid; gap: 7px; }
.field-label, label > span:first-child { color: #cbd5e1; font-size: 0.9rem; font-weight: 600; }
.field-hint { color: #64748b; font-size: 0.78rem; }
.required-star { color: #f87171; }
input, select { width: 100%; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #fff; padding: 11px 12px; font-size: 0.95rem; outline: none; box-sizing: border-box; transition: border-color 0.2s; }
input:focus { border-color: rgba(99,102,241,0.5); }
select option { background: #0f172a; }
.photo-section { display: grid; gap: 8px; }
.photo-drop { border: 2px dashed rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; text-align: center; cursor: pointer; transition: all 0.2s; min-height: 120px; display: flex; align-items: center; justify-content: center; }
.photo-drop:hover { border-color: rgba(99,102,241,0.4); background: rgba(99,102,241,0.04); }
.photo-drop.required { border-color: rgba(245,158,11,0.4); }
.photo-drop.has-photo { border-style: solid; border-color: rgba(34,197,94,0.3); padding: 8px; }
.photo-placeholder { color: #64748b; }
.photo-placeholder p { margin: 8px 0 0; font-size: 0.88rem; }
.drop-hint { font-size: 0.78rem !important; color: #475569 !important; }
.photo-preview { max-width: 100%; max-height: 180px; border-radius: 8px; object-fit: cover; }
.btn-remove-photo { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); color: #f87171; border-radius: 8px; padding: 6px 12px; font-size: 0.82rem; cursor: pointer; width: fit-content; font-weight: 600; }
.btn-remove-photo:hover { background: rgba(239,68,68,0.2); }
.error-msg { color: #f87171; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 10px; padding: 10px 12px; font-size: 0.85rem; }
.modal-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 18px 24px 22px; background: rgba(255, 255, 255, 0.02); }
.btn { padding: 11px 12px; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; transition: all 0.2s; }
.btn:disabled { cursor: not-allowed; opacity: 0.45; }
.btn-ghost { background: rgba(255, 255, 255, 0.06); color: #cbd5e1; }
.btn-ghost:hover:not(:disabled) { background: rgba(255,255,255,0.1); }
.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-admin { background: linear-gradient(135deg, #f59e0b, #d97706); }
.btn-admin:hover:not(:disabled) { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
.fade-backdrop-enter-active, .fade-backdrop-leave-active { transition: opacity 0.2s ease; }
.fade-backdrop-enter-from, .fade-backdrop-leave-to { opacity: 0; }
.scale-modal-enter-active { transition: all 0.2s ease; }
.scale-modal-leave-active { transition: all 0.15s ease; }
.scale-modal-enter-from, .scale-modal-leave-to { opacity: 0; transform: scale(0.96) translateY(10px); }
</style>
