import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dailySummaryApi } from '@/features/daily_summary/api.js'
import { createBackgroundOperation } from '@/composables/useBackgroundOperation.js'
import { i18n } from '@/i18n'

const apiStart = dailySummaryApi.startExport
const apiStatus = dailySummaryApi.getExportStatus
const apiCancel = dailySummaryApi.cancelExport
const apiDownload = dailySummaryApi.downloadExport

export const useExportStore = defineStore('export', () => {
  const isRunning = ref(false)
  const progress = ref(0)
  const currentStep = ref('')
  const error = ref(null)
  const filename = ref(null)
  
  const exportOperation = createBackgroundOperation({
    getStatus: apiStatus,
    intervalMs: 1500,
    requireRunningBeforeComplete: true,
    maxInitialStalePolls: 2,
    onStatus(status) {
      progress.value = status.progress || 0
      currentStep.value = status.current_step || ''
      isRunning.value = Boolean(status.is_running)
    },
    onError(status) {
      error.value = status.error
      isRunning.value = false
    },
    onComplete(status) {
      isRunning.value = false
      if (status.progress === 100) {
        triggerDownload()
      }
    },
    onPollError(e) {
      console.error('Export status poll failed', e)
    },
  })

  async function start(startDate, endDate, viewMode) {
    if (isRunning.value) return
    
    error.value = null
    filename.value = null
    progress.value = 0
    currentStep.value = i18n.global.t('export.starting')
    isRunning.value = true

    try {
      await apiStart(startDate, endDate, viewMode)
      exportOperation.startPolling({ immediate: true })
    } catch (e) {
      error.value = e.message
      isRunning.value = false
    }
  }

  async function cancel() {
    try {
      await apiCancel()
      isRunning.value = false
      exportOperation.stopPolling()
      currentStep.value = i18n.global.t('export.cancelled')
    } catch (e) {
      console.error('Cancel failed', e)
    }
  }

  function triggerDownload() {
    apiDownload()
  }

  return { isRunning, progress, currentStep, error, start, cancel }
})
