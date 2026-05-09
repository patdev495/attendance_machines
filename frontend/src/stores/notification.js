import { defineStore } from 'pinia'
import { ref } from 'vue'
import { i18n } from '@/i18n'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const confirmState = ref({
    isOpen: false,
    title: '',
    message: '',
    resolve: null
  })

  const promptState = ref({
    isOpen: false,
    title: '',
    message: '',
    defaultValue: '',
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

  function confirm(message, title) {
    const defaultTitle = i18n.global.t('common.confirm')
    return new Promise((resolve) => {
      confirmState.value = {
        isOpen: true,
        title: title || defaultTitle,
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

  function prompt(message, title, defaultValue = '') {
    const defaultTitle = i18n.global.t('common.prompt')
    return new Promise((resolve) => {
      promptState.value = {
        isOpen: true,
        title: title || defaultTitle,
        message,
        defaultValue,
        resolve
      }
    })
  }

  function resolvePrompt(value) {
    if (promptState.value.resolve) {
      promptState.value.resolve(value)
    }
    promptState.value.isOpen = false
  }

  return { 
    notifications, add, remove, success, error, info, warn, clearByType,
    confirmState, confirm, resolveConfirm,
    promptState, prompt, resolvePrompt
  }
})
