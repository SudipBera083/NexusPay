import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useWebSocket } from '@/hooks/useWebSocket'

// Pages
import Landing from '@/pages/Landing'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Dashboard from '@/pages/Dashboard'
import Wallet from '@/pages/Wallet'
import Conversion from '@/pages/Conversion'
import Payment from '@/pages/Payment'
import Analytics from '@/pages/Analytics'
import AdminPanel from '@/pages/AdminPanel'
import Layout from '@/components/Layout'

// Web3 Pages
import MerchantDashboard from '@/pages/web3/MerchantDashboard'
import QRGenerator from '@/pages/web3/QRGenerator'
import QRScanner from '@/pages/web3/QRScanner'
import PaymentConfirm from '@/pages/web3/PaymentConfirm'
import BlockchainExplorer from '@/pages/web3/BlockchainExplorer'
import TransactionDetail from '@/pages/web3/TransactionDetail'

function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (adminOnly && user?.role !== 'ADMIN' && user?.role !== 'SUPERADMIN') {
    return <Navigate to="/dashboard" replace />
  }
  return children
}

function PublicRoute({ children }) {
  const { isAuthenticated } = useAuthStore()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return children
}

function AppContent() {
  useWebSocket()
  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

        {/* Protected — inside sidebar layout */}
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/wallet" element={<Wallet />} />
          <Route path="/convert" element={<Conversion />} />
          <Route path="/pay" element={<Payment />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminPanel />
              </ProtectedRoute>
            }
          />
          
          {/* Web3 / Merchant Routes */}
          <Route path="/merchant" element={<MerchantDashboard />} />
          <Route path="/merchant/qr-generate" element={<QRGenerator />} />
          <Route path="/pay/scan" element={<QRScanner />} />
          <Route path="/pay/confirm/:nonce" element={<PaymentConfirm />} />
          <Route path="/explorer" element={<BlockchainExplorer />} />
          <Route path="/explorer/tx/:hash" element={<TransactionDetail />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
