import { useState } from 'react'
import { FileText, Download, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import Button from '../components/ui/Button'
import { useDemo } from '../context/DemoContext'

function GeneratingAnimation() {
  return (
    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 mb-4 flex-1">
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full"
          />
          Generating AI summary...
        </div>
        <div className="space-y-2">
          {[0.9, 0.7, 0.5].map((width, i) => (
            <motion.div
              key={i}
              initial={{ width: 0, opacity: 0.3 }}
              animate={{ width: `${width * 100}%`, opacity: [0.3, 0.6, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
              className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full"
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Reports() {
  const { reports, addNotification } = useDemo()
  const [generating, setGenerating] = useState(false)

  const handleGenerate = () => {
    setGenerating(true)
    addNotification({
      title: 'Report Generation Started',
      message: 'Compiling executive summary from live business data...',
      time: 'Just now',
      type: 'info',
    })
    setTimeout(() => {
      setGenerating(false)
      addNotification({
        title: 'Report Generated',
        message: 'Weekly Executive Summary has been updated',
        time: 'Just now',
        type: 'success',
      })
    }, 4000)
  }

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Executive summaries and AI-generated insights"
        actions={
          <Button icon={FileText} size="sm" onClick={handleGenerate} disabled={generating}>
            {generating ? 'Generating...' : 'Generate Report'}
          </Button>
        }
      />

      <AnimatePresence>
        {generating && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-6 p-4 rounded-2xl bg-primary/5 border border-primary/20"
          >
            <div className="flex items-center gap-3">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent"
              />
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">Generating executive report...</p>
                <p className="text-xs text-slate-500">Analyzing KPIs, inventory, campaigns, and AI decisions</p>
              </div>
            </div>
            <div className="mt-3 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-primary rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: 4, ease: 'easeInOut' }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <AnimatePresence mode="popLayout">
          {reports.map((report, i) => (
            <motion.div
              key={report.id}
              layout
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: report.isNew ? 0 : i * 0.08 }}
            >
              <Card hover className={`h-full flex flex-col ${report.isNew ? 'ring-2 ring-primary/30' : ''}`}>
                {report.isNew && report.status === 'ready' && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="inline-block mb-2 self-start px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400"
                  >
                    New
                  </motion.span>
                )}
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 rounded-xl bg-primary/10 text-primary">
                    <FileText size={18} />
                  </div>
                  <StatusChip status={report.status} />
                </div>

                <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">{report.title}</h3>
                <p className="text-xs text-slate-500 mb-3">{report.type.charAt(0).toUpperCase() + report.type.slice(1)} · {report.date}</p>

                {report.aiSummary && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="p-3 rounded-xl bg-violet-50/50 dark:bg-violet-950/20 border border-violet-100 dark:border-violet-900 mb-4 flex-1"
                  >
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Sparkles size={12} className="text-violet-500" />
                      <span className="text-[10px] font-semibold text-violet-600 dark:text-violet-400 uppercase tracking-wider">AI Summary</span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{report.aiSummary}</p>
                  </motion.div>
                )}

                {!report.aiSummary && report.status === 'generating' && <GeneratingAnimation />}

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
        </AnimatePresence>
      </div>
    </div>
  )
}
