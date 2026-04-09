<template>
  <div class="anim-up">
    <AttendanceFilters />

    <transition name="slide-up" mode="out-in">
      <RawLogsTable v-if="store.currentView === 'raw'" :key="'raw'" />
      <SummaryTable v-else :key="'summary'" />
    </transition>
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
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease-out;
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
