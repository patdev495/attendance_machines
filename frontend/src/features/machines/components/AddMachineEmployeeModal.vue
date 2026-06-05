<template>
  <Transition name="fade-backdrop">
    <div v-if="isOpen" class="modal-backdrop" @click="close">
      <Transition name="scale-modal" appear>
        <form class="modal-card" @submit.prevent="submit" @click.stop>
          <div class="modal-header">
            <div class="icon-wrap">
              <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M16 11h6"/></svg>
            </div>
            <h3>Thêm nhân viên vào máy</h3>
            <p>{{ ip }}</p>
          </div>

          <div class="modal-body">
            <label>
              <span>Mã nhân viên</span>
              <input ref="employeeInput" v-model.trim="form.employeeId" type="text" autocomplete="off" required />
            </label>

            <label>
              <span>Tên trên máy</span>
              <input v-model.trim="form.name" type="text" autocomplete="off" />
            </label>

            <label>
              <span>Role</span>
              <select v-model="form.role">
                <option value="employee">Nhân viên thường</option>
                <option value="manager" disabled>Quản trị viên (cần ảnh và mật khẩu)</option>
              </select>
            </label>

            <p class="note">
              Nhân viên mới được tạo trên riêng máy này. Nếu chưa có dữ liệu khuôn mặt, người này sẽ chưa chấm công bằng khuôn mặt được.
            </p>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" @click="close">Hủy</button>
            <button type="submit" class="btn btn-primary" :disabled="isSubmitting || !form.employeeId">
              {{ isSubmitting ? 'Đang thêm...' : 'Thêm nhân viên' }}
            </button>
          </div>
        </form>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { nextTick, reactive, ref, watch } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  ip: { type: String, required: true },
  isSubmitting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'submit'])

const employeeInput = ref(null)
const form = reactive({
  employeeId: '',
  name: '',
  role: 'employee',
})

watch(() => props.isOpen, async (open) => {
  if (!open) return
  form.employeeId = ''
  form.name = ''
  form.role = 'employee'
  await nextTick()
  employeeInput.value?.focus()
})

function close() {
  if (!props.isSubmitting) emit('close')
}

function submit() {
  if (!form.employeeId) return
  emit('submit', {
    employeeId: form.employeeId,
    name: form.name,
    role: form.role,
  })
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.7);
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
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 22px 24px 14px;
  text-align: center;
}

.icon-wrap {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
}

h3 {
  color: #fff;
  font-size: 1.2rem;
  margin: 0;
}

.modal-header p {
  color: #94a3b8;
  font-family: monospace;
  margin: 6px 0 0;
}

.modal-body {
  padding: 0 24px 20px;
  display: grid;
  gap: 14px;
}

label {
  display: grid;
  gap: 7px;
}

label span {
  color: #cbd5e1;
  font-size: 0.9rem;
  font-weight: 600;
}

input,
select {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #fff;
  padding: 11px 12px;
  font-size: 0.95rem;
  outline: none;
}

select option {
  background: #0f172a;
}

.note {
  color: #94a3b8;
  background: rgba(20, 184, 166, 0.08);
  border: 1px solid rgba(20, 184, 166, 0.18);
  border-radius: 10px;
  padding: 10px 12px;
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
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

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.fade-backdrop-enter-active,
.fade-backdrop-leave-active { transition: opacity 0.2s ease; }
.fade-backdrop-enter-from,
.fade-backdrop-leave-to { opacity: 0; }
.scale-modal-enter-active { transition: all 0.2s ease; }
.scale-modal-leave-active { transition: all 0.15s ease; }
.scale-modal-enter-from,
.scale-modal-leave-to { opacity: 0; transform: scale(0.96) translateY(10px); }
</style>
