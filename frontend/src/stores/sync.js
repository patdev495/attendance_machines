import { defineStore } from 'pinia'
import { ref } from 'vue'
import { triggerSync, getSyncStatus, syncEmployeesExcel, deleteEmployeeFromAllMachines, getDeleteStatus, getExcelSyncStatus } from '@/api/employees.js'
import { useNotificationStore } from '@/stores/notification.js'

export const useSyncStore = defineStore('sync', () => {
  const notification = useNotificationStore()
  const syncRunning = ref(false)
  const syncMessage = ref('')
  const deleteRunning = ref(false)
  const deleteMessage = ref('')

  // Excel Sync State
  const excelSyncRunning = ref(false)
  const excelSyncProgress = ref(0)
  const excelSyncStep = ref('')
  const excelSyncTotal = ref(0)
  const excelSyncError = ref(null)

  let syncPoller = null
  let deletePoller = null
  let excelPoller = null

  async function startSync() {
    if (syncRunning.value) return
    syncRunning.value = true
    syncMessage.value = 'Initiating sync...'
    
    // Start polling immediately so the UI reflects the first machine connection
    const poll = async () => {
      try {
        const status = await getSyncStatus()
        if (!status.is_running) {
          syncMessage.value = 'Sync completed.'
          clearInterval(syncPoller)
          syncPoller = null
          setTimeout(() => { syncRunning.value = false }, 3000)
        } else {
          syncMessage.value = `Syncing: Machine ${status.current_machine_index}/${status.total_machines} (${status.current_machine_ip}) - Records added: ${status.total_added || 0}`
        }
      } catch (e) {
        console.error('Status poll failed', e)
      }
    }

    if (syncPoller) clearInterval(syncPoller)
    syncPoller = setInterval(poll, 1500)
    
    try {
      await triggerSync()
      // Initial poll after trigger to catch immediate state change
      await poll()
    } catch (e) {
      syncMessage.value = 'Sync failed: ' + e.message
      syncRunning.value = false
      if (syncPoller) clearInterval(syncPoller)
    }
  }

  async function syncExcelFile(file) {
    if (excelSyncRunning.value) return
    
    excelSyncError.value = null
    excelSyncProgress.value = 0
    excelSyncStep.value = 'Uploading file...'
    excelSyncRunning.value = true

    try {
      await syncEmployeesExcel(file)
      startExcelPolling()
    } catch (e) {
      excelSyncError.value = e.message
      excelSyncRunning.value = false
      throw e
    }
  }

  function startExcelPolling() {
    if (excelPoller) clearInterval(excelPoller)
    excelPoller = setInterval(async () => {
      try {
        const status = await getExcelSyncStatus()
        excelSyncProgress.value = status.progress
        excelSyncStep.value = status.current_step
        excelSyncTotal.value = status.total
        excelSyncRunning.value = status.is_running
        
        if (status.error) {
          excelSyncError.value = status.error
          stopExcelPolling()
          notification.error('Sync failed: ' + status.error)
        } else if (!status.is_running && status.progress === 100) {
          stopExcelPolling()
          const msg = status.current_step || 'Sync completed.'
          excelSyncStep.value = msg
          notification.success(msg)
          // Hide banner after 5 seconds
          setTimeout(() => { excelSyncRunning.value = false }, 5000)
        }
      } catch (e) {
        console.error('Excel sync status poll failed', e)
      }
    }, 1000)
  }

  function stopExcelPolling() {
    if (excelPoller) clearInterval(excelPoller)
    excelPoller = null
  }

  async function startDeleteEmployee(employeeId) {
    if (deleteRunning.value) return
    deleteRunning.value = true
    deleteMessage.value = `Initiating deletion for ${employeeId}...`
    
    const poll = async () => {
      try {
        const status = await getDeleteStatus(employeeId)
        if (!status.is_running) {
          deleteMessage.value = `Employee ${employeeId} deleted from all machines.`
          clearInterval(deletePoller)
          deletePoller = null
          setTimeout(() => { deleteRunning.value = false }, 3000)
        } else {
          deleteMessage.value = `Deleting ${employeeId}: Machine ${status.processed_count}/${status.total_machines} (${status.current_ip})`
        }
      } catch (e) {
        console.error('Delete status poll failed', e)
      }
    }

    if (deletePoller) clearInterval(deletePoller)
    deletePoller = setInterval(poll, 1500)

    try {
      await deleteEmployeeFromAllMachines(employeeId)
      await poll()
    } catch (e) {
      deleteMessage.value = 'Error: ' + e.message
      deleteRunning.value = false
      if (deletePoller) clearInterval(deletePoller)
    }
  }

  return { 
    syncRunning, syncMessage, deleteRunning, deleteMessage, 
    excelSyncRunning, excelSyncProgress, excelSyncStep, excelSyncTotal, excelSyncError,
    startSync, syncExcelFile, startDeleteEmployee 
  }
})
