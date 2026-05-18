import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Wallet, ArrowLeftRight, CreditCard, RefreshCw, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { dashboardAPI, exchangeAPI } from '@/api/client'
import { useWalletStore, useExchangeStore } from '@/store/walletStore'
import { useAuthStore } from '@/store/authStore'
import { formatINR, formatUSDT, formatRelativeTime, getStatusColor } from '@/utils/format'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const StatCard = ({ title, value, sub, icon: Icon, color = 'primary', trend }) => (
  <div className="glass-card p-5">
    <div className="flex items-start justify-between mb-3">
      <div className={`w-10 h-10 rounded-xl bg-${color}-500/20 border border-${color}-500/30 flex items-center justify-center`}>
        <Icon className={`w-5 h-5 text-${color}-400`} />
      </div>
      {trend !== undefined && (
        <span className={`badge ${trend >= 0 ? 'badge-success' : 'badge-danger'} text-xs`}>
          {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {Math.abs(trend)}%
        </span>
      )}
    </div>
    <p className="text-white/40 text-xs mb-1">{title}</p>
    <p className="text-xl font-black text-white">{value}</p>
    {sub && <p className="text-white/30 text-xs mt-1">{sub}</p>}
  </div>
)

export default function Dashboard() {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const { wallet, setWallet } = useWalletStore()
  const { currentRate, setRate } = useExchangeStore()
  const { user } = useAuthStore()

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ovRes, rateRes] = await Promise.all([
          dashboardAPI.getOverview(),
          exchangeAPI.getCurrentRate(),
        ])
        setOverview(ovRes.data.data)
        setWallet(ovRes.data.data.wallet)
        setRate(rateRes.data.data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="glass-card p-5 h-32 shimmer" />)}
        </div>
      </div>
    )
  }

  const w = overview?.wallet
  const stats = overview?.stats_30d
  const rate = overview?.exchange

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Dashboard</h1>
          <p className="text-white/40 text-sm mt-0.5">Good {new Date().getHours() < 12 ? 'morning' : 'evening'}, {user?.first_name}</p>
        </div>
        <button onClick={() => window.location.reload()} className="btn-secondary py-2 px-3 flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Wallet Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Portfolio */}
        <div className="lg:col-span-1 glass-card p-6 border border-primary-500/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-40 h-40 rounded-full bg-primary-500/10 blur-[40px] pointer-events-none" />
          <p className="text-white/40 text-xs mb-1">Portfolio Value</p>
          <p className="text-3xl font-black text-white mb-1">{formatINR(w?.portfolio_value_inr)}</p>
          <p className="text-white/30 text-xs">Combined INR + USDT equivalent</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="glass-card p-3 border border-white/5">
              <p className="text-white/40 text-xs">INR</p>
              <p className="font-bold text-white text-sm">{formatINR(w?.inr_balance)}</p>
            </div>
            <div className="glass-card p-3 border border-white/5">
              <p className="text-white/40 text-xs">USDT</p>
              <p className="font-bold text-white text-sm">{parseFloat(w?.usdt_balance || 0).toFixed(4)}</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-4">
          <StatCard title="Total Spent (30d)" value={formatINR(stats?.total_spent_inr)} icon={CreditCard} color="rose" />
          <StatCard title="Payments (30d)" value={stats?.payment_count || 0} sub="transactions" icon={TrendingUp} color="emerald" />
          <StatCard title="Conversions (30d)" value={stats?.conversion_count || 0} sub="exchanges" icon={ArrowLeftRight} color="blue" />
        </div>
      </div>

      {/* Exchange Rate */}
      {rate?.usdt_inr_rate && (
        <div className="glass-card p-5 border border-emerald-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-white/40 text-xs mb-1">Live USDT / INR Rate</p>
            <div className="flex items-baseline gap-3">
              <p className="text-2xl font-black text-white">₹{parseFloat(rate.usdt_inr_rate).toFixed(2)}</p>
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                LIVE via CoinGecko
              </span>
            </div>
          </div>
          <div className="flex gap-6 text-sm">
            <div>
              <p className="text-white/40 text-xs">Buy Rate</p>
              <p className="text-white font-medium">₹{parseFloat(rate.buy_rate).toFixed(2)}</p>
            </div>
            <div>
              <p className="text-white/40 text-xs">Sell Rate</p>
              <p className="text-white font-medium">₹{parseFloat(rate.sell_rate).toFixed(2)}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link to="/convert" className="btn-primary py-2 px-4 text-sm flex items-center gap-1">
              Convert <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
            <Link to="/pay" className="btn-secondary py-2 px-4 text-sm">Pay</Link>
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white">Recent Transactions</h2>
          <Link to="/wallet" className="text-primary-400 text-sm hover:text-primary-300 flex items-center gap-1">
            View all <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="space-y-3">
          {overview?.recent_transactions?.length === 0 && (
            <p className="text-white/30 text-sm text-center py-8">No transactions yet. Make a deposit to get started.</p>
          )}
          {overview?.recent_transactions?.map((tx) => (
            <div key={tx.id} className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm ${tx.transaction_type === 'CREDIT' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                  {tx.transaction_type === 'CREDIT' ? '↓' : '↑'}
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{tx.category}</p>
                  <p className="text-xs text-white/30">{formatRelativeTime(tx.created_at)}</p>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-bold text-sm ${tx.transaction_type === 'CREDIT' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {tx.transaction_type === 'CREDIT' ? '+' : '-'}{parseFloat(tx.amount).toFixed(tx.currency === 'INR' ? 2 : 4)} {tx.currency}
                </p>
                <span className={`badge text-xs ${getStatusColor(tx.status)}`}>{tx.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { to: '/wallet', icon: Wallet, label: 'Deposit', color: 'primary' },
          { to: '/convert', icon: ArrowLeftRight, label: 'Convert', color: 'blue' },
          { to: '/pay', icon: CreditCard, label: 'Pay', color: 'emerald' },
          { to: '/analytics', icon: TrendingUp, label: 'Analytics', color: 'accent' },
        ].map(({ to, icon: Icon, label, color }) => (
          <Link key={to} to={to} className="glass-card-hover p-4 flex flex-col items-center gap-2 text-center">
            <div className={`w-10 h-10 rounded-xl bg-${color}-500/20 flex items-center justify-center`}>
              <Icon className={`w-5 h-5 text-${color}-400`} />
            </div>
            <span className="text-sm font-medium text-white/70">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
