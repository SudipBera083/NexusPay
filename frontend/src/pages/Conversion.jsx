import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeftRight, TrendingUp, RefreshCw, CheckCircle, Info } from 'lucide-react'
import { exchangeAPI, transactionAPI } from '@/api/client'
import { useExchangeStore } from '@/store/walletStore'
import { formatINR } from '@/utils/format'
import toast from 'react-hot-toast'

export default function Conversion() {
  const [fromCurrency, setFromCurrency] = useState('USDT')
  const [toCurrency, setToCurrency] = useState('INR')
  const [amount, setAmount] = useState('')
  const [quote, setQuote] = useState(null)
  const [loadingQuote, setLoadingQuote] = useState(false)
  const [converting, setConverting] = useState(false)
  const [lastConversion, setLastConversion] = useState(null)
  const { currentRate, setRate } = useExchangeStore()

  useEffect(() => {
    exchangeAPI.getCurrentRate().then(r => setRate(r.data.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const timer = setTimeout(fetchQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, fromCurrency, toCurrency])

  const fetchQuote = async () => {
    if (!amount) return
    setLoadingQuote(true)
    try {
      const res = await exchangeAPI.getQuote({ from_currency: fromCurrency, to_currency: toCurrency, amount })
      setQuote(res.data.data)
    } catch (e) {
      toast.error('Could not fetch quote')
    } finally { setLoadingQuote(false) }
  }

  const swapCurrencies = () => {
    setFromCurrency(toCurrency)
    setToCurrency(fromCurrency)
    setAmount('')
    setQuote(null)
  }

  const handleConvert = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter an amount'); return }
    setConverting(true)
    try {
      const res = await transactionAPI.convert({ from_currency: fromCurrency, to_currency: toCurrency, amount })
      setLastConversion(res.data.data)
      setAmount('')
      setQuote(null)
      toast.success(`Converted ${amount} ${fromCurrency} → ${res.data.data.to_amount} ${toCurrency}`)
    } catch (e) {
      toast.error(e.response?.data?.message || 'Conversion failed')
    } finally { setConverting(false) }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-black text-white">Currency Conversion</h1>
        <p className="text-white/40 text-sm mt-0.5">Convert between INR and USDT at live market rates</p>
      </div>

      {/* Live Rate Banner */}
      {currentRate && (
        <div className="glass-card p-4 border border-emerald-500/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-white/40">Live USDT/INR</p>
              <p className="font-bold text-white">1 USDT = ₹{parseFloat(currentRate.rate).toFixed(2)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            LIVE
          </div>
        </div>
      )}

      {/* Converter */}
      <div className="glass-card p-6 border border-primary-500/20">
        <h2 className="font-bold text-white mb-5">Convert</h2>

        {/* From */}
        <div className="mb-3">
          <label className="text-xs text-white/40 mb-2 block">From</label>
          <div className="flex gap-3">
            <div className="glass-card border border-white/10 px-4 py-3 rounded-xl font-bold text-white min-w-[100px] flex items-center justify-center">
              {fromCurrency}
            </div>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={fromCurrency === 'INR' ? '10000' : '100'}
              className="input-field flex-1"
              id="convert-amount"
            />
          </div>
        </div>

        {/* Swap */}
        <div className="flex justify-center my-3">
          <button
            onClick={swapCurrencies}
            className="w-10 h-10 rounded-xl bg-primary-500/20 border border-primary-500/30 flex items-center justify-center hover:bg-primary-500/30 transition-colors group"
          >
            <ArrowLeftRight className="w-4 h-4 text-primary-400 group-hover:rotate-180 transition-transform duration-300" />
          </button>
        </div>

        {/* To */}
        <div className="mb-5">
          <label className="text-xs text-white/40 mb-2 block">To</label>
          <div className="flex gap-3">
            <div className="glass-card border border-emerald-500/20 px-4 py-3 rounded-xl font-bold text-emerald-400 min-w-[100px] flex items-center justify-center">
              {toCurrency}
            </div>
            <div className="input-field flex-1 flex items-center">
              {loadingQuote ? (
                <span className="w-4 h-4 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
              ) : (
                <span className={quote ? 'text-emerald-400 font-bold' : 'text-white/30'}>
                  {quote ? parseFloat(quote.to_amount).toFixed(toCurrency === 'INR' ? 2 : 6) : '—'}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Quote Breakdown */}
        <AnimatePresence>
          {quote && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-5 glass-card p-4 border border-white/5 space-y-2 text-sm"
            >
              <div className="flex justify-between">
                <span className="text-white/50">Exchange Rate</span>
                <span className="text-white font-medium">₹{parseFloat(quote.rate).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/50">Spread ({quote.spread_percent}%)</span>
                <span className="text-white/70">included</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/50">Platform Fee ({quote.fee_percent}%)</span>
                <span className="text-amber-400">{parseFloat(quote.fee_amount).toFixed(4)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-white/10 font-bold">
                <span className="text-white">You receive</span>
                <span className="text-emerald-400">{parseFloat(quote.to_amount).toFixed(toCurrency === 'INR' ? 2 : 6)} {toCurrency}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <button
          onClick={handleConvert}
          disabled={converting || !amount || parseFloat(amount) <= 0}
          className="btn-primary w-full py-3.5 flex items-center justify-center gap-2"
          id="convert-btn"
        >
          {converting ? (
            <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <><ArrowLeftRight className="w-4 h-4" />Convert Now</>
          )}
        </button>
      </div>

      {/* Last Conversion Result */}
      <AnimatePresence>
        {lastConversion && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="glass-card p-5 border border-emerald-500/20"
          >
            <div className="flex items-center gap-3 mb-3">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <p className="font-bold text-white">Conversion Successful</p>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><p className="text-white/40 text-xs">Sent</p><p className="text-white font-medium">{parseFloat(lastConversion.from_amount).toFixed(6)} {lastConversion.from_currency}</p></div>
              <div><p className="text-white/40 text-xs">Received</p><p className="text-emerald-400 font-bold">{parseFloat(lastConversion.to_amount).toFixed(6)} {lastConversion.to_currency}</p></div>
              <div><p className="text-white/40 text-xs">Rate</p><p className="text-white font-medium">₹{parseFloat(lastConversion.rate).toFixed(2)}</p></div>
              <div><p className="text-white/40 text-xs">Reference</p><p className="text-white/60 font-mono text-xs">{lastConversion.reference_id}</p></div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Info */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
        <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-blue-300/70">
          Conversion includes a <strong>0.5% spread</strong> (market maker fee) plus a <strong>0.1% platform fee</strong>.
          Rates are sourced from CoinGecko and refreshed every 60 seconds.
        </p>
      </div>
    </div>
  )
}
