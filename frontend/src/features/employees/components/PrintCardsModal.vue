<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <Transition name="scale">
          <div v-if="isOpen" class="modal-content glass shadow-2xl card-print-modal">
            <div class="modal-header">
              <div class="header-title">
                <span class="icon">🖨️</span>
                <h3>{{ $t('employees.card_print.modal_title') }}</h3>
              </div>
              <button class="btn-close" @click="close">×</button>
            </div>

            <div class="modal-body">
              <!-- Mode Selection Switch -->
              <div class="tabs-container">
                <button 
                  id="tab-select"
                  :class="['tab-btn', { active: activeTab === 'select' }]" 
                  @click="activeTab = 'select'"
                >
                  {{ $t('employees.card_print.tab_select') }}
                </button>
                <button 
                  id="tab-upload"
                  :class="['tab-btn', { active: activeTab === 'upload' }]" 
                  @click="activeTab = 'upload'"
                >
                  {{ $t('employees.card_print.tab_upload') }}
                </button>
              </div>

              <!-- Tab content: Select from table -->
              <div v-if="activeTab === 'select'" class="tab-content animate-fade-in">
                <div class="info-banner mb-4">
                  <span class="banner-icon">💡</span>
                  <span v-if="selectedEmployeeIds.length === 0">
                    {{ $t('employees.card_print.select_none_hint') }}
                  </span>
                  <span v-else>
                    {{ $t('employees.card_print.select_count_hint', { count: selectedEmployeeIds.length }) }}
                  </span>
                </div>

                <div v-if="selectedEmployeeIds.length > 0" class="selected-list">
                  <div class="list-title">{{ $t('employees.card_print.preview_list') }}</div>
                  <div class="id-chips-grid">
                    <span 
                      v-for="id in selectedEmployeeIds.slice(0, 6)" 
                      :key="id" 
                      class="id-chip"
                    >
                      ID: {{ id }}
                    </span>
                    <span v-if="selectedEmployeeIds.length > 6" class="id-chip text-danger font-bold">
                      +{{ selectedEmployeeIds.length - 6 }} {{ $t('employees.card_print.more_ignored') }}
                    </span>
                  </div>
                </div>

                <div v-if="selectedEmployeeIds.length > 6" class="alert-banner error-banner mt-3 animate-pulse">
                  ⚠️ <strong>{{ $t('employees.card_print.limit_exceeded_title') }}</strong>: 
                  {{ $t('employees.card_print.limit_exceeded_desc') }}
                </div>
              </div>

              <!-- Tab content: Upload TXT file -->
              <div v-else class="tab-content animate-fade-in">
                <div 
                  class="drop-zone" 
                  :class="{ dragover: isDragOver }"
                  @dragover.prevent="isDragOver = true"
                  @dragleave="isDragOver = false"
                  @drop.prevent="handleFileDrop"
                  @click="$refs.txtFileInput.click()"
                >
                  <input 
                    type="file" 
                    accept=".txt" 
                    hidden 
                    ref="txtFileInput" 
                    @change="handleFileSelect" 
                  />
                  <div class="drop-zone-content">
                    <span class="drop-icon">📄</span>
                    <p class="drop-text">{{ $t('employees.card_print.drop_hint') }}</p>
                    <button class="btn-browse">{{ $t('employees.card_print.browse') }}</button>
                  </div>
                </div>

                <div v-if="uploadedIds.length > 0" class="selected-list mt-4 animate-in">
                  <div class="list-title">
                    {{ $t('employees.card_print.parsed_ids', { count: uploadedIds.length }) }}
                  </div>
                  <div class="id-chips-grid">
                    <span 
                      v-for="(id, idx) in uploadedIds.slice(0, 6)" 
                      :key="id" 
                      class="id-chip"
                      :class="{ 'chip-primary': idx < 6 }"
                    >
                      ID: {{ id }}
                    </span>
                    <span v-if="uploadedIds.length > 6" class="id-chip text-warning font-bold">
                      +{{ uploadedIds.length - 6 }} {{ $t('employees.card_print.more_ignored') }}
                    </span>
                  </div>

                  <div v-if="uploadedIds.length > 6" class="alert-banner warning-banner mt-3">
                    ℹ️ {{ $t('employees.card_print.limit_warn', { count: uploadedIds.length }) }}
                  </div>
                </div>
              </div>

              <!-- Print Settings Form -->
              <div class="settings-form mt-6">
                <div class="form-title">{{ $t('employees.card_print.settings_title') }}</div>
                
                <!-- Agent URL -->
                <div class="form-group">
                  <label for="agent-url">{{ $t('employees.card_print.agent_url') }}</label>
                  <input 
                    id="agent-url"
                    type="text" 
                    v-model="agentUrl" 
                    placeholder="http://localhost:8080" 
                    class="form-control"
                  />
                </div>

                <!-- btw Path -->
                <div class="form-group">
                  <label for="btw-path">{{ $t('employees.card_print.btw_path') }}</label>
                  <input 
                    id="btw-path"
                    type="text" 
                    v-model="btwPath" 
                    placeholder="C:\templates\employee_card.btw" 
                    class="form-control"
                  />
                </div>

                <!-- Printer Selection -->
                <div class="form-group">
                  <div class="label-with-action">
                    <label for="printer-select">{{ $t('employees.card_print.printer_select') }}</label>
                    <button 
                      class="btn-refresh" 
                      @click="fetchPrinters" 
                      :disabled="isFetchingPrinters"
                      title="Tải lại danh sách máy in"
                    >
                      🔄
                    </button>
                  </div>
                  
                  <div class="select-container">
                    <select 
                      id="printer-select"
                      v-model="selectedPrinter" 
                      class="form-control"
                      :disabled="isFetchingPrinters || printers.length === 0"
                    >
                      <option v-if="printers.length === 0" value="">
                        {{ isFetchingPrinters ? $t('employees.card_print.fetching_printers') : $t('employees.card_print.no_printers') }}
                      </option>
                      <option 
                        v-for="p in printers" 
                        :key="p" 
                        :value="p"
                      >
                        {{ p }}
                      </option>
                    </select>
                  </div>

                  <!-- Agent Connection Alert -->
                  <div v-if="agentError" class="alert-banner warning-banner mt-2">
                    ⚠️ {{ agentError }}
                  </div>
                </div>
              </div>

              <!-- Print logs and progress -->
              <div v-if="printStatus.isPrinting || printStatus.message" class="print-log-box mt-4 animate-in">
                <div class="log-header">
                  <span class="log-title">{{ $t('employees.card_print.status') }}</span>
                  <span v-if="printStatus.isPrinting" class="spinner-small"></span>
                </div>
                <div class="log-message" :class="printStatus.type">
                  {{ printStatus.message }}
                </div>
              </div>

              <!-- BTXML Debug Area -->
              <div v-if="isDebugOpen" class="debug-box mt-4 animate-in">
                <div class="log-header">
                  <span class="log-title">XML Script Preview (BTXML)</span>
                  <button class="btn-copy-code" @click="copyBtxml">Sao chép</button>
                </div>
                <pre class="debug-code"><code>{{ debugBtxml }}</code></pre>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-secondary" @click="toggleDebug" :disabled="currentEmployeeIds.length === 0">
                {{ isDebugOpen ? 'Ẩn XML' : 'Xem XML' }}
              </button>
              <button class="btn-secondary" @click="close">{{ $t('common.cancel') }}</button>
              <button 
                class="btn-primary btn-print" 
                @click="handlePrint" 
                :disabled="currentEmployeeIds.length === 0 || currentEmployeeIds.length > 6 || printStatus.isPrinting"
              >
                <span class="icon">🖨️</span> {{ $t('employees.card_print.button_print') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { employeesApi } from '../api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  isOpen: Boolean,
  selectedEmployeeIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const activeTab = ref('select') // 'select' | 'upload'
const isDragOver = ref(false)
const uploadedIds = ref([])

// Settings
const agentUrl = ref(localStorage.getItem('bartender_agent_url') || 'http://localhost:8080')
const btwPath = ref(localStorage.getItem('bartender_btw_path') || 'C:\\templates\\employee_card.btw')
const selectedPrinter = ref(localStorage.getItem('bartender_selected_printer') || '')

const printers = ref([])
const isFetchingPrinters = ref(false)
const agentError = ref('')

// Printing state
const printStatus = ref({
  isPrinting: false,
  message: '',
  type: '' // 'info', 'success', 'error'
})

// Debug preview
const isDebugOpen = ref(false)
const debugBtxml = ref('')

const currentEmployeeIds = computed(() => {
  if (activeTab.value === 'select') {
    return props.selectedEmployeeIds
  } else {
    return uploadedIds.value
  }
})

// Persist configurations
watch(agentUrl, (newVal) => {
  localStorage.setItem('bartender_agent_url', newVal)
})
watch(btwPath, (newVal) => {
  localStorage.setItem('bartender_btw_path', newVal)
})
watch(selectedPrinter, (newVal) => {
  localStorage.setItem('bartender_selected_printer', newVal)
})

// Fetch printers from agent on open
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    fetchPrinters()
    // Reset state
    printStatus.value = { isPrinting: false, message: '', type: '' }
    uploadedIds.value = []
    isDebugOpen.value = false
    debugBtxml.value = ''
  }
})

