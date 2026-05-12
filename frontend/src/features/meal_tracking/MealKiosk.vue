<template>
  <div class="kiosk-container">
    <header class="kiosk-header">
      <div class="logo-area">
        <h1>🍽️ {{ $t('meal.kiosk_title') }}</h1>
        <div class="clock">{{ currentTime }}</div>
      </div>
      <div class="controls">
        <button class="btn toggle-history-btn" @click="toggleHistory">
          {{ $t('meal.search_btn') }}
        </button>
        <select v-model="selectedMachine" class="machine-select">
          <option value="all">{{ $t('meal.all_machines') }}</option>
          <option v-for="ip in canteenMachines" :key="ip" :value="ip">
            {{ getMachineStatusIcon(ip) }} {{ ip }}
          </option>
        </select>
        <button 
          class="btn live-btn" 
          :class="{ active: isConnected }"
          @click="toggleLive"
        >
          <span class="dot"></span> LIVE
        </button>
        <select v-model="currentLang" @change="changeLanguage" class="lang-select">
          <option value="vi">🇻🇳 VI</option>
          <option value="en">🇬🇧 EN</option>
          <option value="zh">🇨🇳 ZH</option>
        </select>
        <button class="btn" :class="isMuted ? 'btn-danger' : 'btn-secondary'" @click="toggleMute" :title="isMuted ? 'Unmute' : 'Mute'">
          {{ isMuted ? '🔇' : '🔊' }}
        </button>
        <button class="btn fullscreen-btn" @click="enterFullscreen" title="Fullscreen">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
        </button>
        <button class="btn btn-secondary home-btn" @click="goHome">
          🏠 {{ $t('common.home') }}
        </button>
      </div>
    </header>

    <main class="kiosk-main split-layout">
      <!-- Left Panel -->
      <section class="left-panel">
        
        <!-- Input Bar (Top, Smaller) -->
        <div class="input-bar small-input">
          <input type="text" ref="searchInput" v-model="quickSearchQuery" :placeholder="$t('meal.quick_search_placeholder')" @keyup.enter="handleQuickSearch" :disabled="isQuickSearching" autofocus />
          <button class="btn btn-primary" @click="handleQuickSearch">{{ $t('meal.input_code_btn') }}</button>
          <button class="btn btn-secondary" @click="focusInput">Focus</button>
        </div>

        <!-- Big Status Card Grid -->
        <div class="main-card-wrapper" :style="{ gridTemplateColumns: `repeat(${activeMachines.length || 1}, 1fr)` }">
          <div v-for="ip in activeMachines" :key="ip" class="machine-column">
            <div class="machine-ip-label">{{ $t('meal.machine_label') }} {{ ip }}</div>
            <transition name="pop" mode="out-in">
              <div v-if="latestSwipes[ip]" :key="latestSwipes[ip].id" class="swipe-card" :class="getSwipeStatusClass(latestSwipes[ip])">
                <div class="status-banner">
                  {{ getSwipeStatusText(latestSwipes[ip]) }}
                </div>
                <div class="swipe-inner">
                  <div class="emp-info">
                    <div class="avatar">{{ getInitials(latestSwipes[ip].emp_name) }}</div>
                    <div class="details">
                      <h2 class="name">{{ latestSwipes[ip].emp_name || $t('meal.unknown_name') }}</h2>
                      <p class="emp-id">{{ $t('meal.emp_id_label') }} {{ latestSwipes[ip].employee_id }}</p>
                      <p class="dept">{{ $t('meal.dept_label') }} {{ latestSwipes[ip].department || '-' }}</p>
                    </div>
                  </div>
                  <div class="meal-info">
                    <template v-if="latestSwipes[ip].meal_info && latestSwipes[ip].meal_info.is_registered !== false">
                      <div class="meal-icon">🍱</div>
                      <h3 class="meal-name">{{ getMealName(latestSwipes[ip].meal_info) }}</h3>
                    </template>
                    <template v-else>
                      <div class="meal-icon error">❌</div>
                      <h3 class="meal-name">{{ $t('meal.not_registered') }}</h3>
                    </template>
                  </div>
                </div>
                <div class="swipe-footer">
                  {{ $t('meal.time_label') }} {{ formatTime(latestSwipes[ip].attendance_time) }}
                </div>
              </div>
              
              <div v-else class="waiting-card swipe-card">
                <div class="spinner"></div>
                <p>{{ $t('meal.waiting') }}</p>
              </div>
            </transition>
          </div>
        </div>

        <!-- Stats Grid -->
        <div class="stats-grid">
          <div class="stat-box" v-for="type in ['RICE', 'NOODLE', 'BREAD']" :key="type">
            <div class="stat-title">{{ $t(`meal.stats.${type.toLowerCase()}`) }}</div>
            <div class="stat-numbers">
              <div class="stat-col">
                <span class="stat-label">{{ $t('meal.stats.registered') }}</span>
                <span class="stat-val">{{ stats[type]?.registered || 0 }}</span>
              </div>
              <div class="stat-col">
                <span class="stat-label">{{ $t('meal.stats.picked_up') }}</span>
                <span class="stat-val highlight">{{ stats[type]?.picked_up || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

      </section>

      <!-- Right Panel -->
      <section class="right-panel">
        <div class="history-header-live">
          <h3>{{ $t('meal.live_history_title') }}</h3>
          <span style="font-size: 0.9rem; color: #94a3b8; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 12px;">
            {{ $t('meal.record_count', { count: liveHistory.length }) }}
          </span>
        </div>
        <div class="live-history-list">
          <transition-group name="list">
            <div v-for="item in liveHistory" :key="item.id" class="history-item" :class="getSwipeStatusClass(item)">
              <div class="hi-top">
                <span class="hi-name">{{ item.emp_name || '?' }} ({{ item.employee_id }})</span>
                <span class="hi-time">{{ formatTime(item.attendance_time) }}</span>
              </div>
              <div class="hi-status">{{ getSwipeStatusText(item) }}</div>
              <div class="hi-desc" v-if="item.meal_info && item.meal_info.is_registered !== false">
                {{ $t('meal.today_reg_msg', { meal: getMealName(item.meal_info) }) }}
              </div>
            </div>
          </transition-group>
        </div>
      </section>

      <!-- Old History & Search Section (Toggleable) -->
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
import { useRouter } from 'vue-router'
import { mealApi } from './api'
import { getLiveStatus } from '@/features/machines/api'
import { useLiveLogs } from '@/features/logs/composables/useLiveLogs'
import { useUIStore } from '@/stores/ui'
import { setLanguage } from '@/i18n/index.js'

const { t, locale } = useI18n()
const uiStore = useUIStore()
const router = useRouter()

const currentLang = ref(locale.value)
const isMuted = ref(localStorage.getItem('meal_kiosk_muted') === 'true')

function toggleMute() {
  isMuted.value = !isMuted.value
  localStorage.setItem('meal_kiosk_muted', isMuted.value)
}

function changeLanguage() {
  setLanguage(currentLang.value)
}

function getMealName(mealInfo) {
  if (!mealInfo) return ''
  const code = mealInfo.meal_code?.toLowerCase()
  if (code && t(`meal.stats.${code}`) !== `meal.stats.${code}`) {
    return t(`meal.stats.${code}`)
  }
  return locale.value === 'vi' ? mealInfo.meal_name_vi : mealInfo.meal_name_zh
}

function goHome() {
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(err => console.log(err));
  }
  router.push('/')
}

const canteenMachines = ref([])
const selectedMachine = ref(localStorage.getItem('meal_kiosk_selected_machine') || 'all')

watch(selectedMachine, (newVal) => {
  localStorage.setItem('meal_kiosk_selected_machine', newVal)
})

watch(locale, (newVal) => {
  currentLang.value = newVal
  updateClock()
})

const latestSwipes = ref({})
const liveHistory = ref([])
const stats = ref({
  RICE: { registered: 0, picked_up: 0 },
  NOODLE: { registered: 0, picked_up: 0 },
  BREAD: { registered: 0, picked_up: 0 }
})
const machineStatus = ref({})
const showHistory = ref(false)

const searchInput = ref(null)
const quickSearchQuery = ref('')
const isQuickSearching = ref(false)

function focusInput() {
  if (searchInput.value) searchInput.value.focus()
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

const activeMachines = computed(() => {
  if (selectedMachine.value === 'all') {
    return canteenMachines.value.length > 0 ? canteenMachines.value : ['Manual Entry']
  }
  return [selectedMachine.value]
})

async function fetchStats() {
  try {
    const { data } = await mealApi.getTodayStats()
    if (!data.error) {
      stats.value = data
    }
  } catch(e) {
    console.error("Failed to fetch stats", e)
  }
}

const { connect, disconnect, isConnected } = useLiveLogs((payload) => {
  if (payload.type === 'meal_event' || payload.type === 'new_log') {
    const data = payload.data
    const ip = data.machine_ip || 'Manual Entry'
    
    if (activeMachines.value.includes(ip) || selectedMachine.value === 'all') {
      const currentEmpId = data.emp_no || data.employee_id;
      
      // Debounce rapid duplicate swipes (e.g. holding finger on scanner)
      const previousSwipe = latestSwipes.value[ip];
      if (previousSwipe && previousSwipe.employee_id === currentEmpId && data.is_duplicate) {
        const timeDiff = Math.abs(new Date(data.attendance_time) - new Date(previousSwipe.attendance_time));
        if (timeDiff < 10000) { // 10 seconds
          console.log("Ignoring rapid duplicate swipe from scanner");
          return;
        }
      }

      const swipeObj = { ...data, id: Date.now() + Math.random(), employee_id: currentEmpId }
      latestSwipes.value = {
        ...latestSwipes.value,
        [ip]: swipeObj
      }
      
      const isSuccess = !data.is_duplicate && data.meal_info && data.meal_info.is_registered !== false;
      
      if (isSuccess) {
        liveHistory.value.unshift(swipeObj)
        if (liveHistory.value.length > 50) liveHistory.value.pop()
      }
      
      if (data.is_duplicate) {
        playSound('duplicate', data.meal_info)
      } else if (isSuccess) {
        playSound('success')
        speakMeal(data.meal_info)
        fetchStats()
      } else {
        playSound('error')
      }
    }
  }
})

function getSwipeStatusClass(swipe) {
  if (!swipe) return ''
  // Error if: No meal info at all, OR explicitly not registered
  if (!swipe.meal_info || swipe.meal_info.is_registered === false) return 'status-error'
  if (swipe.is_duplicate) return 'status-warning'
  return 'status-success'
}

function getSwipeStatusText(swipe) {
  if (!swipe) return ''
  if (!swipe.meal_info || swipe.meal_info.is_registered === false) return t('meal.status_invalid')
  if (swipe.is_duplicate) return t('meal.status_duplicate')
  return t('meal.status_valid')
}

function toggleLive() {
  if (isConnected.value) disconnect()
  else connect()
}

async function fetchCanteenMachines() {
  try {
    const { data } = await mealApi.getCanteenMachines()
    canteenMachines.value = data.machines || []
    fetchLiveStatus()
  } catch (e) {
    console.error('Error fetching canteen machines:', e)
  }
}

async function fetchLiveStatus() {
  try {
    const data = await getLiveStatus()
    machineStatus.value = data || {}
  } catch (e) {
    console.error('Error fetching machine status:', e)
  }
}

function getMachineStatusIcon(ip) {
  const status = machineStatus.value[ip]
  if (status === 'connected') return '🟢'
  if (status === 'stuck') return '🟡'
  if (status === 'disconnected') return '🔴'
  return '⚪'
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
    
    showHistoryItemOnScreen({
      emp_no: data.emp_no || quickSearchQuery.value,
      emp_name: data.emp_name || t('meal.unknown_name'),
      department: data.department || '-',
      machine_ip: targetIp,
      attendance_time: new Date().toISOString(),
      meal_info: data.found ? data : null,
      is_registered: data.is_registered,
      is_duplicate: data.is_duplicate
    });
    
    quickSearchQuery.value = '';
  } catch (e) {
    console.error('Manual swipe error:', e);
    playSound('error');
  } finally {
    isQuickSearching.value = false;
    focusInput();
  }
}

function showHistoryItemOnScreen(item) {
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
    mealInfo = { is_registered: false };
  }
  
  const ip = item.machine_ip || 'Manual Entry'

  const swipeObj = {
    id: Date.now(),
    employee_id: item.emp_no || item.employee_id,
    emp_name: item.emp_name,
    department: item.department,
    machine_ip: ip,
    attendance_time: item.attendance_time || new Date().toISOString(),
    meal_info: mealInfo,
    is_duplicate: item.is_duplicate,
    is_live: false
  }
  
  latestSwipes.value = {
    ...latestSwipes.value,
    [ip]: swipeObj
  }
  
  const isSuccess = !item.is_duplicate && mealInfo && mealInfo.is_registered !== false;
  if (isSuccess) {
    liveHistory.value.unshift(swipeObj)
    if (liveHistory.value.length > 50) liveHistory.value.pop()
  }

  if (item.is_duplicate) playSound('duplicate', mealInfo)
  else if (isSuccess) {
    playSound('success')
    speakMeal(mealInfo)
    fetchStats()
  }
  else playSound('error')
  
  showHistory.value = false
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

let audioContext = null;

function playAudioFile(fileName) {
  if (isMuted.value) return;
  try {
    const audio = new Audio(`/audio/${fileName}`);
    audio.volume = 1.0;
    audio.play().catch(e => console.warn(`Audio file ${fileName} missing or failed:`, e));
  } catch (e) {
    console.error("Audio error:", e);
  }
}

function playSound(type, mealInfo = null) {
  if (isMuted.value) return;
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = audioContext;
    
    const playTone = (freq, t, duration, startTime = 0, gainValue = 1.0) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.type = t;
      osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);
      
      gain.gain.setValueAtTime(0, ctx.currentTime + startTime);
      gain.gain.linearRampToValueAtTime(gainValue, ctx.currentTime + startTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + startTime + duration);
      
      osc.start(ctx.currentTime + startTime);
      osc.stop(ctx.currentTime + startTime + duration);
    };

    if (type === 'success') {
      playTone(1200, 'sine', 0.15, 0, 1.0);
      playTone(1500, 'sine', 0.2, 0.1, 1.0);
    } else if (type === 'duplicate') {
      playTone(600, 'triangle', 0.3, 0, 1.0);
      playTone(400, 'triangle', 0.4, 0.2, 1.0);
      
      // Chọn file trung lặp theo món ăn
      const code = mealInfo?.meal_code?.toLowerCase() || '';
      let fileName = 'trung_lap.mp3';
      if (code.includes('rice')) fileName = 'trung_lap_com.mp3';
      else if (code.includes('noodle')) fileName = 'trung_lap_my.mp3';
      else if (code.includes('bread')) fileName = 'trung_lap_banh_mi.mp3';
      
      setTimeout(() => playAudioFile(fileName), 500);
    } else {
      playTone(150, 'sawtooth', 0.2, 0, 1.0);
      playTone(150, 'sawtooth', 0.2, 0.15, 1.0);
      playTone(100, 'sawtooth', 0.3, 0.3, 1.0);
      setTimeout(() => playAudioFile('chua_dang_ky.mp3'), 500);
    }
  } catch (e) {
    console.error('Audio error:', e);
  }
}

