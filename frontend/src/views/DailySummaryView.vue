<template>
  <div class="anim-up">
    <AttendanceFilters />
    <SummaryTable />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAttendanceStore } from '@/stores/attendance.js'
import AttendanceFilters from '@/components/attendance/AttendanceFilters.vue'
import SummaryTable from '@/components/attendance/SummaryTable.vue'

const store = useAttendanceStore()

onMounted(async () => {
  store.setView('summary', false) // Set state but don't load twice
  await store.initDateRange()
  store.fetchMachines()
  store.loadData(1)
})
</script>
