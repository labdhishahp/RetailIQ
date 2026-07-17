import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'

export default function PromptSuggestions({ suggestions, onSelect }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {suggestions.map((suggestion, i) => (
        <motion.button
          key={suggestion}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(suggestion)}
          className="flex items-start gap-2 p-3 rounded-xl text-left text-sm text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-primary/30 hover:bg-primary/5 transition-all duration-200 group"
        >
          <Sparkles size={14} className="text-primary mt-0.5 flex-shrink-0 opacity-60 group-hover:opacity-100" />
          <span>{suggestion}</span>
        </motion.button>
      ))}
    </div>
  )
}
