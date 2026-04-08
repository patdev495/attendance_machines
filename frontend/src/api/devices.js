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

export function getDevicesCapacity() {
  return apiFetch('/devices/capacity')
}

export function getDeviceEmployees(ip, page = 1, size = 5000) {
  return apiFetch(`/devices/${encodeURIComponent(ip)}/employees?page=${page}&size=${size}`)
}

export function deleteDeviceEmployee(ip, employeeId) {
  return apiFetch(`/devices/${encodeURIComponent(ip)}/employees/${employeeId}`, { method: 'DELETE' })
}

export function bulkDeleteDeviceEmployees(ip, employeeIds) {
  return apiFetch(`/devices/${encodeURIComponent(ip)}/employees/bulk_delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_ids: employeeIds })
  })
}

export function updateEmployeeName(employeeId, newName) {
  return apiFetch('/devices/update_name', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_id: employeeId, new_name: newName })
  })
}

export function syncFingerprints(ip, employee_id) {
  return apiFetch('/devices/sync_fingerprints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ip, employee_id })
  })
}

export function syncAllFingerprints(ip) {
  return apiFetch(`/devices/${encodeURIComponent(ip)}/sync_all_fingerprints`, { method: 'POST' })
}

export const EXPORT_FINGERPRINTS_URL = BASE + '/devices/export-fingerprints'
