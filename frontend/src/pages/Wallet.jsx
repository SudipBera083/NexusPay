import React, { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Wallet as WalletIcon, Plus, Minus, ArrowDown, ArrowUp,
  QrCode, Copy, CheckCircle, ExternalLink, RefreshCw, Smartphone, CreditCard, X
} from 'lucide-react'
import { walletAPI } from '@/api/client'
import { useWalletStore } from '@/store/walletStore'
import { formatINR, formatRelativeTime, getStatusColor } from '@/utils/format'
import toast from 'react-hot-toast'
import { useNavigate, useSearchParams } from 'react-router-dom'
import QRCode from 'qrcode'

export default function Wallet() {
  const { wallet, setWallet, transactions, setTransactions } = useWalletStore()
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ currency: '', category: '' })
  const [meta, setMeta] = useState(null)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // UPI Deposit state
  const [showUPIDeposit, setShowUPIDeposit] = useState(false)
  const [upiAmount, setUpiAmount] = useState('')
  const [upiDescription, setUpiDescription] = useState('')
  const [upiLoading, setUpiLoading] = useState(false)
  const [paymentLink, setPaymentLink] = useState(null)
  const [qrDataUrl, setQrDataUrl] = useState(null)
  const [copied, setCopied] = useState(false)
  const pollRef = useRef(null)

  // Withdraw state
  const [showWithdraw, setShowWithdraw] = useState(false)
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [withdrawing, setWithdrawing] = useState(false)

  useEffect(() => {
    fetchData()
    // If redirected back from Razorpay, show success
    if (searchParams.get('deposit') === 'success') {
      toast.success('Payment received! Your balance will update shortly.')
    }
  }, [filter])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [wRes, txRes] = await Promise.all([
        walletAPI.getWallet(),
        walletAPI.getTransactions({ ...filter }),
      ])
      setWallet(wRes.data.data)
      setTransactions(txRes.data.data)
      setMeta(txRes.data.meta?.pagination)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  // ── UPI Deposit ────────────────────────────────────────────────────────────

  const handleCreatePaymentLink = async () => {
    if (!upiAmount || parseFloat(upiAmount) < 1) {
      toast.error('Enter an amount of at least ₹1')
      return
    }
    setUpiLoading(true)
    try {
      const res = await walletAPI.initiateUPIDeposit({
        amount: upiAmount,
        description: upiDescription || `NexusPay deposit ₹${upiAmount}`,
      })
      const data = res.data.data
      setPaymentLink(data)

      // Generate QR code from the short URL
      const qr = await QRCode.toDataURL(data.short_url, {
        width: 280,
        margin: 2,
        color: { dark: '#ffffff', light: '#1a1a2e' },
      })
      setQrDataUrl(qr)

      toast.success('Payment link created! Share it with the payer.')

      // Poll wallet balance every 5s to detect when payment arrives
      pollRef.current = setInterval(async () => {
        const w = await walletAPI.getWallet()
        const newBalance = parseFloat(w.data.data.inr_balance)
        const oldBalance = parseFloat(wallet?.inr_balance || 0)
        if (newBalance > oldBalance) {
          clearInterval(pollRef.current)
          setWallet(w.data.data)
          fetchData()
          toast.success(`₹${(newBalance - oldBalance).toFixed(2)} received! Balance updated.`)
        }
      }, 5000)

      // Stop polling after 30 minutes
      setTimeout(() => clearInterval(pollRef.current), 30 * 60 * 1000)

    } catch (e) {
      const msg = e.response?.data?.message || 'Failed to create payment link'
      toast.error(msg)
    } finally {
      setUpiLoading(false)
    }
  }

  const handleCopyLink = () => {
    navigator.clipboard.writeText(paymentLink?.short_url || '')
    setCopied(true)
    toast.success('Payment link copied!')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCloseUPI = () => {
    clearInterval(pollRef.current)
    setShowUPIDeposit(false)
    setPaymentLink(null)
    setQrDataUrl(null)
    setUpiAmount('')
    setUpiDescription('')
  }

  // ── Withdraw ───────────────────────────────────────────────────────────────

  const handleWithdrawClick = () => {
    if (!wallet?.web3_address) {
      toast.error('Link your MetaMask wallet in Dashboard first.')
      navigate('/dashboard')
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
      toast.success(`Withdrawal of ${withdrawAmount} USDT initiated → MetaMask`)
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

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black text-white">Wallet</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowUPIDeposit(true)}
            className="btn-primary flex items-center gap-2 py-2 px-4 text-sm"
          >
            <Plus className="w-4 h-4" /> Receive via UPI
          </button>
          <button
            onClick={handleWithdrawClick}
            className="btn-secondary flex items-center gap-2 py-2 px-4 text-sm"
          >
            <Minus className="w-4 h-4" /> Send to MetaMask
          </button>
        </div>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
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
          <p className="text-white/30 text-xs mt-2">Received via UPI / GPay / PhonePe</p>
        </div>

        <div className="glass-card p-6 border border-emerald-500/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-emerald-500/10 blur-[40px]" />
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
              <span className="text-emerald-400 font-black text-xs">USDC</span>
            </div>
            <span className="badge badge-success">USDC</span>
          </div>
          <p className="text-white/40 text-xs mb-1">USDC Balance (MetaMask)</p>
          <p className="text-3xl font-black text-white">{usdtBalance.toFixed(4)}</p>
          {wallet?.web3_address ? (
            <p className="text-white/30 text-xs mt-2 font-mono truncate">
              → {wallet.web3_address.slice(0, 10)}...{wallet.web3_address.slice(-6)}
            </p>
          ) : (
            <button onClick={() => navigate('/dashboard')} className="text-primary-400 text-xs mt-2 underline">
              Connect MetaMask to enable on-chain
            </button>
          )}
        </div>
      </div>

      {/* Flow explanation */}
      <div className="glass-card p-5 border border-white/5">
        <h3 className="text-white/70 text-sm font-bold mb-3">How it works</h3>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 text-xs text-white/50">
          {[
            { icon: <Smartphone className="w-4 h-4 text-primary-400" />, label: 'Person pays via GPay / UPI' },
            { icon: <ArrowDown className="w-4 h-4 text-emerald-400" />, label: 'INR credited to your wallet' },
            { icon: <RefreshCw className="w-4 h-4 text-yellow-400" />, label: 'Auto-converts to USDC' },
            { icon: <WalletIcon className="w-4 h-4 text-purple-400" />, label: 'USDC sent to MetaMask on Polygon' },
          ].map((step, i) => (
            <React.Fragment key={i}>
              <div className="flex items-center gap-2">
                {step.icon}
                <span>{step.label}</span>
              </div>
              {i < 3 && <span className="hidden sm:block text-white/20">→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* UPI Deposit Modal */}
      <AnimatePresence>
        {showUPIDeposit && (
          <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={handleCloseUPI}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-card p-8 w-full max-w-md border border-primary-500/20 relative"
            >
              <button onClick={handleCloseUPI} className="absolute top-4 right-4 text-white/30 hover:text-white">
                <X className="w-5 h-5" />
              </button>

              {!paymentLink ? (
                /* Step 1: Enter amount */
                <>
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                      <QrCode className="w-5 h-5 text-primary-400" />
                    </div>
                    <div>
                      <h2 className="text-xl font-black text-white">Receive via UPI</h2>
                      <p className="text-xs text-white/40">GPay · PhonePe · Paytm · Debit Card</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-sm text-white/60 mb-2 block">Amount to receive (₹)</label>
                      <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40 font-bold">₹</span>
                        <input
                          type="number"
                          value={upiAmount}
                          onChange={(e) => setUpiAmount(e.target.value)}
                          placeholder="500"
                          className="input-field pl-9"
                          id="upi-amount"
                          autoFocus
                        />
                      </div>
                    </div>

                    {/* Quick amount chips */}
                    <div className="flex gap-2 flex-wrap">
                      {[100, 500, 1000, 5000, 10000].map((amt) => (
                        <button
                          key={amt}
                          onClick={() => setUpiAmount(String(amt))}
                          className="py-1.5 px-3 rounded-lg text-xs font-bold bg-white/5 text-white/60 hover:bg-primary-500/20 hover:text-primary-400 transition-all"
                        >
                          ₹{amt.toLocaleString()}
                        </button>
                      ))}
                    </div>

                    <div>
                      <label className="text-sm text-white/60 mb-2 block">Description (optional)</label>
                      <input
                        type="text"
                        value={upiDescription}
                        onChange={(e) => setUpiDescription(e.target.value)}
                        placeholder="e.g. Freelance payment, Rent, etc."
                        className="input-field"
                        id="upi-description"
                      />
                    </div>

                    <button
                      onClick={handleCreatePaymentLink}
                      disabled={upiLoading}
                      className="btn-primary w-full py-3 flex items-center justify-center gap-2"
                    >
                      {upiLoading
                        ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        : <><QrCode className="w-4 h-4" /> Generate UPI Payment Link</>
                      }
                    </button>

                    <p className="text-center text-xs text-white/30">
                      Powered by Razorpay · Accepts GPay, PhonePe, UPI, Debit/Credit Cards
                    </p>
                  </div>
                </>
              ) : (
                /* Step 2: Show QR + link */
                <>
                  <div className="text-center mb-6">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-3">
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                    </div>
                    <h2 className="text-xl font-black text-white">Payment Link Ready</h2>
                    <p className="text-sm text-white/40 mt-1">
                      Share with the payer · ₹{upiAmount} via any UPI app
                    </p>
                  </div>

                  {/* QR Code */}
                  {qrDataUrl && (
                    <div className="flex justify-center mb-5">
                      <div className="p-3 rounded-2xl border border-white/10 bg-white/5">
                        <img src={qrDataUrl} alt="UPI QR Code" className="w-48 h-48 rounded-xl" />
                      </div>
                    </div>
                  )}

                  <p className="text-center text-xs text-white/40 mb-3">
                    Or share this link
                  </p>

                  {/* Short URL */}
                  <div className="flex items-center gap-2 bg-white/5 rounded-xl p-3 border border-white/10 mb-4">
                    <span className="text-xs text-primary-400 font-mono flex-1 truncate">
                      {paymentLink.short_url}
                    </span>
                    <button onClick={handleCopyLink} className="text-white/50 hover:text-white flex-shrink-0">
                      {copied ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <a href={paymentLink.short_url} target="_blank" rel="noopener noreferrer" className="text-white/50 hover:text-white flex-shrink-0">
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>

                  {/* Waiting indicator */}
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                    <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse flex-shrink-0" />
                    <p className="text-xs text-yellow-300">
                      Waiting for payment… Your balance will update automatically.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mt-4">
                    <button onClick={handleCopyLink} className="btn-primary py-2.5 text-sm flex items-center justify-center gap-2">
                      <Copy className="w-4 h-4" /> Copy Link
                    </button>
                    <button onClick={handleCloseUPI} className="btn-secondary py-2.5 text-sm">
                      Done
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Withdraw to MetaMask Modal */}
      <AnimatePresence>
        {showWithdraw && (
          <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowWithdraw(false)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-card p-8 w-full max-w-sm border border-emerald-500/20"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <WalletIcon className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h2 className="text-xl font-black text-white">Send to MetaMask</h2>
                  <p className="text-xs text-white/40">On-chain transfer via Polygon</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm text-white/60 mb-2 block">Destination (MetaMask)</label>
                  <div className="glass-card p-3 border border-white/10 text-xs font-mono text-emerald-400 break-all">
                    {wallet?.web3_address}
                  </div>
                </div>
                <div>
                  <label className="text-sm text-white/60 mb-2 block">Amount (USDC)</label>
                  <input
                    type="number"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    placeholder="50.00"
                    className="input-field"
                    id="withdraw-amount"
                  />
                  <p className="text-xs text-white/30 mt-1">Available: {usdtBalance.toFixed(4)} USDC</p>
                </div>
                <button
                  onClick={handleWithdraw}
                  disabled={withdrawing}
                  className="btn-primary w-full py-3 flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 border-emerald-500"
                >
                  {withdrawing
                    ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    : <><ArrowUp className="w-4 h-4" /> Send USDC to MetaMask</>
                  }
                </button>
                <p className="text-center text-xs text-white/30">
                  USDC will appear in MetaMask on Polygon within ~30 seconds
                </p>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

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
              <option value="USDT">USDC</option>
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
            <p className="text-xs mt-1">Receive via UPI to get started</p>
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
                    <p className="text-xs text-white/30">{tx.description || tx.reference_id?.slice(0, 20) || '-'} · {formatRelativeTime(tx.created_at)}</p>
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
            <button className="btn-secondary py-1.5 px-3 text-sm" disabled={!meta.previous}>← Prev</button>
            <span className="text-white/40 text-sm py-1.5 px-3">{meta.current_page} / {meta.total_pages}</span>
            <button className="btn-secondary py-1.5 px-3 text-sm" disabled={!meta.next}>Next →</button>
          </div>
        )}
      </div>
    </div>
  )
}
