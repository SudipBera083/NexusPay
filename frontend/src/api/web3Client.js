import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// -- existing apis --

export const merchantAPI = {
  getProfile: () => apiClient.get('/merchants/profile/'),
  register: (data) => apiClient.post('/merchants/register/', data),
  getAnalytics: () => apiClient.get('/merchants/analytics/'),
  getQRCodes: () => apiClient.get('/merchants/qr/'),
  generateQR: (data) => apiClient.post('/merchants/qr/generate/', data),
  getQRStatus: (nonce) => apiClient.get(`/merchants/qr/${nonce}/`),
  scanQR: (nonce) => apiClient.post('/merchants/qr/scan/', { nonce }),
  submitTx: (data) => apiClient.post('/merchants/qr/submit-tx/', data),
};

export const blockchainAPI = {
  getTransactions: () => apiClient.get('/blockchain/transactions/'),
  getTransactionDetail: (hash) => apiClient.get(`/blockchain/transactions/${hash}/`),
  getSettlements: () => apiClient.get('/blockchain/settlements/'),
};

export default apiClient;