let currentUtterance = null; // Prevent garbage collection

function playMealAudio(mealInfo) {
  if (isMuted.value || !mealInfo || !mealInfo.meal_code) return;
  
  const code = mealInfo.meal_code.toLowerCase();
  let fileName = '';
  
  // Ánh xạ mã suất ăn sang tên file mp3
  if (code.includes('rice')) fileName = 'com.mp3';
  else if (code.includes('noodle')) fileName = 'my.mp3';
  else if (code.includes('bread')) fileName = 'banh_mi.mp3';
  else fileName = 'success.mp3'; // Fallback nếu không khớp

  try {
    const audio = new Audio(`/audio/${fileName}`);
    audio.volume = 1.0;
    
    // Phát sau một khoảng nghỉ ngắn để không bị chồng lên tiếng bíp hệ thống
    setTimeout(() => {
      audio.play().catch(e => console.warn("Audio play failed (maybe file missing):", e));
    }, 500);
  } catch (e) {
    console.error("Audio error:", e);
  }
}

function speakMeal(mealInfo) {
  // Giữ lại tên hàm cũ để không phải sửa nhiều chỗ, nhưng đổi ruột sang dùng playMealAudio
  playMealAudio(mealInfo);
}

function enterFullscreen() {
  const elem = document.querySelector('.kiosk-container') || document.documentElement;
  if (elem.requestFullscreen) {
    elem.requestFullscreen().catch(err => {
      console.log(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
    });
  }
}

async function loadTodayPickups() {
  try {
    const { data } = await mealApi.getTodayPickups()
    if (data && data.items) {
      const mappedItems = data.items.map(item => ({
        id: item.emp_no + item.attendance_time,
        employee_id: item.emp_no,
        emp_name: item.emp_name,
        department: item.department,
        attendance_time: item.attendance_time,
        machine_ip: item.machine_ip,
        meal_info: {
          meal_code: item.meal_code,
          meal_name_vi: item.meal_name_vi,
          is_registered: true
        },
        is_duplicate: false
      }));
      
      liveHistory.value = mappedItems;
      
      // Also populate latestSwipes so the left panel isn't empty on load
      const newLatest = { ...latestSwipes.value };
      for (let i = mappedItems.length - 1; i >= 0; i--) {
        const item = mappedItems[i];
        if (item.machine_ip) {
          newLatest[item.machine_ip] = item;
        }
      }
      latestSwipes.value = newLatest;
    }
  } catch (e) {
    console.error('Failed to load today pickups', e)
    alert('Lỗi khi tải lịch sử ăn: ' + (e.message || e))
  }
}

onMounted(() => {
  uiStore.setSidebar(false)
  enterFullscreen()
  const today = new Date().toISOString().split('T')[0]
  startDate.value = today
  endDate.value = today
  
  updateClock()
  timeInterval = setInterval(updateClock, 1000)
  
  fetchStats()
  loadTodayPickups()
  setInterval(fetchStats, 60000) 
  setInterval(fetchLiveStatus, 10000) 
  
  fetchCanteenMachines().then(() => {
    if (showHistory.value) handleSearch()
  })
  connect()
})

onUnmounted(() => {
  clearInterval(timeInterval)
  disconnect()
  uiStore.setSidebar(true)
})
</script>

<style scoped>
.kiosk-container { display: flex; flex-direction: column; flex: 1; height: 100%; min-height: calc(100vh - 60px); background-color: var(--bg-color); color: var(--text-color); font-family: 'Inter', sans-serif; overflow: hidden; }
.kiosk-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 24px; background: var(--card-bg); border-bottom: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 10; }
.logo-area { display: flex; align-items: center; gap: 20px; }
.logo-area h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: white; }
.clock { font-size: 1.25rem; font-weight: 600; color: #60a5fa; font-variant-numeric: tabular-nums; }
.controls { display: flex; gap: 16px; align-items: center; }

.btn { padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s; border: 1px solid rgba(255,255,255,0.1); white-space: nowrap; }
.btn-primary { background: #3b82f6; color: white; border-color: #2563eb; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { background: rgba(255,255,255,0.1); color: white; }
.btn-secondary:hover { background: rgba(255,255,255,0.2); }
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

.split-layout {
  display: flex;
  flex-direction: row;
  flex: 1;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}
.left-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 15px;
  min-width: 0;
  overflow-y: auto; 
}
.right-panel {
  flex: 1;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 350px;
}

/* Left Panel Elements */
.input-bar { display: flex; gap: 10px; padding: 10px 15px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; align-items: center; }
.input-bar.small-input input { flex: 1; padding: 8px 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); color: white; font-size: 1rem; outline: none; transition: border-color 0.3s; }
.input-bar.small-input input:focus { border-color: #3b82f6; }
.input-bar.small-input .btn { font-size: 0.95rem; padding: 6px 16px; }

.main-card-wrapper {
  flex: 1;
  display: grid;
  gap: 20px;
  min-height: 250px;
}
.machine-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.machine-ip-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #94a3b8;
  text-align: center;
  background: rgba(255, 255, 255, 0.05);
  padding: 6px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.btn:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.lang-select {
  background: #1e293b;
  color: white;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  outline: none;
}
.lang-select:hover {
  border-color: var(--primary);
}

.swipe-card { width: 100%; height: 100%; display: flex; flex-direction: column; background: var(--card-bg); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3); transition: all 0.3s; }
.status-success { border: 4px solid #10b981; box-shadow: inset 0 0 20px rgba(16, 185, 129, 0.1); }
.status-error { border: 4px solid #ef4444; box-shadow: inset 0 0 20px rgba(239, 68, 68, 0.1); }
.status-warning { border: 4px solid #f59e0b; box-shadow: inset 0 0 20px rgba(245, 158, 11, 0.1); }

.status-banner { padding: 10px; text-align: center; font-size: 1.1rem; font-weight: 800; color: white; letter-spacing: 1px; }
.status-success .status-banner { background: #10b981; }
.status-error .status-banner { background: #ef4444; }
.status-warning .status-banner { background: #f59e0b; }

.swipe-inner { display: flex; padding: 15px; gap: 15px; flex: 1; align-items: center; justify-content: center; }
.emp-info { display: flex; flex-direction: column; align-items: center; gap: 10px; flex: 1; border-right: 1px solid var(--border); padding-right: 15px; text-align: center; }
.avatar { width: 70px; height: 70px; min-width: 70px; border-radius: 50%; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 700; color: white; }
.name { font-size: 1.3rem; margin: 0 0 4px 0; font-weight: 700; color: white; line-height: 1.2; word-break: break-word; }
.emp-id, .dept { font-size: 0.9rem; color: #94a3b8; margin: 2px 0; }

.meal-info { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
.meal-icon { font-size: 2.8rem; margin-bottom: 5px; }
.meal-icon.error { filter: grayscale(1); opacity: 0.5; }
.meal-name { font-size: 1.4rem; margin: 0; color: #10b981; font-weight: 800; line-height: 1.2;}
.status-error .meal-name { color: #ef4444; }

.swipe-footer { padding: 8px 15px; background: rgba(0,0,0,0.2); font-size: 0.85rem; color: #64748b; text-align: center; }

.waiting-card { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; color: var(--text-muted); background: var(--card-bg); border: 2px dashed rgba(255,255,255,0.1); }
.spinner { width: 50px; height: 50px; border: 4px solid rgba(255,255,255,0.1); border-top-color: #60a5fa; border-radius: 50%; animation: spin 1s linear infinite; }

.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: auto; }
.stat-box { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.stat-title { font-size: 1rem; font-weight: 700; color: #94a3b8; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 6px; }
.stat-numbers { display: flex; justify-content: space-around; }
.stat-col { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.stat-label { font-size: 0.8rem; color: #64748b; }
.stat-val { font-size: 1.4rem; font-weight: 800; color: white; }
.stat-val.highlight { color: #10b981; }

/* Right Panel Elements */
.history-header-live { padding: 15px 20px; border-bottom: 1px solid var(--border); background: rgba(255,255,255,0.02); display: flex; justify-content: space-between; align-items: center; }
.history-header-live h3 { margin: 0; font-size: 1.1rem; color: white; }
.history-header-live span { font-size: 0.9rem; color: #64748b; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 12px; }
.live-history-list { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }
.history-item { padding: 12px 15px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 4px solid transparent; display: flex; flex-direction: column; gap: 6px; }
.history-item.status-success { border-left-color: #10b981; background: rgba(16, 185, 129, 0.05); }
.history-item.status-error { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
.history-item.status-warning { border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.05); }
.hi-top { display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; }
.hi-name { font-weight: 700; color: white; }
.hi-time { color: #64748b; font-size: 0.8rem; }
.hi-status { font-weight: 700; font-size: 0.95rem; }
.status-success .hi-status { color: #10b981; }
.status-error .hi-status { color: #ef4444; }
.status-warning .hi-status { color: #f59e0b; }
.hi-desc { font-size: 0.85rem; color: #94a3b8; }

/* Existing Overlay Modals */
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
.list-enter-active, .list-leave-active { transition: all 0.3s ease; }
.list-enter-from { opacity: 0; transform: translateX(30px); }
.list-leave-to { opacity: 0; transform: translateX(-30px); }

.modal-enter-active, .modal-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: translate(-50%, -45%) scale(0.95); }

.pop-enter-active { animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.pop-leave-active { animation: pop-out 0.1s ease-in; }
@keyframes pop-in { 0% { opacity: 0; transform: scale(0.95); } 100% { opacity: 1; transform: scale(1); } }
@keyframes pop-out { 0% { opacity: 1; transform: scale(1); } 100% { opacity: 0; transform: scale(0.98); } }
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
