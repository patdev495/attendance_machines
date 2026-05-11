<template>
  <header class="site-header" v-if="route.name !== 'meal'">
    <div class="header-left">
      <a href="#" class="site-title" @click.prevent="goHome">{{ $t('nav.title') }}</a>
      <p class="tagline">{{ $t('layout.tagline') }}</p>
    </div>
    <nav class="header-actions">
      <!-- Language Switcher -->
      <select v-model="currentLang" @change="changeLanguage" id="langSwitcher" name="lang">
        <option value="vi">🇻🇳 Tiếng Việt</option>
        <option value="en">🇬🇧 English</option>
        <option value="zh">🇨🇳 中文</option>
      </select>
    </nav>
  </header>

  <!-- Status banners (Intelligent slimmest version) -->
  <div v-if="syncStore.syncRunning" class="status-banner sync-banner">{{ syncStore.syncMessage }}</div>
  <div v-if="syncStore.deleteRunning" class="status-banner delete-banner">{{ syncStore.deleteMessage }}</div>
  
  <!-- Export Progress Banner -->
  <div v-if="exportStore.isRunning || exportStore.error" class="status-banner" :class="exportStore.error ? 'delete-banner' : 'sync-banner'">
    <div v-if="exportStore.error">{{ exportStore.error }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: exportStore.progress + '%' }"></div>
      </div>
      <span>{{ $t('export.progress_label') || 'Export' }}: {{ exportStore.currentStep }} ({{ exportStore.progress }}%)</span>
    </div>
  </div>

  <!-- Excel Sync Progress Banner -->
  <div v-if="syncStore.excelSyncRunning || syncStore.excelSyncError" class="status-banner" :class="syncStore.excelSyncError ? 'delete-banner' : 'sync-banner'" style="background: rgba(45, 212, 191, 0.1); border-bottom-color: #2dd4bf;">
    <div v-if="syncStore.excelSyncError" style="color: #f87171;">{{ syncStore.excelSyncError }}</div>
    <div v-else class="export-banner-content">
      <div class="progress-container">
        <div class="progress-fill" :style="{ width: syncStore.excelSyncProgress + '%', backgroundColor: '#2dd4bf' }"></div>
      </div>
      <span style="color: #2dd4bf;">{{ $t('sync.progress_label') || 'Sync' }}: {{ syncStore.excelSyncStep }} ({{ syncStore.excelSyncProgress }}%)</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSyncStore } from '@/stores/sync.js'
import { useExportStore } from '@/stores/export.js'
import { useAttendanceStore } from '@/stores/attendance.js'
import { useI18n } from 'vue-i18n'
import { setLanguage } from '@/i18n/index.js'
import { useRouter, useRoute } from 'vue-router'

const syncStore = useSyncStore()
const exportStore = useExportStore()
const attendanceStore = useAttendanceStore()
const router = useRouter()
const route = useRoute()

const { locale } = useI18n()
const currentLang = ref(locale.value)

function changeLanguage() {
  setLanguage(currentLang.value)
}

function goHome() {
  router.push('/logs')
}
</script>

<style scoped>
.site-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px clamp(16px, 3vw, 40px);
  border-bottom: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(10px);
}
.site-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: white;
  text-decoration: none;
  letter-spacing: -0.3px;
  cursor: pointer;
  transition: color 0.2s;
}
.site-title:hover { color: var(--primary); }

.tagline { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; }
.header-actions { display: flex; gap: 10px; align-items: center; }

select { 
  padding: 6px 10px; 
  font-size: 0.85rem; 
  background: #1e293b; 
  color: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  outline: none;
}
option {
  background: #1e293b;
  color: white;
}

.status-banner {
  padding: 8px 24px;
  font-size: 0.85rem;
  text-align: center;
}
.sync-banner {
  background: rgba(99,102,241,0.1);
  border-bottom: 1px solid var(--primary);
  color: var(--accent);
}
.delete-banner {
  background: rgba(239,68,68,0.08);
  border-bottom: 1px solid var(--danger);
  color: #f87171;
}

.export-banner-content { display: flex; align-items: center; justify-content: center; gap: 12px; max-width: 600px; margin: 0 auto; }
.progress-container { flex: 1; height: 6px; background: rgba(0,0,0,0.2); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--primary); transition: width 0.3s ease; }
</style>
