import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const sidebarOpen = ref(true)
  
  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function setSidebar(val) {
    sidebarOpen.value = val
  }

  return {
    sidebarOpen,
    toggleSidebar,
    setSidebar
  }
})
