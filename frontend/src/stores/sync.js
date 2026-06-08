import { defineStore } from 'pinia'
import { ref } from 'vue'
import { logsApi } from '@/features/logs/api.js'
import { dailySummaryApi } from '@/features/daily_summary/api.js'
import { employeesApi } from '@/features/employees/api.js'
import { getDeleteStatus as apiGetDeleteStatus } from '@/features/machines/api.js'
import { createBackgroundOperation } from '@/composables/useBackgroundOperation.js'
import { useNotificationStore } from '@/stores/notification.js'
import { i18n } from '@/i18n'

const triggerSync = logsApi.startSync
const getSyncStatus = logsApi.getSyncStatus
const syncEmployeesExcel = dailySummaryApi.syncExcel
const getExcelSyncStatus = dailySummaryApi.getSyncStatus
const deleteEmployeeFromAllMachines = employeesApi.deleteEmployee
const getDeleteStatus = apiGetDeleteStatus

export const useSyncStore = defineStore('sync', () => {
  const notification = useNotificationStore()
  const syncRunning = ref(false)
  const syncMessage = ref('')
  const deleteRunning = ref(false)
  const deleteMessage = ref('')

  const excelSyncRunning = ref(false)
  const excelSyncProgress = ref(0)
  const excelSyncStep = ref('')
  const excelSyncTotal = ref(0)
  const excelSyncError = ref(null)

  let syncHideTimer = null
  let deleteHideTimer = null
  let excelHideTimer = null
  let deleteOperation = null

  const rawLogOperation = createBackgroundOperation({
    getStatus: getSyncStatus,
    intervalMs: 1500,
    requireRunningBeforeComplete: true,
    maxInitialStalePolls: 2,
    onStatus(status) {
      if (status.is_running) {
        syncMessage.value = i18n.global.t('sync.progress', {
          current: status.current_machine_index,
          total: status.total_machines,
          ip: status.current_machine_ip,
          added: status.total_added || 0
        })
      }
    },
    onComplete() {
      syncMessage.value = i18n.global.t('sync.completed')
      syncHideTimer = setTimeout(() => { syncRunning.value = false }, 3000)
    },
    onPollError(error) {
      console.error('Status poll failed', error)
    },
  })

  const excelOperation = createBackgroundOperation({
    getStatus: getExcelSyncStatus,
    intervalMs: 1000,
    requireRunningBeforeComplete: true,
    maxInitialStalePolls: 2,
    onStatus(status) {
      excelSyncProgress.value = status.progress || 0
      excelSyncStep.value = status.current_step || ''
      excelSyncTotal.value = status.total || 0
      excelSyncRunning.value = Boolean(status.is_running)
    },
    onError(status) {
      excelSyncError.value = status.error
      excelSyncRunning.value = false
      notification.error('Sync failed: ' + status.error)
    },
    onComplete(status) {
      if (status.progress === 100) {
        const msg = status.current_step || i18n.global.t('sync.completed')
        excelSyncStep.value = msg
        notification.success(msg)
        excelHideTimer = setTimeout(() => { excelSyncRunning.value = false }, 5000)
      } else {
        excelSyncRunning.value = false
      }
    },
    onPollError(error) {
      console.error('Excel sync status poll failed', error)
    },
  })

  async function startSync(filters = {}) {
    if (syncRunning.value) return
    if (syncHideTimer) clearTimeout(syncHideTimer)

    syncRunning.value = true
    syncMessage.value = i18n.global.t('sync.initiating')

    const syncParams = {
      start_date: filters.start_date,
      end_date: filters.end_date
    }

    try {
      await triggerSync(syncParams)
      rawLogOperation.startPolling({ immediate: true })
    } catch (e) {
      syncMessage.value = 'Sync failed: ' + e.message
      syncRunning.value = false
      rawLogOperation.stopPolling()
    }
  }

  async function syncExcelFile(file) {
    if (excelSyncRunning.value) return
    if (excelHideTimer) clearTimeout(excelHideTimer)

    excelSyncError.value = null
    excelSyncProgress.value = 0
    excelSyncStep.value = i18n.global.t('sync.uploading')
    excelSyncRunning.value = true

    try {
      await syncEmployeesExcel(file)
      excelOperation.startPolling({ immediate: true })
    } catch (e) {
      excelSyncError.value = e.message
      excelSyncRunning.value = false
      excelOperation.stopPolling()
      throw e
    }
  }

  async function startDeleteEmployee(employeeId) {
    if (deleteRunning.value) return
    if (deleteHideTimer) clearTimeout(deleteHideTimer)

    deleteRunning.value = true
    deleteMessage.value = i18n.global.t('actions.delete_initiating', { id: employeeId })

    deleteOperation?.stopPolling()
    deleteOperation = createBackgroundOperation({
      getStatus: () => getDeleteStatus(employeeId),
      intervalMs: 1500,
      requireRunningBeforeComplete: true,
      maxInitialStalePolls: 2,
      onStatus(status) {
        if (status.is_running) {
          deleteMessage.value = i18n.global.t('actions.delete_progress', {
            id: employeeId,
            current: status.processed_count,
            total: status.total_machines,
            ip: status.current_ip
          })
        }
      },
      onComplete() {
        deleteMessage.value = i18n.global.t('actions.delete_completed', { id: employeeId })
        deleteHideTimer = setTimeout(() => { deleteRunning.value = false }, 3000)
      },
      onPollError(error) {
        console.error('Delete status poll failed', error)
      },
    })

    try {
      await deleteEmployeeFromAllMachines(employeeId)
      deleteOperation.startPolling({ immediate: true })
    } catch (e) {
      deleteMessage.value = 'Error: ' + e.message
      deleteRunning.value = false
      deleteOperation.stopPolling()
    }
  }

  return {
    syncRunning,
    syncMessage,
    deleteRunning,
    deleteMessage,
    excelSyncRunning,
    excelSyncProgress,
    excelSyncStep,
    excelSyncTotal,
    excelSyncError,
    startSync,
    syncExcelFile,
    startDeleteEmployee
  }
})
