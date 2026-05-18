import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Zap, Mail, Lock, Eye, EyeOff, ArrowRight, Shield } from 'lucide-react'
import { authAPI, walletAPI } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { useWalletStore } from '@/store/walletStore'
import toast from 'react-hot-toast'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const { setWallet } = useWalletStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm()

  const onSubmit = async (data) => {
    setIsLoading(true)
    try {
      const res = await authAPI.login(data)
      const { user, tokens } = res.data.data
      login(user, tokens.access, tokens.refresh)

      try {
        const wRes = await walletAPI.getWallet()
        setWallet(wRes.data.data)
      } catch {}

      toast.success(`Welcome back, ${user.first_name}!`)
      navigate('/dashboard')
    } catch (err) {
      const data = err.response?.data
      let msg = data?.message || 'Login failed. Please check your credentials.'
      if (data?.errors?.non_field_errors) {
        msg = data.errors.non_field_errors[0]
      } else if (data?.errors?.email) {
        msg = `Email: ${data.errors.email[0]}`
      } else if (data?.errors?.password) {
        msg = `Password: ${data.errors.password[0]}`
      }
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left decorative panel */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-dark-800 items-center justify-center p-16">
        <div className="absolute inset-0">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary-500/15 blur-[80px]" />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full bg-accent-500/10 blur-[60px]" />
          <div className="absolute inset-0 bg-mesh opacity-20" />
        </div>

        <div className="relative text-center">
          <motion.div
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className="glass-card p-8 mb-10 max-w-xs mx-auto border border-primary-500/20 shadow-glow"
          >
            <div className="flex justify-between items-start mb-5">
              <div>
                <p className="text-white/40 text-xs mb-1">INR Balance</p>
                <p className="text-2xl font-black text-white">₹48,250</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="glass-card p-3 border border-white/5 flex justify-between items-center">
              <div>
                <p className="text-white/40 text-xs">USDT</p>
                <p className="font-bold text-white">906.50 USDT</p>
              </div>
              <span className="badge badge-success text-xs">+2.4%</span>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-white/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              1 USDT = ₹84.12
            </div>
          </motion.div>

          <h2 className="text-3xl font-black text-white mb-3">
            Your Money,<br />
            <span className="text-gradient">Your Control</span>
          </h2>
          <p className="text-white/40 text-sm max-w-xs mx-auto">
            Manage INR and USDT in one powerful wallet with real-time rates and instant conversions.
          </p>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6 bg-dark-900">
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Logo */}
          <div className="flex items-center gap-3 mb-10">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-sm">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-gradient">NexusPay</span>
          </div>

          <h1 className="text-3xl font-black text-white mb-2">Sign In</h1>
          <p className="text-white/40 mb-8">Welcome back. Enter your credentials to continue.</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  {...register('email', {
                    required: 'Email is required',
                    pattern: { value: /^\S+@\S+$/i, message: 'Invalid email address' },
                  })}
                  type="email"
                  placeholder="you@example.com"
                  className="input-field pl-10"
                  id="login-email"
                />
              </div>
              {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  {...register('password', { required: 'Password is required' })}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="input-field pl-10 pr-10"
                  id="login-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3.5 flex items-center justify-center gap-2 mt-6"
              id="login-submit"
            >
              {isLoading ? (
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Sign In <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-white/40">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
              Create one
            </Link>
          </p>

          <div className="mt-8 flex items-center gap-2 text-xs text-white/25 justify-center">
            <Shield className="w-3.5 h-3.5" />
            Protected by JWT + rate limiting
          </div>
        </motion.div>
      </div>
    </div>
  )
}
