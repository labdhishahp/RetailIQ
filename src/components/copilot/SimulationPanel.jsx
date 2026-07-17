import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, TrendingUp, TrendingDown, DollarSign, Package, Heart, Sparkles, Play } from 'lucide-react'
import Card from '../ui/Card'
import Button from '../ui/Button'
import { simulationDefaults } from '../../data/mockData'

const metricIcons = {
  estimatedSales: TrendingUp,
  revenue: DollarSign,
  profit: TrendingUp,
  inventory: Package,
  customerSatisfaction: Heart,
}

const metricLabels = {
  estimatedSales: 'Est. Sales Change',
  revenue: 'Revenue Impact',
  profit: 'Profit Impact',
  inventory: 'Inventory Change',
  customerSatisfaction: 'Customer Satisfaction',
}

export default function SimulationPanel() {
  const [query, setQuery] = useState(simulationDefaults.question)
  const [results, setResults] = useState(null)
  const [running, setRunning] = useState(false)

  const runSimulation = () => {
    setRunning(true)
    setResults(null)
    setTimeout(() => {
      setResults(simulationDefaults.results)
      setRunning(false)
    }, 2500)
  }

  return (
    <Card className="!p-0 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-violet-500/5 to-primary/5">
        <div className="flex items-center gap-2">
          <FlaskConical size={18} className="text-violet-500" />
          <h3 className="font-semibold text-slate-900 dark:text-white">What-If Simulation</h3>
        </div>
        <p className="text-xs text-slate-500 mt-1">Model business scenarios before making decisions</p>
      </div>

      <div className="p-5 space-y-4">
        <div>
          <label className="text-xs font-medium text-slate-500 mb-1.5 block">Scenario Question</label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/30 resize-none"
          />
        </div>

        <Button onClick={runSimulation} disabled={running} icon={Play} className="w-full">
          {running ? 'Running Simulation...' : 'Run Simulation'}
        </Button>

        <AnimatePresence>
          {running && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center py-8"
            >
              <div className="text-center">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  className="w-10 h-10 mx-auto mb-3 rounded-full border-2 border-primary border-t-transparent"
                />
                <p className="text-sm text-slate-500">Modeling scenario outcomes...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {results && !running && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(results).filter(([key]) => key !== 'recommendation').map(([key, data], i) => {
                  const Icon = metricIcons[key] || TrendingUp
                  return (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.1 }}
                      className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon size={14} className="text-slate-400" />
                        <span className="text-[10px] text-slate-500 font-medium">{metricLabels[key]}</span>
                      </div>
                      <p className={`text-lg font-bold ${data.positive ? 'text-success' : 'text-danger'}`}>
                        {data.value}
                      </p>
                    </motion.div>
                  )
                })}
              </div>

              <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
                <div className="flex items-start gap-2">
                  <Sparkles size={16} className="text-primary mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-primary mb-1">AI Recommendation</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{simulationDefaults.recommendation}</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  )
}
