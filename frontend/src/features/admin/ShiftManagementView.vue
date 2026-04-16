<template>
  <div class="shift-management-view">
    <div class="header">
      <div class="title-section">
        <h1>Quản Lý Ca Làm Việc</h1>
        <p class="subtitle">Định nghĩa giờ bắt đầu, kết thúc, giờ nghỉ và định mức công cho từng mã ca.</p>
      </div>
      
      <button class="btn-add btn-primary shadow-lg" @click="handleAdd">
        <span class="icon">+</span> Thêm Ca Mới
      </button>
    </div>

    <div class="glass-container">
      <div class="table-wrapper">
        <table class="shift-table">
          <thead>
            <tr>
              <th>Mã Ca</th>
              <th>Khung Giờ</th>
              <th>Loại Ngày</th>
              <th class="text-center">Công</th>
              <th class="text-center">Nghỉ</th>
              <th class="text-center" title="Nghỉ Phép">P</th>
              <th class="text-center" title="Việc Riêng">R</th>
              <th class="text-center" title="Ốm/Khác">O</th>
              <th class="text-center" title="Nghỉ Tang">T</th>
              <th class="text-center" title="Nghỉ Cưới">C</th>
              <th class="text-center" title="Không Phép">K</th>
              <th class="text-center" title="Định mức làm tròn">Tròn</th>
              <th class="text-center" title="Định mức chia công">Chia</th>
              <th>Mô Tả</th>
              <th class="text-right">Thao Tác</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="shift in shifts" :key="shift.shift_code" class="shift-row">
              <td>
                <span class="shift-badge" :class="{ 'night': shift.is_night_shift }">
                  {{ shift.shift_code }}
                </span>
              </td>
              <td class="time-col">
                <div class="time-window">
                  <span class="time">{{ shift.start_time?.slice(0, 5) || '--:--' }}</span>
                  <span class="arrow">→</span>
                  <span class="time">{{ shift.end_time?.slice(0, 5) || '--:--' }}</span>
                  <span v-if="shift.ot_start_time" class="ot-badge" :title="'Tăng ca tính từ ' + shift.ot_start_time">
                    OT: {{ shift.ot_start_time.slice(0, 5) }}
                  </span>
                  <span v-if="shift.is_night_shift" class="tag-night">Đêm</span>

                </div>
              </td>
              <td>
                <span class="category-badge" :class="getCategoryClass(shift.shift_category)">
                  {{ formatCategory(shift.shift_category) }}
                </span>
              </td>
              <td class="text-center font-semibold">{{ shift.work_hours.toFixed(1) }}h</td>
              <td class="text-center text-muted">{{ shift.break_hours.toFixed(1) }}h</td>
              <td class="text-center text-success" :class="{ 'inactive': shift.leave_hours_p === 0 }">
                {{ shift.leave_hours_p.toFixed(1) }}
              </td>
              <td class="text-center text-warning" :class="{ 'inactive': shift.leave_hours_r === 0 }">
                {{ shift.leave_hours_r.toFixed(1) }}
              </td>
              <td class="text-center text-danger" :class="{ 'inactive': shift.leave_hours_o === 0 }">
                {{ shift.leave_hours_o.toFixed(1) }}
              </td>
              <td class="text-center" :class="{ 'inactive': shift.leave_hours_t === 0 }">
                {{ shift.leave_hours_t.toFixed(1) }}
              </td>
              <td class="text-center" :class="{ 'inactive': shift.leave_hours_c === 0 }">
                {{ shift.leave_hours_c.toFixed(1) }}
              </td>
              <td class="text-center" :class="{ 'inactive': shift.leave_hours_k === 0 }">
                {{ shift.leave_hours_k.toFixed(1) }}
              </td>
              <td class="text-center text-primary">{{ shift.standard_hours.toFixed(1) }}</td>
              <td class="text-center text-accent font-bold">{{ shift.workday_base.toFixed(1) }}</td>
              <td class="text-muted italic desc-col">{{ shift.description || '-' }}</td>
              <td class="text-right actions">
                <button class="btn-icon" title="Sửa" @click="handleEdit(shift)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="btn-icon delete" title="Xóa" @click="handleDelete(shift)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                </button>
              </td>
            </tr>
            <tr v-if="shifts.length === 0">
              <td colspan="9" class="empty-state">
                Không có dữ liệu
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <EditShiftModal 
      :isOpen="isModalOpen"
      :shift="selectedShift"
      @close="isModalOpen = false"
      @saved="fetchShifts"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { shiftsApi } from './api'
