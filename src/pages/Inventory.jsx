import { AlertTriangle, PackageX, PackagePlus, RefreshCw, Warehouse } from 'lucide-react'
import { motion } from 'framer-motion'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Card from '../components/ui/Card'
import StatusChip from '../components/ui/StatusChip'
import Button from '../components/ui/Button'
import { inventoryData, formatCurrency, formatNumber } from '../data/mockData'

function HeatmapCell({ value }) {
  const intensity = value / 100
  const bg = value >= 80 ? `rgba(34, 197, 94, ${intensity * 0.6})`
    : value >= 50 ? `rgba(245, 158, 11, ${intensity * 0.6})`
    : `rgba(239, 68, 68, ${intensity * 0.6})`

  return (
    <div
      className="w-full aspect-square rounded-md flex items-center justify-center text-[10px] font-medium text-slate-700 dark:text-slate-300"
      style={{ backgroundColor: bg }}
      title={`${value}%`}
    >
      {value}
    </div>
  )
}

export default function Inventory() {
  const { summary, lowStock, deadStock, overstock, reorderSuggestions, warehouses, heatmap } = inventoryData

  return (
    <div>
      <PageHeader
        title="Inventory Health"
        subtitle="Monitor stock levels, turnover, and reorder needs"
        actions={<Button icon={RefreshCw} size="sm">Refresh Data</Button>}
      />

      {/* Summary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Total SKUs" value={summary.totalSKUs} icon={PackagePlus} format="number" delay={0} />
        <KpiCard title="Inventory Value" value={summary.totalValue} icon={Warehouse} delay={0.05} />
        <KpiCard title="Turnover Rate" value={summary.turnoverRate} icon={RefreshCw} format="number" delay={0.1} />
        <KpiCard title="Fill Rate" value={summary.fillRate} icon={PackagePlus} format="percent" delay={0.15} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Low Stock */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-warning" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Low Stock Alerts</h3>
          </div>
          <div className="space-y-3">
            {lowStock.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{item.name}</p>
                  <p className="text-xs text-slate-500">{item.current} units · Reorder at {item.reorder}</p>
                </div>
                <span className="text-xs font-bold text-warning">{item.daysLeft}d left</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Dead Stock */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <PackageX size={16} className="text-danger" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Dead Stock</h3>
          </div>
          <div className="space-y-3">
            {deadStock.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-xl bg-red-50/50 dark:bg-red-950/20 border border-red-100 dark:border-red-900">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{item.name}</p>
                  <p className="text-xs text-slate-500">{item.units} units · {item.daysIdle} days idle</p>
                </div>
                <span className="text-xs font-bold text-danger">{formatCurrency(item.value)}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Overstock */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <PackagePlus size={16} className="text-primary" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Overstock</h3>
          </div>
          <div className="space-y-3">
            {overstock.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-xl bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{item.name}</p>
                  <p className="text-xs text-slate-500">{item.current} current · {item.optimal} optimal</p>
                </div>
                <span className="text-xs font-bold text-primary">+{item.excess} excess</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Reorder + Warehouses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Reorder Suggestions</h3>
          <div className="space-y-3">
            {reorderSuggestions.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-slate-700">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{item.name}</p>
                  <p className="text-xs text-slate-500">Order {item.qty} units · {formatCurrency(item.cost)}</p>
                </div>
                <StatusChip status={item.urgency} label={item.urgency} />
              </div>
            ))}
          </div>
          <Button className="w-full mt-4" size="sm">Approve All Reorders</Button>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Warehouse Summary</h3>
          <div className="space-y-4">
            {warehouses.map((wh) => (
              <div key={wh.name}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-slate-900 dark:text-white">{wh.name}</span>
                  <span className="text-xs text-slate-500">{wh.skus} SKUs · {formatCurrency(wh.value)}</span>
                </div>
                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${wh.capacity}%` }}
                    transition={{ duration: 0.8 }}
                    className={`h-full rounded-full ${wh.capacity > 80 ? 'bg-warning' : 'bg-primary'}`}
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">{wh.capacity}% capacity</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Heatmap */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Inventory Heatmap</h3>
        <p className="text-xs text-slate-500 mb-4">Stock health by category over 8 weeks (percentage of optimal levels)</p>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="text-left text-xs font-medium text-slate-500 pb-2 pr-4">Category</th>
                {['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8'].map((w) => (
                  <th key={w} className="text-center text-xs font-medium text-slate-500 pb-2 px-1">{w}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heatmap.map((row) => (
                <tr key={row.category}>
                  <td className="text-sm font-medium text-slate-700 dark:text-slate-300 py-1.5 pr-4 whitespace-nowrap">{row.category}</td>
                  {['w1', 'w2', 'w3', 'w4', 'w5', 'w6', 'w7', 'w8'].map((w) => (
                    <td key={w} className="p-0.5"><HeatmapCell value={row[w]} /></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-4 mt-4 text-[10px] text-slate-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-400/60" /> Healthy (&gt;80%)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-400/60" /> Warning (50-80%)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-400/60" /> Critical (&lt;50%)</span>
        </div>
      </Card>
    </div>
  )
}
