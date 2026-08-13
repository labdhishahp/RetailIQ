import { useState } from 'react'
import { Bell, Shield, Palette, Globe, Database, Key } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { useTheme } from '../context/ThemeContext'

const settingsSections = [
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifications',
    description: 'Configure alert preferences and email notifications',
    settings: [
      { label: 'Critical stock alerts', type: 'toggle', default: true },
      { label: 'AI recommendation notifications', type: 'toggle', default: true },
      { label: 'Weekly report emails', type: 'toggle', default: true },
      { label: 'Campaign performance alerts', type: 'toggle', default: false },
    ],
  },
  {
    id: 'security',
    icon: Shield,
    title: 'Security',
    description: 'Manage authentication and access controls',
    settings: [
      { label: 'Two-factor authentication', type: 'toggle', default: true },
      { label: 'Session timeout (minutes)', type: 'select', options: ['15', '30', '60', '120'], default: '30' },
      { label: 'IP whitelist', type: 'toggle', default: false },
    ],
  },
  {
    id: 'appearance',
    icon: Palette,
    title: 'Appearance',
    description: 'Customize the look and feel of RetailIQ',
    settings: [
      { label: 'Dark mode', type: 'theme' },
      { label: 'Compact sidebar', type: 'toggle', default: false },
      { label: 'Animation effects', type: 'toggle', default: true },
    ],
  },
  {
    id: 'regional',
    icon: Globe,
    title: 'Regional',
    description: 'Language, timezone, and currency preferences',
    settings: [
      { label: 'Language', type: 'select', options: ['English (US)', 'English (UK)', 'Spanish', 'French'], default: 'English (US)' },
      { label: 'Timezone', type: 'select', options: ['UTC-5 (EST)', 'UTC-8 (PST)', 'UTC+0 (GMT)', 'UTC+5:30 (IST)'], default: 'UTC+5:30 (IST)' },
      { label: 'Currency', type: 'select', options: ['USD ($)', 'EUR (€)', 'GBP (£)', 'INR (₹)'], default: 'USD ($)' },
    ],
  },
  {
    id: 'data',
    icon: Database,
    title: 'Data & Integrations',
    description: 'Connect data sources and manage sync settings',
    settings: [
      { label: 'Auto-sync inventory data', type: 'toggle', default: true },
      { label: 'Sync frequency', type: 'select', options: ['Real-time', 'Every 15 min', 'Hourly', 'Daily'], default: 'Every 15 min' },
      { label: 'ERP integration', type: 'toggle', default: true },
    ],
  },
  {
    id: 'api',
    icon: Key,
    title: 'API Access',
    description: 'Manage API keys and webhook configurations',
    settings: [
      { label: 'API access enabled', type: 'toggle', default: true },
    ],
  },
]

function Toggle({ defaultOn = false }) {
  const [on, setOn] = useState(defaultOn)
  return (
    <button
      onClick={() => setOn(!on)}
      className={`relative w-10 h-5 rounded-full transition-colors ${on ? 'bg-primary' : 'bg-slate-300 dark:bg-slate-600'}`}
    >
      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${on ? 'translate-x-5' : 'translate-x-0.5'}`} />
    </button>
  )
}

export default function Settings() {
  const { darkMode, toggleTheme } = useTheme()

  return (
    <div>
      <PageHeader title="Settings" subtitle="Manage your RetailIQ platform preferences" />

      <div className="space-y-4 max-w-3xl">
        {settingsSections.map((section) => (
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
              {section.settings.map((setting) => (
                <div key={setting.label} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
                  <span className="text-sm text-slate-700 dark:text-slate-300">{setting.label}</span>
                  {setting.type === 'toggle' && <Toggle defaultOn={setting.default} />}
                  {setting.type === 'theme' && (
                    <button
                      onClick={toggleTheme}
                      className={`relative w-10 h-5 rounded-full transition-colors ${darkMode ? 'bg-primary' : 'bg-slate-300 dark:bg-slate-600'}`}
                    >
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${darkMode ? 'translate-x-5' : 'translate-x-0.5'}`} />
                    </button>
                  )}
                  {setting.type === 'select' && (
                    <select defaultValue={setting.default} className="px-3 py-1.5 text-sm rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20">
                      {setting.options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ))}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary">Reset to Defaults</Button>
          <Button>Save Changes</Button>
        </div>
      </div>
    </div>
  )
}
