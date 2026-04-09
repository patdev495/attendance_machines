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

export async function downloadExport() {
  console.log('Initiating Blob download...');
  const res = await fetch(`${BASE}/download`)
  if (!res.ok) throw new Error('Download failed')
  
  const blob = await res.blob();
  console.log('Blob received:', blob.size, 'bytes');
  
  // Extract filename from Content-Disposition header
  const disposition = res.headers.get('Content-Disposition')
  console.log('Content-Disposition header:', disposition);

  let filename = `Attendance_Export_${new Date().toISOString().slice(0,10)}.xlsx`
  
  if (disposition && (disposition.includes('filename=') || disposition.includes('filename*='))) {
    const match = disposition.match(/filename="([^"]+)"/)
    if (match) {
      filename = match[1]
    } else {
      const simpleMatch = disposition.match(/filename=([^;]+)/)
      if (simpleMatch) filename = simpleMatch[1].trim()
    }
  }

  // Final check: ensure filename has .xlsx extension
  if (!filename.toLowerCase().endsWith('.xlsx')) {
    console.warn('Filename missing .xlsx extension, adding it now:', filename);
    filename += '.xlsx';
  }

  console.log('Final download filename:', filename);

  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  
  // Cleanup
  setTimeout(() => {
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }, 200)
}
