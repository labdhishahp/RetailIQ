import { Megaphone, DollarSign, Eye, TrendingUp } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import ChartCard from '../components/charts/ChartCard'
import BarChartComponent from '../components/charts/BarChartComponent'
import { campaigns, campaignPerformance, formatCurrency, formatNumber } from '../data/mockData'

export default function CampaignAnalytics() {
  const activeCampaigns = campaigns.filter((c) => c.status === 'active')
  const totalBudget = campaigns.reduce((s, c) => s + c.budget, 0)
  const totalSpent = campaigns.reduce((s, c) => s + c.spent, 0)
  const avgROI = campaigns.filter((c) => c.roi > 0).reduce((s, c, _, arr) => s + c.roi / arr.length, 0)

  return (
    <div>
      <PageHeader title="Campaign Analytics" subtitle="Monitor marketing performance and ROI" />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Active Campaigns" value={activeCampaigns.length} icon={Megaphone} format="number" delay={0} />
        <KpiCard title="Total Budget" value={totalBudget} icon={DollarSign} delay={0.05} />
        <KpiCard title="Total Spent" value={totalSpent} icon={Eye} delay={0.1} />
        <KpiCard title="Avg ROI" value={avgROI.toFixed(1)} icon={TrendingUp} format="number" delay={0.15} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2">
          <ChartCard title="Channel Performance" subtitle="Spend vs revenue by channel">
            <BarChartComponent data={campaignPerformance} dataKey="revenue" xKey="channel" height={280} />
          </ChartCard>
        </div>

        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">ROI by Channel</h3>
          <div className="space-y-4">
            {campaignPerformance.map((ch) => (
              <div key={ch.channel}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-slate-900 dark:text-white">{ch.channel}</span>
                  <span className={`text-sm font-bold ${ch.roi >= 3 ? 'text-success' : ch.roi >= 2 ? 'text-warning' : 'text-danger'}`}>
                    {ch.roi}x
                  </span>
                </div>
                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${ch.roi >= 3 ? 'bg-success' : ch.roi >= 2 ? 'bg-warning' : 'bg-danger'}`}
                    style={{ width: `${Math.min(ch.roi * 20, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{formatCurrency(ch.spend)} spent · {formatCurrency(ch.revenue)} revenue</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Campaign List */}
      <Card className="!p-0 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">All Campaigns</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                {['Campaign', 'Status', 'Budget', 'Spent', 'ROI', 'Impressions', 'Conversions', 'Period'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900 dark:text-white">{c.name}</p>
                    <p className="text-xs text-slate-400">{c.id}</p>
                  </td>
                  <td className="px-4 py-3"><StatusChip status={c.status} /></td>
                  <td className="px-4 py-3">{formatCurrency(c.budget)}</td>
                  <td className="px-4 py-3">
                    <span>{formatCurrency(c.spent)}</span>
                    {c.budget > 0 && (
                      <div className="w-16 h-1 bg-slate-200 dark:bg-slate-700 rounded-full mt-1">
                        <div className="h-full bg-primary rounded-full" style={{ width: `${(c.spent / c.budget) * 100}%` }} />
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${c.roi >= 3 ? 'text-success' : c.roi >= 2 ? 'text-warning' : c.roi > 0 ? 'text-danger' : 'text-slate-400'}`}>
                      {c.roi > 0 ? `${c.roi}x` : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">{c.impressions > 0 ? formatNumber(c.impressions) : '—'}</td>
                  <td className="px-4 py-3">{c.conversions > 0 ? formatNumber(c.conversions) : '—'}</td>
                  <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{c.startDate} → {c.endDate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
