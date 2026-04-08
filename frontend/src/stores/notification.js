import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const confirmState = ref({
    isOpen: false,
    title: '',
    message: '',
    resolve: null
  })

  function add(message, type = 'info', duration = 5000) {
    const id = Math.random().toString(36).substring(2, 11) + Date.now().toString(36)
    notifications.value.push({
      id,
      message,
      type,
      duration
    })

    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }

    return id
  }

  function remove(id) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function clearByType(type) {
    notifications.value = notifications.value.filter(n => n.type !== type)
  }

  // Helper methods
  const success = (msg, dur) => add(msg, 'success', dur)
  const error = (msg, dur) => add(msg, 'error', dur)
  const info = (msg, dur) => add(msg, 'info', dur)
  const warn = (msg, dur) => add(msg, 'warning', dur)

  function confirm(message, title = 'Confirm Action') {
    return new Promise((resolve) => {
      confirmState.value = {
        isOpen: true,
        title,
        message,
        resolve
      }
    })
  }

  function resolveConfirm(value) {
    if (confirmState.value.resolve) {
      confirmState.value.resolve(value)
    }
    confirmState.value.isOpen = false
  }

  return { 
    notifications, add, remove, success, error, info, warn, clearByType,
    confirmState, confirm, resolveConfirm
  }
})
