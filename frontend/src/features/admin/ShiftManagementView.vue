<template>
  <div class="shift-management-view anim-up">
    <!-- Header -->
    <div class="header">
      <div class="title-section">
        <h1 class="title">{{ $t('employees.shifts.title') }}</h1>
        <p class="subtitle">{{ $t('employees.shifts.subtitle') }}</p>
      </div>
      
      <button class="btn btn-primary btn-add" @click="handleAdd">
        <Plus :size="16" />
        <span>{{ $t('employees.shifts.add_btn') }}</span>
      </button>
    </div>

    <!-- Shift Legend Pill Bar -->
    <div class="legend-bar card">
      <div class="legend-item">
        <span class="legend-badge p-badge">P</span>
        <span>Phép năm</span>
      </div>
      <div class="legend-item">
        <span class="legend-badge r-badge">R</span>
        <span>Nghỉ bù/chế độ</span>
      </div>
      <div class="legend-item">
        <span class="legend-badge o-badge">O</span>
        <span>Nghỉ không lương</span>
      </div>
      <div class="legend-item">
        <span class="legend-badge t-badge">T</span>
        <span>Thai sản</span>
      </div>
      <div class="legend-item">
        <span class="legend-badge c-badge">C</span>
        <span>Công tác</span>
      </div>
      <div class="legend-item">
        <span class="legend-badge k-badge">K</span>
        <span>Nghỉ khác</span>
      </div>
    </div>

    <!-- Shifts Table -->
    <div class="table-container card glow">
      <div class="scrollable">
        <table class="shift-table">
          <thead>
            <tr>
              <th style="width: 100px;">{{ $t('employees.shifts.table.code') }}</th>
              <th style="width: 220px;">{{ $t('employees.shifts.table.range') }}</th>
              <th style="width: 120px;">{{ $t('employees.shifts.table.type') }}</th>
              <th class="text-center" style="width: 80px;">{{ $t('employees.shifts.table.work') }}</th>
              <th class="text-center" style="width: 80px;">{{ $t('employees.shifts.table.break') }}</th>
              <th class="text-center" style="width: 45px;" :title="$t('employees.shifts.leave_types.p')">P</th>
              <th class="text-center" style="width: 45px;" :title="$t('employees.shifts.leave_types.r')">R</th>
              <th class="text-center" style="width: 45px;" :title="$t('employees.shifts.leave_types.o')">O</th>
              <th class="text-center" style="width: 45px;" :title="$t('employees.shifts.leave_types.t')">T</th>
              <th class="text-center" style="width: 45px;" :title="$t('employees.shifts.leave_types.c')">C</th>
              <th class="text-center" style="width: 45px;" :title="$t('employees.shifts.leave_types.k')">K</th>
              <th class="text-center" style="width: 70px;" :title="$t('employees.shifts.table.round')">{{ $t('employees.shifts.table.round_short') }}</th>
              <th class="text-center" style="width: 70px;" :title="$t('employees.shifts.table.base')">{{ $t('employees.shifts.table.base_short') }}</th>
              <th>{{ $t('employees.shifts.table.desc') }}</th>
              <th class="text-right" style="width: 90px;">{{ $t('employees.shifts.table.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="shift in shifts" :key="shift.shift_code" class="shift-row">
              <td>
                <span class="shift-badge" :class="{ 'night': shift.is_night_shift }">
                  <Moon :size="12" v-if="shift.is_night_shift" class="moon-icon" />
                  <Sun :size="12" v-else class="sun-icon" />
                  <span>{{ shift.shift_code }}</span>
                </span>
              </td>
              <td class="time-col">
                <div class="time-window">
                  <span class="mono-time">{{ shift.start_time?.slice(0, 5) || '--:--' }}</span>
                  <span class="arrow">→</span>
                  <span class="mono-time">{{ shift.end_time?.slice(0, 5) || '--:--' }}</span>
                  <span v-if="shift.ot_start_time" class="ot-badge" :title="$t('employees.shifts.ot_start') + ' ' + shift.ot_start_time">
                    OT: {{ shift.ot_start_time.slice(0, 5) }}
                  </span>
                </div>
              </td>
              <td>
                <span class="category-badge" :class="getCategoryClass(shift.shift_category)">
                  {{ formatCategory(shift.shift_category) }}
                </span>
              </td>
              <td class="text-center font-mono font-semibold">{{ shift.work_hours.toFixed(1) }}h</td>
              <td class="text-center font-mono text-muted">{{ shift.break_hours.toFixed(1) }}h</td>
              <td class="text-center text-success font-mono" :class="{ 'inactive': shift.leave_hours_p === 0 }">
                {{ shift.leave_hours_p.toFixed(1) }}
              </td>
              <td class="text-center text-warning font-mono" :class="{ 'inactive': shift.leave_hours_r === 0 }">
                {{ shift.leave_hours_r.toFixed(1) }}
              </td>
              <td class="text-center text-danger font-mono" :class="{ 'inactive': shift.leave_hours_o === 0 }">
                {{ shift.leave_hours_o.toFixed(1) }}
              </td>
              <td class="text-center font-mono" :class="{ 'inactive': shift.leave_hours_t === 0 }">
                {{ shift.leave_hours_t.toFixed(1) }}
              </td>
              <td class="text-center font-mono" :class="{ 'inactive': shift.leave_hours_c === 0 }">
                {{ shift.leave_hours_c.toFixed(1) }}
              </td>
              <td class="text-center font-mono" :class="{ 'inactive': shift.leave_hours_k === 0 }">
                {{ shift.leave_hours_k.toFixed(1) }}
              </td>
              <td class="text-center text-primary font-mono font-semibold">{{ shift.standard_hours.toFixed(1) }}</td>
              <td class="text-center text-accent font-mono font-bold">{{ shift.workday_base.toFixed(1) }}</td>
              <td class="text-muted italic desc-col">{{ shift.description || '—' }}</td>
              <td class="text-right actions">
                <div class="row-actions-right">
                  <button class="btn-icon" :title="$t('common.edit')" @click="handleEdit(shift)">
                    <Edit2 :size="14" />
                  </button>
                  <button class="btn-icon delete" :title="$t('common.delete')" @click="handleDelete(shift)">
                    <Trash2 :size="14" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="shifts.length === 0">
              <td colspan="15" class="empty-state">
                <Inbox :size="36" class="empty-icon" />
                <span>{{ $t('attendance.table.no_records') }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Edit Shift Modal -->
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
import { useI18n } from 'vue-i18n'
import { shiftsApi } from './api'
import EditShiftModal from './components/EditShiftModal.vue'
import { useNotificationStore } from '@/stores/notification'
import { Plus, Edit2, Trash2, Moon, Sun, Inbox } from 'lucide-vue-next'

const { t } = useI18n()
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
    t('employees.shifts.delete_confirm', { code: shift.shift_code }),
    t('common.confirm')
  )
  if (confirmed) {
    try {
      await shiftsApi.deleteShift(shift.shift_code)
      notification.success(t('employees.shifts.delete_success'))
      fetchShifts()
    } catch (err) {
      notification.error(t('employees.shifts.delete_error'))
    }
  }
}

const formatCategory = (cat) => {
  if (cat === 'HOLIDAY') return t('employees.shifts.cat_holiday')
  if (cat === 'ROTATION') return t('employees.shifts.cat_rotation')
  return t('employees.shifts.cat_normal')
}

const getCategoryClass = (cat) => {
  if (cat === 'HOLIDAY') return 'tag-holiday'
  if (cat === 'ROTATION') return 'tag-rotation'
  return 'tag-normal'
}

onMounted(fetchShifts)
</script>

<style scoped>
.shift-management-view {
  color: #e2e8f0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.title {
  font-size: 1.7rem;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--text-muted);
  font-size: 0.88rem;
  margin-top: 2px;
}

.btn-add {
  padding: 9px 18px;
}

/* Legend Bar */
.legend-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 18px;
  border-radius: var(--radius-md);
  flex-wrap: wrap;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-badge {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 0.72rem;
  padding: 1px 6px;
  border-radius: 4px;
}
.p-badge { background: rgba(16, 185, 129, 0.15); color: #34d399; }
.r-badge { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.o-badge { background: rgba(244, 63, 94, 0.15); color: #fb7185; }
.t-badge { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }
.c-badge { background: rgba(6, 182, 212, 0.15); color: #22d3ee; }
.k-badge { background: rgba(255, 255, 255, 0.08); color: #cbd5e1; }

.shift-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.84rem;
  background: rgba(6, 182, 212, 0.12);
  color: #22d3ee;
  border: 1px solid rgba(6, 182, 212, 0.25);
}
.shift-badge.night {
  background: rgba(168, 85, 247, 0.15);
  color: #d8b4fe;
  border-color: rgba(168, 85, 247, 0.3);
}
.sun-icon { color: #f59e0b; }
.moon-icon { color: #c084fc; }

.time-window {
  display: flex;
  align-items: center;
  gap: 6px;
}
.mono-time {
  font-family: var(--font-mono);
  font-weight: 600;
  color: #fff;
  font-size: 0.85rem;
}
.arrow { color: var(--text-dim); }

.ot-badge {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  color: #fcd34d;
  background: rgba(245, 158, 11, 0.15);
  padding: 1px 5px;
  border-radius: 4px;
}

.category-badge {
  font-size: 0.74rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.tag-normal { background: rgba(99, 102, 241, 0.12); color: #a5b4fc; }
.tag-holiday { background: rgba(244, 63, 94, 0.12); color: #fb7185; }
.tag-rotation { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }

.inactive { opacity: 0.25; }
.font-mono { font-family: var(--font-mono); }

.row-actions-right {
  display: inline-flex;
  gap: 6px;
}
</style>
