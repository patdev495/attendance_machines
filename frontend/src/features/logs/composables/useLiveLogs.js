import { ref, onUnmounted } from 'vue'

export function useLiveLogs(onMessage) {
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const error = ref(null)
  let socket = null
  let reconnectTimer = null
  let manuallyClosed = false

  const connect = () => {
    if (socket || isConnecting.value) return

    isConnecting.value = true
    manuallyClosed = false
    error.value = null

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/logs/live/ws`

    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      isConnected.value = true
      isConnecting.value = false
      console.log('Live Logs WebSocket connected')
    }

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (onMessage) onMessage(payload)
      } catch (e) {
        console.error('Error parsing live log message:', e)
      }
    }

    socket.onclose = () => {
      isConnected.value = false
      isConnecting.value = false
      socket = null
      
      if (manuallyClosed) {
        console.log('Live Logs WebSocket closed manually')
        return
      }

      console.log('Live Logs WebSocket disconnected. Retrying in 5s...')
      
      // Auto-reconnect logic
      if (reconnectTimer) clearTimeout(reconnectTimer)
      reconnectTimer = setTimeout(() => {
        connect()
      }, 5000)
    }

    socket.onerror = (err) => {
      error.value = 'WebSocket connection error'
      console.error('WebSocket Error:', err)
      socket.close() // Trigger onclose to reconnect
    }
  }

  const disconnect = () => {
    manuallyClosed = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (socket) {
      socket.close()
      socket = null
    }
    isConnected.value = false
    isConnecting.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect
  }
}
