<template>
  <div class="kiosk-container">
    <header class="kiosk-header">
      <div class="logo-area">
        <h1>🍽️ {{ $t('meal.kiosk_title') }}</h1>
        <div class="clock">{{ currentTime }}</div>
      </div>
      <div class="controls">
        <div class="search-box header-search">
          <input type="text" v-model="quickSearchQuery" :placeholder="$t('meal.quick_search_placeholder')" @input="onQuickSearchInput" @keyup.enter="handleQuickSearch" :disabled="isQuickSearching" />
        </div>
        <button class="btn toggle-history-btn" @click="toggleHistory">
          {{ $t('meal.search_btn') }}
        </button>
        <select v-model="selectedMachine" class="machine-select">
          <option value="all">{{ $t('meal.all_machines') }}</option>
          <option v-for="ip in canteenMachines" :key="ip" :value="ip">{{ ip }}</option>
        </select>
        <button 
          class="btn live-btn" 
          :class="{ active: isConnected }"
          @click="toggleLive"
        >
          <span class="dot"></span> LIVE
        </button>
        <button class="btn fullscreen-btn" @click="enterFullscreen">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
        </button>
      </div>
    </header>

    <main class="kiosk-main">
      <!-- Live Monitoring Grid -->
      <section class="live-grid" :class="gridClass">
        <div v-for="ip in activeMachines" :key="ip" class="machine-panel">
          <div class="panel-header">{{ $t('meal.machine_label') }} <span>{{ ip }}</span></div>
          
          <div class="panel-content">
            <transition name="pop" mode="out-in">
              <div v-if="currentSwipes[ip]" :key="currentSwipes[ip].id" class="swipe-card" :class="getSwipeStatusClass(currentSwipes[ip])">
                <div class="status-banner">
                  {{ getSwipeStatusText(currentSwipes[ip]) }}
                </div>
                <div class="swipe-inner">
                  <div class="emp-info">
                    <div class="avatar">{{ getInitials(currentSwipes[ip].emp_name) }}</div>
                    <div class="details">
                      <h2 class="name">{{ currentSwipes[ip].emp_name || $t('meal.unknown_name') }}</h2>
                      <p class="emp-id">{{ $t('meal.emp_id_label') }} {{ currentSwipes[ip].employee_id }}</p>
                      <p class="dept">{{ $t('meal.dept_label') }} {{ currentSwipes[ip].department || '-' }}</p>
                    </div>
                  </div>
                  <div class="meal-info">
                    <template v-if="currentSwipes[ip].meal_info && currentSwipes[ip].meal_info.is_registered !== false">
                      <div class="meal-icon">🍱</div>
                      <h3 class="meal-name">{{ currentSwipes[ip].meal_info.meal_name_vi }}</h3>
                    </template>
                    <template v-else>
                      <div class="meal-icon error">❌</div>
                      <h3 class="meal-name">{{ $t('meal.not_registered') }}</h3>
                    </template>
                  </div>
                </div>
                <div class="swipe-footer">
                  {{ $t('meal.time_label') }} {{ formatTime(currentSwipes[ip].attendance_time) }}
                </div>
              </div>
              
              <div v-else class="waiting-card">
                <div class="spinner"></div>
                <p>{{ $t('meal.waiting') }}</p>
              </div>
            </transition>
          </div>
        </div>
      </section>

      <!-- History & Search Section (Toggleable) -->
      <transition name="modal">
        <section v-if="showHistory" class="history-section">
          <div class="history-header">
            <h3>{{ $t('meal.history_title') }}</h3>
            <div class="filters">
              <input type="date" v-model="startDate" class="date-input" />
              <span>-</span>
              <input type="date" v-model="endDate" class="date-input" />
              <div class="search-box">
                <input type="text" v-model="searchQuery" :placeholder="$t('meal.search_placeholder')" @keyup.enter="handleSearch" />
                <button @click="handleSearch">{{ $t('meal.find_btn') }}</button>
              </div>
              <button class="close-history-btn" @click="showHistory = false">✖</button>
            </div>
          </div>

          <div class="history-table-wrapper">
            <table class="history-table">
              <thead>
                <tr>
                  <th>{{ $t('meal.table.time') }}</th>
                  <th>{{ $t('meal.table.emp_id') }}</th>
                  <th>{{ $t('meal.table.name') }}</th>
                  <th>{{ $t('meal.table.dept') }}</th>
                  <th>{{ $t('meal.table.meal') }}</th>
                  <th>{{ $t('meal.table.source') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loadingHistory">
                  <td colspan="6" class="text-center">{{ $t('common.loading') }}</td>
                </tr>
                <tr v-else-if="historyList.length === 0">
                  <td colspan="6" class="text-center">{{ $t('common.no_data') }}</td>
                </tr>
                <tr v-for="(item, index) in historyList" :key="index" class="clickable-row" @click="showHistoryItemOnScreen(item)">
                  <td>{{ item.mfg_day }}</td>
                  <td>{{ item.emp_no }}</td>
                  <td>{{ item.emp_name }}</td>
                  <td>{{ item.department }}</td>
                  <td>
                    <span v-if="item.meal_name_vi" class="meal-tag success">
                      {{ item.meal_name_vi }}
                    </span>
                    <span v-else class="meal-tag error">{{ $t('meal.table.no_dk') }}</span>
                  </td>
                  <td>{{ $t('meal.table.database') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { mealApi } from './api'
import { useLiveLogs } from '@/features/logs/composables/useLiveLogs'
import { useUIStore } from '@/stores/ui'

const { t, locale } = useI18n()
const uiStore = useUIStore()

const canteenMachines = ref([])
const selectedMachine = ref(localStorage.getItem('meal_kiosk_selected_machine') || 'all')

watch(selectedMachine, (newVal) => {
  localStorage.setItem('meal_kiosk_selected_machine', newVal)
})

const currentSwipes = ref({}) // Tracks latest swipe per IP

const showHistory = ref(false)

const quickSearchQuery = ref('')
const isQuickSearching = ref(false)
let searchTimeout = null

function onQuickSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    if (quickSearchQuery.value && quickSearchQuery.value.trim().length >= 3) {
      handleQuickSearch()
    }
  }, 400) // 400ms debounce
}

function toggleHistory() {
  showHistory.value = !showHistory.value
  if (showHistory.value && historyList.value.length === 0) {
    handleSearch()
  }
}

const startDate = ref('')
const endDate = ref('')
const searchQuery = ref('')
const historyList = ref([])
const loadingHistory = ref(false)

const currentTime = ref('')
let timeInterval = null

// Determine which machines to show in the grid
const activeMachines = computed(() => {
  if (selectedMachine.value === 'all') {
    return canteenMachines.value.length > 0 ? canteenMachines.value : []
  }
  return [selectedMachine.value]
})

// Dynamic grid class based on number of active machines
const gridClass = computed(() => {
  const count = activeMachines.value.length
  if (count <= 1) return 'grid-1'
  if (count === 2) return 'grid-2'
  if (count <= 4) return 'grid-2x2'
  return 'grid-auto'
})

const { connect, disconnect, isConnected } = useLiveLogs((payload) => {
  if (payload.type === 'meal_event' || payload.type === 'new_log') {
    const data = payload.data
    const ip = data.machine_ip
    
    // Only process if it belongs to an active machine
    if (activeMachines.value.includes(ip)) {
      // Update the specific machine's latest swipe
      currentSwipes.value[ip] = { ...data, id: Date.now() + Math.random() }
      
      // Play sound
      if (data.meal_info) {
        playSound('success')
      } else {
        playSound('error')
      }
    }
  }
})

function getSwipeStatusClass(swipe) {
  if (!swipe) return ''
  return (swipe.meal_info && swipe.meal_info.is_registered !== false) ? 'status-success' : 'status-error'
}

function getSwipeStatusText(swipe) {
  if (!swipe) return ''
  return (swipe.meal_info && swipe.meal_info.is_registered !== false) 
    ? t('meal.status_valid') 
    : t('meal.status_invalid')
}

function toggleLive() {
  if (isConnected.value) disconnect()
  else connect()
}

async function fetchCanteenMachines() {
  try {
    const { data } = await mealApi.getCanteenMachines()
    canteenMachines.value = data.machines || []
  } catch (e) {
    console.error('Error fetching canteen machines:', e)
  }
}

async function handleSearch() {
  loadingHistory.value = true
  try {
    const listParams = {
      start_date: startDate.value,
      end_date: endDate.value
    }
    if (searchQuery.value) {
      listParams.emp_no = searchQuery.value
    }
    
    const listRes = await mealApi.getMealList(listParams)
    historyList.value = listRes.data.items || []

  } catch (e) {
    console.error('Search error:', e)
  } finally {
    loadingHistory.value = false
  }
}

async function handleQuickSearch() {
  if (!quickSearchQuery.value || isQuickSearching.value) return;
  isQuickSearching.value = true;
  
  try {
    const targetIp = activeMachines.value[0] || 'Manual Entry';
    const { data } = await mealApi.manualSwipe(quickSearchQuery.value, targetIp);
    
    // Format the response into a swipe item for the screen
    showHistoryItemOnScreen({
      emp_no: data.emp_no || quickSearchQuery.value,
      emp_name: data.emp_name || t('meal.unknown_name'),
      department: data.department || '-',
      machine_ip: targetIp,
      attendance_time: new Date().toISOString(),
      meal_info: data.found ? data : null,
      is_registered: data.is_registered
    });
    
    quickSearchQuery.value = ''; // clear after success
  } catch (e) {
    console.error('Manual swipe error:', e);
    playSound('error');
  } finally {
    isQuickSearching.value = false;
    // Keep focus on input for fast typing
    const el = document.querySelector('.header-search input');
    if (el) el.focus();
  }
}

function showHistoryItemOnScreen(item) {
  const targetIp = activeMachines.value[0] || 'all';
  
  if (targetIp && targetIp !== 'all') {
    // Determine meal_info structure depending on if it's from live or DB
    let mealInfo = null;
    if (item.meal_info && item.meal_info.is_registered !== false) {
      mealInfo = item.meal_info;
    } else if (item.is_registered) {
      mealInfo = {
        meal_name_vi: item.meal_name_vi,
        meal_code: item.meal_code,
        is_registered: true
      };
    } else {
      mealInfo = { is_registered: false }; // ensure error status
    }

    currentSwipes.value[targetIp] = {
      id: Date.now(),
      employee_id: item.emp_no || item.employee_id,
      emp_name: item.emp_name,
      department: item.department,
      machine_ip: item.machine_ip || t('meal.history_record'),
      attendance_time: item.attendance_time || new Date().toISOString(),
      meal_info: mealInfo,
      is_live: false
    }

    if (mealInfo && mealInfo.is_registered !== false) playSound('success')
    else playSound('error')
    
    // Auto close history overlay for better view
    showHistory.value = false
  }
}

function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString(locale.value === 'vi' ? 'vi-VN' : 'en-US', { hour12: false })
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString(locale.value === 'vi' ? 'vi-VN' : 'en-US')
}