import EditShiftModal from './components/EditShiftModal.vue'
import { useNotificationStore } from '@/stores/notification'

const notification = useNotificationStore()

const shifts = ref([])
const isModalOpen = ref(false)
const selectedShift = ref(null)

const fetchShifts = async () => {
  try {
    shifts.value = await shiftsApi.getShifts()
  } catch (err) {
    console.error('Failed to fetch shifts:', err)
  }
}

const handleAdd = () => {
  selectedShift.value = null
  isModalOpen.value = true
}

const handleEdit = (shift) => {
  selectedShift.value = { ...shift }
  isModalOpen.value = true
}

const handleDelete = async (shift) => {
  const confirmed = await notification.confirm(
    `Bạn có chắc muốn xóa mã ca ${shift.shift_code}?`,
    'Xác nhận'
  )
  if (confirmed) {
    try {
      await shiftsApi.deleteShift(shift.shift_code)
      notification.success('Thành công')
      fetchShifts()
    } catch (err) {
      notification.error('Lỗi khi xóa')
    }
  }
}

const formatCategory = (cat) => {
  if (cat === 'HOLIDAY') return 'Nghỉ Lễ';
  if (cat === 'ROTATION') return 'Luân Phiên';
  return 'Ngày Thường';
}

const getCategoryClass = (cat) => {
  if (cat === 'HOLIDAY') return 'tag-holiday';
  if (cat === 'ROTATION') return 'tag-rotation';
  return 'tag-normal';
}

onMounted(fetchShifts)
</script>

<style scoped>
.shift-management-view {
  padding: 24px;
  color: #e2e8f0;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
}

.title-section h1 {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: white;
}

.subtitle {
  color: #94a3b8;
  margin: 0;
  font-size: 0.85rem;
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  font-weight: 600;
  border-radius: 10px;
  font-size: 0.9rem;
}

.glass-container {
  background: rgba(30, 41, 59, 0.5);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  overflow: hidden;
}

.table-wrapper {
  overflow-x: auto;
}

.shift-table {
  width: 100%;
  border-collapse: collapse;
}

.shift-table th {
  text-align: left;
  padding: 12px 14px;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
  border-bottom: 2px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
  white-space: nowrap;
}

.shift-table td {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  font-size: 0.9rem;
  white-space: nowrap;
}

.desc-col {
  white-space: normal !important;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.shift-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.shift-badge {
  padding: 0.3rem 0.6rem;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.75rem;
}

.shift-badge.night {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  border-color: rgba(139, 92, 246, 0.2);
}

.time-window {
  display: flex;
  align-items: center;
  gap: 6px;
}

.time {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
}

.arrow {
  color: #475569;
  font-size: 0.8rem;
}

.ot-badge {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 700;
  border: 1px solid rgba(245, 158, 11, 0.3);
  white-space: nowrap;
}

.tag-night {

  font-size: 0.65rem;
  padding: 1px 4px;
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
  border-radius: 4px;
  margin-left: 2px;
}

.category-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.tag-normal { background: rgba(52, 211, 153, 0.15); color: #34d399; }
.tag-holiday { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.tag-rotation { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }

.text-muted { color: #64748b; }
.text-success { color: #2ecc71; }
.text-warning { color: #f1c40f; }
.text-danger { color: #ff4757; }
.text-primary { color: #3498db; }
.text-accent { color: #00d2ff; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.font-semibold { font-weight: 600; }
.italic { font-style: italic; }

.inactive {
  opacity: 0.15;
  color: #475569 !important;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  margin-left: 6px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.btn-icon.delete:hover {
  background: #ef4444;
  border-color: #ef4444;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
  color: #475569;
}
</style>
