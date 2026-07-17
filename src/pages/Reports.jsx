import { FileText, Download, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import Button from '../components/ui/Button'
import { reports } from '../data/mockData'

export default function Reports() {
  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Executive summaries and AI-generated insights"
        actions={
          <Button icon={FileText} size="sm">Generate Report</Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {reports.map((report, i) => (
          <motion.div
            key={report.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <Card hover className="h-full flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <FileText size={18} />
                </div>
                <StatusChip status={report.status} />
              </div>

              <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">{report.title}</h3>
              <p className="text-xs text-slate-500 mb-3">{report.type.charAt(0).toUpperCase() + report.type.slice(1)} · {report.date}</p>

              {report.aiSummary && (
                <div className="p-3 rounded-xl bg-violet-50/50 dark:bg-violet-950/20 border border-violet-100 dark:border-violet-900 mb-4 flex-1">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Sparkles size={12} className="text-violet-500" />
                    <span className="text-[10px] font-semibold text-violet-600 dark:text-violet-400 uppercase tracking-wider">AI Summary</span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{report.aiSummary}</p>
                </div>
              )}

              {!report.aiSummary && report.status === 'generating' && (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 mb-4 flex-1 flex items-center justify-center">
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    Generating AI summary...
                  </div>
                </div>
              )}

              <div className="flex gap-2 mt-auto">
                <Button variant="secondary" icon={Download} size="sm" className="flex-1" disabled={report.status !== 'ready'}>
                  PDF
                </Button>
                <Button variant="secondary" icon={Download} size="sm" className="flex-1" disabled={report.status !== 'ready'}>
                  Excel
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
