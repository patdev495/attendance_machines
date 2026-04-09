<template>
  <div class="anim-up">
    <AttendanceFilters />
    <RawLogsTable />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAttendanceStore } from '@/stores/attendance.js'
import AttendanceFilters from '@/components/attendance/AttendanceFilters.vue'
import RawLogsTable from '@/components/attendance/RawLogsTable.vue'

const store = useAttendanceStore()

onMounted(async () => {
  store.setView('raw', false) // Set state but don't load twice
  await store.initDateRange()
  store.fetchMachines()
  store.loadData(1)
})
</script>
