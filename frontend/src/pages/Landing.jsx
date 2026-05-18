import React from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, ArrowRight, Shield, TrendingUp, Globe, Layers, Lock, Activity } from 'lucide-react'

const features = [
  { icon: Shield, title: 'Bank-Grade Security', desc: 'End-to-end encryption, 2FA, and immutable audit logs protect every transaction.' },
  { icon: TrendingUp, title: 'Live Exchange Rates', desc: 'Real-time USDT/INR rates from CoinGecko with minimal 0.5% spread.' },
  { icon: Layers, title: 'Ledger Architecture', desc: 'Immutable double-entry ledger ensures every rupee is accounted for.' },
  { icon: Globe, title: 'Cross-Border Payments', desc: 'Hold INR and USDT. Convert instantly. Pay anywhere.' },
  { icon: Lock, title: 'Atomic Transactions', desc: 'PostgreSQL transactions guarantee your money never gets lost in transit.' },
  { icon: Activity, title: 'Real-Time Updates', desc: 'WebSocket-powered live balance and notification system.' },
]

const stats = [
  { value: '₹0 Fees', label: 'On Deposits' },
  { value: '0.5%', label: 'Conversion Spread' },
  { value: '< 1s', label: 'Settlement Time' },
  { value: '99.9%', label: 'Uptime SLA' },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-dark-900 overflow-hidden">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 lg:px-16 py-5 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-sm">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl text-gradient">NexusPay</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="btn-secondary text-sm py-2 px-4">Sign In</Link>
          <Link to="/register" className="btn-primary text-sm py-2 px-4">Get Started</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-6 lg:px-16 pt-20 pb-32 text-center overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[800px] h-[400px] rounded-full bg-primary-500/10 blur-[120px]" />
        </div>
        <div className="absolute inset-0 bg-mesh opacity-30" />

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="relative"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary-500/30 bg-primary-500/10 text-primary-300 text-sm mb-8">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Live exchange rates via CoinGecko
          </div>

          <h1 className="text-5xl lg:text-7xl font-black mb-6 leading-tight">
            The Future of
            <br />
            <span className="text-gradient">INR ↔ USDT</span>
            <br />
            Transactions
          </h1>

          <p className="text-white/50 text-lg lg:text-xl max-w-2xl mx-auto mb-10">
            NexusPay is a production-grade hybrid wallet infrastructure. Hold, convert, and spend Indian Rupees and USDT — instantly, securely, and transparently.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link to="/register" className="btn-primary text-base py-3.5 px-8 flex items-center gap-2">
              Start for Free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/login" className="btn-secondary text-base py-3.5 px-8">
              Sign In
            </Link>
          </div>
        </motion.div>

        {/* Floating wallet card */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.3 }}
          className="relative mt-20 max-w-md mx-auto"
        >
          <div className="glass-card p-6 border border-primary-500/20 shadow-glow">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-white/40 text-xs">Portfolio Value</p>
                <p className="text-3xl font-black text-white">₹1,24,500.00</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center animate-spin-slow">
                <Zap className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-card p-3 border border-white/5">
                <p className="text-white/40 text-xs mb-1">INR Balance</p>
                <p className="text-white font-bold">₹48,250.00</p>
                <p className="text-emerald-400 text-xs mt-1">+2.4% today</p>
              </div>
              <div className="glass-card p-3 border border-white/5">
                <p className="text-white/40 text-xs mb-1">USDT Balance</p>
                <p className="text-white font-bold">906.50 USDT</p>
                <p className="text-emerald-400 text-xs mt-1">≈ ₹76,250</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 text-xs text-white/40">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Live rate: 1 USDT = ₹84.12
            </div>
          </div>
        </motion.div>
      </section>

      {/* Stats */}
      <section className="px-6 lg:px-16 py-16 border-y border-white/5">
        <div className="max-w-4xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map(({ value, label }) => (
            <div key={label} className="text-center">
              <p className="text-3xl font-black text-gradient mb-1">{value}</p>
              <p className="text-white/40 text-sm">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="px-6 lg:px-16 py-24">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-black mb-4">
              Built for <span className="text-gradient">production</span>
            </h2>
            <p className="text-white/40 max-w-xl mx-auto">
              Every feature engineered with enterprise-grade reliability, security, and compliance in mind.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, desc }, i) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
                className="glass-card-hover p-6"
              >
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 border border-primary-500/30 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-primary-400" />
                </div>
                <h3 className="font-bold text-white mb-2">{title}</h3>
                <p className="text-white/40 text-sm leading-relaxed">{desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 lg:px-16 py-24 text-center relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-[600px] h-[300px] rounded-full bg-accent-500/8 blur-[100px]" />
        </div>
        <div className="relative max-w-2xl mx-auto">
          <h2 className="text-4xl lg:text-5xl font-black mb-6">
            Ready to experience<br />
            <span className="text-gradient">next-gen finance?</span>
          </h2>
          <p className="text-white/40 mb-10">Join NexusPay and get instant access to your hybrid INR-USDT wallet.</p>
          <Link to="/register" className="btn-primary text-lg py-4 px-10 inline-flex items-center gap-2">
            Create Free Account <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 px-6 lg:px-16 py-8 text-center text-white/30 text-sm">
        © 2024 NexusPay. Production-grade fintech infrastructure simulator.
      </footer>
    </div>
  )
}
