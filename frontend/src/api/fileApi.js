const API_BASE = window.location.origin + '/api'

export async function readFile(filePath) {
  const res = await fetch(`${API_BASE}/file?path=${encodeURIComponent(filePath)}`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to read file')
  }
  return res.json()
}

export async function writeFile(filePath, content) {
  const res = await fetch(`${API_BASE}/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath, content })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to write file')
  }
  return res.json()
}

export async function exportToPdf(content, path) {
  const res = await fetch(`${API_BASE}/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, path })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to export PDF')
  }
  return res.json()
}

export async function exportToHtml(content, path) {
  const res = await fetch(`${API_BASE}/export/html`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, path })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to export HTML')
  }
  return res.json()
}