const close = () => {
  emit('close')
}

// Fetch printer list from local agent
async function fetchPrinters() {
  isFetchingPrinters.value = true
  agentError.value = ''
  printers.value = []
  
  const cleanUrl = agentUrl.value.replace(/\/+$/, '')
  try {
    const res = await fetch(`${cleanUrl}/printers`, { signal: AbortSignal.timeout(3000) })
    if (!res.ok) throw new Error('Cannot fetch printer list')
    const list = await res.json()
    printers.value = list
    
    // Auto-select first printer if not set or not in list
    if (list.length > 0) {
      if (!selectedPrinter.value || !list.includes(selectedPrinter.value)) {
        selectedPrinter.value = list[0]
      }
    }
  } catch (err) {
    console.error('Failed to contact print agent:', err)
    agentError.value = t('employees.card_print.agent_offline_error')
  } finally {
    isFetchingPrinters.value = false
  }
}

// File uploads
function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) parseFile(file)
}

function handleFileDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) parseFile(file)
}

function parseFile(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target.result
    // Split by newlines, trim, and filter empty lines
    const ids = text.split(/\r?\n/).map(line => line.trim()).filter(line => line.length > 0)
    uploadedIds.value = ids
  }
  reader.readAsText(file)
}

// Debug XML preview
async function toggleDebug() {
  if (isDebugOpen.value) {
    isDebugOpen.value = false
    return
  }
  
  const ids = currentEmployeeIds.value.slice(0, 6)
  if (ids.length === 0) return
  
  try {
    printStatus.value = { isPrinting: true, message: 'Đang chuẩn bị dữ liệu XML...', type: 'info' }
    const res = await employeesApi.getCardPrintBtxml(ids)
    
    // Inject correct template path
    let xml = res.btxml
    xml = xml.replace('<Format>C:\\templates\\employee_card.btw</Format>', `<Format>${btwPath.value}</Format>`)
    if (selectedPrinter.value) {
      xml = xml.replace('<Printer>Default</Printer>', `<Printer>${selectedPrinter.value}</Printer>`)
    }
    
    debugBtxml.value = xml
    isDebugOpen.value = true
    printStatus.value = { isPrinting: false, message: '', type: '' }
  } catch (err) {
    printStatus.value = { 
      isPrinting: false, 
      message: `Không thể tạo XML: ${err.response?.data?.detail || err.message}`, 
      type: 'error' 
    }
  }
}

