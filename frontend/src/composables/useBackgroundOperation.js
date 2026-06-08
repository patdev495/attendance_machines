import { ref } from 'vue'

export function unwrapApiPayload(result) {
  return result && typeof result === 'object' && 'data' in result ? result.data : result
}

export function createBackgroundOperation({
  getStatus,
  startRequest = null,
  intervalMs = 1500,
  initialStatus = {},
  isComplete = (status) => !status?.is_running,
  isError = (status) => Boolean(status?.error),
  requireRunningBeforeComplete = false,
  maxInitialStalePolls = 0,
  onStatus = null,
  onComplete = null,
  onError = null,
  onPollError = null,
} = {}) {
  if (typeof getStatus !== 'function') {
    throw new Error('createBackgroundOperation requires getStatus')
  }

  const status = ref({ ...initialStatus })
  const isPolling = ref(false)
  const lastError = ref(null)

  let timer = null
  let runId = 0
  let seenRunning = false
  let initialStalePolls = 0

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    isPolling.value = false
  }

  function reset(nextStatus = initialStatus) {
    stopPolling()
    runId += 1
    seenRunning = false
    initialStalePolls = 0
    status.value = { ...nextStatus }
    lastError.value = null
  }

  async function pollOnce(activeRunId = runId) {
    try {
      const nextStatus = unwrapApiPayload(await getStatus())
      if (activeRunId !== runId) return null

      status.value = nextStatus || {}
      onStatus?.(status.value)

      if (status.value?.is_running) {
        seenRunning = true
      }

      if (isError(status.value)) {
        stopPolling()
        onError?.(status.value)
      } else if (isComplete(status.value)) {
        if (requireRunningBeforeComplete && !seenRunning && initialStalePolls < maxInitialStalePolls) {
          initialStalePolls += 1
          return status.value
        }
        stopPolling()
        onComplete?.(status.value)
      }

      return status.value
    } catch (error) {
      if (activeRunId !== runId) return null
      lastError.value = error
      onPollError?.(error)
      return null
    }
  }

  function startPolling({ immediate = true } = {}) {
    stopPolling()
    runId += 1
    seenRunning = false
    initialStalePolls = 0
    const activeRunId = runId
    isPolling.value = true

    if (immediate) {
      pollOnce(activeRunId)
    }

    timer = setInterval(() => {
      pollOnce(activeRunId)
    }, intervalMs)
  }

  async function start(...args) {
    if (startRequest) {
      await startRequest(...args)
    }
    startPolling({ immediate: true })
  }

  return {
    status,
    isPolling,
    lastError,
    pollOnce,
    start,
    startPolling,
    stopPolling,
    reset,
    dispose: stopPolling,
  }
}

export function createBackgroundInterval({
  run,
  intervalMs,
  immediate = false,
  onError = null,
} = {}) {
  if (typeof run !== 'function') {
    throw new Error('createBackgroundInterval requires run')
  }

  let timer = null

  async function runOnce() {
    try {
      return await run()
    } catch (error) {
      onError?.(error)
      return null
    }
  }

  function start() {
    stop()
    if (immediate) runOnce()
    timer = setInterval(runOnce, intervalMs)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return {
    start,
    stop,
    runOnce,
    dispose: stop,
  }
}
