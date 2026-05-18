import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CreditCard, CheckCircle, AlertTriangle, Store, Zap } from 'lucide-react'
import { transactionAPI } from '@/api/client'
import { useWalletStore } from '@/store/walletStore'
import { formatINR } from '@/utils/format'
import toast from 'react-hot-toast'

const MERCHANTS = [
  { name: 'Amazon India', category: 'E-Commerce', icon: '🛒' },
  { name: 'Swiggy', category: 'Food & Dining', icon: '🍔' },
  { name: 'Uber', category: 'Transport', icon: '🚗' },
  { name: 'Netflix', category: 'Entertainment', icon: '🎬' },
  { name: 'Reliance Jio', category: 'Telecom', icon: '📱' },
  { name: 'BookMyShow', category: 'Entertainment', icon: '🎭' },
]

export default function Payment() {
  const { wallet } = useWalletStore()
  const [selectedMerchant, setSelectedMerchant] = useState(null)
  const [customMerchant, setCustomMerchant] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [paying, setPaying] = useState(false)
  const [result, setResult] = useState(null)

  const merchant = selectedMerchant || (customMerchant ? { name: customMerchant, category: 'General', icon: '🏪' } : null)

  const handlePay = async () => {
    if (!merchant) { toast.error('Select or enter a merchant'); return }
    if (!amount || parseFloat(amount) < 1) { toast.error('Enter a valid amount (min ₹1)'); return }
    setPaying(true)
    try {
      const res = await transactionAPI.pay({
        merchant_name: merchant.name,
        amount_inr: amount,
        description: description || `Payment to ${merchant.name}`,
        merchant_category: merchant.category,
      })
      setResult(res.data.data)
      setAmount('')
      setDescription('')
      toast.success(`Payment of ₹${amount} to ${merchant.name} successful!`)
    } catch (e) {
      toast.error(e.response?.data?.message || 'Payment failed')
    } finally { setPaying(false) }
  }

  const inrBalance = parseFloat(wallet?.inr_balance || 0)
  const usdtBalance = parseFloat(wallet?.usdt_balance || 0)
  const amountNum = parseFloat(amount || 0)
  const needsConversion = amountNum > inrBalance && amountNum <= inrBalance + usdtBalance * 84

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-black text-white">Payment Simulator</h1>
        <p className="text-white/40 text-sm mt-0.5">Simulate merchant payments with smart USDT→INR conversion</p>
      </div>

      {/* Balance Preview */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-card p-4 border border-primary-500/20">
          <p className="text-white/40 text-xs">INR Available</p>
          <p className="text-xl font-black text-white">{formatINR(inrBalance)}</p>
        </div>
        <div className="glass-card p-4 border border-emerald-500/20">
          <p className="text-white/40 text-xs">USDT Available</p>
          <p className="text-xl font-black text-emerald-400">{usdtBalance.toFixed(4)}</p>
        </div>
      </div>

      {/* Merchant Selection */}
      <div className="glass-card p-6">
        <h2 className="font-bold text-white mb-4">Select Merchant</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
          {MERCHANTS.map((m) => (
            <button
              key={m.name}
              onClick={() => { setSelectedMerchant(m); setCustomMerchant('') }}
              className={`p-3 rounded-xl border text-left transition-all ${selectedMerchant?.name === m.name ? 'border-primary-500/60 bg-primary-500/15' : 'border-white/10 bg-white/3 hover:bg-white/6'}`}
            >
              <span className="text-2xl block mb-1">{m.icon}</span>
              <p className="text-sm font-medium text-white">{m.name}</p>
              <p className="text-xs text-white/40">{m.category}</p>
            </button>
          ))}
        </div>
        <div>
          <label className="text-xs text-white/40 mb-2 block">Or enter custom merchant</label>
          <div className="relative">
            <Store className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              value={customMerchant}
              onChange={(e) => { setCustomMerchant(e.target.value); setSelectedMerchant(null) }}
              placeholder="e.g. Local Coffee Shop"
              className="input-field pl-10"
              id="custom-merchant"
            />
          </div>
        </div>
      </div>

      {/* Payment Details */}
      <div className="glass-card p-6">
        <h2 className="font-bold text-white mb-4">Payment Details</h2>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-white/60 mb-2 block">Amount (INR)</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/40 font-bold">₹</span>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="input-field pl-8"
                id="payment-amount"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-white/60 mb-2 block">Description (optional)</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this for?"
              className="input-field"
              id="payment-description"
            />
          </div>

          {/* Smart conversion indicator */}
          <AnimatePresence>
            {needsConversion && amountNum > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20"
              >
                <Zap className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-300">
                  <p className="font-bold mb-0.5">Smart Conversion Active</p>
                  <p className="text-amber-300/70">
                    Your INR balance (₹{formatINR(inrBalance)}) is insufficient. NexusPay will automatically convert the required USDT to cover the shortfall of ₹{formatINR(amountNum - inrBalance)}.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <button
            onClick={handlePay}
            disabled={paying || !merchant || !amount || parseFloat(amount) < 1}
            className="btn-primary w-full py-3.5 flex items-center justify-center gap-2"
            id="pay-btn"
          >
            {paying ? (
              <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <><CreditCard className="w-4 h-4" />Pay {amount ? formatINR(amount) : ''} to {merchant?.name || '...'}</>
            )}
          </button>
        </div>
      </div>

      {/* Result */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 border border-emerald-500/20"
          >
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
              <div>
                <p className="font-bold text-white">Payment Successful</p>
                <p className="text-xs text-white/40">{result.reference_id}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><p className="text-white/40 text-xs">Merchant</p><p className="text-white">{result.merchant_name}</p></div>
              <div><p className="text-white/40 text-xs">Amount</p><p className="text-white font-bold">{formatINR(result.amount_inr)}</p></div>
              {parseFloat(result.usdt_converted) > 0 && (
                <>
                  <div><p className="text-white/40 text-xs">From INR Balance</p><p className="text-white">{formatINR(result.inr_from_balance)}</p></div>
                  <div><p className="text-white/40 text-xs">USDT Converted</p><p className="text-amber-400">{parseFloat(result.usdt_converted).toFixed(6)} USDT</p></div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
