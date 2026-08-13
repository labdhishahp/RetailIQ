import { motion } from 'framer-motion'

export default function Card({ children, className = '', hover = false, glass = false, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`
        rounded-2xl p-5
        ${glass ? 'glass-card' : 'bg-white dark:bg-slate-900'}
        shadow-premium
        border border-slate-200/60 dark:border-slate-700/60
        ${hover ? 'transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 cursor-pointer' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </motion.div>
  )
}
