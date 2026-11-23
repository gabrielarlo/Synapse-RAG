import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || ''

const client = axios.create({ baseURL })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token && config.url && config.url.startsWith('/api')) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401 try one refresh, then force re-login.
client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 403 &&
        error.response?.data?.detail === 'account deactivated') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (window.location.pathname !== '/login') window.location.href = '/login'
      return Promise.reject(error)
    }
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${baseURL}/api/auth/refresh`, {
            refresh_token: refreshToken
          })
          localStorage.setItem('access_token', data.access_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return client(original)
        } catch {
          // fall through to logout
        }
      }
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

function tokenPayload() {
  try {
    const t = localStorage.getItem('access_token')
    if (!t) return {}
    return JSON.parse(atob(t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return {}
  }
}

export function currentRole() {
  return tokenPayload().role || ''
}

export function currentUsername() {
  return tokenPayload().sub || ''
}

// Surface the real error: API returns JSON {detail}, but nginx/proxy HTML
// errors (413, 502...) have no detail — show status instead of a vague fallback.
// Generic "Not Found" (FastAPI default for unknown route) is not actionable, so
// map it to the caller-provided fallback with status to preserve context.
export function errorDetail(e, fallback = 'Request failed.') {
  const isGenericNotFound = (s) => typeof s === 'string' && s.trim().toLowerCase() === 'not found'
  const d = e?.response?.data
  if (typeof d?.detail === 'string' && d.detail) {
    const t = d.detail.trim()
    if (isGenericNotFound(t)) {
      const s = e?.response?.status
      return s ? `${fallback} (HTTP ${s})` : fallback
    }
    return t
  }
  if (typeof d === 'string' && d.trim() && !d.trim().startsWith('<')) {
    const t = d.trim()
    if (isGenericNotFound(t)) {
      const s = e?.response?.status
      return s ? `${fallback} (HTTP ${s})` : fallback
    }
    return t
  }
  const s = e?.response?.status
  if (s === 413) return 'File too large.'
  if (s) return `${fallback} (HTTP ${s})`
  if (!e?.response) return `${fallback} (network error — is the API up?)`
  return fallback
}

export const api = {
  login: (username, password) =>
    client.post('/api/auth/login', { username, password }),
  refresh: (refresh_token) =>
    client.post('/api/auth/refresh', { refresh_token }),
  listAccounts: () => client.get('/api/accounts'),
  createAccount: (name) => client.post('/api/accounts', { name }),
  archiveAccount: (id) => client.post(`/api/accounts/${id}/archive`),
  unarchiveAccount: (id) => client.post(`/api/accounts/${id}/unarchive`),
  getAccount: (id) => client.get(`/api/accounts/${id}`),
  assignStaff: (accountId, user_id) =>
    client.post(`/api/accounts/${accountId}/staff`, { user_id }),
  unassignStaff: (accountId, userId) =>
    client.delete(`/api/accounts/${accountId}/staff/${userId}`),
  listUsers: () => client.get('/api/auth/users'),
  createUser: (username, password, role) =>
    client.post('/api/auth/users', { username, password, role }),
  deactivateUser: (userId) =>
    client.post(`/api/auth/users/${userId}/deactivate`),
  listDocuments: (params) => client.get('/api/documents', { params }),
  getDocument: (id) => client.get(`/api/documents/${id}`),
  replaceDocument: (id, file, filename) => {
    const form = new FormData()
    form.append('file', file)
    return client.put(`/api/documents/${id}`, form, {
      params: filename ? { filename } : {},
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  deleteDocument: (id) => client.delete(`/api/documents/${id}`),
  transferDocument: (id, target_account_id) => client.post(`/api/documents/${id}/transfer`, { target_account_id }),
  uploadDocument: (file, params) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/api/documents', form, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  chat: (payload) => client.post('/api/chat', payload),
  listSessions: (params) => client.get('/api/chat/sessions', { params }),
  getSessionHistory: (id) => client.get(`/api/chat/sessions/${id}/history`),
  deleteSession: (id) => client.delete(`/api/chat/sessions/${id}`),
  listAudit: (params) => client.get('/api/audit', { params }),
  listCredentials: (accountId) => client.get(`/api/accounts/${accountId}/credentials`),
  issueCredential: (accountId, payload = {}) => client.post(`/api/accounts/${accountId}/credentials`, payload || {}),
  rotateCredential: (keyId) => client.post(`/api/credentials/${keyId}/rotate`),
  revokeCredential: (keyId) => client.post(`/api/credentials/${keyId}/revoke`),
  deleteCredential: (keyId) => client.delete(`/api/credentials/${keyId}`)
}

export default client
