import { defineStore } from 'pinia'
import { ref } from 'vue'
import { triggerSync, getSyncStatus, syncEmployeesExcel, deleteEmployeeFromAllMachines, getDeleteStatus } from '@/api/employees.js'

export const useSyncStore = defineStore('sync', () => {
  const syncRunning = ref(false)
  const syncMessage = ref('')
  const deleteRunning = ref(false)
  const deleteMessage = ref('')

  let syncPoller = null
  let deletePoller = null

  async function startSync() {
    if (syncRunning.value) return
    syncRunning.value = true
    syncMessage.value = 'Connecting to machines...'
    try {
      await triggerSync()
      syncPoller = setInterval(async () => {
        try {
          const status = await getSyncStatus()
          if (!status.is_running) {
            syncMessage.value = 'Sync completed.'
            clearInterval(syncPoller)
            setTimeout(() => { syncRunning.value = false }, 3000)
          } else {
            syncMessage.value = `Syncing: Machine ${status.current_machine_index}/${status.total_machines} (${status.current_machine_ip}) - Logs added: ${status.processed_count}`
          }
        } catch (e) {
          console.error('Status poll failed', e)
        }
      }, 2000)
    } catch (e) {
      syncMessage.value = 'Sync failed: ' + e.message
      syncRunning.value = false
    }
  }

  async function syncExcelFile(file) {
    return syncEmployeesExcel(file)
  }

  async function startDeleteEmployee(employeeId) {
    if (deleteRunning.value) return
    deleteRunning.value = true
    deleteMessage.value = `Initiating deletion for ${employeeId}...`
    try {
      await deleteEmployeeFromAllMachines(employeeId)
      deletePoller = setInterval(async () => {
        try {
          const status = await getDeleteStatus()
          if (!status.is_running) {
            deleteMessage.value = `Employee ${employeeId} deleted from all machines.`
            clearInterval(deletePoller)
            setTimeout(() => { deleteRunning.value = false }, 3000)
          } else {
            deleteMessage.value = `Deleting ${employeeId}: Machine ${status.processed_count}/${status.total_machines} (${status.current_ip})`
          }
        } catch (e) {
          console.error('Delete status poll failed', e)
        }
      }, 2000)
    } catch (e) {
      deleteMessage.value = 'Error: ' + e.message
      deleteRunning.value = false
    }
  }

  return { syncRunning, syncMessage, deleteRunning, deleteMessage, startSync, syncExcelFile, startDeleteEmployee }
})
