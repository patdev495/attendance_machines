<template>
  <aside :class="['app-sidebar', ui.sidebarOpen ? 'open' : 'collapsed']">
    <!-- Brand Header -->
    <div class="sidebar-brand">
      <div class="brand-logo" @click="ui.toggleSidebar">
        <div class="logo-icon-wrapper">
          <Fingerprint :size="22" class="logo-icon" />
          <span class="logo-glow"></span>
        </div>
        <div class="brand-info" v-if="ui.sidebarOpen">
          <span class="brand-name">NIENYI</span>
          <span class="brand-tag">ATTENDANCE OS</span>
        </div>
      </div>
      <button class="toggle-btn" @click="ui.toggleSidebar" :title="ui.sidebarOpen ? 'Co gọn menu' : 'Mở rộng menu'">
        <ChevronLeft v-if="ui.sidebarOpen" :size="16" />
        <ChevronRight v-else :size="16" />
      </button>
    </div>

    <!-- Navigation Menu -->
    <nav class="sidebar-nav">
      <!-- Raw Logs -->
      <router-link 
        to="/logs" 
        :class="['nav-item', route.path === '/logs' ? 'active' : '']"
        :data-tooltip="$t('attendance.raw_logs')"
      >
        <div class="nav-icon-box">
          <FileText :size="19" />
        </div>
        <span class="label">{{ $t('attendance.raw_logs') }}</span>
        <span class="active-indicator" v-if="route.path === '/logs'"></span>
      </router-link>

      <!-- Daily Summary -->
      <router-link 
        to="/summary" 
        :class="['nav-item', route.path === '/summary' ? 'active' : '']"
        :data-tooltip="$t('attendance.daily_summary')"
      >
        <div class="nav-icon-box">
          <CalendarCheck :size="19" />
        </div>
        <span class="label">{{ $t('attendance.daily_summary') }}</span>
        <span class="active-indicator" v-if="route.path === '/summary'"></span>
      </router-link>

      <div class="nav-section-title" v-if="ui.sidebarOpen">QUẢN TRỊ THIẾT BỊ</div>
      <div class="nav-divider" v-else></div>

      <!-- Machines -->
      <router-link 
        to="/machines" 
        :class="['nav-item', route.path.startsWith('/machines') ? 'active' : '']"
        :data-tooltip="$t('nav.machines')"
      >
        <div class="nav-icon-box">
          <Cpu :size="19" />
        </div>
        <span class="label">{{ $t('nav.machines') }}</span>
        <span class="active-indicator" v-if="route.path.startsWith('/machines')"></span>
      </router-link>

      <!-- Employees -->
      <router-link 
        to="/employees" 
        :class="['nav-item', route.path.startsWith('/employees') ? 'active' : '']"
        :data-tooltip="$t('nav.employees')"
      >
        <div class="nav-icon-box">
          <Users :size="19" />
        </div>
        <span class="label">{{ $t('nav.employees') }}</span>
        <span class="active-indicator" v-if="route.path.startsWith('/employees')"></span>
      </router-link>

      <!-- Shifts -->
      <router-link 
        to="/shifts" 
        :class="['nav-item', route.path.startsWith('/shifts') ? 'active' : '']"
        :data-tooltip="$t('nav.shifts')"
      >
        <div class="nav-icon-box">
          <Clock :size="19" />
        </div>
        <span class="label">{{ $t('nav.shifts') }}</span>
        <span class="active-indicator" v-if="route.path.startsWith('/shifts')"></span>
      </router-link>

      <div class="nav-section-title" v-if="ui.sidebarOpen">TIỆN ÍCH DỊCH VỤ</div>
      <div class="nav-divider" v-else></div>

      <!-- Meal Kiosk -->
      <router-link 
        to="/meal" 
        :class="['nav-item nav-item-kiosk', route.path === '/meal' ? 'active' : '']"
        :data-tooltip="$t('meal.kiosk_title')"
      >
        <div class="nav-icon-box kiosk-icon-box">
          <UtensilsCrossed :size="19" />
        </div>
        <span class="label">{{ $t('meal.kiosk_title') }}</span>
        <span class="kiosk-live-chip" v-if="ui.sidebarOpen">LIVE</span>
        <span class="active-indicator" v-if="route.path === '/meal'"></span>
      </router-link>
    </nav>

    <!-- Sidebar Footer with Status -->
    <div class="sidebar-footer">
      <div class="status-pill" v-if="ui.sidebarOpen">
        <span class="pulse-dot-green"></span>
        <span class="status-text">SYSTEM ONLINE</span>
      </div>
      <div class="status-pill-collapsed" v-else title="System Online">
        <span class="pulse-dot-green"></span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useUIStore } from '@/stores/ui.js'
