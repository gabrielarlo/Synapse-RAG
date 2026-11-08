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

export const api = {
  login: (username, password) =>
    client.post('/api/auth/login', { username, password }),
  refresh: (refresh_token) =>
    client.post('/api/auth/refresh', { refresh_token }),
  listAccounts: () => client.get('/api/accounts'),
  createAccount: (name) => client.post('/api/accounts', { name }),
  getAccount: (id) => client.get(`/api/accounts/${id}`),
  assignStaff: (accountId, user_id) =>
    client.post(`/api/accounts/${accountId}/staff`, { user_id }),
  unassignStaff: (accountId, userId) =>
    client.delete(`/api/accounts/${accountId}/staff/${userId}`),
  listUsers: () => client.get('/api/users'),
  createUser: (username, password, role) =>
    client.post('/api/users', { username, password, role }),
  listDocuments: (params) => client.get('/api/documents', { params }),
  uploadDocument: (file, params) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/api/documents', form, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  chat: (payload) => client.post('/api/chat', payload),
  listAudit: (params) => client.get('/api/audit', { params })
}

export default client
