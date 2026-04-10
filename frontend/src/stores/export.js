import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dailySummaryApi } from '@/features/daily_summary/api.js'
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
  
  let poller = null

  async function start(startDate, endDate, viewMode) {
    if (isRunning.value) return
    
    error.value = null
    filename.value = null
    progress.value = 0
    currentStep.value = i18n.global.t('export.starting')
    isRunning.value = true

    try {
      await apiStart(startDate, endDate, viewMode)
      startPolling()
    } catch (e) {
      error.value = e.message
      isRunning.value = false
    }
  }

  function startPolling() {
    if (poller) clearInterval(poller)
    poller = setInterval(async () => {
      try {
        const status = await apiStatus()
        progress.value = status.progress
        currentStep.value = status.current_step
        isRunning.value = status.is_running
        
        if (status.error) {
          error.value = status.error
          stopPolling()
        } else if (!status.is_running && status.progress === 100) {
          stopPolling()
          triggerDownload()
        }
      } catch (e) {
        console.error('Export status poll failed', e)
      }
    }, 1500)
  }

  function stopPolling() {
    if (poller) clearInterval(poller)
    poller = null
  }

  async function cancel() {
    try {
      await apiCancel()
      isRunning.value = false
      stopPolling()
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