import { useRoute } from 'vue-router'
import { 
  FileText, 
  CalendarCheck, 
  Cpu, 
  Users, 
  Clock, 
  UtensilsCrossed, 
  ChevronLeft, 
  ChevronRight,
  Fingerprint
} from 'lucide-vue-next'

const ui = useUIStore()
const route = useRoute()
</script>

<style scoped>
.app-sidebar {
  width: 260px;
  background: rgba(10, 16, 30, 0.88);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 101;
  user-select: none;
}

.app-sidebar.collapsed {
  width: 78px;
}

/* Brand Header */
.sidebar-brand {
  padding: 20px 18px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  overflow: hidden;
}

.logo-icon-wrapper {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(6, 182, 212, 0.2) 100%);
  border: 1px solid rgba(99, 102, 241, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}

.logo-icon {
  color: #22d3ee;
  filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.6));
}

.brand-info {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-tag {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #06b6d4;
  margin-top: -2px;
}

.toggle-btn {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.toggle-btn:hover {
  background: var(--primary-light);
  color: #fff;
  border-color: var(--primary);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
}

/* Nav Menu */
.sidebar-nav {
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  overflow-y: auto;
}

.nav-section-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-dim);
  letter-spacing: 0.1em;
  padding: 14px 14px 4px;
}

.nav-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 10px 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  white-space: nowrap;
  border: 1px solid transparent;
}

.nav-icon-box {
  min-width: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: color 0.2s, transform 0.2s;
}

.nav-item .label {
  font-size: 0.92rem;
  font-weight: 600;
  margin-left: 10px;
  opacity: 1;
  transition: opacity 0.2s;
}

.collapsed .nav-item .label {
  opacity: 0;
  pointer-events: none;
  width: 0;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #ffffff;
  border-color: var(--border);
  transform: translateX(2px);
}

.nav-item:hover .nav-icon-box {
  color: var(--cyan);
  transform: scale(1.1);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.08) 100%);
  color: #ffffff;
  border-color: rgba(99, 102, 241, 0.45);
  box-shadow: 0 4px 20px -2px rgba(99, 102, 241, 0.35);
}

.nav-item.active .nav-icon-box {
  color: #a5b4fc;
}

.active-indicator {
  position: absolute;
  left: 0;
  top: 25%;
  bottom: 25%;
  width: 3.5px;
  border-radius: 0 4px 4px 0;
  background: linear-gradient(to bottom, #818cf8, #22d3ee);
  box-shadow: 0 0 10px #818cf8;
}

/* Kiosk Special Styling */
.nav-item-kiosk {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(244, 63, 94, 0.05) 100%);
  border-color: rgba(245, 158, 11, 0.15);
}
.nav-item-kiosk:hover {
  border-color: rgba(245, 158, 11, 0.4);
}
.kiosk-icon-box {
  color: #fbbf24;
}
.kiosk-live-chip {
  margin-left: auto;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.2);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

/* Tooltip on collapsed */
.collapsed .nav-item:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 78px;
  top: 50%;
  transform: translateY(-50%);
  background: #0f172a;
  color: #f8fafc;
  padding: 6px 12px;
  font-size: 0.82rem;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5);
  white-space: nowrap;
  z-index: 999;
  pointer-events: none;
}

/* Footer */
.sidebar-footer {
  padding: 14px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  width: 100%;
  justify-content: center;
}

.status-text {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #34d399;
}

.status-pill-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .app-sidebar {
    position: fixed;
    left: 0;
    transform: translateX(-100%);
    box-shadow: 0 0 40px rgba(0, 0, 0, 0.7);
  }
  .app-sidebar.open {
    transform: translateX(0);
  }
}
</style>
