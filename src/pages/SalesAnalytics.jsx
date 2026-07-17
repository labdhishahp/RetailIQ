import { useState } from 'react'
import { DollarSign, TrendingUp, ShoppingCart, BarChart3 } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import ChartCard from '../components/charts/ChartCard'
import RevenueTrendChart from '../components/charts/RevenueTrendChart'
import BarChartComponent from '../components/charts/BarChartComponent'
import PieChartComponent from '../components/charts/PieChartComponent'
import LineChartComponent from '../components/charts/LineChartComponent'
import {
  salesAnalytics, storeComparison, categorySales, kpiData, formatCurrency, formatPercent,
} from '../data/mockData'

const tabs = [
  { id: 'daily', label: 'Daily' },
  { id: 'weekly', label: 'Weekly' },
  { id: 'monthly', label: 'Monthly' },
]

export default function SalesAnalytics() {
  const [period, setPeriod] = useState('daily')
  const data = salesAnalytics[period]

  const totalRevenue = period === 'daily'
    ? data.reduce((s, d) => s + d.revenue, 0)
    : period === 'weekly'
    ? data.reduce((s, d) => s + d.revenue, 0)
    : kpiData.revenue.value

  return (
    <div>
      <PageHeader title="Sales Analytics" subtitle="Deep dive into revenue, profit, and growth metrics" />

      {/* Period Tabs */}
      <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl w-fit mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setPeriod(tab.id)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              period === tab.id
                ? 'bg-white dark:bg-slate-900 text-primary shadow-sm'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Revenue" value={totalRevenue} change={kpiData.revenue.change} trend="up" icon={DollarSign} delay={0} />
        <KpiCard title="Profit" value={kpiData.profit.value} change={kpiData.profit.change} trend="down" icon={TrendingUp} delay={0.05} />
        <KpiCard title="Orders" value={kpiData.orders.value} change={kpiData.orders.change} trend="up" icon={ShoppingCart} format="number" delay={0.1} />
        <KpiCard title="Growth Rate" value={12.4} change={2.1} trend="up" icon={BarChart3} format="percent" delay={0.15} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <ChartCard title={`${period.charAt(0).toUpperCase() + period.slice(1)} Revenue & Profit`} subtitle="Performance over selected period">
          {period === 'monthly' ? (
            <RevenueTrendChart data={data} />
          ) : (
            <LineChartComponent
              data={data}
              xKey={period === 'daily' ? 'day' : 'week'}
              lines={[
                { key: 'revenue', color: '#2563EB', name: 'Revenue' },
                { key: 'profit', color: '#22C55E', name: 'Profit' },
              ]}
              height={300}
            />
          )}
        </ChartCard>

        <ChartCard title="Store Comparison" subtitle="Revenue by location">
          <BarChartComponent data={storeComparison} dataKey="revenue" xKey="store" height={300} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Top Categories" subtitle="Revenue distribution by category">
          <PieChartComponent data={categorySales} height={300} />
        </ChartCard>

        <ChartCard title="Sales Growth" subtitle="Growth rate by store">
          <div className="space-y-4 pt-2">
            {storeComparison.map((store) => (
              <div key={store.store}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-slate-900 dark:text-white">{store.store}</span>
                  <span className={`text-sm font-bold ${store.growth >= 10 ? 'text-success' : 'text-warning'}`}>
                    {formatPercent(store.growth)}
                  </span>
                </div>
                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-700"
                    style={{ width: `${Math.min(store.growth * 4, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{formatCurrency(store.revenue)} · {store.orders.toLocaleString()} orders</p>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
