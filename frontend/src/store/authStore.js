import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),

      logout: () => {
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
        window.location.href = '/login'
      },

      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),

      updateUser: (userData) => set({ user: { ...get().user, ...userData } }),

      isAdmin: () => {
        const role = get().user?.role
        return role === 'ADMIN' || role === 'SUPERADMIN'
      },
    }),
    {
      name: 'nexuspay-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
