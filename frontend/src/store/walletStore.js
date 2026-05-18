import { create } from 'zustand'

export const useWalletStore = create((set, get) => ({
  wallet: null,
  transactions: [],
  isLoading: false,

  setWallet: (wallet) => set({ wallet }),
  setTransactions: (transactions) => set({ transactions }),

  updateBalances: (inr_balance, usdt_balance) =>
    set((state) => ({
      wallet: state.wallet
        ? { ...state.wallet, inr_balance, usdt_balance }
        : null,
    })),

  setLoading: (isLoading) => set({ isLoading }),
}))

export const useExchangeStore = create((set) => ({
  currentRate: null,
  rateHistory: [],
  lastUpdated: null,
  isLive: false,

  setRate: (rate) => set({ currentRate: rate, lastUpdated: new Date() }),
  setRateHistory: (history) => set({ rateHistory: history }),
  setLive: (isLive) => set({ isLive }),
}))

export const useNotificationStore = create((set, get) => ({
  notifications: [],

  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        { id: Date.now(), ...notification, read: false },
        ...state.notifications,
      ].slice(0, 50), // Keep max 50
    })),

  markRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
    })),

  clearAll: () => set({ notifications: [] }),

  unreadCount: () => get().notifications.filter((n) => !n.read).length,
}))
