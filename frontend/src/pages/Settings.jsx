import { useCallback, useEffect, useState } from 'react'
import { Bell, Shield, Palette, Globe, Database, Save, RotateCcw } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { useTheme } from '../context/ThemeContext'
import { useDemo } from '../context/DemoContext'
import { getPreferences, savePreferences } from '../api/retail'

// Only settings the application actually honours are listed. Preferences are
// persisted per user via /auth/me/preferences.
const SECTIONS = [
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifications',
    description: 'Which conditions raise an alert for you',
    fields: [
      { key: 'alert_stock', label: 'Stock and reorder alerts', type: 'toggle', default: true },
      { key: 'alert_campaign', label: 'Campaign ROI alerts', type: 'toggle', default: true },
      { key: 'alert_customer', label: 'Customer churn alerts', type: 'toggle', default: true },
    ],
  },
  {
    id: 'thresholds',
    icon: Shield,
    title: 'Decision thresholds',
    description: 'Values the recommendation and alert rules compare against',
    fields: [
      { key: 'cover_days_warning', label: 'Low-cover warning (days)', type: 'select',
        options: ['7', '14', '21', '30'], default: '14' },
      { key: 'campaign_roi_target', label: 'Campaign ROI target', type: 'select',
        options: ['1.5', '2.0', '2.5', '3.0'], default: '2.5' },
      { key: 'churn_days', label: 'Churn window (days)', type: 'select',
        options: ['30', '60', '90', '120'], default: '60' },
    ],
  },
  {
    id: 'appearance',
    icon: Palette,
    title: 'Appearance',
    description: 'How RetailIQ looks for you',
    fields: [{ key: 'theme', label: 'Dark mode', type: 'theme' }],
  },
  {
    id: 'regional',
    icon: Globe,
    title: 'Regional',
    description: 'Formatting preferences',
    fields: [
      { key: 'currency', label: 'Currency', type: 'select',
        options: ['USD ($)', 'EUR (€)', 'GBP (£)', 'INR (₹)'], default: 'USD ($)' },
      { key: 'timezone', label: 'Timezone', type: 'select',
        options: ['UTC+0 (GMT)', 'UTC-5 (EST)', 'UTC-8 (PST)', 'UTC+5:30 (IST)'], default: 'UTC+5:30 (IST)' },
    ],
  },
  {
    id: 'data',
    icon: Database,
    title: 'Data',
    description: 'How often the dashboard refetches',
    fields: [
      { key: 'auto_refresh', label: 'Auto-refresh dashboard', type: 'toggle', default: false },
      { key: 'refresh_minutes', label: 'Refresh interval (minutes)', type: 'select',
        options: ['1', '5', '15', '60'], default: '15' },
    ],
  },
]

const DEFAULTS = Object.fromEntries(
  SECTIONS.flatMap((s) => s.fields.filter((f) => f.type !== 'theme').map((f) => [f.key, f.default])),
)

function Toggle({ id, checked, onChange }) {
  return (
    <button
      id={id} role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      className={`relative w-10 h-5 rounded-full transition-colors ${checked ? 'bg-primary' : 'bg-slate-300 dark:bg-slate-600'}`}
    >
      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} />
    </button>
  )
}

export default function Settings() {
  const { darkMode, toggleTheme } = useTheme()
  const { pushToast } = useDemo()
  const [values, setValues] = useState(DEFAULTS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  const load = useCallback(async () => {
    try {
      const pref = await getPreferences()
      setValues({ ...DEFAULTS, ...(pref.settings || {}) })
    } catch {
      setValues(DEFAULTS)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const update = (key, value) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    setDirty(true)
  }

  const save = async () => {
    setSaving(true)
    try {
      await savePreferences({ settings: values, theme: darkMode ? 'dark' : 'light' })
      setDirty(false)
      pushToast({ title: 'Settings saved', message: 'Your preferences are stored on your account', type: 'success' })
    } catch (err) {
      pushToast({ title: 'Could not save settings', message: err.message, type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const reset = () => {
    setValues(DEFAULTS)
    setDirty(true)
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Preferences are saved to your account" />

      <div className="space-y-4 max-w-3xl">
        {SECTIONS.map((section) => (
          <Card key={section.id}>
            <div className="flex items-start gap-3 mb-4">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <section.icon size={18} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{section.title}</h3>
                <p className="text-xs text-slate-500">{section.description}</p>
              </div>
            </div>

            <div className="space-y-3">
              {section.fields.map((field) => (
                <div key={field.key} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
                  <label htmlFor={`set-${field.key}`} className="text-sm text-slate-700 dark:text-slate-300">
                    {field.label}
                  </label>
                  {field.type === 'toggle' && (
                    <Toggle
                      id={`set-${field.key}`}
                      checked={!!values[field.key]}
                      onChange={(v) => update(field.key, v)}
                    />
                  )}
                  {field.type === 'theme' && (
                    <Toggle id={`set-${field.key}`} checked={darkMode} onChange={toggleTheme} />
                  )}
                  {field.type === 'select' && (
                    <select
                      id={`set-${field.key}`}
                      value={values[field.key] ?? field.default}
                      onChange={(e) => update(field.key, e.target.value)}
                      disabled={loading}
                      className="px-3 py-1.5 text-sm rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      {field.options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ))}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" icon={RotateCcw} onClick={reset}>Reset to defaults</Button>
          <Button icon={Save} onClick={save} disabled={saving || !dirty}>
            {saving ? 'Saving…' : dirty ? 'Save changes' : 'Saved'}
          </Button>
        </div>
      </div>
    </div>
  )
}
