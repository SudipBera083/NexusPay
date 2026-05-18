import React, { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useExchangeStore, useNotificationStore } from '@/store/walletStore'
import { authAPI } from '@/api/client'
import toast from 'react-hot-toast'
import {
  LayoutDashboard, Wallet, ArrowLeftRight, CreditCard,
  BarChart3, ShieldCheck, LogOut, Bell, Menu, X,
  Zap, ChevronDown, User
} from 'lucide-react'
import { formatINR } from '@/utils/format'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/wallet', icon: Wallet, label: 'Wallet' },
  { to: '/convert', icon: ArrowLeftRight, label: 'Convert' },
  { to: '/pay', icon: CreditCard, label: 'Pay' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
]

export default function Layout() {
  const { user, logout, refreshToken, isAdmin } = useAuthStore()
  const { currentRate } = useExchangeStore()
  const unreadCount = useNotificationStore((s) => s.notifications.filter((n) => !n.read).length)
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const handleLogout = async () => {
    try {
      await authAPI.logout(refreshToken)
    } catch {}
    logout()
    toast.success('Logged out successfully')
  }

  return (
    <div className="flex min-h-screen">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed top-0 left-0 h-full z-30 w-64 flex flex-col transition-transform duration-300',
          'border-r border-white/8',
          'bg-dark-800/95 backdrop-blur-xl',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-white/8">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-sm">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-bold text-white text-gradient text-lg leading-none">NexusPay</p>
            <p className="text-white/40 text-xs">Wallet Infrastructure</p>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="w-5 h-5 text-white/40" />
          </button>
        </div>

        {/* Live Rate Ticker */}
        {currentRate && (
          <div className="mx-4 mt-3 px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <p className="text-xs text-emerald-400/70">Live USDT/INR</p>
            <p className="text-sm font-bold text-emerald-400">
              ₹{parseFloat(currentRate.rate).toFixed(2)}
              <span className="ml-2 text-xs font-normal text-emerald-400/60 animate-pulse">● LIVE</span>
            </p>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx('nav-link', isActive && 'active')
              }
              onClick={() => setSidebarOpen(false)}
            >
              <Icon className="w-4.5 h-4.5 flex-shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}

          {isAdmin?.() && (
            <NavLink
              to="/admin"
              className={({ isActive }) => clsx('nav-link', isActive && 'active')}
              onClick={() => setSidebarOpen(false)}
            >
              <ShieldCheck className="w-4.5 h-4.5 flex-shrink-0" />
              <span>Admin Panel</span>
            </NavLink>
          )}
        </nav>

        {/* User */}
        <div className="border-t border-white/8 p-4">
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-sm font-bold flex-shrink-0">
              {user?.first_name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 text-left min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.full_name || user?.email}</p>
              <p className="text-xs text-white/40 capitalize">{user?.role?.toLowerCase()}</p>
            </div>
            <ChevronDown className={clsx('w-4 h-4 text-white/40 transition-transform', profileOpen && 'rotate-180')} />
          </button>

          {profileOpen && (
            <div className="mt-2 space-y-1">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:ml-64">
        {/* Top bar */}
        <header className="sticky top-0 z-10 flex items-center justify-between px-4 lg:px-8 py-4 border-b border-white/8 bg-dark-900/80 backdrop-blur-xl">
          <button
            className="lg:hidden p-2 rounded-xl hover:bg-white/10"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="lg:hidden flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-400" />
            <span className="font-bold text-gradient">NexusPay</span>
          </div>

          <div className="hidden lg:block">
            <h2 className="text-sm text-white/40">
              Welcome back, <span className="text-white font-medium">{user?.first_name}</span>
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Notification bell */}
            <button className="relative p-2 rounded-xl hover:bg-white/10 transition-colors">
              <Bell className="w-5 h-5 text-white/60" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-primary-500 rounded-full text-[10px] font-bold flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Verified badge */}
            {user?.is_verified && (
              <span className="badge badge-success hidden sm:flex">
                <ShieldCheck className="w-3 h-3" />
                Verified
              </span>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
