<template>
  <div class="anim-up">
    <!-- View Toggle -->
    <div class="view-toggle">
      <button :class="['toggle-btn', store.currentView === 'raw' ? 'active' : '']" @click="store.setView('raw')">Raw Logs</button>
      <button :class="['toggle-btn', store.currentView === 'summary' ? 'active' : '']" @click="store.setView('summary')">Daily Summary</button>
    </div>

    <AttendanceFilters />

    <RawLogsTable v-if="store.currentView === 'raw'" />
    <SummaryTable v-else />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAttendanceStore } from '@/stores/attendance.js'
import AttendanceFilters from '@/components/attendance/AttendanceFilters.vue'
import RawLogsTable from '@/components/attendance/RawLogsTable.vue'
import SummaryTable from '@/components/attendance/SummaryTable.vue'

const store = useAttendanceStore()

onMounted(async () => {
  await store.initDateRange()
  store.fetchMachines()
  store.loadData(1)
})
</script>

<style scoped>
.view-toggle {
  display: flex;
  gap: 2px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 4px;
  width: fit-content;
  margin-bottom: 16px;
}
.toggle-btn {
  padding: 8px 24px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.9rem;
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.toggle-btn.active {
  background: var(--primary);
  color: white;
  box-shadow: 0 4px 15px rgba(99,102,241,0.3);
}
.toggle-btn:not(.active):hover { color: white; }
</style>
