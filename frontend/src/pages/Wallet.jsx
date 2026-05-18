import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Wallet as WalletIcon, Plus, Minus, ArrowDown, ArrowUp, Filter, Search } from 'lucide-react'
import { walletAPI } from '@/api/client'
import { useWalletStore } from '@/store/walletStore'
import { formatINR, formatRelativeTime, getStatusColor } from '@/utils/format'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

export default function Wallet() {
  const { wallet, setWallet, transactions, setTransactions } = useWalletStore()
  const [loading, setLoading] = useState(true)
  const [showDeposit, setShowDeposit] = useState(false)
  const [depositCurrency, setDepositCurrency] = useState('INR')
  const [depositAmount, setDepositAmount] = useState('')
  const [depositing, setDepositing] = useState(false)
  
  const [showWithdraw, setShowWithdraw] = useState(false)
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [withdrawing, setWithdrawing] = useState(false)

  const [filter, setFilter] = useState({ currency: '', category: '' })
  const [page, setPage] = useState(1)
  const [meta, setMeta] = useState(null)
  const navigate = useNavigate()

  useEffect(() => { fetchData() }, [filter])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [wRes, txRes] = await Promise.all([
        walletAPI.getWallet(),
        walletAPI.getTransactions({ ...filter, page }),
      ])
      setWallet(wRes.data.data)
      setTransactions(txRes.data.data)
      setMeta(txRes.data.meta?.pagination)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleDeposit = async () => {
    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      toast.error('Enter a valid amount')
      return
    }
    setDepositing(true)
    try {
      await walletAPI.deposit({ currency: depositCurrency, amount: depositAmount })
      toast.success(`Deposited ${depositAmount} ${depositCurrency}`)
      setShowDeposit(false)
      setDepositAmount('')
      fetchData()
    } catch (e) {
      toast.error(e.response?.data?.message || 'Deposit failed')
    } finally {
      setDepositing(false)
    }
  }

  const handleWithdrawClick = () => {
    if (!wallet?.web3_address) {
      toast.error("Please link your Web3 wallet in the Dashboard first.")
      navigate("/dashboard")
      return
    }
    setShowWithdraw(true)
  }

  const handleWithdraw = async () => {
    if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) {
      toast.error('Enter a valid amount')
      return
    }
    setWithdrawing(true)
    try {
      await walletAPI.withdraw({ currency: 'USDT', amount: withdrawAmount })
      toast.success(`Withdrawal of ${withdrawAmount} USDT initiated`)
      setShowWithdraw(false)
      setWithdrawAmount('')
      fetchData()
    } catch (e) {
      toast.error(e.response?.data?.message || 'Withdrawal failed')
    } finally {
      setWithdrawing(false)
    }
  }

  const inrBalance = parseFloat(wallet?.inr_balance || 0)
  const usdtBalance = parseFloat(wallet?.usdt_balance || 0)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black text-white">Wallet</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowDeposit(true)} className="btn-primary flex items-center gap-2 py-2 px-4 text-sm">
            <Plus className="w-4 h-4" /> Deposit
          </button>
          <button onClick={handleWithdrawClick} className="btn-secondary flex items-center gap-2 py-2 px-4 text-sm">
            <Minus className="w-4 h-4" /> Withdraw
          </button>
        </div>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {/* INR */}
        <div className="glass-card p-6 border border-primary-500/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-primary-500/10 blur-[40px]" />
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-primary-500/20 border border-primary-500/30 flex items-center justify-center">
              <span className="text-primary-400 font-black text-sm">₹</span>
            </div>
            <span className="badge badge-primary">INR</span>
          </div>
          <p className="text-white/40 text-xs mb-1">Indian Rupee Balance</p>
          <p className="text-3xl font-black text-white">{formatINR(inrBalance)}</p>
          {wallet?.is_locked && <p className="text-red-400 text-xs mt-2">⚠ Wallet locked</p>}
        </div>
        {/* USDT */}
        <div className="glass-card p-6 border border-emerald-500/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-emerald-500/10 blur-[40px]" />
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
              <span className="text-emerald-400 font-black text-xs">USDT</span>
            </div>
            <span className="badge badge-success">USDT</span>
          </div>
          <p className="text-white/40 text-xs mb-1">Tether USD Balance</p>
          <p className="text-3xl font-black text-white">{usdtBalance.toFixed(4)}</p>
          <p className="text-white/30 text-xs mt-1">Tether USD</p>
        </div>
      </div>

      {/* Deposit Modal */}
      {showDeposit && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setShowDeposit(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-card p-8 w-full max-w-sm border border-primary-500/20"
          >
            <h2 className="text-xl font-black text-white mb-6">Simulate Deposit</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-white/60 mb-2 block">Currency</label>
                <div className="grid grid-cols-2 gap-3">
                  {['INR', 'USDT'].map((c) => (
                    <button
                      key={c}
                      onClick={() => setDepositCurrency(c)}
                      className={`py-2.5 rounded-xl font-bold text-sm transition-all ${depositCurrency === c ? 'bg-primary-500 text-white' : 'bg-white/5 text-white/50 hover:bg-white/10'}`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm text-white/60 mb-2 block">Amount</label>
                <input
                  type="number"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  placeholder={depositCurrency === 'INR' ? '10000' : '100'}
                  className="input-field"
                  id="deposit-amount"
                />
              </div>
              <button onClick={handleDeposit} disabled={depositing} className="btn-primary w-full py-3 flex items-center justify-center gap-2">
                {depositing ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><ArrowDown className="w-4 h-4" />Deposit {depositCurrency}</>}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdraw && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setShowWithdraw(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-card p-8 w-full max-w-sm border border-emerald-500/20"
          >
            <h2 className="text-xl font-black text-white mb-6">Withdraw USDT</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-white/60 mb-2 block">Destination Address</label>
                <div className="glass-card p-3 border border-white/10 text-xs font-mono text-emerald-400 break-all">
                  {wallet?.web3_address}
                </div>
              </div>
              <div>
                <label className="text-sm text-white/60 mb-2 block">Amount (USDT)</label>
                <input
                  type="number"
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                  placeholder="50.00"
                  className="input-field"
                  id="withdraw-amount"
                />
              </div>
              <button onClick={handleWithdraw} disabled={withdrawing} className="btn-primary w-full py-3 flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 border-emerald-500">
                {withdrawing ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><ArrowUp className="w-4 h-4" />Withdraw USDT</>}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Transaction List */}
      <div className="glass-card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
          <h2 className="font-bold text-white">Transaction History</h2>
          <div className="flex gap-3">
            <select
              value={filter.currency}
              onChange={(e) => setFilter(f => ({ ...f, currency: e.target.value }))}
              className="input-field py-1.5 text-xs w-28"
            >
              <option value="">All Currencies</option>
              <option value="INR">INR</option>
              <option value="USDT">USDT</option>
            </select>
            <select
              value={filter.category}
              onChange={(e) => setFilter(f => ({ ...f, category: e.target.value }))}
              className="input-field py-1.5 text-xs w-32"
            >
              <option value="">All Types</option>
              <option value="DEPOSIT">Deposit</option>
              <option value="WITHDRAWAL">Withdrawal</option>
              <option value="CONVERSION">Conversion</option>
              <option value="PAYMENT">Payment</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="h-14 rounded-xl shimmer" />)}</div>
        ) : transactions?.length === 0 ? (
          <div className="text-center py-12 text-white/30">
            <WalletIcon className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p>No transactions yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {transactions?.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between py-3.5 px-4 rounded-xl hover:bg-white/3 transition-colors border border-transparent hover:border-white/5">
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold ${tx.transaction_type === 'CREDIT' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                    {tx.transaction_type === 'CREDIT' ? <ArrowDown className="w-4 h-4" /> : <ArrowUp className="w-4 h-4" />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{tx.category}</p>
                    <p className="text-xs text-white/30">{tx.description || tx.reference_id?.slice(0, 16) || '-'} · {formatRelativeTime(tx.created_at)}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-bold text-sm ${tx.transaction_type === 'CREDIT' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {tx.transaction_type === 'CREDIT' ? '+' : '-'}{parseFloat(tx.amount).toFixed(tx.currency === 'INR' ? 2 : 6)} {tx.currency}
                  </p>
                  <span className={`badge text-xs ${getStatusColor(tx.status)}`}>{tx.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {meta && meta.total_pages > 1 && (
          <div className="flex justify-center gap-2 mt-6">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={!meta.previous} className="btn-secondary py-1.5 px-3 text-sm">← Prev</button>
            <span className="text-white/40 text-sm py-1.5 px-3">{meta.current_page} / {meta.total_pages}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={!meta.next} className="btn-secondary py-1.5 px-3 text-sm">Next →</button>
          </div>
        )}
      </div>
    </div>
  )
}
