import axios from 'axios'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// Request interceptor — attach JWT
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor — handle 401 + token refresh
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)))
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = useAuthStore.getState().refreshToken
      if (!refreshToken) {
        useAuthStore.getState().logout()
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        })
        const newAccessToken = data.access
        useAuthStore.getState().setTokens(newAccessToken, refreshToken)
        processQueue(null, newAccessToken)
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return api(originalRequest)
      } catch (err) {
        processQueue(err, null)
        useAuthStore.getState().logout()
        toast.error('Session expired. Please log in again.')
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// ─── API Modules ──────────────────────────────────────────────────────────────

export const authAPI = {
  register: (data) => api.post('/auth/register/', data),
  login: (data) => api.post('/auth/login/', data),
  logout: (refresh) => api.post('/auth/logout/', { refresh }),
  profile: () => api.get('/auth/profile/'),
  updateProfile: (data) => api.patch('/auth/profile/', data),
  changePassword: (data) => api.post('/auth/change-password/', data),
  requestOTP: (email) => api.post('/auth/otp/request/', { email }),
  verifyOTP: (data) => api.post('/auth/otp/verify/', data),
}

export const walletAPI = {
  getWallet: () => api.get('/wallet/'),
  deposit: (data) => api.post('/wallet/deposit/', data),
  initiateUPIDeposit: (data) => api.post('/wallet/deposit/upi/initiate/', data),
  withdraw: (data) => api.post('/wallet/withdraw/', data),
  getTransactions: (params) => api.get('/wallet/transactions/', { params }),
  getTransaction: (id) => api.get(`/wallet/transactions/${id}/`),
  linkWeb3Wallet: (data) => api.post('/wallet/web3/link/', data),
}

export const exchangeAPI = {
  getCurrentRate: () => api.get('/exchange/rate/'),
  getQuote: (data) => api.post('/exchange/quote/', data),
  getRateHistory: () => api.get('/exchange/history/'),
}

export const transactionAPI = {
  convert: (data) => api.post('/transactions/convert/', data, {
    headers: { 'Idempotency-Key': crypto.randomUUID() }
  }),
  getConversions: (params) => api.get('/transactions/conversions/', { params }),
  pay: (data) => api.post('/transactions/pay/', data, {
    headers: { 'Idempotency-Key': crypto.randomUUID() }
  }),
  getPayments: (params) => api.get('/transactions/payments/', { params }),
}

export const dashboardAPI = {
  getOverview: () => api.get('/dashboard/overview/'),
  getAnalytics: (days) => api.get('/dashboard/analytics/', { params: { days } }),
}

export const adminAPI = {
  getStats: () => api.get('/admin-panel/stats/'),
  getUsers: (params) => api.get('/admin-panel/users/', { params }),
  getUserDetail: (id) => api.get(`/admin-panel/users/${id}/`),
  updateUser: (id, data) => api.patch(`/admin-panel/users/${id}/`, data),
  getWallet: (userId) => api.get(`/admin-panel/users/${userId}/wallet/`),
  lockWallet: (userId, data) => api.patch(`/admin-panel/users/${userId}/wallet/`, data),
  getTransactions: (params) => api.get('/admin-panel/transactions/', { params }),
  reverseTransaction: (id) => api.post(`/admin-panel/transactions/${id}/reverse/`),
  getAuditLogs: () => api.get('/admin-panel/audit-logs/'),
  setExchangeRate: (data) => api.post('/admin-panel/exchange-rate/override/', data),
}

export default api
