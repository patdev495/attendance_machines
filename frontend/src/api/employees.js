const BASE = '/api'

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

export function triggerSync() {
  return apiFetch('/sync', { method: 'POST' })
}

export function getSyncStatus() {
  return apiFetch('/sync/status')
}

export function syncEmployeesExcel(file) {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch('/sync/excel', { method: 'POST', body: fd })
}

export function deleteEmployeeFromAllMachines(employeeId) {
  return apiFetch(`/devices/delete_global/${employeeId}`, { method: 'DELETE' })
}

export function getDeleteStatus(employeeId) {
  return apiFetch(`/devices/delete_status/${employeeId}`)
}

export function getExcelSyncStatus() {
  return apiFetch('/sync/excel/status')
}

export function getBiometricCoverage(employeeId) {
  return apiFetch(`/employees/${employeeId}/biometric_coverage`)
}
