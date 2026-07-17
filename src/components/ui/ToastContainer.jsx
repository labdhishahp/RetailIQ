import { AnimatePresence, motion } from 'framer-motion'
import { Bell, CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'
import { useDemo } from '../../context/DemoContext'

const icons = {
  success: CheckCircle2,
  warning: AlertTriangle,
  info: Info,
  error: AlertTriangle,
}

const colors = {
  success: 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40',
  warning: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40',
  info: 'border-primary/20 bg-primary/5',
  error: 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40',
}

const iconColors = {
  success: 'text-emerald-500',
  warning: 'text-amber-500',
  info: 'text-primary',
  error: 'text-danger',
}

export default function ToastContainer() {
  const { toasts } = useDemo()

  return (
    <div className="fixed top-20 right-6 z-50 flex flex-col gap-3 pointer-events-none w-80 max-w-[calc(100vw-3rem)]">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => {
          const Icon = icons[toast.type] || Bell
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, x: 80, scale: 0.92 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 80, scale: 0.92 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className={`pointer-events-auto rounded-2xl border shadow-xl backdrop-blur-xl p-4 ${colors[toast.type] || colors.info}`}
            >
              <div className="flex items-start gap-3">
                <Icon size={18} className={`flex-shrink-0 mt-0.5 ${iconColors[toast.type] || iconColors.info}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">{toast.title}</p>
                  {toast.message && (
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{toast.message}</p>
                  )}
                </div>
                <X size={14} className="text-slate-400 flex-shrink-0" />
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
