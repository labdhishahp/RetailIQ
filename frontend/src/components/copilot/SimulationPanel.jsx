import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, Play, TrendingUp, TrendingDown, AlertTriangle, RotateCcw } from 'lucide-react'
import Card from '../ui/Card'
import Button from '../ui/Button'
import { useDemo } from '../../context/DemoContext'
import { formatCurrency } from '../../data/mockData'

const CATEGORIES = [
  'Personal Care', 'Electronics', 'Groceries', 'Apparel', 'Home & Living', 'Sports & Outdoors',
]

export default function SimulationPanel() {
  const { runSimulation, simulationPhase, simulationResult } = useDemo()
  const [category, setCategory] = useState('Personal Care')
  const [discount, setDiscount] = useState(15)
  const [duration, setDuration] = useState(28)
  const [spend, setSpend] = useState(0)
  const [error, setError] = useState('')

  const running = simulationPhase === 'running'
  const results = simulationResult?.results

  const launch = async () => {
    setError('')
    try {
      await runSimulation({
        name: `${category} ${discount}% promotion`,
        discount_pct: Number(discount),
        duration_days: Number(duration),
        category,
        extra_spend: Number(spend) || 0,
      })
    } catch (err) {
      setError(err.message || 'Simulation failed')
    }
  }

  return (
    <Card className="!p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 rounded-xl bg-violet-100 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400">
          <FlaskConical size={16} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">What-if Simulation</h3>
          <p className="text-xs text-slate-500">Modelled on real sales elasticity</p>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <label htmlFor="sim-category" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Category
          </label>
          <select
            id="sim-category" value={category} onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div>
          <label htmlFor="sim-discount" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Discount — {discount}%
          </label>
          <input
            id="sim-discount" type="range" min="0" max="50" step="5"
            value={discount} onChange={(e) => setDiscount(e.target.value)}
            className="w-full accent-primary"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="sim-duration" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Duration (days)
            </label>
            <input
              id="sim-duration" type="number" min="1" max="365" value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label htmlFor="sim-spend" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Extra spend
            </label>
            <input
              id="sim-spend" type="number" min="0" step="500" value={spend}
              onChange={(e) => setSpend(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <Button onClick={launch} disabled={running} icon={running ? RotateCcw : Play} className="w-full justify-center">
          {running ? 'Running…' : 'Run simulation'}
        </Button>

        {error && (
          <p role="alert" className="text-xs text-danger">{error}</p>
        )}
      </div>

      <AnimatePresence>
        {results && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800"
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Projected impact
            </p>
            <div className="grid grid-cols-2 gap-2 mb-3">
              {['sales', 'revenue', 'profit'].map((key) => {
                const m = results[key]
                const Icon = m.positive ? TrendingUp : TrendingDown
                return (
                  <div key={key} className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60">
                    <p className="text-[10px] uppercase tracking-wider text-slate-400">{key}</p>
                    <div className={`flex items-center gap-1 mt-0.5 ${m.positive ? 'text-success' : 'text-danger'}`}>
                      <Icon size={13} />
                      <span className="text-sm font-bold">{m.value}</span>
                    </div>
                  </div>
                )
              })}
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60">
                <p className="text-[10px] uppercase tracking-wider text-slate-400">Inventory</p>
                <div className={`flex items-center gap-1 mt-0.5 ${results.inventory.isStockout ? 'text-danger' : 'text-success'}`}>
                  {results.inventory.isStockout && <AlertTriangle size={13} />}
                  <span className="text-xs font-bold">{results.inventory.value}</span>
                </div>
              </div>
            </div>

            {results.totals && (
              <div className="text-xs text-slate-500 space-y-1 mb-3">
                <div className="flex justify-between">
                  <span>Baseline revenue</span>
                  <span className="font-medium">{formatCurrency(results.totals.baseline_revenue)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Projected revenue</span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {formatCurrency(results.totals.projected_revenue)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Projected margin</span>
                  <span className={`font-medium ${results.totals.projected_margin < 0 ? 'text-danger' : ''}`}>
                    {formatCurrency(results.totals.projected_margin)}
                  </span>
                </div>
              </div>
            )}

            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed p-3 rounded-xl bg-violet-50/50 dark:bg-violet-950/20">
              {simulationResult.summary}
            </p>

            {results.products?.length > 0 && (
              <div className="mt-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Per product
                </p>
                <div className="space-y-1">
                  {results.products.slice(0, 5).map((p) => (
                    <div key={p.sku} className="flex items-center justify-between text-xs">
                      <span className="text-slate-600 dark:text-slate-400 truncate mr-2">{p.name}</span>
                      <span className="text-slate-400 whitespace-nowrap">
                        e={p.elasticity} · {p.unit_uplift_pct > 0 ? '+' : ''}{p.unit_uplift_pct}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}
