<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl">
            <div class="modal-header">
              <h3>{{ isEdit ? 'Chỉnh Sửa Ca Làm Việc' : 'Thêm Ca Làm Việc Mới' }}</h3>
              <button class="btn-close" @click="close">×</button>
            </div>

            <div class="modal-body">
              <form @submit.prevent="handleSave">
                <!-- Shift Code -->
                <div class="form-group">
                  <label>Mã Ca Làm Việc (Ví dụ: N, D12, 4N4P)</label>
                  <input 
                    type="text" 
                    v-model="formData.shift_code" 
                    :disabled="isEdit"
                    :class="{ 'input-disabled': isEdit }"
                    placeholder="Nhập mã ca..."
                    required
                  />
                </div>

                <!-- Shift Category -->
                <div class="form-group">
                  <label>Phân Loại Ngày Làm Việc (Tính công/Tăng ca)</label>
                  <select v-model="formData.shift_category" class="form-select">
                    <option value="NORMAL">Ngày Thường (Tính công chuẩn/OT thường)</option>
                    <option value="HOLIDAY">Nghỉ Lễ (Tính công/OT Lễ)</option>
                    <option value="ROTATION">Nghỉ Luân Phiên (Tính công/OT Luân phiên)</option>
                  </select>
                </div>

                <div class="form-row">
                  <!-- Start Time -->
                  <div class="form-group flex-1">
                    <label>Giờ Bắt Đầu</label>
                    <input type="time" v-model="formData.start_time" step="1" />
                  </div>
                  <!-- End Time -->
                  <div class="form-group flex-1">
                    <label>Giờ Kết Thúc</label>
                    <input type="time" v-model="formData.end_time" step="1" />
                  </div>
                </div>

                <!-- Night Shift Toggle -->
                <div class="form-group checkbox-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="formData.is_night_shift" />
                    <span>Đây là ca đêm (Kết thúc vào sáng hôm sau)</span>
                  </label>
                </div>

                <!-- OT Start Time (Custom Anchor) -->
                <div class="form-group">
                  <label>Mốc Tính Tăng Ca <span class="text-xs text-muted">(Bỏ trống = Tính từ lúc kết thúc ca)</span></label>
                  <input type="time" v-model="formData.ot_start_time" step="1" placeholder="Bỏ trống nếu tính từ lúc hết ca" />
                </div>


                <div class="form-row">
                  <!-- Work Hours -->
                  <div class="form-group flex-1">
                    <label>Số Giờ Làm Thực Tế</label>
                    <input type="number" v-model.number="formData.work_hours" step="0.1" min="0" />
                  </div>
                  <!-- Break Hours -->
                  <div class="form-group flex-1">
                    <label>Số Giờ Nghỉ Giữa Ca</label>
                    <input type="number" v-model.number="formData.break_hours" step="0.1" min="0" />
                  </div>
                </div>
                <div class="form-row">
                  <!-- P -->
                  <div class="form-group flex-1">
                    <label>Phép (P)</label>
                    <input type="number" v-model.number="formData.leave_hours_p" step="0.1" min="0" />
                  </div>
                  <!-- R -->
                  <div class="form-group flex-1">
                    <label>Việc Riêng (R)</label>
                    <input type="number" v-model.number="formData.leave_hours_r" step="0.1" min="0" />
                  </div>
                  <!-- O -->
                  <div class="form-group flex-1">
                    <label>Ốm (O)</label>
                    <input type="number" v-model.number="formData.leave_hours_o" step="0.1" min="0" />
                  </div>
                </div>

                <div class="form-row">
                  <!-- T -->
                  <div class="form-group flex-1">
                    <label>Tang (T)</label>
                    <input type="number" v-model.number="formData.leave_hours_t" step="0.1" min="0" />
                  </div>
                  <!-- C -->
                  <div class="form-group flex-1">
                    <label>Cưới (C)</label>
                    <input type="number" v-model.number="formData.leave_hours_c" step="0.1" min="0" />
                  </div>
                  <!-- K -->
                  <div class="form-group flex-1">
                    <label>Không Phép (K)</label>
                    <input type="number" v-model.number="formData.leave_hours_k" step="0.1" min="0" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group flex-1">
                    <label>Định Mức LÀM TRÒN (VD: 8.0, 12.0)</label>
                    <input type="number" v-model.number="formData.standard_hours" step="0.1" min="0" />
                  </div>
                  <div class="form-group flex-1">
                    <label>Định Mức CHIA CÔNG (VD: 8.0, 12.0)</label>
                    <input type="number" v-model.number="formData.workday_base" step="0.1" min="0" />
                  </div>
                </div>

                <div class="form-group">
                  <label>Mô Tả Ghi Chú</label>
                  <input type="text" v-model="formData.description" placeholder="Nhập mô tả ca..." />
                </div>
              </form>
            </div>

            <div class="modal-footer">
              <button class="btn-cancel" @click="close" :disabled="loading">Hủy Bỏ</button>
              <button class="btn-save" @click="handleSave" :disabled="loading">
                <span v-if="loading">Đang lưu...</span>
                <span v-else>Lưu Thông Tin</span>
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
import { shiftsApi } from '../api.js'
import { useNotificationStore } from '@/stores/notification'

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
    notify.success('Cập nhật thành công')
    emit('saved')
    close()
  } catch (err) {
    console.error(err)
    notify.error('Có lỗi xảy ra: ' + (err.response?.data?.detail || err.message))
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
