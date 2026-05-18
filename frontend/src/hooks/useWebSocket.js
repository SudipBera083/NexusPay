import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useWalletStore, useExchangeStore, useNotificationStore } from '@/store/walletStore'
import toast from 'react-hot-toast'

const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`

export function useWebSocket() {
  const walletWs = useRef(null)
  const ratesWs = useRef(null)
  const reconnectTimer = useRef(null)
  const { accessToken, isAuthenticated } = useAuthStore()
  const { updateBalances } = useWalletStore()
  const { setRate, setLive } = useExchangeStore()
  const { addNotification } = useNotificationStore()

  const connectWallet = useCallback(() => {
    if (!isAuthenticated || !accessToken) return
    if (walletWs.current?.readyState === WebSocket.OPEN) return

    const url = `${WS_BASE}/ws/wallet/?token=${accessToken}`
    walletWs.current = new WebSocket(url)

    walletWs.current.onopen = () => {
      console.log('[WS] Wallet connected')
    }

    walletWs.current.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        switch (msg.type) {
          case 'wallet_balance':
          case 'wallet_update':
            updateBalances(msg.data.inr_balance, msg.data.usdt_balance)
            break
          case 'transaction_notification':
            addNotification({
              type: msg.data.event_type,
              message: `${msg.data.event_type}: ${msg.data.from || msg.data.merchant || ''}`,
              ...msg.data,
            })
            toast.success(`New ${msg.data.event_type} transaction`, { duration: 3000 })
            break
          case 'rate_update':
            setRate(msg.data)
            break
        }
      } catch {}
    }

    walletWs.current.onclose = () => {
      setLive(false)
      reconnectTimer.current = setTimeout(connectWallet, 3000)
    }

    walletWs.current.onerror = () => {
      walletWs.current?.close()
    }
  }, [accessToken, isAuthenticated])

  const connectRates = useCallback(() => {
    if (ratesWs.current?.readyState === WebSocket.OPEN) return
    const url = `${WS_BASE}/ws/rates/`
    ratesWs.current = new WebSocket(url)

    ratesWs.current.onopen = () => setLive(true)
    ratesWs.current.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'rate_update') setRate(msg.data)
      } catch {}
    }
    ratesWs.current.onclose = () => {
      setLive(false)
      setTimeout(connectRates, 5000)
    }
  }, [])

  useEffect(() => {
    connectWallet()
    connectRates()
    return () => {
      clearTimeout(reconnectTimer.current)
      walletWs.current?.close()
      ratesWs.current?.close()
    }
  }, [connectWallet, connectRates])

  return { isConnected: walletWs.current?.readyState === WebSocket.OPEN }
}
