import { CheckCircle2, XCircle, Clock, TrendingUp, MessageSquare } from 'lucide-react'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import KpiCard from '../components/ui/KpiCard'
import { decisionHistory } from '../data/mockData'

const statusIcons = {
  accepted: CheckCircle2,
  rejected: XCircle,
  pending: Clock,
}

const statusColors = {
  accepted: 'text-success border-success/30 bg-success/5',
  rejected: 'text-danger border-danger/30 bg-danger/5',
  pending: 'text-warning border-warning/30 bg-warning/5',
}

export default function DecisionHistory() {
  const accepted = decisionHistory.filter((d) => d.status === 'accepted').length
  const totalROI = decisionHistory.filter((d) => d.roi).reduce((s, d) => s + d.roi, 0)

  return (
    <div>
      <PageHeader title="Decision History" subtitle="Track AI recommendations and their outcomes" />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <KpiCard title="Total Decisions" value={decisionHistory.length} icon={MessageSquare} format="number" delay={0} />
        <KpiCard title="Accepted" value={accepted} icon={CheckCircle2} format="number" delay={0.05} />
        <KpiCard title="Total ROI" value={totalROI} icon={TrendingUp} format="number" delay={0.1} />
      </div>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block" />

        <div className="space-y-4">
          {decisionHistory.map((decision, i) => {
            const StatusIcon = statusIcons[decision.status]
            return (
              <motion.div
                key={decision.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="relative sm:pl-14"
              >
                {/* Timeline dot */}
                <div className={`absolute left-4 top-5 w-5 h-5 rounded-full border-2 hidden sm:flex items-center justify-center bg-white dark:bg-slate-900 ${statusColors[decision.status]}`}>
                  <StatusIcon size={10} />
                </div>

                <Card>
                  <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <StatusChip status={decision.status} />
                        <span className="text-xs text-slate-400">{decision.date}</span>
                        <span className="text-xs font-mono text-slate-400">{decision.id}</span>
                      </div>

                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                        "{decision.question}"
                      </h3>

                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 mt-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Recommendation</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300">{decision.recommendation}</p>
                      </div>

                      {decision.outcome && (
                        <div className="mt-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Outcome</p>
                          <p className="text-sm text-slate-600 dark:text-slate-400">{decision.outcome}</p>
                        </div>
                      )}
                    </div>

                    <div className="flex sm:flex-col gap-3 sm:items-end sm:text-right flex-shrink-0">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Impact</p>
                        <p className="text-sm font-bold text-primary">{decision.impact}</p>
                      </div>
                      {decision.roi !== null && (
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">ROI</p>
                          <p className="text-sm font-bold text-success">{decision.roi}%</p>
                        </div>
                      )}
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Confidence</p>
                        <p className="text-sm font-bold text-slate-900 dark:text-white">{decision.confidence}%</p>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
