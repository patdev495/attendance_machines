const BASE = '/api/export-attendance'

async function apiFetch(url, options = {}) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export function startExport(startDate, endDate, viewMode) {
  const q = new URLSearchParams({ start_date: startDate, end_date: endDate, view_mode: viewMode }).toString()
  return apiFetch(`${BASE}/start?${q}`, { method: 'POST' })
}

export function getExportStatus() {
  return apiFetch(`${BASE}/status`)
}

export function cancelExport() {
  return apiFetch(`${BASE}/cancel`, { method: 'POST' })
}

export function downloadExport() {
  window.location.href = `${BASE}/download`
}
