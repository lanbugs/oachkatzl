import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // Don't redirect on 401 from auth endpoints — let the form handle those errors
    const url: string = err.config?.url ?? ''
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/2fa')
    if (err.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default api
