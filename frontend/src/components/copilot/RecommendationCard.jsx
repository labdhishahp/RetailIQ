import { motion } from 'framer-motion'
import {
  AlertTriangle, Target, TrendingUp, Shield, Package, Megaphone, ListChecks, BarChart3,
  Play, CheckCircle2, BookOpen,
} from 'lucide-react'
import Card from '../ui/Card'
import Button from '../ui/Button'
import StatusChip from '../ui/StatusChip'
import { useDemo } from '../../context/DemoContext'
import { formatCurrency } from '../../data/mockData'

export default function RecommendationCard({ result, simulationPhase }) {
  const { runSimulation } = useDemo()

  if (!result) return null

  const sections = [
    { icon: AlertTriangle, label: 'Root Cause', value: result.rootCause, color: 'text-danger' },
    { icon: BarChart3, label: 'Confidence Score', value: `${result.confidence}%`, color: 'text-primary' },
    { icon: Target, label: 'Business Impact', value: result.businessImpact, color: 'text-warning' },
    { icon: Shield, label: 'Risk Level', value: result.riskLevel, isChip: true },
    { icon: TrendingUp, label: 'Revenue Impact', value: formatCurrency(result.revenueImpact), color: result.revenueImpact < 0 ? 'text-danger' : 'text-success' },
    { icon: Package, label: 'Inventory Impact', value: result.inventoryImpact, color: 'text-slate-600' },
    { icon: Megaphone, label: 'Suggested Campaign', value: result.suggestedCampaign, color: 'text-primary' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="p-2 rounded-xl bg-gradient-to-br from-violet-500 to-primary text-white">
          <Target size={18} />
        </div>
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white">Final Recommendation</h3>
          <p className="text-xs text-slate-500">
            Synthesised from {result.agents?.length ?? 0} agent analyses
            {result.elapsedMs ? ` · ${(result.elapsedMs / 1000).toFixed(1)}s` : ''}
            {result.synthesis ? ` · ${result.synthesis === 'llm' ? 'LLM' : 'rule'} synthesis` : ''}
          </p>
        </div>
        <div className="ml-auto">
          <StatusChip status={result.priority} label={`${result.priority} Priority`} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map((section, i) => (
          <motion.div
            key={section.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <Card className="!p-4">
              <div className="flex items-start gap-3">
                <section.icon size={16} className={`mt-0.5 flex-shrink-0 ${section.color}`} />
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{section.label}</p>
                  {section.isChip ? (
                    <StatusChip status={section.value} label={section.value} />
                  ) : (
                    <p className={`text-sm mt-1 ${section.color || 'text-slate-700 dark:text-slate-300'}`}>{section.value}</p>
                  )}
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card className="!p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-3">Evidence</p>
        <ul className="space-y-2">
          {result.evidence.map((item, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.06 }}
              className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
              {item}
            </motion.li>
          ))}
        </ul>
      </Card>

      {result.citations?.length > 0 && (
        <Card className="!p-4">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={16} className="text-violet-500" />
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Retrieved sources
            </p>
          </div>
          <div className="space-y-2">
            {result.citations.map((c, i) => (
              <div key={`${c.chunk_id}-${i}`} className="p-2.5 rounded-xl bg-violet-50/50 dark:bg-violet-950/20 border border-violet-100 dark:border-violet-900">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">{c.title}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300">
                    {c.doc_type}
                  </span>
                  {c.similarity != null && (
                    <span className="text-[10px] text-slate-400 ml-auto">match {(c.similarity * 100).toFixed(0)}%</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-1 leading-snug">{c.excerpt?.slice(0, 220)}…</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="!p-4">
        <div className="flex items-center gap-2 mb-3">
          <ListChecks size={16} className="text-primary" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Next Steps</p>
        </div>
        <ol className="space-y-2">
          {result.nextSteps.map((step, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + i * 0.06 }}
              className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-400"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                {i + 1}
              </span>
              {step}
            </motion.li>
          ))}
        </ol>
      </Card>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <Card className="!p-5 bg-gradient-to-br from-violet-50 to-primary/5 dark:from-violet-950/30 dark:to-primary/10 border-primary/20">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Ready to validate this recommendation?</p>
              <p className="text-xs text-slate-500 mt-1">
                Run a what-if simulation to project sales, revenue, profit, and inventory impact across the business.
              </p>
            </div>
            {simulationPhase === 'complete' ? (
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
              >
                <CheckCircle2 size={18} />
                <span className="text-sm font-semibold">Simulation Applied</span>
              </motion.div>
            ) : (
              <Button
                onClick={runSimulation}
                disabled={simulationPhase === 'running'}
                icon={Play}
                className="whitespace-nowrap"
              >
                {simulationPhase === 'running' ? 'Running Simulation...' : 'Run Simulation'}
              </Button>
            )}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
