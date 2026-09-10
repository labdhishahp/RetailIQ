import { useEffect, useState } from 'react'
import { Mail, Phone, MapPin, Building, Calendar, Edit3, Save, X, CheckCircle2, MessageSquare, TrendingUp } from 'lucide-react'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import KpiCard from '../components/ui/KpiCard'
import StatusChip from '../components/ui/StatusChip'
import { useAuth } from '../context/AuthContext'
import { useDemo } from '../context/DemoContext'
import { updateMe } from '../api/retail'

export default function Profile() {
  const { user } = useAuth()
  const { decisions, recommendations, pushToast } = useDemo()
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ full_name: '', job_title: '', location: '', phone: '' })

  useEffect(() => {
    if (user) {
      setForm({
        full_name: user.full_name ?? '',
        job_title: user.job_title ?? '',
        location: user.location ?? '',
        phone: user.phone ?? '',
      })
    }
  }, [user])

  const accepted = decisions.filter((d) => d.status === 'accepted')
  const initials = (user?.full_name || 'RQ').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()

  const save = async () => {
    setSaving(true)
    try {
      await updateMe(form)
      pushToast({ title: 'Profile updated', message: 'Your details have been saved', type: 'success' })
      setEditing(false)
    } catch (err) {
      pushToast({ title: 'Could not save profile', message: err.message, type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const details = [
    { icon: Mail, label: 'Email', value: user?.email },
    { icon: Phone, label: 'Phone', value: form.phone || '—' },
    { icon: MapPin, label: 'Location', value: form.location || '—' },
    { icon: Building, label: 'Role', value: user?.role },
    { icon: Calendar, label: 'Member since', value: user?.created_at?.slice(0, 10) },
  ]

  return (
    <div>
      <PageHeader
        title="User Profile"
        subtitle="Your account and activity"
        actions={editing ? (
          <div className="flex gap-2">
            <Button variant="secondary" icon={X} size="sm" onClick={() => setEditing(false)}>Cancel</Button>
            <Button icon={Save} size="sm" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </div>
        ) : (
          <Button variant="secondary" icon={Edit3} size="sm" onClick={() => setEditing(true)}>Edit profile</Button>
        )}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card className="text-center">
            <div className="w-24 h-24 rounded-2xl gradient-primary flex items-center justify-center text-white text-3xl font-bold mx-auto shadow-lg shadow-primary/25 mb-4">
              {initials}
            </div>

            {editing ? (
              <div className="space-y-2 text-left">
                {[
                  { key: 'full_name', label: 'Full name' },
                  { key: 'job_title', label: 'Job title' },
                  { key: 'location', label: 'Location' },
                  { key: 'phone', label: 'Phone' },
                ].map((f) => (
                  <div key={f.key}>
                    <label htmlFor={`pf-${f.key}`} className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                      {f.label}
                    </label>
                    <input
                      id={`pf-${f.key}`} value={form[f.key]}
                      onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                      className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">{user?.full_name}</h2>
                <p className="text-sm text-slate-500 mt-1">{user?.job_title || '—'}</p>
                <div className="mt-3 flex justify-center">
                  <StatusChip status={user?.role === 'admin' ? 'accepted' : 'info'} label={user?.role} />
                </div>
                <div className="mt-6 space-y-3 text-left">
                  {details.map((d) => (
                    <div key={d.label} className="flex items-center gap-3">
                      <d.icon size={15} className="text-slate-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-[10px] uppercase tracking-wider text-slate-400">{d.label}</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300 truncate">{d.value}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard title="Decisions logged" value={decisions.length} icon={MessageSquare} format="number" delay={0} />
            <KpiCard title="Accepted" value={accepted.length} icon={CheckCircle2} format="number" delay={0.05} />
            <KpiCard title="Open recommendations" value={recommendations.filter((r) => r.status === 'pending').length} icon={TrendingUp} format="number" delay={0.1} />
          </div>

          <Card>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Recent decisions</h3>
            {decisions.length === 0 ? (
              <p className="text-sm text-slate-400">No decisions recorded yet. Accept a recommendation to start the log.</p>
            ) : (
              <div className="space-y-3">
                {decisions.slice(0, 6).map((d) => (
                  <motion.div
                    key={d.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                    className="flex items-start gap-3 pb-3 border-b border-slate-100 dark:border-slate-800 last:border-0 last:pb-0"
                  >
                    <StatusChip status={d.status} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800 dark:text-slate-200 truncate">{d.question}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{d.date} · {d.impact}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
