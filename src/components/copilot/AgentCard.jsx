import { motion } from 'framer-motion'
import {
  Brain, TrendingDown, Package, DollarSign, Megaphone, Users, Sparkles, CheckCircle2, Loader2,
} from 'lucide-react'

const iconMap = {
  Brain, TrendingDown, Package, DollarSign, Megaphone, Users, Sparkles,
}

export default function AgentCard({ agent, status, progress, index }) {
  const Icon = iconMap[agent.icon] || Brain
  const isActive = status === 'active'
  const isComplete = status === 'complete'
  const isPending = status === 'pending'

  return (
    <motion.div
      initial={{ opacity: 0, x: -20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className={`
        relative rounded-2xl p-4 border transition-all duration-300
        ${isActive ? 'bg-primary/5 border-primary/30 shadow-lg shadow-primary/10 ring-1 ring-primary/20' : ''}
        ${isComplete ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800' : ''}
        ${isPending ? 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 opacity-50' : ''}
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`
          p-2.5 rounded-xl flex-shrink-0 transition-all duration-300
          ${isActive ? 'bg-primary text-white shadow-lg shadow-primary/30' : ''}
          ${isComplete ? 'bg-emerald-500 text-white' : ''}
          ${isPending ? 'bg-slate-200 dark:bg-slate-700 text-slate-400' : ''}
        `}>
          {isComplete ? <CheckCircle2 size={20} /> : isActive ? <Loader2 size={20} className="animate-spin" /> : <Icon size={20} />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{agent.name}</h4>
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full
              ${isActive ? 'bg-primary/10 text-primary' : ''}
              ${isComplete ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' : ''}
              ${isPending ? 'bg-slate-100 text-slate-400 dark:bg-slate-800' : ''}
            `}>
              {isActive ? 'Working...' : isComplete ? 'Complete' : 'Waiting'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{agent.task}</p>

          {(isActive || isComplete) && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                <span>Progress</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full ${isComplete ? 'bg-emerald-500' : 'bg-primary'}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              {isActive && (
                <p className="text-[10px] text-slate-400 mt-1.5">
                  Est. {Math.ceil((agent.duration * (1 - progress / 100)) / 1000)}s remaining
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-2xl border-2 border-primary/20"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </motion.div>
  )
}
