<template>
  <aside :class="['app-sidebar', ui.sidebarOpen ? 'open' : 'collapsed']">
    <div class="sidebar-header">
      <button class="toggle-btn" @click="ui.toggleSidebar">
        <svg v-if="ui.sidebarOpen" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
      </button>
    </div>

    <nav class="sidebar-nav">
      <!-- Raw Logs -->
      <router-link 
        to="/logs" 
        :class="['nav-item', route.path === '/logs' ? 'active' : '']"
      >
        <div class="icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>
        </div>
        <span class="label">{{ $t('attendance.raw_logs') }}</span>
      </router-link>

      <!-- Daily Summary -->
      <router-link 
        to="/summary" 
        :class="['nav-item', route.path === '/summary' ? 'active' : '']"
      >
        <div class="icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="m9 16 2 2 4-4"/></svg>
        </div>
        <span class="label">{{ $t('attendance.daily_summary') }}</span>
      </router-link>

      <div class="nav-divider"></div>

      <!-- Machines -->
      <router-link 
        to="/machines" 
        :class="['nav-item', route.path.startsWith('/machines') ? 'active' : '']"
      >
        <div class="icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <span class="label">{{ $t('nav.machines') }}</span>
      </router-link>

      <!-- Employees -->
      <router-link 
        to="/employees" 
        :class="['nav-item', route.path.startsWith('/employees') ? 'active' : '']"
      >
        <div class="icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <span class="label">{{ $t('nav.employees') }}</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup>
import { useUIStore } from '@/stores/ui.js'
import { useRoute } from 'vue-router'

const ui = useUIStore()
const route = useRoute()
</script>

<style scoped>
.app-sidebar {
  width: 260px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 101;
}

.app-sidebar.collapsed {
  width: 80px;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}

.toggle-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn:hover {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.sidebar-nav {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-radius: 12px;
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.2s;
  overflow: hidden;
  white-space: nowrap;
}

.nav-item .icon {
  min-width: 24px;
  display: flex;
  justify-content: center;
  margin-right: 12px;
}

.nav-item .label {
  font-size: 0.95rem;
  font-weight: 500;
  opacity: 1;
  transition: opacity 0.2s;
}

.collapsed .nav-item .label {
  opacity: 0;
  pointer-events: none;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.nav-item.active {
  background: var(--primary);
  color: white;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.nav-divider {
  height: 1px;
  background: var(--border);
  margin: 16px 12px;
}

/* Adjust for small screens */
@media (max-width: 768px) {
  .app-sidebar {
    position: fixed;
    left: 0;
    transform: translateX(-100%);
  }
  .app-sidebar.open {
    transform: translateX(0);
  }
}
</style>