function playSound(type) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    
    if (type === 'success') {
      osc.type = 'sine'
      osc.frequency.setValueAtTime(800, ctx.currentTime)
      gain.gain.setValueAtTime(0.5, ctx.currentTime)
      osc.start()
      osc.stop(ctx.currentTime + 0.2)
    } else {
      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(300, ctx.currentTime)
      osc.frequency.exponentialRampToValueAtTime(100, ctx.currentTime + 0.5)
      gain.gain.setValueAtTime(0.8, ctx.currentTime)
      osc.start()
      osc.stop(ctx.currentTime + 0.5)
    }
  } catch (e) {
    console.error('Audio error:', e)
  }
}

function enterFullscreen() {
  const elem = document.documentElement;
  if (elem.requestFullscreen) {
    elem.requestFullscreen().catch(err => {
      console.log(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
    });
  }
}

onMounted(() => {
  uiStore.setSidebar(false)
  
  // Try to enter fullscreen (browser may block if not triggered by gesture)
  enterFullscreen()
  const today = new Date().toISOString().split('T')[0]
  startDate.value = today
  endDate.value = today
  
  updateClock()
  timeInterval = setInterval(updateClock, 1000)
  
  fetchCanteenMachines().then(() => {
    // Check if we need to load history automatically
    if (showHistory.value) handleSearch()
  })
  connect()
})

onUnmounted(() => {
  clearInterval(timeInterval)
  disconnect()
})
</script>

<style scoped>
.kiosk-container { display: flex; flex-direction: column; height: calc(100vh - 80px); background-color: var(--bg-color); color: var(--text-color); font-family: 'Inter', sans-serif; overflow: hidden; }
.kiosk-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 24px; background: var(--card-bg); border-bottom: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 10; }
.logo-area { display: flex; align-items: center; gap: 20px; }
.logo-area h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: white; }
.clock { font-size: 1.25rem; font-weight: 600; color: #60a5fa; font-variant-numeric: tabular-nums; }
.controls { display: flex; gap: 16px; align-items: center; }

.btn { padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s; border: 1px solid rgba(255,255,255,0.1); white-space: nowrap; }
.toggle-history-btn { background: #3b82f6; color: white; border-color: #2563eb; }
.toggle-history-btn:hover { background: #2563eb; }
.fullscreen-btn { background: rgba(255,255,255,0.05); color: #94a3b8; display: flex; align-items: center; justify-content: center; padding: 8px; }
.fullscreen-btn:hover { background: rgba(255,255,255,0.1); color: white; }
.machine-select { padding: 8px 12px; border-radius: 8px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: white; font-size: 0.95rem; outline: none; }
.machine-select option { background: var(--card-bg, #1e293b); color: white; }
.live-btn { display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.05); color: #94a3b8; }
.live-btn.active { background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #f87171; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.live-btn.active .dot { animation: pulse 1.5s infinite; }

.kiosk-main { flex: 1; display: flex; flex-direction: column; padding: 16px; gap: 16px; overflow: hidden; position: relative; }

/* Grid Layout */
.live-grid { flex: 1; display: grid; gap: 16px; overflow: hidden; }
.grid-1 { grid-template-columns: 1fr; grid-template-rows: 1fr; }
.grid-2 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr; }
.grid-2x2 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
.grid-auto { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }

.machine-panel { display: flex; flex-direction: column; background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; }
.panel-header { padding: 10px 16px; background: rgba(255,255,255,0.05); font-weight: 600; font-size: 1.1rem; border-bottom: 1px solid var(--border); }
.panel-header span { color: #60a5fa; }
.panel-content { flex: 1; display: flex; align-items: center; justify-content: center; padding: 16px; position: relative; }

.waiting-card { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: var(--text-muted); }
.spinner { width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #60a5fa; border-radius: 50%; animation: spin 1s linear infinite; }

/* Swipe Card Adaptations */
.swipe-card { width: 100%; height: 100%; display: flex; flex-direction: column; background: var(--card-bg); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3); transition: all 0.3s; }
.status-success { border: 4px solid #10b981; box-shadow: inset 0 0 20px rgba(16, 185, 129, 0.1); }
.status-error { border: 4px solid #ef4444; box-shadow: inset 0 0 20px rgba(239, 68, 68, 0.1); }

.status-banner { padding: 10px; text-align: center; font-size: 1.2rem; font-weight: 800; color: white; letter-spacing: 1px; }
.status-success .status-banner { background: #10b981; }
.status-error .status-banner { background: #ef4444; }

.swipe-inner { display: flex; padding: 20px; gap: 20px; flex: 1; align-items: center; }
.emp-info { display: flex; align-items: center; gap: 16px; flex: 1.2; border-right: 1px solid var(--border); padding-right: 20px; }
.avatar { width: 80px; height: 80px; min-width: 80px; border-radius: 50%; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: 700; color: white; }
.name { font-size: 1.6rem; margin: 0 0 5px 0; font-weight: 700; color: white; line-height: 1.2; }
.emp-id, .dept { font-size: 1rem; color: #94a3b8; margin: 2px 0; }

.meal-info { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
.meal-icon { font-size: 3rem; margin-bottom: 5px; }
.meal-icon.error { filter: grayscale(1); opacity: 0.5; }
.meal-name { font-size: 1.8rem; margin: 0; color: #10b981; font-weight: 800; line-height: 1.2;}
.status-error .meal-name { color: #ef4444; }

.swipe-footer { padding: 8px 20px; background: rgba(0,0,0,0.2); font-size: 0.85rem; color: #64748b; text-align: right; }

/* History Section Overlay */
.history-section { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90vw; max-width: 1200px; height: 80vh; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 100vw rgba(0,0,0,0.6); display: flex; flex-direction: column; overflow: hidden; z-index: 1000; }
.history-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 24px; border-bottom: 1px solid #1e293b; background: #1e293b; }
.history-header h3 { margin: 0; }
.filters { display: flex; gap: 10px; align-items: center; }
.close-history-btn { background: none; border: none; color: #ef4444; font-size: 1.2rem; cursor: pointer; padding: 4px; margin-left: 10px; }

.date-input { padding: 6px 10px; border-radius: 6px; background: rgba(0,0,0,0.2); border: 1px solid #1e293b; color: white; color-scheme: dark; }
.search-box { display: flex; margin-left: 10px; }
.search-box input { padding: 6px 12px; border-radius: 6px 0 0 6px; background: rgba(0,0,0,0.2); border: 1px solid #1e293b; color: white; outline: none; min-width: 250px; }
.search-box button { padding: 6px 16px; border-radius: 0 6px 6px 0; background: #3b82f6; border: none; color: white; font-weight: 600; cursor: pointer; transition: background 0.3s; }
.search-box button:hover:not(:disabled) { background: #2563eb; }
.search-box button:disabled { opacity: 0.7; cursor: not-allowed; }

.header-search { margin-left: 0; }
.header-search input { border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; min-width: 220px; }

.history-table-wrapper { flex: 1; overflow-y: auto; }
.history-table { width: 100%; border-collapse: collapse; text-align: left; }
.history-table th { padding: 10px 20px; background: rgba(0,0,0,0.4); font-weight: 600; color: #94a3b8; font-size: 0.9rem; position: sticky; top: 0; }
.history-table td { padding: 10px 20px; border-bottom: 1px solid #1e293b; font-size: 0.95rem; }

.clickable-row { cursor: pointer; transition: background 0.2s; }
.clickable-row:hover td { background: rgba(255, 255, 255, 0.05); }

.meal-tag { padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 600; }
.meal-tag.success { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.meal-tag.error { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

/* Animations */
.modal-enter-active, .modal-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: translate(-50%, -45%) scale(0.95); }

.pop-enter-active { animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.pop-leave-active { animation: pop-out 0.1s ease-in; }
@keyframes pop-in { 0% { opacity: 0; transform: scale(0.95); } 100% { opacity: 1; transform: scale(1); } }
@keyframes pop-out { 0% { opacity: 1; transform: scale(1); } 100% { opacity: 0; transform: scale(0.98); } }
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
