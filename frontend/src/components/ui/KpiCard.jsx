import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { formatPercent } from '../../data/mockData'
import AnimatedCounter from './AnimatedCounter'

export default function KpiCard({ title, value, change, trend, icon: Icon, format = 'currency', delay = 0, highlight = false }) {
  const isPositive = trend === 'up'

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0, boxShadow: highlight ? '0 0 0 2px rgba(37, 99, 235, 0.3)' : undefined }}
      transition={{ duration: 0.4, delay }}
      className="rounded-2xl p-5 bg-white dark:bg-slate-900 shadow-premium border border-slate-200/60 dark:border-slate-700/60 hover:shadow-lg transition-all duration-200"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1 tracking-tight">
            <AnimatedCounter value={value} format={format} />
          </p>
          {change !== undefined && (
            <div className={`flex items-center gap-1 mt-2 text-sm font-medium ${isPositive ? 'text-success' : 'text-danger'}`}>
              {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              <span>{formatPercent(change)}</span>
              <span className="text-slate-400 font-normal">vs last month</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
            <Icon size={20} />
          </div>
        )}
      </div>
    </motion.div>
  )
}
