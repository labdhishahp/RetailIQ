import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, TrendingUp, TrendingDown, DollarSign, Package, Sparkles, Play, AlertTriangle } from 'lucide-react'
import Card from '../ui/Card'
import Button from '../ui/Button'
import { useDemo } from '../../context/DemoContext'
import { simulationDefaults } from '../../data/mockData'

const metricIcons = {
  sales: TrendingUp,
  revenue: DollarSign,
  profit: TrendingUp,
  inventory: Package,
}

const metricLabels = {
  sales: 'Sales Change',
  revenue: 'Revenue Impact',
  profit: 'Profit Impact',
  inventory: 'Inventory Outlook',
}

export default function SimulationPanel() {
  const { runSimulation, simulationPhase } = useDemo()
  const [query, setQuery] = useState(simulationDefaults.question)
  const [showResults, setShowResults] = useState(false)

  const handleRun = () => {
    setShowResults(false)
    runSimulation()
    setTimeout(() => setShowResults(true), 2800)
  }

  const results = simulationDefaults.results
  const isRunning = simulationPhase === 'running'
  const isComplete = simulationPhase === 'complete'

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

        <Button onClick={handleRun} disabled={isRunning} icon={Play} className="w-full">
          {isRunning ? 'Running Simulation...' : 'Run Simulation'}
        </Button>

        <AnimatePresence>
          {isRunning && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="py-6">
                <div className="relative h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mb-4">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-violet-500 to-primary rounded-full"
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2.8, ease: 'easeInOut' }}
                  />
                </div>
                <div className="flex items-center justify-center gap-3">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                    className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent"
                  />
                  <p className="text-sm text-slate-500">Modeling scenario outcomes...</p>
                </div>
                <div className="mt-4 space-y-2">
                  {['Sales forecasting', 'Revenue projection', 'Margin analysis', 'Inventory depletion'].map((step, i) => (
                    <motion.div
                      key={step}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.5 }}
                      className="flex items-center gap-2 text-xs text-slate-500"
                    >
                      <motion.span
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ delay: i * 0.5, duration: 0.5 }}
                        className="w-1.5 h-1.5 rounded-full bg-primary"
                      />
                      {step}
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {(showResults || isComplete) && !isRunning && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(results).map(([key, data], i) => {
                  const Icon = metricIcons[key] || TrendingUp
                  const isNegative = !data.positive
                  return (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, scale: 0.85, y: 10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      transition={{ delay: i * 0.12, type: 'spring', stiffness: 300 }}
                      className={`p-3 rounded-xl border ${
                        data.isStockout
                          ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800'
                          : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {data.isStockout ? (
                          <AlertTriangle size={14} className="text-amber-500" />
                        ) : (
                          <Icon size={14} className="text-slate-400" />
                        )}
                        <span className="text-[10px] text-slate-500 font-medium">{metricLabels[key]}</span>
                      </div>
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 + i * 0.1 }}
                        className={`text-lg font-bold ${isNegative ? 'text-danger' : 'text-success'}`}
                      >
                        {data.value}
                      </motion.p>
                    </motion.div>
                  )
                })}
              </div>

              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="p-4 rounded-xl bg-primary/5 border border-primary/20"
              >
                <div className="flex items-start gap-2">
                  <Sparkles size={16} className="text-primary mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-primary mb-1">AI Recommendation</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{simulationDefaults.recommendation}</p>
                  </div>
                </div>
              </motion.div>

              {isComplete && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-center"
                >
                  <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
                    Dashboard, inventory, and decision history updated live
                  </p>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  )
}
