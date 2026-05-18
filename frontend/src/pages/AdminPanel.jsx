import React, { useEffect, useState } from 'react'
import { adminAPI } from '@/api/client'
import { formatINR, formatDateTime, getStatusColor } from '@/utils/format'
import { ShieldCheck, Users, Activity, BarChart3, AlertTriangle, RefreshCw, Lock, Unlock, RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'

const Tab = ({ label, active, onClick, icon: Icon }) => (
  <button onClick={onClick} className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${active ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30' : 'text-white/50 hover:text-white hover:bg-white/5'}`}>
    <Icon className="w-4 h-4" /> {label}
  </button>
)

export default function AdminPanel() {
  const [tab, setTab] = useState('stats')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [transactions, setTransactions] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [rateOverride, setRateOverride] = useState('')

  useEffect(() => {
    fetchStats()
  }, [])

  useEffect(() => {
    if (tab === 'users') fetchUsers()
    else if (tab === 'transactions') fetchTransactions()
    else if (tab === 'audit') fetchAudit()
  }, [tab])

  const fetchStats = async () => {
    try {
      const r = await adminAPI.getStats()
      setStats(r.data.data)
    } catch (e) { toast.error('Failed to load stats') }
    finally { setLoading(false) }
  }

  const fetchUsers = async () => {
    try {
      const r = await adminAPI.getUsers({ search })
      setUsers(r.data.data)
    } catch {}
  }

  const fetchTransactions = async () => {
    try {
      const r = await adminAPI.getTransactions()
      setTransactions(r.data.data)
    } catch {}
  }

  const fetchAudit = async () => {
    try {
      const r = await adminAPI.getAuditLogs()
      setAuditLogs(r.data.data)
    } catch {}
  }

  const handleReverseTransaction = async (id) => {
    if (!confirm('Reverse this transaction?')) return
    try {
      await adminAPI.reverseTransaction(id)
      toast.success('Transaction reversed')
      fetchTransactions()
    } catch (e) { toast.error(e.response?.data?.message || 'Reversal failed') }
  }

  const handleSetRate = async () => {
    if (!rateOverride) return
    try {
      await adminAPI.setExchangeRate({ rate: rateOverride })
      toast.success(`Rate set to ₹${rateOverride}`)
      setRateOverride('')
      fetchStats()
    } catch (e) { toast.error('Failed to set rate') }
  }

  const toggleUserStatus = async (userId, isActive) => {
    try {
      await adminAPI.updateUser(userId, { is_active: !isActive })
      toast.success(`User ${!isActive ? 'activated' : 'deactivated'}`)
      fetchUsers()
    } catch {}
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center">
          <ShieldCheck className="w-5 h-5 text-red-400" />
        </div>
        <div>
          <h1 className="text-2xl font-black text-white">Admin Panel</h1>
          <p className="text-white/40 text-sm">Platform management and monitoring</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2">
        <Tab label="Statistics" icon={BarChart3} active={tab === 'stats'} onClick={() => setTab('stats')} />
        <Tab label="Users" icon={Users} active={tab === 'users'} onClick={() => setTab('users')} />
        <Tab label="Transactions" icon={Activity} active={tab === 'transactions'} onClick={() => setTab('transactions')} />
        <Tab label="Audit Logs" icon={AlertTriangle} active={tab === 'audit'} onClick={() => setTab('audit')} />
      </div>

      {/* Stats Tab */}
      {tab === 'stats' && stats && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Total Users', value: stats.users.total, sub: `${stats.users.active} active` },
              { label: 'Verified Users', value: stats.users.verified, sub: 'KYC passed' },
              { label: "Today's Revenue", value: formatINR(stats.today.payment_volume_inr), sub: `${stats.today.payment_count} payments` },
              { label: "Fees Collected", value: formatINR(stats.today.conversion_fees_collected), sub: 'from conversions' },
            ].map(({ label, value, sub }) => (
              <div key={label} className="glass-card p-5">
                <p className="text-white/40 text-xs mb-1">{label}</p>
                <p className="text-xl font-black text-white">{value}</p>
                <p className="text-white/30 text-xs mt-1">{sub}</p>
              </div>
            ))}
          </div>

          {/* Fraud Alert */}
          {stats.fraud.suspicious_large_transactions_last_hour > 0 && (
            <div className="glass-card p-4 border border-red-500/30 flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <div>
                <p className="font-bold text-red-400">Fraud Alert</p>
                <p className="text-sm text-white/60">{stats.fraud.suspicious_large_transactions_last_hour} suspicious large transaction(s) in the last hour</p>
              </div>
            </div>
          )}

          {/* System Balances */}
          <div className="glass-card p-5">
            <h3 className="font-bold text-white mb-3">System-Wide Balances</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><p className="text-white/40 text-xs">Total INR in System</p><p className="text-white font-bold">{formatINR(stats.balances.total_inr_in_system)}</p></div>
              <div><p className="text-white/40 text-xs">Total USDT in System</p><p className="text-white font-bold">{parseFloat(stats.balances.total_usdt_in_system).toFixed(4)} USDT</p></div>
            </div>
          </div>

          {/* Rate Override */}
          <div className="glass-card p-5">
            <h3 className="font-bold text-white mb-3">Exchange Rate Control</h3>
            <p className="text-xs text-white/40 mb-3">Current Rate: 1 USDT = {stats.exchange?.current_usdt_inr ? `₹${parseFloat(stats.exchange.current_usdt_inr).toFixed(2)}` : 'N/A'}</p>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/40 font-bold text-sm">₹</span>
                <input value={rateOverride} onChange={(e) => setRateOverride(e.target.value)} type="number" placeholder="Override rate..." className="input-field pl-8" id="rate-override" />
              </div>
              <button onClick={handleSetRate} className="btn-danger py-2 px-4 text-sm">Override</button>
            </div>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {tab === 'users' && (
        <div className="glass-card p-6">
          <div className="flex gap-3 mb-5">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name or email..." className="input-field flex-1" id="user-search" />
            <button onClick={fetchUsers} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"><RefreshCw className="w-4 h-4" />Search</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/40 text-xs border-b border-white/5">
                  <th className="text-left py-3 pr-4">User</th>
                  <th className="text-left py-3 pr-4">Role</th>
                  <th className="text-left py-3 pr-4">Status</th>
                  <th className="text-left py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-white/5 hover:bg-white/2">
                    <td className="py-3 pr-4">
                      <p className="text-white font-medium">{u.full_name}</p>
                      <p className="text-white/40 text-xs">{u.email}</p>
                    </td>
                    <td className="py-3 pr-4"><span className="badge badge-primary">{u.role}</span></td>
                    <td className="py-3 pr-4">
                      <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>{u.is_active ? 'Active' : 'Inactive'}</span>
                      {u.is_verified && <span className="badge badge-info ml-1">Verified</span>}
                    </td>
                    <td className="py-3">
                      <button onClick={() => toggleUserStatus(u.id, u.is_active)} className={`text-xs px-3 py-1 rounded-lg ${u.is_active ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'}`}>
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && <tr><td colSpan={4} className="text-center py-8 text-white/30">No users found</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Transactions Tab */}
      {tab === 'transactions' && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold text-white">All Transactions</h2>
            <button onClick={fetchTransactions} className="btn-secondary py-2 px-3 text-sm flex items-center gap-2"><RefreshCw className="w-4 h-4" />Refresh</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/40 text-xs border-b border-white/5">
                  <th className="text-left py-3 pr-4">Type</th>
                  <th className="text-left py-3 pr-4">Currency</th>
                  <th className="text-left py-3 pr-4">Amount</th>
                  <th className="text-left py-3 pr-4">Status</th>
                  <th className="text-left py-3 pr-4">Date</th>
                  <th className="text-left py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-b border-white/5 hover:bg-white/2">
                    <td className="py-3 pr-4"><span className={`badge ${tx.transaction_type === 'CREDIT' ? 'badge-success' : 'badge-danger'}`}>{tx.transaction_type}</span></td>
                    <td className="py-3 pr-4 text-white">{tx.currency}</td>
                    <td className="py-3 pr-4 font-mono text-white">{parseFloat(tx.amount).toFixed(4)}</td>
                    <td className="py-3 pr-4"><span className={`badge ${getStatusColor(tx.status)}`}>{tx.status}</span></td>
                    <td className="py-3 pr-4 text-white/40 text-xs">{formatDateTime(tx.created_at)}</td>
                    <td className="py-3">
                      {tx.status === 'COMPLETED' && (
                        <button onClick={() => handleReverseTransaction(tx.id)} className="text-xs px-3 py-1 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 flex items-center gap-1">
                          <RotateCcw className="w-3 h-3" /> Reverse
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {transactions.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-white/30">No transactions</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Audit Tab */}
      {tab === 'audit' && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold text-white">Audit Logs</h2>
            <button onClick={fetchAudit} className="btn-secondary py-2 px-3 text-sm flex items-center gap-2"><RefreshCw className="w-4 h-4" />Refresh</button>
          </div>
          <div className="space-y-2">
            {auditLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-3 py-3 px-4 rounded-xl hover:bg-white/3 border border-transparent hover:border-white/5">
                <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Activity className="w-3.5 h-3.5 text-primary-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{log.action}</p>
                  <p className="text-xs text-white/40">{log.resource_type} {log.resource_id?.slice(0, 12)} · by {log.actor_email || 'System'}</p>
                </div>
                <p className="text-xs text-white/30 whitespace-nowrap">{formatDateTime(log.timestamp)}</p>
              </div>
            ))}
            {auditLogs.length === 0 && <p className="text-center py-8 text-white/30">No audit logs</p>}
          </div>
        </div>
      )}
    </div>
  )
}
