import React, { useEffect, useState } from 'react'
import { dashboardAPI } from '@/api/client'
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { formatINR, formatDate } from '@/utils/format'
import { TrendingUp, BarChart3, PieChart as PieIcon } from 'lucide-react'

const COLORS = ['#6366f1', '#d946ef', '#10b981', '#f59e0b', '#3b82f6', '#ef4444']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card p-3 border border-white/10 text-xs">
      <p className="text-white/60 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-bold">{p.name}: {typeof p.value === 'number' ? formatINR(p.value) : p.value}</p>
      ))}
    </div>
  )
}

export default function Analytics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  useEffect(() => {
    dashboardAPI.getAnalytics(days).then(r => { setData(r.data.data); setLoading(false) }).catch(() => setLoading(false))
  }, [days])

  if (loading) return (
    <div className="space-y-6">
      {[...Array(3)].map((_, i) => <div key={i} className="glass-card h-64 shimmer" />)}
    </div>
  )

  const dailySpending = data?.daily_spending?.map(d => ({
    date: formatDate(d.day),
    Spending: parseFloat(d.total || 0),
    Count: d.count,
  })) || []

  const categories = data?.category_breakdown || []

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Analytics</h1>
          <p className="text-white/40 text-sm mt-0.5">Spending insights and transaction analytics</p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <button key={d} onClick={() => setDays(d)} className={`py-1.5 px-3 rounded-xl text-sm font-medium transition-all ${days === d ? 'bg-primary-500 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'}`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Daily Spending Chart */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-2 mb-5">
          <BarChart3 className="w-4 h-4 text-primary-400" />
          <h2 className="font-bold text-white">Daily Spending (₹)</h2>
        </div>
        {dailySpending.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-white/30 text-sm">No spending data for this period</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dailySpending}>
              <defs>
                <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="Spending" stroke="#6366f1" strokeWidth={2} fill="url(#spendGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-5">
            <PieIcon className="w-4 h-4 text-accent-400" />
            <h2 className="font-bold text-white">Spending by Category</h2>
          </div>
          {categories.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-white/30 text-sm">No category data</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={categories} dataKey="total" nameKey="merchant_category" cx="50%" cy="50%" outerRadius={80} innerRadius={50}>
                  {categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => formatINR(v)} />
                <Legend formatter={(v) => <span className="text-white/60 text-xs">{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-5">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h2 className="font-bold text-white">Top Categories</h2>
          </div>
          <div className="space-y-3">
            {categories.length === 0 ? (
              <p className="text-white/30 text-sm text-center py-8">No data</p>
            ) : categories.slice(0, 6).map((c, i) => {
              const total = categories.reduce((s, x) => s + parseFloat(x.total), 0)
              const pct = total > 0 ? ((parseFloat(c.total) / total) * 100).toFixed(1) : 0
              return (
                <div key={c.merchant_category}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white/70">{c.merchant_category}</span>
                    <span className="text-white font-medium">{formatINR(c.total)} ({pct}%)</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/5">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