function copyBtxml() {
  navigator.clipboard.writeText(debugBtxml.value)
  alert('Đã sao chép mã XML vào Clipboard!')
}

// Perform printing
async function handlePrint() {
  const ids = currentEmployeeIds.value.slice(0, 6)
  if (ids.length === 0) return
  
  printStatus.value = { isPrinting: true, message: t('employees.card_print.log_generating_btxml'), type: 'info' }
  
  try {
    // 1. Get BTXML from Server
    const res = await employeesApi.getCardPrintBtxml(ids)
    let xml = res.btxml
    
    // Inject the btw path and printer overrides
    xml = xml.replace('<Format>C:\\templates\\employee_card.btw</Format>', `<Format>${btwPath.value}</Format>`)
    if (selectedPrinter.value) {
      xml = xml.replace('<Printer>Default</Printer>', `<Printer>${selectedPrinter.value}</Printer>`)
    }
    
    printStatus.value = { isPrinting: true, message: t('employees.card_print.log_sending_agent'), type: 'info' }
    
    const cleanUrl = agentUrl.value.replace(/\/+$/, '')
    // 2. Post to Local Print Agent
    const printRes = await fetch(`${cleanUrl}/print`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        xml_content: xml,
        printer_name: selectedPrinter.value || null,
        local_template_dir: null
      }),
      signal: AbortSignal.timeout(15000)
    })
    
    const printData = await printRes.json()
    if (!printRes.ok) {
      throw new Error(printData.detail || 'Lỗi in từ Agent')
    }
    
    printStatus.value = { 
      isPrinting: false, 
      message: t('employees.card_print.log_success'), 
      type: 'success' 
    }
  } catch (err) {
    console.error('Printing failed:', err)
    let errMsg = err.message
    if (err.message === 'Failed to fetch' || err.name === 'TimeoutError') {
      errMsg = t('employees.card_print.log_agent_conn_failed')
    }
    printStatus.value = { 
      isPrinting: false, 
      message: `${t('employees.card_print.log_failed')}: ${errMsg}`, 
      type: 'error' 
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 11, 14, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1.5rem;
}

.modal-content {
  background: rgba(23, 25, 30, 0.95);
  width: 100%;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: white;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.modal-header {
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-title h3 {
  margin: 0;
  font-size: 1.25rem;
}

.btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
}

.btn-close:hover {
  color: #f43f5e;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

/* Transition animations */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.scale-enter-active, .scale-leave-active {
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease;
}
.scale-enter-from, .scale-leave-to {
  transform: scale(0.95);
  opacity: 0;
}

.card-print-modal {
  max-width: 580px;
}

.tabs-container {
  display: flex;
  border-bottom: 2px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 1.5rem;
}

.tab-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--accent-color, #3b82f6);
  border-bottom: 2px solid var(--accent-color, #3b82f6);
}

.info-banner {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  color: #93c5fd;
  font-size: 0.9rem;
  line-height: 1.4;
}

.selected-list {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 1rem;
}

.list-title {
  font-size: 0.85rem;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
  font-weight: 700;
}

.id-chips-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.id-chip {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.35rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-family: monospace;
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
}

.chip-primary {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.drop-zone {
  border: 2px dashed rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  padding: 2.5rem 1.5rem;
  text-align: center;
  background: rgba(255, 255, 255, 0.01);
  cursor: pointer;
  transition: all 0.3s ease;
}

.drop-zone:hover, .drop-zone.dragover {
  border-color: var(--accent-color, #3b82f6);
  background: rgba(59, 130, 246, 0.04);
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.drop-icon {
  font-size: 2.5rem;
}

.drop-text {
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin: 0;
}

.btn-browse {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-browse:hover {
  background: rgba(255, 255, 255, 0.15);
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-title {
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
  border-left: 3px solid var(--accent-color, #3b82f6);
  padding-left: 0.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.label-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-refresh {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  transition: transform 0.2s ease;
}

.btn-refresh:active {
  transform: rotate(90deg);
}

.form-control {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  padding: 0.65rem 0.85rem;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  width: 100%;
}

.form-control:focus {
  border-color: var(--accent-color, #3b82f6);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
  outline: none;
}

.alert-banner {
  padding: 0.65rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  line-height: 1.4;
}

.warning-banner {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  color: #fcd34d;
}

.error-banner {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.print-log-box {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 0.75rem 1rem;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.log-title {
  font-size: 0.8rem;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--text-secondary);
}

.log-message {
  font-size: 0.9rem;
  font-family: var(--font-family);
  font-weight: 500;
}

.log-message.info {
  color: #60a5fa;
}

.log-message.success {
  color: #34d399;
}

.log-message.error {
  color: #f87171;
}

/* XML Preview Styles */
.debug-box {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 0.75rem 1rem;
}

.btn-copy-code {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-copy-code:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.15);
}

.debug-code {
  max-height: 180px;
  overflow-y: auto;
  margin: 0.5rem 0 0 0;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
  font-size: 0.8rem;
  color: #34d399;
  text-align: left;
}

.btn-print {
  min-width: 120px;
}

/* Animations */
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
