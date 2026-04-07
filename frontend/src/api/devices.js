const BASE = '/api'

async function apiFetch(url, options = {}) {
  const res = await fetch(BASE + url, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
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
