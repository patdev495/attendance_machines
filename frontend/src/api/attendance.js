const BASE = '/api'

async function apiFetch(url, options = {}) {
  const res = await fetch(BASE + url, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export function getMachines() {
  return apiFetch('/machines')
}

export function getAttendance(params) {
  const q = new URLSearchParams(params).toString()
  return apiFetch(`/attendance?${q}`)
}

export function getAttendanceSummary(params) {
  const q = new URLSearchParams(params).toString()
  return apiFetch(`/attendance/summary?${q}`)
}

export function exportAttendance(startDate, endDate, viewMode) {
  window.location.href = `${BASE}/export-attendance?start_date=${startDate}&end_date=${endDate}&view_mode=${viewMode}`
}
