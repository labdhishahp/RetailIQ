import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sparkles, LogIn, AlertCircle } from 'lucide-react'
import Button from '../components/ui/Button'
import { useAuth } from '../context/AuthContext'

const DEMO_ACCOUNTS = [
  { label: 'Admin', email: 'admin@retailiq.app' },
  { label: 'Manager', email: 'manager@retailiq.app' },
  { label: 'Analyst (read-only)', email: 'analyst@retailiq.app' },
]
const DEMO_PASSWORD = 'RetailIQ2026!'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@retailiq.app')
  const [password, setPassword] = useState(DEMO_PASSWORD)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.status === 401 ? 'Incorrect email or password.' : (err.message || 'Sign-in failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background dark:bg-slate-950 p-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm"
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-xl gradient-primary flex items-center justify-center shadow-lg shadow-primary/25">
            <span className="text-white font-bold">RQ</span>
          </div>
          <div>
            <h1 className="font-bold text-xl text-slate-900 dark:text-white tracking-tight">RetailIQ</h1>
            <p className="text-xs text-slate-400">Decision Intelligence</p>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Sign in</h2>
          <p className="text-sm text-slate-500 mb-5">Access your retail intelligence workspace.</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                Email
              </label>
              <input
                id="email" type="email" required autoComplete="username"
                value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                Password
              </label>
              <input
                id="password" type="password" required autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            {error && (
              <div role="alert" className="flex items-start gap-2 p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                <AlertCircle size={15} className="text-danger mt-0.5 flex-shrink-0" />
                <p className="text-xs text-red-700 dark:text-red-400">{error}</p>
              </div>
            )}

            <Button type="submit" icon={busy ? Sparkles : LogIn} disabled={busy} className="w-full justify-center">
              {busy ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">Demo accounts</p>
            <div className="space-y-1.5">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.email} type="button"
                  onClick={() => { setEmail(a.email); setPassword(DEMO_PASSWORD) }}
                  className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <span className="text-slate-600 dark:text-slate-400">{a.label}</span>
                  <span className="font-mono text-slate-400">{a.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
