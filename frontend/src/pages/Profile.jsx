import { Mail, Phone, MapPin, Building, Calendar, Edit3, Camera } from 'lucide-react'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import KpiCard from '../components/ui/KpiCard'
import { MessageSquare, CheckCircle2, TrendingUp } from 'lucide-react'

const userProfile = {
  name: 'LABDHI SHAH',
  role: 'Retail Operations Manager',
  email: 'labdhi@retailiq.com',
  phone: '+91 9999999999',
  location: 'Mumbai, Maharashtra',
  department: 'Operations',
  joinDate: 'March 2024',
  bio: 'Experienced retail operations manager with 8+ years in multi-channel retail. Leading digital transformation initiatives and AI-driven decision making at RetailIQ.',
}

const activityStats = {
  decisionsReviewed: 47,
  recommendationsAccepted: 38,
  avgROI: 245,
}

const recentActivity = [
  { action: 'Accepted AI recommendation', detail: 'Shampoo promotion campaign', time: '2 hours ago' },
  { action: 'Generated report', detail: 'Weekly Executive Summary', time: '1 day ago' },
  { action: 'Reviewed inventory alert', detail: 'Wireless Earbuds low stock', time: '2 days ago' },
  { action: 'Updated campaign budget', detail: 'Summer Sale 2026', time: '3 days ago' },
  { action: 'Ran AI investigation', detail: 'Customer churn analysis', time: '5 days ago' },
]

export default function Profile() {
  return (
    <div>
      <PageHeader
        title="User Profile"
        subtitle="Manage your account and view activity"
        actions={<Button variant="secondary" icon={Edit3} size="sm">Edit Profile</Button>}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <div className="lg:col-span-1">
          <Card className="text-center">
            <div className="relative inline-block mb-4">
              <div className="w-24 h-24 rounded-2xl gradient-primary flex items-center justify-center text-white text-3xl font-bold mx-auto shadow-lg shadow-primary/25">
                AK
              </div>
              <button className="absolute -bottom-1 -right-1 p-1.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
                <Camera size={14} className="text-slate-500" />
              </button>
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">{userProfile.name}</h2>
            <p className="text-sm text-slate-500 mt-1">{userProfile.role}</p>

            <div className="mt-6 space-y-3 text-left">
              {[
                { icon: Mail, value: userProfile.email },
                { icon: Phone, value: userProfile.phone },
                { icon: MapPin, value: userProfile.location },
                { icon: Building, value: userProfile.department },
                { icon: Calendar, value: `Joined ${userProfile.joinDate}` },
              ].map(({ icon: Icon, value }) => (
                <div key={value} className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                  <Icon size={14} className="text-slate-400 flex-shrink-0" />
                  <span>{value}</span>
                </div>
              ))}
            </div>

            <p className="text-sm text-slate-500 mt-4 text-left leading-relaxed">{userProfile.bio}</p>
          </Card>
        </div>

        {/* Stats + Activity */}
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard title="Decisions Reviewed" value={activityStats.decisionsReviewed} icon={MessageSquare} format="number" delay={0} />
            <KpiCard title="Accepted" value={activityStats.recommendationsAccepted} icon={CheckCircle2} format="number" delay={0.05} />
            <KpiCard title="Avg ROI" value={activityStats.avgROI} icon={TrendingUp} format="number" delay={0.1} />
          </div>

          <Card>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Recent Activity</h3>
            <div className="space-y-4">
              {recentActivity.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-start gap-3 pb-4 border-b border-slate-100 dark:border-slate-800 last:border-0 last:pb-0"
                >
                  <div className="w-2 h-2 rounded-full bg-primary mt-2 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{item.action}</p>
                    <p className="text-xs text-slate-500">{item.detail}</p>
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">{item.time}</span>
                </motion.div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
