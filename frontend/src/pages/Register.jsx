import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Zap, Mail, Lock, Eye, EyeOff, User, Phone, ArrowRight, Shield, CheckCircle } from 'lucide-react'
import { authAPI } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'

export default function Register() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [step, setStep] = useState('form') // form | otp
  const [otpCode, setOtpCode] = useState('')
  const [email, setEmail] = useState('')
  const [simulatedOtp, setSimulatedOtp] = useState('')

  const { register, handleSubmit, watch, formState: { errors } } = useForm()

  const onSubmit = async (data) => {
    setIsLoading(true)
    try {
      const res = await authAPI.register(data)
      const { user, tokens, otp_code } = res.data.data
      login(user, tokens.access, tokens.refresh)
      setEmail(data.email)
      if (otp_code) setSimulatedOtp(otp_code)
      setStep('otp')
      toast.success('Account created! Please verify your OTP.')
    } catch (err) {
      const errors = err.response?.data?.errors
      if (errors) {
        Object.values(errors).flat().forEach(msg => toast.error(msg))
      } else {
        toast.error(err.response?.data?.message || 'Registration failed')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleOtpVerify = async () => {
    if (!otpCode || otpCode.length !== 6) {
      toast.error('Please enter a 6-digit OTP')
      return
    }
    setIsLoading(true)
    try {
      await authAPI.verifyOTP({ email, otp: otpCode })
      toast.success('Account verified successfully!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.message || 'Invalid OTP')
    } finally {
      setIsLoading(false)
    }
  }

  if (step === 'otp') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md glass-card p-8 border border-primary-500/20"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-full bg-primary-500/20 border border-primary-500/30 flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-primary-400" />
            </div>
            <h1 className="text-2xl font-black text-white">Verify OTP</h1>
            <p className="text-white/40 mt-2 text-sm">Enter the 6-digit code sent to {email}</p>
            {simulatedOtp && (
              <div className="mt-3 px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
                🔧 Simulation Mode — OTP: <strong>{simulatedOtp}</strong>
              </div>
            )}
          </div>
          <input
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            type="text"
            placeholder="000000"
            className="input-field text-center text-2xl tracking-widest font-mono mb-6"
            id="otp-input"
            maxLength={6}
          />
          <button
            onClick={handleOtpVerify}
            disabled={isLoading || otpCode.length !== 6}
            className="btn-primary w-full py-3.5 flex items-center justify-center gap-2"
            id="otp-verify"
          >
            {isLoading ? <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><CheckCircle className="w-4 h-4" /> Verify & Continue</>}
          </button>
          <button onClick={() => navigate('/dashboard')} className="mt-3 w-full text-sm text-white/40 hover:text-white/60 text-center">
            Skip for now
          </button>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <Zap className="w-5 h-5" />
          </div>
          <span className="font-bold text-xl text-gradient">NexusPay</span>
        </div>

        <h1 className="text-3xl font-black text-white mb-2">Create Account</h1>
        <p className="text-white/40 mb-8">Join thousands using NexusPay for hybrid INR-USDT management.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">First Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input {...register('first_name', { required: 'Required' })} placeholder="John" className="input-field pl-10" id="first-name" />
              </div>
              {errors.first_name && <p className="mt-1 text-xs text-red-400">{errors.first_name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">Last Name</label>
              <input {...register('last_name', { required: 'Required' })} placeholder="Doe" className="input-field" id="last-name" />
              {errors.last_name && <p className="mt-1 text-xs text-red-400">{errors.last_name.message}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input
                {...register('email', { required: 'Email required', pattern: { value: /^\S+@\S+$/i, message: 'Invalid email' } })}
                type="email" placeholder="you@example.com" className="input-field pl-10" id="reg-email"
              />
            </div>
            {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">Phone (optional)</label>
            <div className="relative">
              <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input {...register('phone')} placeholder="+91 98765 43210" className="input-field pl-10" id="phone" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input
                {...register('password', { required: 'Password required', minLength: { value: 8, message: 'Min 8 characters' } })}
                type={showPassword ? 'text' : 'password'} placeholder="••••••••" className="input-field pl-10 pr-10" id="reg-password"
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/30">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.password && <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input
                {...register('password_confirm', {
                  required: 'Please confirm password',
                  validate: (v) => v === watch('password') || 'Passwords do not match',
                })}
                type="password" placeholder="••••••••" className="input-field pl-10" id="password-confirm"
              />
            </div>
            {errors.password_confirm && <p className="mt-1 text-xs text-red-400">{errors.password_confirm.message}</p>}
          </div>

          <button type="submit" disabled={isLoading} className="btn-primary w-full py-3.5 flex items-center justify-center gap-2 mt-2" id="register-submit">
            {isLoading ? <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <>Create Account <ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-white/40">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium">Sign In</Link>
        </p>
      </motion.div>
    </div>
  )
}
