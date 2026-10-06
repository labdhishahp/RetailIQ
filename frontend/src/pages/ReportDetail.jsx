import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Target, ListChecks, FileSearch, BookOpen } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import StatusChip from '../components/ui/StatusChip'
import ChartCard from '../components/charts/ChartCard'
import LineChartComponent from '../components/charts/LineChartComponent'
import BarChartComponent from '../components/charts/BarChartComponent'
import PieChartComponent from '../components/charts/PieChartComponent'
import AgentCard from '../components/copilot/AgentCard'
import { getReportDetail, downloadReport } from '../api/retail'
import { useDemo } from '../context/DemoContext'
import { formatCurrency } from '../data/mockData'

// Series colours only; every value plotted comes from the report payload.
const LINE_COLORS = ['#2563EB', '#22C55E', '#F59E0B']

const formatDate = (iso) => (iso ? new Date(iso).toLocaleString() : '—')

function ReportChart({ chart }) {
  let body
  if (chart.type === 'line') {
    body = (
      <LineChartComponent
        data={chart.data} xKey={chart.xKey}
        lines={chart.lines.map((l, i) => ({ ...l, color: LINE_COLORS[i % LINE_COLORS.length] }))}
      />
    )
  } else if (chart.type === 'bar') {
    body = <BarChartComponent data={chart.data} xKey={chart.xKey} dataKey={chart.dataKey} format={chart.format} />
  } else if (chart.type === 'pie') {
    body = <PieChartComponent data={chart.data} />
  } else {
    return null
  }
  return (
    <ChartCard title={chart.title} subtitle={chart.subtitle}>
      {body}
      <p className="mt-2 text-[10px] font-mono text-faint">Source: {chart.source}</p>
    </ChartCard>
  )
}

export default function ReportDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { pushToast } = useDemo()
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let live = true
    getReportDetail(id)
      .then((r) => { if (live) setReport(r) })
      .catch((err) => { if (live) setError(err.message) })
    return () => { live = false }
  }, [id])

  const handleDownload = async (fmt) => {
    try {
      await downloadReport(report.id, report.code, fmt)
    } catch (err) {
      pushToast({ title: 'Download failed', message: err.message, type: 'error' })
    }
  }

  const back = (
    <Button variant="secondary" size="sm" icon={ArrowLeft} onClick={() => navigate('/reports')}>
      Reports
    </Button>
  )

  if (error) {
    return (
      <div>
        <PageHeader title="Report" actions={back} />
        <Card><p className="text-sm text-danger">{error}</p></Card>
      </div>
    )
  }
  if (!report) {
    return (
      <div>
        <PageHeader title="Report" subtitle="Loading…" actions={back} />
      </div>
    )
  }

  const p = report.payload || {}
  const isDecision = report.kind === 'decision'
  const summary = p.summary || {}
  const recommendation = p.recommendation || {}
  const trace = p.trace || {}

  return (
    <div>
      <PageHeader
        title={report.title}
        subtitle={`${report.code} · ${report.kind}`}
        actions={
          <div className="flex gap-2">
            {back}
            <Button variant="secondary" size="sm" icon={Download}
              disabled={report.status !== 'ready'} onClick={() => handleDownload('csv')}>CSV</Button>
            <Button variant="secondary" size="sm" icon={Download}
              disabled={report.status !== 'ready'} onClick={() => handleDownload('json')}>JSON</Button>
            {isDecision && (
              <Button size="sm" icon={Download}
                disabled={report.status !== 'ready'} onClick={() => handleDownload('pdf')}>Download PDF</Button>
            )}
          </div>
        }
      />

      {!isDecision && (
        <Card><p className="text-sm text-body">{report.summary}</p></Card>
      )}

      {isDecision && (
        <div className="space-y-6">
          <Card>
            <p className="text-xs font-semibold uppercase tracking-wider text-faint mb-1">Question</p>
            <p className="text-sm font-medium text-slate-900 dark:text-white mb-4">{p.question}</p>
            <p className="text-xs font-semibold uppercase tracking-wider text-faint mb-1">Root cause</p>
            <p className="text-sm text-body mb-4">{summary.rootCause}</p>
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
              {summary.riskLevel && <StatusChip status={summary.riskLevel} label={`${summary.riskLevel} risk`} />}
              {summary.confidence != null && <span>Confidence {summary.confidence}%</span>}
              {summary.revenueImpact != null && <span>Revenue impact {formatCurrency(summary.revenueImpact)}</span>}
              {summary.synthesis && <span>Synthesis: {summary.synthesis}</span>}
            </div>
            {summary.businessImpact && <p className="text-xs text-muted mt-3">{summary.businessImpact}</p>}
            {summary.inventoryImpact && <p className="text-xs text-muted mt-1">{summary.inventoryImpact}</p>}
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <Target size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Recommendation</h3>
              </div>
              <p className="text-sm text-body mb-3">{recommendation.action}</p>
              <ol className="list-decimal ml-5 space-y-1 text-xs text-body">
                {(recommendation.nextSteps || []).map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <ListChecks size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Evidence</h3>
              </div>
              <ul className="list-disc ml-5 space-y-1 text-xs text-body">
                {(p.evidence || []).map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </Card>
          </div>

          {(p.charts || []).length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {p.charts.map((c) => <ReportChart key={c.id} chart={c} />)}
            </div>
          )}

          <Card>
            <div className="flex items-center gap-2 mb-1">
              <FileSearch size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Agent investigation trace</h3>
            </div>
            <p className="text-xs text-muted mb-3">
              Mode: {trace.mode ?? '—'} · {trace.delegations ?? 0} delegations · {trace.toolCalls ?? 0} tool calls
              {trace.fallback ? ` · fallback: ${trace.fallback}` : ''}
            </p>
            {(trace.decisions || []).length > 0 && (
              <ul className="mb-4 space-y-1 text-xs text-body">
                {trace.decisions.map((d, i) => (
                  <li key={i}>
                    <span className="font-mono text-faint">R{d.round}</span>{' '}
                    <span className="font-medium">{d.agent}</span>
                    {d.focus ? ` (${d.focus})` : ''} — {d.reason}
                  </li>
                ))}
              </ul>
            )}
            <div className="space-y-2">
              {(p.agents || []).map((a, i) => (
                <AgentCard key={a.id || i} agent={a} status="complete" progress={100} index={i} />
              ))}
            </div>
          </Card>

          {(p.citations || []).length > 0 && (
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Policy and context sources</h3>
              </div>
              <ul className="space-y-2 text-xs text-body">
                {p.citations.map((c, i) => (
                  <li key={i}><span className="font-medium">{c.title}</span> ({c.doc_type}): {c.excerpt?.slice(0, 200)}…</li>
                ))}
              </ul>
            </Card>
          )}

          <p className="text-[11px] text-faint">
            Investigated {formatDate(p.source?.investigated_at)} · Charts computed {formatDate(p.generated_at)} from
            data as of {formatDate(p.data_as_of)}
          </p>
        </div>
      )}
    </div>
  )
}
