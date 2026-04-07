const BASE = '/api'

async function apiFetch(url, options = {}) {
  const res = await fetch(BASE + url, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export function triggerSync() {
  return apiFetch('/sync', { method: 'POST' })
}

export function getSyncStatus() {
  return apiFetch('/sync-status')
}

export function syncEmployeesExcel(file) {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch('/employees/sync', { method: 'POST', body: fd })
}

export function deleteEmployeeFromAllMachines(employeeId) {
  return apiFetch(`/employees/${employeeId}/machine-data`, { method: 'DELETE' })
}

export function getDeleteStatus() {
  return apiFetch('/employees/delete-status')
}
