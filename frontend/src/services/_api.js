const DEFAULT_LOCAL_API_BASE = 'http://127.0.0.1:8001'
const DEFAULT_CLOUD_API_BASE = 'https://astra-guard-backend.onrender.com'
const BROWSER_FRAME_REQUEST_TIMEOUT_MS = 15000

function resolveApiBase() {
  const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim()

  if (configuredBase) {
    return configuredBase.replace(/\/+$/, '')
  }

  try {
    if (typeof window !== 'undefined' && window.location) {
      const host = window.location.hostname
      const isLocalHost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(host)
      if (isLocalHost) {
        return DEFAULT_LOCAL_API_BASE
      }
    }
  } catch {
    // Ignore browser access errors.
  }

  return DEFAULT_CLOUD_API_BASE
}

const API_BASE = resolveApiBase()

export const CAMERA_STREAM_URL = `${API_BASE}/api/camera/stream`
export const CAMERA_SNAPSHOT_URL = `${API_BASE}/api/camera/snapshot`
export const CAMERA_STATUS_URL = `${API_BASE}/api/camera/status`

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  if (!res.ok) {
    const response = await res.json().catch(() => ({}))
    const detail = response?.detail
    throw new Error(typeof detail === 'string' ? detail : `POST ${path} -> ${res.status}`)
  }
  return res.json()
}

async function uploadVideo(experimentId, file) {
  const query = new URLSearchParams({ experiment_id: experimentId, filename: file.name })
  const res = await fetch(`${API_BASE}/api/sessions/video/start?${query}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/octet-stream' },
    body: file,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Video upload failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  base: API_BASE,
  health: () => get('/api/health'),
  performance: () => get('/api/performance'),
  perceptionStatus: () => get('/api/perception/status'),
  reportDashboardDisplay: (displayedFps, displayedAt) =>
    post('/api/performance/display', { displayed_fps: displayedFps, displayed_at: displayedAt }),
  mission: () => get('/api/mission'),
  missionStatus: () => get('/api/mission/status'),
  missionProgress: () => get('/api/mission/progress'),
  missionSummary: () => get('/api/mission/summary'),
  missionProtocol: () => get('/api/mission/protocol'),
  resetMission: () => post('/api/mission/reset', {}),
  cameraStatus: () => get('/api/camera/status'),
  selectCamera: (cameraIndex, source, backend = 'dshow', sourceName) =>
    post('/api/camera/select', {
      camera_index: cameraIndex,
      source,
      backend,
      source_name: sourceName,
    }),
  discoverCameras: (maxIndex = 5) =>
    get(`/api/camera/discover?max_index=${maxIndex}&backends=dshow&backends=msmf`),
  processBrowserFrame: async (frame) => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), BROWSER_FRAME_REQUEST_TIMEOUT_MS)
    try {
      const res = await fetch(`${API_BASE}/api/camera/browser-frame`, {
        method: 'POST',
        headers: { 'Content-Type': 'image/jpeg' },
        body: frame,
        signal: controller.signal,
      })
      if (!res.ok) {
        const response = await res.json().catch(() => ({}))
        throw new Error(response?.detail ?? `POST /api/camera/browser-frame -> ${res.status}`)
      }
      return await res.json()
    } catch (error) {
      if (error?.name === 'AbortError') {
        throw new Error('Browser frame upload timed out. Check the backend connection and try again.')
      }
      throw error
    } finally {
      clearTimeout(timeout)
    }
  },
  startCamera: () => post('/api/camera/start', {}),
  stopCamera: () => post('/api/camera/stop', {}),
  events: (limit) =>
    get(typeof limit === 'number' ? `/api/events?limit=${limit}` : '/api/events'),
  status: () => get('/api/status'),
  voiceStatus: () => get('/api/voice/status'),
  setVoiceLanguage: (language) => post('/api/voice/language', { language }),
  setVoiceEnabled: (enabled) => post('/api/voice/enabled', { enabled }),
  experiments: () => get('/api/experiments'),
  selectExperiment: (experimentId) => post(`/api/experiments/${encodeURIComponent(experimentId)}/select`, {}),
  startSession: (experimentId, inputSource = 'webcam') =>
    post('/api/sessions/start', { experiment_id: experimentId, input_source: inputSource }),
  uploadVideo,
  sessions: () => get('/api/sessions'),
  session: (sessionId) => get(`/api/sessions/${encodeURIComponent(sessionId)}`),
  endSession: (sessionId, status = 'CANCELLED') =>
    post(`/api/sessions/${encodeURIComponent(sessionId)}/end`, { status }),
  confirmSessionStep: (sessionId, operator) =>
    post(`/api/sessions/${encodeURIComponent(sessionId)}/confirm`, { operator }),
  sessionAction: (sessionId, action, operator = 'not_provided') =>
    post(`/api/sessions/${encodeURIComponent(sessionId)}/actions`, { action, operator }),
  sessionExportUrl: (sessionId, format = 'json') =>
    `${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}/export?format=${encodeURIComponent(format)}`,
  sessionVideoUrl: (sessionId) => `${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}/video`,
  sessionEvidenceUrl: (sessionId, evidencePath) =>
    `${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}/evidence/${encodeURIComponent(evidencePath.split(/[\\/]/).pop())}`,
  protocolSummary: () => get('/api/protocol/summary'),
  protocolSteps: () => get('/api/protocol/steps'),
  protocolStep: (stepId) => get(`/api/protocol/steps/${encodeURIComponent(stepId)}`),
  protocolActivities: () => get('/api/protocol/activities'),
  protocolObjects: () => get('/api/protocol/objects'),
  protocolRules: () => get('/api/protocol/rules'),
  protocolValidate: () => get('/api/protocol/validate'),
  protocolReload: () => post('/api/protocol/reload', {}),
}

export function formatConfidence(value) {
  if (value === null || value === undefined || value === '') return 'N/A'
  const num = Number(value)
  if (Number.isNaN(num)) return String(value)
  if (num >= 0 && num <= 1) return `${(num * 100).toFixed(1)}%`
  return `${num.toFixed(1)}%`
}

export function display(value) {
  if (value === null || value === undefined || value === '') return 'N/A'
  return String(value)
}

export function prettyId(value) {
  if (value === null || value === undefined || value === '') return 'N/A'
  return String(value).split('_').map((w) => w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w).join(' ')
}

export function stepNumber(stepId) {
  const m = /^S(\d+)$/.exec(String(stepId ?? '').trim().toUpperCase())
  if (!m) return null
  return parseInt(m[1], 10)
}

export function statusColor(status) {
  switch (String(status ?? '').toUpperCase()) {
    case 'CORRECT':
      return 'var(--success)'
    case 'COMPLETED':
      return 'var(--success)'
    case 'DEVIATION':
      return 'var(--danger)'
    case 'UNCERTAIN':
      return 'var(--warning)'
    case 'RECOVERED':
      return 'var(--primary)'
    default:
      return 'var(--muted)'
  }
}
