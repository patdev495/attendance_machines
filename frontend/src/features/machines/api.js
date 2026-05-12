const BASE = '/api/machines'

async function apiFetch(url, options = {}) {
  const res = await fetch(BASE + url, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    let msg = err.detail || 'Request failed'
    if (Array.isArray(err.detail)) {
      msg = err.detail.map(d => `${d.loc?.join('.') || 'error'}: ${d.msg}`).join(', ')
    }
    throw new Error(msg)
  }
  return res.json()
}

export function getMachines() {
  return apiFetch('')
}

export function getMachinesCapacity() {
  return apiFetch('/capacity')
}

export function getLiveStatus() {
  return apiFetch('/live-status')
}

export function getMachineEmployees(ip) {
  return apiFetch(`/${encodeURIComponent(ip)}/employees`)
}

export function deleteMachineEmployee(ip, employeeId) {
  return apiFetch(`/${encodeURIComponent(ip)}/employees/${employeeId}`, { method: 'DELETE' })
}

export function bulkDeleteMachineEmployees(ip, employeeIds) {
  return apiFetch(`/${encodeURIComponent(ip)}/employees/bulk-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_ids: employeeIds })
  })
}

export function updateEmployeeName(employeeId, newName) {
  return apiFetch('/update-name', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_id: employeeId, new_name: newName })
  })
}

export function syncFingerprints(ip, employeeId) {
  return apiFetch('/sync-fingerprints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ip, employee_id: employeeId })
  })
}

export function syncAllMachineFingerprints(ip) {
  return apiFetch(`/${encodeURIComponent(ip)}/sync-all-fingerprints`, { method: 'POST' })
}

export function getDeleteStatus(employeeId) {
  return apiFetch(`/delete-status/${employeeId}`)
}

export function syncMachineTime(ip) {
  return apiFetch(`/${encodeURIComponent(ip)}/sync-time`, { method: 'POST' })
}

export function syncAllMachinesTime() {
  return apiFetch('/sync-time-all', { method: 'POST' })
}

export function bulkDeleteGlobal(employeeIds) {
  return apiFetch('/bulk-delete-global', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_ids: employeeIds })
  })
}

export function getBulkDeleteStatus() {
  return apiFetch('/bulk-delete-status')
}

export function bulkPushFingerprints(employeeIds, targetIps) {
  return apiFetch('/bulk-push-fingerprints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_ids: employeeIds, target_ips: targetIps })
  })
}

export function getBulkPushStatus() {
  return apiFetch('/bulk-push-status')
}

export function pushFingerprints(employeeId, targetIps) {
  return apiFetch('/push-fingerprints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_id: employeeId, target_ips: targetIps })
  })
}

export function previewBulkPush(employeeIds) {
  return apiFetch('/bulk-push-preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_ids: employeeIds })
  })
}

export function getPushStatus() {
  return apiFetch('/push-status')
}

export function triggerGlobalSync() {
  return apiFetch('/sync-all-fingerprints-global', { method: 'POST' })
}

export function getGlobalSyncStatus() {
  return apiFetch('/sync-all-fingerprints-global/status')
}

export function clearMachineFingerprints(ip) {
  return apiFetch(`/${ip}/clear-fingerprints`, { method: 'POST' })
}

export function getClearFpStatus() {
  return apiFetch('/clear-fingerprints-status')
}

export function updateUserPrivilege(ip, employeeId, privilege) {
  return apiFetch(`/${encodeURIComponent(ip)}/users/${employeeId}/privilege`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ privilege })
  })
}

export function enrollUser(ip, employeeId, fingerIndex = 0) {
  return apiFetch(`/${encodeURIComponent(ip)}/enroll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_id: employeeId, finger_index: fingerIndex })
  })
}

export function getEnrollStatus(ip) {
  return apiFetch(`/${encodeURIComponent(ip)}/enroll/status`)
}

export function cancelEnroll(ip) {
  return apiFetch(`/${encodeURIComponent(ip)}/enroll/cancel`, { method: 'POST' })
}

export const EXPORT_FINGERPRINTS_URL = BASE + '/export-fingerprints'
